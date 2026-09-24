"""Audited, read-only source media import into a fresh v3 job.

The copied Flow journals remain byte-for-byte source evidence. Imported module
payloads point at those copies and carry new-job input versions; they never
claim that a new Flow request was submitted. Quality decisions are not copied.
"""
import copy
import shutil
import time
from pathlib import PurePosixPath

from pilot import Blocked, digest, hashobj, read, write


class ImportProducer:
    """The only producer accepted by Pilot.run for an imported media revision."""
    def __init__(self, receipt_path, part, build):
        self.receipt_path = receipt_path
        self.part = part
        self.build = build

    def __call__(self, out):
        return self.build(out)


def _safe_rel(value):
    path = PurePosixPath(value)
    if not value or path.is_absolute() or '..' in path.parts or str(path) != value:
        raise Blocked('IMPORT_PATH: unsafe source artifact path')
    return value


def _narration(content):
    return [(s['id'], s['narration'], s.get('narration_en')) for s in content['scenes']]


def _envelope(p, source, module, row):
    if row['state'] != 'approved' or not row['envelope']:
        raise Blocked(f'IMPORT_SOURCE: {module} must have a technical acceptance')
    envelope = read(p.path(source, row['envelope']))
    if (envelope.get('job_id') != source or envelope.get('module') != module
            or envelope.get('revision') != row['revision']
            or p.snapshot_hash(source, envelope) != row['hash']):
        raise Blocked(f'IMPORT_SOURCE: {module} envelope or source files changed')
    return envelope


def _audit_source(p, source, parts):
    import workflow
    import image_pipeline
    cfg = workflow.settings(p, source)
    if cfg['mode'] != 'auto' or not workflow.approved(p, source, 'content'):
        raise Blocked('IMPORT_SOURCE: source content needs a genuine auto decision')
    rows = p.rows(source)
    content = _envelope(p, source, 'content', rows['content'])
    envelopes = {'content': (rows['content']['envelope'], rows['content']['hash'], content)}
    audited_files = set()
    if 'audio' in parts:
        audio = _envelope(p, source, 'audio', rows['audio'])
        if audio['input_versions'].get('content') != rows['content']['hash']:
            raise Blocked('IMPORT_SOURCE: audio was not made from source content')
        if audio['payload'].get('import_receipt'):
            raise Blocked('IMPORT_SOURCE: chained media imports are not supported')
        audited_files.update(p.checks(source, 'audio', audio['payload']))
        envelopes['audio'] = (rows['audio']['envelope'], rows['audio']['hash'], audio)
    if 'images' in parts:
        if rows['images']['state'] != 'approved':
            raise Blocked('IMPORT_SOURCE: final images need technical acceptance')
        refs = image_pipeline.approved(p, source, 'references')
        final = image_pipeline.approved(p, source, 'final')
        if not refs or not final or final['payload'].get('import_receipt'):
            raise Blocked('IMPORT_SOURCE: reference/final checkpoint or native Flow evidence missing')
        if (final['revision'] != rows['images']['revision']
                or p.snapshot_hash(source, final) != rows['images']['hash']
                or final['input_versions'].get('content') != rows['content']['hash']):
            raise Blocked('IMPORT_SOURCE: final image revision changed')
        audited_files.update(p.checks(source, 'images', refs['payload']))
        audited_files.update(p.checks(source, 'images', final['payload']))
        for stage, envelope in [('references', refs), ('final', final)]:
            with p._db_lock:
                row = p.db.execute(
                    'SELECT envelope,hash,signature FROM image_reviews '
                    'WHERE job=? AND checkpoint=? AND revision=?',
                    (source, stage, envelope['revision'])).fetchone()
            if (not row or row['hash'] != p.snapshot_hash(source, envelope)
                    or row['signature'] != envelope['payload']['signature']):
                raise Blocked('IMPORT_SOURCE: image checkpoint record changed')
            envelopes['images_' + stage] = (row['envelope'], row['hash'], envelope)
        selected = [*refs['payload']['references'], *final['payload']['items']]
        targets = set()
        for item in selected:
            request = read(p.path(source, item['request']))
            if request.get('state') != 'downloaded' or request.get('sha256') != item['sha256']:
                raise Blocked('IMPORT_SOURCE: missing or ambiguous downloaded image')
            targets.add(request['identity']['target'])
            for ref in item['references']:
                reg = read(p.path(source, ref['registration_journal']))
                confirmation = read(p.path(source, ref['confirmation']))
                if reg.get('state') != 'downloaded' or reg.get('sha256') != ref['registration_hash']:
                    raise Blocked('IMPORT_SOURCE: registration was not downloaded')
                if (confirmation.get('matches_approved_reference') is not True
                        or confirmation.get('observer') != 'machine'
                        or not confirmation.get('report')
                        or not p.path(source, confirmation['report']).is_file()):
                    raise Blocked('IMPORT_SOURCE: machine registration comparison missing')
                targets.add(reg['identity']['target'])
        for path in (p.job(source) / 'flow/attempts').glob('*/request.json'):
            request = read(path)
            if request['identity']['target'] in targets and request['state'] in ('submitted', 'ambiguous'):
                raise Blocked('IMPORT_SOURCE: unresolved Flow request for selected media')
    return envelopes, sorted(audited_files)


