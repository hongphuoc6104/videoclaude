"""Python bridge for B-2 Illustrator session communication over Unix domain socket."""
import json
import os
import socket
import time
from pathlib import Path
from pilot import Blocked, digest

ROOT = Path(__file__).resolve().parent
SOCKET_PATH = ROOT / "experiments/b2_illustrator/results/controller/session.sock"


def get_socket_path() -> Path:
    return SOCKET_PATH


def is_session_available() -> bool:
    if not SOCKET_PATH.exists():
        return False
    try:
        res = query_status()
        return res.get("status") == "connected"
    except Exception:
        return False


def not_submitted(message: str) -> Blocked:
    """A failure before any command reached the session, so nothing was sent to Flow and the caller may submit again."""
    error = Blocked(message)
    error.generation_submitted = False
    return error


def send_raw_command(command: str, timeout: float = 120.0) -> dict:
    if not SOCKET_PATH.exists():
        raise not_submitted(
            f"B-2 Illustrator session socket not found at {SOCKET_PATH}. "
            "Ensure b2-session service is running (e.g. systemctl --user start b2-session.service)."
        )
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(timeout)
    try:
        client.connect(str(SOCKET_PATH))
    except OSError as exc:
        client.close()
        raise not_submitted(f"B-2 Illustrator session socket refused the connection: {exc}")
    try:
        payload = (command.strip() + "\n").encode("utf-8")
        client.sendall(payload)
        
        response_chunks = []
        while True:
            chunk = client.recv(4096)
            if not chunk:
                break
            response_chunks.append(chunk)
            if b"\n" in chunk:
                break
        
        response_text = b"".join(response_chunks).decode("utf-8").strip()
        if not response_text:
            raise Blocked("Empty response from B-2 Illustrator session socket")
        return json.loads(response_text)
    except socket.timeout:
        raise Blocked(f"B-2 Illustrator session command timed out after {timeout}s: {command[:50]}")
    except (json.JSONDecodeError, OSError) as exc:
        raise Blocked(f"B-2 Illustrator session communication error: {exc}")
    finally:
        client.close()


def query_status() -> dict:
    return send_raw_command("status", timeout=5.0)


def ensure_connected() -> dict:
    """Runs before every submission, so any failure here means nothing was sent to Flow."""
    try:
        status = query_status()
        if status.get("status") == "connected":
            return status
        result = send_raw_command("connect", timeout=75.0)
    except Blocked as ex:
        if getattr(ex, "generation_submitted", True) is False:
            raise
        raise not_submitted(f"B-2 session check failed before submission: {ex}") from ex
    if result.get("status") != "connected":
        raise not_submitted(f"B-2 connection blocked: {result.get('reason', 'not connected')}")
    return result


CANONICAL_GUIDANCE = (
    " Strict Stickman CH01 canonical anatomy: exactly ONE single torso wearing plain light ocean blue shirt #8CCFE8, "
    "exactly two simple navy stick arms, two simple navy stick legs, round white head with dark navy contour, "
    "two solid black vertical oval eyes, simple open smile with coral tongue, absolutely NO eyebrows, NO teeth, NO white anime pupils. "
    "Maintain identical camera perspective, framing, and furniture structure from the reference."
)
STYLE_NOTES = {
    "canonical": "Match the attached canonical character and scene references.",
    "story": "Match the attached character reference exactly: same face, age, hair, build and clothes. "
             "Draw any other person only from the prompt text. Keep the scene reference framing if one is attached.",
    "none": "No character reference is attached. Follow the prompt text for every person. "
            "Keep the scene reference framing if one is attached.",
}


def queue_spec(test_case, prompt, ratio, out_dir, *, base_ref_path=None, base_media_id=None,
               char_ref_path=None, char_media_id=None, canonical=False, no_character=False,
               preserve="", change="", literal_text=""):
    """One queue request. Exactly one of: the canonical mascot, a story character's own reference, or none."""
    if no_character == bool(char_ref_path):
        raise Blocked("CHARACTER_REFERENCE_REQUIRED: attach one character reference or declare no_character")
    kind = "none" if no_character else ("canonical" if canonical else "story")
    if kind == "canonical" and "Stickman CH01" not in prompt:
        prompt = prompt + "\n" + CANONICAL_GUIDANCE
    return {
        "testCase": test_case,
        "testName": f"Pipeline B-2 Generation: {test_case}",
        "prompt": prompt,
        "styleNote": STYLE_NOTES[kind],
        "preserve": preserve,
        "change": change,
        "literalText": literal_text,
        "ratio": ratio,
        "outDir": str(Path(out_dir).resolve()),
        "baseRefPath": str(Path(base_ref_path).resolve()) if base_ref_path else None,
        "characterRefPath": str(Path(char_ref_path).resolve()) if char_ref_path else None,
        "baseMediaId": base_media_id,
        "charMediaId": char_media_id,
        "noCharacter": bool(no_character),
    }


