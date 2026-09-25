# Flow queue: tool storage limit and profile rotation on quota — 2026-09-24

Scope: `sys/experiments/b2_illustrator/` plus two small retry-safe hooks in `sys/b2_bridge.py` and
`sys/image_pipeline.py`. No generation was submitted, no account was signed in, no profile was switched live,
nothing was committed.

## 1. Storage limit

### Root cause (measured)

- Chrome's localStorage quota for the tool iframe origin is 5,242,880 UTF-16 chars (10 MiB). Evidence:
  run of 2026-09-23 13:47Z held 22 images. The saved result base64 in the journals adds up to 5,083,568 chars.
  With the configs included, docs/flow-queue-operations.md records 5,166,163 chars. The 23rd item, REQ-D8N1P,
  ended `UNKNOWN` with "Persistence failure after result". The session-inspect snapshot
  `results/controller/session-inspect-1790171647216.json` shows it together with "LATCH: BLOCKED".
- Per-image size from the 93 journals: mean 164–231 K chars per run, and the largest was 327,132 chars.
  Request config is ≤ 5.3 K. The backup `tool-state/1790180097605.json` holds 17 items at 2,789,441 chars
  (≈164 K per image).
- One correction to the stated premise: `executeQueue` never receives a whole wave. `adapters.gflow('batch')`
  splits every wave into groups of ≤ 4, and each group is a separate session command
  (`prepareRequests` refuses more than 4). The 22-image overflow happened in runs from before commit 3c08f2f,
  which had no compaction at all. After 3c08f2f, the 16:12Z run compacted once and finished 25/25. The fixed
  2.5 M threshold still left these weaknesses:
  1. It measured only `VP_LAB_STATE_V2`, not the whole origin.
  2. The fixed threshold ignored image size.
  3. When compaction was blocked, the run stopped even though there was room left.
  4. Latent bug: `noMedia()` returned true for "Persistence failure after result", because the item has an
     error and no media. Python would then have made its one "no-media retry" and generated the same image
     again, which is a duplicate spend. That image had in fact been generated.
  5. Polling copied the full multi-MB state over CDP every 500 ms.

### Design

I kept the existing compaction semantics and made the decision budget-based. `queue-runner.mjs` works as follows:

- Before each dispatch, it measures the whole origin (all keys). It estimates one image as
  `max(360,000, 1.15 × largest item in the tool)` and computes
  `capacity = floor((0.8 × 5,242,880 − used) / estimate)`. With the real numbers:
  - empty tool: 11
  - 2.79 M (the backup above): 3, so a group of 4 now compacts first
  - 5.17 M: 0
- If the remaining requests do not fit, it compacts first through the unchanged `resetToolState` and
  `toolStateBlockers` rules. If compaction is blocked, it sends only what fits. If nothing fits, it refuses
  before dispatch (`generationSubmitted:false`).
- Groups are sent in storage-sized chunks. After each chunk resolves, its images are written to disk and
  validated (`collected`) straight away, so the next chunk can compact safely. The journal stays the source of
  truth, and a dispatched request is never re-sent.
- Classification changes:
  - "Persistence failure", "QuotaExceededError" and similar are `storage` failures. They are not no-media, they
    block compaction, and they stop the queue.
  - CAPTCHA and sign-in answers are also excluded from no-media.
- Snapshots now carry sizes and flags only. A result's base64 is read once, when the item completes.

I rejected dropping items one by one from localStorage. The tool's React state rewrites the whole value from
memory on its next save, so an external removal would be undone. It could also race a worker writing a result.
Only backup + remove + reload is safe, and that is what `resetToolState` already does.

## 2. Profile rotation on quota

- **Detection** (`profile-rotation.mjs`, `classifyFailure`): case-insensitive patterns, checked in this order:
  captcha → login → storage → quota → rate_limit → other. Storage is checked before quota, so the browser's
  "exceeded the quota" is never read as account quota.
  - **The real Flow quota wording has not been observed.** No saved result, backup, snapshot or doc contains it.
  - The quota list is specific: RESOURCE_EXHAUSTED, quota, daily/usage/generation limit, out of / not enough /
    insufficient credits.
  - Patterns can be extended with `failure_patterns.quota` in `browser-profiles.json` or `machine.local.json`.
  - Only an item with an error **and no mediaId/result** counts. The attempt gets the new journal state
    `failed_no_media`, which requires evidence (queueId, error, classification, profile) and cannot follow
    `generated`.