def _source_files(p, source, envelopes, audited_files):
    import workflow
    paths = {'workflow.json', 'integrity.json', 'brief-current.json'}
    brief = p.brief(source)
    paths.add(f'briefs/{brief[1]}.json')
    current = workflow.current(p, source, 'content')
    paths.update([current['review'], current['decision'],
                  f"reviews/content/{current['revision']}/manifest.json"])
    decision = read(p.path(source, current['decision']))
    if decision.get('report'):
        paths.add(decision['report'])
    for rel, _, envelope in envelopes.values():
        paths.add(rel)
        paths.update(envelope['files'])
    paths.update(audited_files)
    if 'images_final' in envelopes:
        final = envelopes['images_final'][2]['payload']
        for item in final['items']:
            for ref in item['references']:
                confirmation = read(p.path(source, ref['confirmation']))
                if confirmation.get('report'):
                    paths.add(confirmation['report'])
    for rel in paths:
        if not p.path(source, _safe_rel(rel)).is_file():
            raise Blocked('IMPORT_SOURCE: missing artifact ' + rel)
    return sorted(paths)


def _source_decision(p, source):
    import workflow
    manifest = workflow.current(p, source, 'content')
    if not manifest:
        raise Blocked('IMPORT_SOURCE: content manifest is not current')
    decision = read(p.path(source, manifest['decision']))
    stamp = hashobj(decision)
    if (decision.get('approved') is not True or decision.get('actor') != 'machine'
            or decision.get('manifest_hash') != hashobj(manifest)
            or not decision.get('report')
            or digest(p.path(source, decision['report'])) != decision.get('report_hash')):
        raise Blocked('IMPORT_SOURCE: content machine decision is invalid')
    with p._db_lock:
        row = p.db.execute(
            "SELECT id,detail FROM events WHERE job=? AND module='content' "
            "AND event='machine_approved' AND detail=? ORDER BY id LIMIT 1",
            (source, stamp)).fetchone()
    if not row:
        raise Blocked('IMPORT_SOURCE: content approval event is missing')
    return {'manifest': f"reviews/content/{manifest['revision']}/manifest.json",
            'decision': manifest['decision'], 'event_id': row['id'],
            'event_hash': row['detail'], 'report': decision['report']}


def _mapped(receipt, source_rel):
    return f"{receipt['prefix']}/source/{_safe_rel(source_rel)}"


def _map_audio(source_payload, receipt, receipt_path):
    result = copy.deepcopy(source_payload)
    result['wav'] = _mapped(receipt, result['wav'])
    result['srt'] = _mapped(receipt, result['srt'])
    for segment in result['segments']:
        segment['path'] = _mapped(receipt, segment['path'])
    if result.get('en'):
        result['en']['wav'] = _mapped(receipt, result['en']['wav'])
        for scene in result['en']['scenes']:
            scene['path'] = _mapped(receipt, scene['path'])
    result['import_receipt'] = receipt_path
    result['import_kind'] = 'source-copy'
    return result