def generate_b2_image(
    prompt: str,
    ratio: str = "16:9",
    base_ref_path: str | Path | None = None,
    char_ref_path: str | Path | None = None,
    base_media_id: str | None = None,
    char_media_id: str | None = None,
    canonical: bool = False,
    no_character: bool = False,
    preserve: str = "",
    change: str = "",
    literal_text: str = "",
    out_dir: str | Path | None = None,
    test_case: str = "SCENE",
    timeout: float = 120.0
) -> dict:
    """Generate image via B-2 Illustrator applet and harvest committed result.

    The caller decides the character reference; there is no mascot fallback,
    because a story character drawn from the mascot reference becomes a stickman.
    """
    require_queue_acceptance()
    ensure_connected()

    target_dir = Path(out_dir).resolve() if out_dir else (ROOT / "experiments/b2_illustrator/results/controller").resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    spec = queue_spec(test_case, prompt, ratio, target_dir, base_ref_path=base_ref_path, base_media_id=base_media_id,
                      char_ref_path=char_ref_path, char_media_id=char_media_id, canonical=canonical,
                      no_character=no_character, preserve=preserve, change=change, literal_text=literal_text)

    spec_file = target_dir / f".spec-{test_case}-{int(time.time() * 1000)}.json"
    spec_file.write_text(json.dumps(spec, indent=2), encoding="utf-8")

    item = generate_b2_batch([spec], timeout=timeout)[0]
    if item.get("failed"):
        error = Blocked(item["failed"])  # sent to Flow: unknown, unless Flow answered with no image
        if item["failed"].startswith("FLOW_NO_MEDIA"):
            error.outcome = "no_media"
        if item.get("not_submitted"):
            error.generation_submitted = False  # journal proves no image exists for this request: may be sent again
        raise error
    return item


# Queue failures whose journal proves no image exists for the request, so a later call may send it again:
# never dispatched (FLOW_NOT_SUBMITTED), or every profile answered "out of quota" with no image (FLOW_QUOTA_NO_MEDIA).
RETRY_SAFE = ("FLOW_NOT_SUBMITTED", "FLOW_QUOTA_NO_MEDIA")


def record_profile_switches(specs: list[dict], switches: list[dict]) -> None:
    """Keep the queue's profile switches next to the run's own batch records, so each switch is auditable there too."""
    if not switches:
        return
    folder = Path(specs[0]["outDir"]).parent
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / "profile-switches.json"
    earlier = json.loads(log.read_text(encoding="utf-8")) if log.is_file() else []
    log.write_text(json.dumps(earlier + switches, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_b2_batch(specs: list[dict], timeout: float = 240.0) -> list[dict]:
    """Submit immutable groups through the persistent queue UI adapter."""
    require_queue_acceptance()
    ensure_connected()
    if not 1 <= len(specs) <= 4:
        raise Blocked("B-2 queue requires one to four independent requests")
    folder = ROOT / "experiments/b2_illustrator/results/controller"
    folder.mkdir(parents=True, exist_ok=True)
    import uuid
    manifest = folder / f"queue-{uuid.uuid4().hex}.json"
    manifest.write_text(json.dumps(specs, ensure_ascii=False, indent=2), encoding="utf-8")
    result = send_raw_command(f"tool-snapshot:queue:{manifest}", timeout=max(timeout, 240))
    if result.get("status") == "blocked":
        error = Blocked(result.get("reason", "B-2 queue blocked"))
        error.generation_submitted = result.get("generationSubmitted", True)
        raise error
    items = result.get("items", [])
    if len(items) != len(specs):
        raise Blocked("B-2 incomplete batch; reconcile before retry")
    # One entry per spec, in order. A request Flow did not return is {"failed": reason}; the others stand.
    reasons = {x["index"]: x["reason"] for x in result.get("failures", [])}
    record_profile_switches(specs, result.get("profileSwitches", []))
    out = []
    for i, (spec, item) in enumerate(zip(specs, items)):
        if item is None:
            reason = reasons.get(i, "B-2 request unresolved; reconcile before retry")
            out.append({"failed": reason, "request_id": spec["testCase"],
                        **({"not_submitted": True} if reason.startswith(RETRY_SAFE) else {})})
            continue
        if item.get("request_id") != spec["testCase"] or not Path(item["path"]).is_file():
            raise Blocked("B-2 result mapping failed")
        item["sha256"] = digest(Path(item["path"]))
        out.append(item)
    return out


def require_queue_acceptance():
    record = json.loads((ROOT / "experiments/b2_illustrator/acceptance.json").read_text())
    config = json.loads((ROOT / "config.json").read_text())
    if record.get("production_ready") is not True and config.get("flow_queue_trial_enabled") is not True:
        raise Blocked("B2_QUEUE_NOT_ACCEPTED: see docs/flow-queue-operations.md; production remains blocked")