- **Persistent exhaustion ledger**: `results/controller/profile-exhaustion.json` stores
  `{exhaustedAt, resetAt = next local midnight (or quota_reset_hours), evidence}`. Later runs skip an exhausted
  profile before dispatch. The ledger is also written when rotation is off; in that case the queue stops with
  `FLOW_PROFILE_QUOTA_EXHAUSTED`.
- **Switch** (`session.mjs`, `openProfileTab`):
  1. Refuses a profile directory that does not exist, so Chrome never creates a new signed-out profile.
  2. Runs `google-chrome --user-data-dir=<same dir> --profile-directory=<target> chrome://version/?vp-switch=<nonce>`.
     The running Chrome opens a window in that profile.
  3. Finds that tab by the nonce and checks the profile path and executable, exactly like the first connection.
  4. Opens the profile's `tool_url`.
  5. Stops hard on a sign-in page, a visible reCAPTCHA challenge (the normal badge is ignored) or a tool that is
     not ready.
  6. Never types or signs in, and never closes the previous profile's tab.
- **Which profile is next**: the first entry in `priority` that is not exhausted, not `enabled:false`, and has a
  `tool_url`. The home profile uses `machine.local.json` `tool_url`. When none is left, the queue stops with
  `FLOW_QUOTA_ALL_PROFILES_EXHAUSTED`.
- **Reference media across accounts**: a Flow media id belongs to the account that created it. The journals now
  record the profile on each `submitting` event, which gives each generated media id an owner. Media with no
  recorded owner, such as the mascot or older runs, belong to the home profile. A request goes to profile B only
  if one of these is true:
  - B owns the media
  - B maps it in `profiles[B].media_ids`
  - B declares `reference_media: "shared"`

  Otherwise the request is reported as `FLOW_NOT_SUBMITTED: REFERENCE_MEDIA_NOT_ON_PROFILE`.
- **No duplicates**: only quota-answered, no-image attempts are resent. Each resend is a new attempt, with
  identity plus `resend: n` and at most `priority.length` resends. The original's `failed_no_media` record is the
  proof that nothing was produced. Items that timed out, stayed unknown, hit a storage failure or were answered
  by CAPTCHA/sign-in are never moved. A replay reads the journal chain and sends nothing.
- **Audit trail**:
  - `results/controller/profile-switches.ndjson` (append-only, fsync): events `exhausted`, `switch`,
    `switch_failed`, `all_exhausted`, each with the from/to profile, the request ids and the evidence.
  - Every `submitting` event records `profile` and `toolUrl`, and every result carries `profile`.
  - `b2_bridge` also writes `profile-switches.json` into the run's batch folder.
- **Python**: a failure prefixed `FLOW_NOT_SUBMITTED` or `FLOW_QUOTA_NO_MEDIA` is marked retry-safe.
  `batch_submit` leaves it unjournaled, and the single path records `not_submitted`. So it is never
  `ambiguous` and needs no manual reconcile. `FLOW_NO_MEDIA` keeps its one-retry rule.

## Files changed

- **New**: `experiments/b2_illustrator/profile-rotation.mjs`, `test-profile-rotation.mjs`,
  `test-queue-rotation.mjs`.
- **Changed**:
  - `queue-runner.mjs`: storage budget, driver, chunking, rotation, `noMedia` fix, per-chunk collection
  - `attempt-store.mjs`: `failed_no_media` state and `recordNoMedia`
  - `session.mjs`: `openProfileTab`, `signInOrCaptcha`, switch wiring
  - `controller.mjs`: inspect follows the bound profile and tool URL
  - `browser-operations.mjs`: bound tool URL
  - `browser-profiles.json`
  - `CONTROLLER.md`: short note
  - `sys/b2_bridge.py`, `sys/image_pipeline.py`, `sys/tests/test_character_refs.py`, `sys/tests/test_images_v2.py`

## Tests

- `node --test` in b2_illustrator: **62/62 pass**. There are 20 new tests, all with fakes and no browser:
  - chunking and compaction with real sizes
  - refusal before dispatch
  - quota rotation that moves only the unanswered requests
  - an unknown item that is never moved
  - all profiles exhausted
  - rotation off
  - CAPTCHA and storage hard stops
  - sign-in on switch
  - reference mapping
  - ledger persistence and reset
  - switch verification failures