def _map_refs(p, source, references, receipt, archive_job=None):
    result = copy.deepcopy(references)
    for ref in result:
        journal = (_mapped(receipt, ref['registration_journal']) if archive_job
                   else ref['registration_journal'])
        original = read(p.path(archive_job or source, journal))
        ref['registration_image'] = _mapped(receipt, original['path'])
        confirmation = (_mapped(receipt, ref['confirmation']) if archive_job
                        else ref['confirmation'])
        report = read(p.path(archive_job or source, confirmation)).get('report')
        if report:
            ref['registration_report'] = _mapped(receipt, report)
        ref['registration_journal'] = _mapped(receipt, ref['registration_journal'])
        ref['confirmation'] = _mapped(receipt, ref['confirmation'])
    return result


def _map_images(p, source, source_payload, receipt, receipt_path, content_hash, signature,
                archive_job=None):
    result = copy.deepcopy(source_payload)
    result['content_hash'] = content_hash
    result['signature'] = signature
    result['contact_sheet'] = _mapped(receipt, result['contact_sheet'])
    for item in result['references'] + result['items']:
        item['path'] = _mapped(receipt, item['path'])
        item['request'] = _mapped(receipt, item['request'])
        item['references'] = _map_refs(p, source, item['references'], receipt, archive_job)
    result['import_receipt'] = receipt_path
    result['import_kind'] = 'source-copy'
    return result


def verify_receipt(p, job, relative, part):
    """Verify every copied source byte and source envelope without source writes."""
    receipt = read(p.path(job, relative))
    prefix = receipt.get('prefix', '')
    if (receipt.get('schema') != 'vp-media-import-1' or receipt.get('destination_job') != job
            or part not in receipt.get('parts', []) or not relative.startswith(prefix + '/')
            or len(PurePosixPath(_safe_rel(prefix)).parts) != 3
            or PurePosixPath(prefix).parts[:2] != ('imports', receipt.get('source_job'))
            or not receipt.get('files') or not receipt.get('source_envelopes')):
        raise Blocked('IMPORT_RECEIPT: invalid receipt or part')
    p.job(receipt['source_job'])
    files = [relative]
    for mapped, stamp in receipt['files'].items():
        if not mapped.startswith(receipt['prefix'] + '/source/'):
            raise Blocked('IMPORT_RECEIPT: copied source path escaped archive')
        path = p.path(job, mapped)
        if not path.is_file() or digest(path) != stamp:
            raise Blocked('IMPORT_RECEIPT: copied source file changed: ' + mapped)
        files.append(mapped)
    for source_rel in receipt.get('audited_files', []):
        if _mapped(receipt, source_rel) not in receipt['files']:
            raise Blocked('IMPORT_RECEIPT: audited evidence omitted')
    for name, entry in receipt['source_envelopes'].items():
        source_rel = entry['path']
        mapped = _mapped(receipt, source_rel)
        envelope = read(p.path(job, mapped))
        for rel in envelope['files']:
            if _mapped(receipt, rel) not in receipt['files']:
                raise Blocked('IMPORT_RECEIPT: source envelope file omitted: ' + name)
        if (envelope.get('job_id') != receipt['source_job']
                or envelope.get('module') != name.split('_')[0]
                or hashobj({'envelope': envelope, 'files': {
                    rel: digest(p.path(job, _mapped(receipt, rel))) for rel in envelope['files']
                }}) != entry['hash']):
            raise Blocked('IMPORT_RECEIPT: source envelope changed: ' + name)
    attestation = receipt.get('source_content_decision') or {}
    manifest = read(p.path(job, _mapped(receipt, attestation.get('manifest', ''))))
    decision = read(p.path(job, _mapped(receipt, attestation.get('decision', ''))))
    source_content = read(p.path(job, _mapped(receipt, receipt['source_envelopes']['content']['path'])))
    source_workflow = read(p.path(job, _mapped(receipt, 'workflow.json')))
    if (decision.get('approved') is not True or decision.get('actor') != 'machine'
            or decision.get('manifest_hash') != hashobj(manifest)
            or manifest.get('snapshot', {}).get('settings') != hashobj(source_workflow)
            or manifest.get('snapshot', {}).get('modules', {}).get('content') != {
                'revision': source_content['revision'],
                'hash': receipt['source_envelopes']['content']['hash']}
            or hashobj(decision) != attestation.get('event_hash')
            or decision.get('report') != attestation.get('report')
            or digest(p.path(job, _mapped(receipt, decision['report']))) != decision.get('report_hash')):
        raise Blocked('IMPORT_RECEIPT: source content decision differs')
    with p._db_lock:
        row = p.db.execute(
            "SELECT detail FROM events WHERE id=? AND job=? AND module='content' "
            "AND event='machine_approved'",
            (attestation.get('event_id'), receipt['source_job'])).fetchone()
    if not row or row['detail'] != attestation['event_hash']:
        raise Blocked('IMPORT_RECEIPT: source approval event differs')
    content = p.payload(job, 'content')
    if receipt['brief_hash'] != hashobj(p.brief(job)[0]):
        raise Blocked('IMPORT_RECEIPT: destination brief differs')
    if part == 'audio' and receipt['narration_hash'] != hashobj(_narration(content)):
        raise Blocked('IMPORT_RECEIPT: narration differs')
    if part == 'images' and receipt['content_payload_hash'] != hashobj(content):
        raise Blocked('IMPORT_RECEIPT: image plan differs')
    return {'receipt': receipt, 'files': files}