- `.venv/bin/python -m unittest discover -s tests`: **284 OK** (2 new).
- `unittest discover -s experiments/b2_illustrator`: 4 failures that were already there. They are in
  `test_b2_illustrator.py`, which fails with "model must remain Nano Banana Pro" because
  `experiments/b2_illustrator/config.json` says Nano Banana 2 Lite. I did not change those files.

## Live observation (read-only)

- The user's open Chrome is the default data dir `~/.config/google-chrome` (pid 40343). Its DevToolsActivePort
  is `9222` with `/devtools/browser/277fb055-aca8-4162-98de-67b710c40dcc`. `/json/version` returns 404, but the
  browser WebSocket accepted a connection.
- I attached once with `chromium.connectOverCDP('ws://127.0.0.1:9222/devtools/browser/277fb055-…')`. I only
  listed tabs and read frames: no clicks, no new tabs, no navigation. There was one context and one tab,
  `https://flow.google.com/project/7c815425-…/tool/bc72cb6a-…`, in the Tool/Edit (Tool Builder) view. No frame
  had `VP_LAB_STATE_V2`, so there were no live storage numbers and no limit text.
- The probe process then exited. That dropped my client socket but did not close the browser. **The connection
  is not held open.** A second read-only probe was refused by the permission classifier, and I did not
  re-attach.
- `machine.local.json` points the session at `sys/.gflow/profiles/video-pilot`, but that Chrome is not running:
  its DevToolsActivePort `34975` is stale. The session has to be pointed at the Chrome that actually runs.

## Still needs a live check (with user approval)

1. Restart the session. queue-runner is cached per process, and the session.mjs changes need a new process.
   Then run the read-only `session.mjs tool-snapshot:queue-state` and check `localStorageChars` against the
   estimate.
2. At the first real quota hit on Profile 10, run `queue-state` and copy the exact error into
   `failure_patterns.quota` if it did not match.
3. For each of Profile 102, 13 and 14, the user opens the tool link in that profile and remixes or copies the
   tool. Then:
   - put that profile's `tool_url` in its entry in `machine.local.json` (key `profiles`)
   - register the mascot, then set `media_ids` (`{"de94a39b-155f-4afe-acbb-d9d4b59ad532": "<new id>"}`), or
     confirm with a test that the media is shared
4. One controlled switch test, which spends one image on Profile 102. Write a Profile 10 entry into the ledger
   by hand, send one no-reference image, and confirm:
   - the new window opens in Profile 102
   - the chrome://version check passes
   - the tool loads without sign-in
   - the image is collected
   - `profile-switches.ndjson` records the switch

   Also check that Chrome accepts the `chrome://version/?vp-switch=` command-line URL and that CDP exposes the
   other profile's tab. Neither is proven yet.
5. Run one 8–12 image wave and confirm that a backup appears in `results/controller/tool-state/` and that the
   chunks do not overlap.

## Exact config changes

- Done: `browser-profiles.json` now has `profiles` (notes, `tool_url: null`, `reference_media: "own"`,
  `media_ids: {}`), `failure_patterns.quota: []`, `rotation_note`, and, set last,
  `"automatic_account_switching": true`.
- **Needed**:
  - `machine.local.json` still has `"automatic_account_switching": false`, and it overrides
    browser-profiles.json. Change it to `true`, or remove the key.
  - Add `profiles["Profile 102"|"Profile 13"|"Profile 14"].tool_url` (and `media_ids`, or
    `reference_media: "shared"`). Until then, a quota hit on Profile 10 stops with
    `FLOW_QUOTA_ALL_PROFILES_EXHAUSTED`, which is safe.
  - Point `flow_user_data_dir` at the running Chrome.
  - Optional: `quota_reset_hours`.
- Profile 14 does not exist in `.gflow/profiles/video-pilot`. It is refused as `PROFILE_NOT_FOUND`.
- For the lead: `AGENTS.md` and `docs/flow-queue-operations.md` still say not to switch account/profile
  automatically and that quota stops the queue. They also still describe the fixed 2.5 M compaction.
- The in-progress job `tieng-go-sau-guong-thu-20260924` already fails its integrity baseline, with 25 protected
  files changed (adapters.py, pilot.py and others). These changes add to that list.