def check_imported_audio(p, job, payload):
    info = verify_receipt(p, job, payload['import_receipt'], 'audio')
    receipt = info['receipt']
    source = read(p.path(job, _mapped(receipt, receipt['source_envelopes']['audio']['path'])))['payload']
    if payload != _map_audio(source, receipt, payload['import_receipt']):
        raise Blocked('IMPORT_AUDIO: payload differs from audited source')
    return info['files']


def check_imported_images(p, job, payload):
    import image_pipeline
    from scripts.story_plan import image_units
    from PIL import Image
    info = verify_receipt(p, job, payload['import_receipt'], 'images')
    receipt = info['receipt']
    stage = payload['checkpoint']
    key = 'images_' + stage
    if key not in receipt['source_envelopes']:
        raise Blocked('IMPORT_IMAGES: source checkpoint missing')
    source = read(p.path(job, _mapped(receipt, receipt['source_envelopes'][key]['path'])))['payload']
    expected = _map_images(p, receipt['source_job'], source, receipt, payload['import_receipt'],
                           p.rows(job)['content']['hash'], image_pipeline.signature(p, job, stage),
                           archive_job=job)
    if payload != expected:
        raise Blocked('IMPORT_IMAGES: payload differs from audited source')
    content = p.payload(job, 'content')
    if [ref['character_id'] for ref in payload['references']] != [c['id'] for c in content['characters']]:
        raise Blocked('IMPORT_IMAGES: character references differ')
    units = [] if stage == 'references' else image_pipeline.planned_units(p, job)
    if [x.get('image_id', x['scene_id']) for x in payload['items']] != [x.get('image_id', x['id']) for x in units]:
        raise Blocked('IMPORT_IMAGES: image plan order differs')
    if stage == 'final':
        approved = image_pipeline.approved(p, job, 'references')
        if not approved or approved['payload']['references'] != payload['references']:
            raise Blocked('IMPORT_IMAGES: reference checkpoint missing')
    for item in payload['references'] + payload['items']:
        if digest(p.path(job, item['path'])) != item['sha256']:
            raise Blocked('IMPORT_IMAGES: image bytes changed')
        with Image.open(p.path(job, item['path'])) as im:
            im.verify()
        request = read(p.path(job, item['request']))
        if (request.get('state') != 'downloaded' or request.get('sha256') != item['sha256']
                or request['identity']['prompt'] != item['prompt']
                or request['identity']['actual_prompt'] != item['actual_prompt']):
            raise Blocked('IMPORT_IMAGES: downloaded request evidence differs')
        for ref in item['references']:
            registration = read(p.path(job, ref['registration_journal']))
            confirmation = read(p.path(job, ref['confirmation']))
            if (registration.get('state') != 'downloaded'
                    or registration.get('sha256') != ref['registration_hash']
                    or digest(p.path(job, ref['registration_image'])) != ref['registration_hash']
                    or confirmation.get('result_hash') != ref['registration_hash']
                    or confirmation.get('reference_hash') != ref['sha256']
                    or confirmation.get('matches_approved_reference') is not True
                    or confirmation.get('observer') != 'machine'
                    or not confirmation.get('report')
                    or (confirmation.get('report') and ref.get('registration_report') !=
                        _mapped(receipt, confirmation['report']))):
                raise Blocked('IMPORT_IMAGES: character registration evidence differs')
    return info['files']


def import_media(p, job, source, part='all'):
    """Create fresh technical revisions, never a source quality decision."""
    import workflow
    import image_pipeline
    if part not in ('audio', 'images', 'all') or job == source:
        raise Blocked('IMPORT_MEDIA: choose audio, images, or all from another job')
    p.refresh(job)
    destination_mode = workflow.settings(p, job)['mode']
    if destination_mode != 'auto' or not workflow.approved(p, job, 'content'):
        raise Blocked('IMPORT_MEDIA: destination content needs a fresh auto decision')
    selected = ['audio', 'images'] if part == 'all' else [part]
    rows = p.rows(job)
    if any(rows[module]['state'] != 'pending' or rows[module]['revision'] != 0 for module in selected):
        raise Blocked('IMPORT_MEDIA: selected destination modules must be untouched')
    source_brief = p.brief(source)[0]
    destination_brief = p.brief(job)[0]
    if source_brief != destination_brief:
        raise Blocked('IMPORT_MEDIA: briefs differ')
    source_content = p.payload(source, 'content')
    destination_content = p.payload(job, 'content')
    if 'audio' in selected and _narration(source_content) != _narration(destination_content):
        raise Blocked('IMPORT_MEDIA: narration differs')
    if 'images' in selected and source_content != destination_content:
        raise Blocked('IMPORT_MEDIA: image plans differ; import audio only or regenerate images')
    envelopes, audited_files = _audit_source(p, source, selected)
    attestation = _source_decision(p, source)
    paths = _source_files(p, source, envelopes, audited_files)
    prefix = f'imports/{source}/{part}-{time.time_ns()}'
    receipt_path = prefix + '/receipt.json'
    receipt = {'schema': 'vp-media-import-1', 'source_job': source,
               'destination_job': job, 'parts': selected, 'prefix': prefix,
               'created_at': time.time(), 'brief_hash': hashobj(destination_brief),
               'narration_hash': hashobj(_narration(destination_content)),
               'content_payload_hash': hashobj(destination_content),
               'source_content_decision': attestation,
               'audited_files': audited_files,
               'source_envelopes': {name: {'path': rel, 'hash': stamp}
                                    for name, (rel, stamp, _) in envelopes.items()},
               'files': {}}
    for rel in paths:
        mapped = _mapped(receipt, rel)
        source_path = p.path(source, rel)
        destination_path = p.path(job, mapped)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        if destination_path.exists():
            raise Blocked('IMPORT_MEDIA: destination archive collision')
        shutil.copyfile(source_path, destination_path)
        source_hash = digest(source_path)
        if digest(destination_path) != source_hash:
            raise Blocked('IMPORT_MEDIA: copied artifact differs')
        receipt['files'][mapped] = source_hash
    write(p.path(job, receipt_path), receipt)
    verify_receipt(p, job, receipt_path, selected[0])
    if 'audio' in selected:
        source_audio = envelopes['audio'][2]['payload']
        p.run(job, 'audio', producer=ImportProducer(receipt_path, 'audio',
              lambda out: _map_audio(source_audio, receipt, receipt_path)))
        workflow.accept_module(p, job, 'audio')
    if 'images' in selected:
        for stage in ('references', 'final'):
            source_images = envelopes['images_' + stage][2]['payload']
            def imported(out, s=source_images, checkpoint=stage):
                return _map_images(p, source, s, receipt, receipt_path,
                                   p.rows(job)['content']['hash'], image_pipeline.signature(p, job, checkpoint))
            p.run(job, 'images', producer=ImportProducer(receipt_path, 'images', imported))
            workflow.accept_module(p, job, 'images')
    if all(p.rows(job)[m]['state'] == 'approved' for m in ('audio', 'images')):
        workflow.prepare(p, job, 'media')
    result = workflow.status(p, job)
    result['import_receipt'] = str(p.path(job, receipt_path))
    return result
