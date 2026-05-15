"""
Integration test: Backend SSE Event Stream.

Validates end-to-end flow:
  1. Health check
  2. SSE connection
  3. Trigger audit
  4. Collect all events
  5. Validate structure, state transitions, completeness

Usage:
  cd /home/rio/Documents/PEMALI
  python3 backend/test_sse_integration.py
"""

import asyncio
import json
import sys
import time
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("[FAIL] httpx not installed. Run: pip install httpx")
    sys.exit(1)

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT = 120
SSE_TIMEOUT = 300

PASS = 0
FAIL = 0
EVENTS_RECEIVED: list[dict] = []


def log(msg: str, ok: bool = True):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✓ {msg}")
    else:
        FAIL += 1
        print(f"  ✗ {msg}")


def check(label: str, condition: bool, detail: str = ""):
    if condition:
        log(label)
    else:
        log(f"{label} — {detail}", False)


# ──────────────────────────────────────────────
# 1. Health check
# ──────────────────────────────────────────────
async def step_health(client: httpx.AsyncClient) -> bool:
    print("\n[1] Health check")
    try:
        r = await client.get("/api/status", timeout=5)
        data = r.json()
        check("GET /api/status → 200", r.status_code == 200, f"got {r.status_code}")
        check("fastapi_active == true", data.get("fastapi_active") is True, str(data))
        if "modules_loaded" in data:
            check(f"modules_loaded = {data['modules_loaded']}", True)
        return r.status_code == 200
    except Exception as e:
        log(f"GET /api/status failed: {e}", False)
        return False


# ──────────────────────────────────────────────
# 2. SSE connection — stream events in background
# ──────────────────────────────────────────────
async def step_sse(client: httpx.AsyncClient) -> asyncio.Task:
    print("\n[2] SSE connection")
    sse_done = asyncio.Event()

    async def stream():
        try:
            async with client.stream("GET", "/api/telemetry", timeout=httpx.Timeout(SSE_TIMEOUT, connect=10)) as resp:
                if resp.status_code != 200:
                    log(f"SSE returned {resp.status_code}", False)
                    sse_done.set()
                    return
                log(f"SSE connected (200 OK)", True)
                async for line in resp.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            evt = json.loads(line[6:])
                            EVENTS_RECEIVED.append(evt)
                        except json.JSONDecodeError:
                            pass
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log(f"SSE stream error: {e}", False)
        finally:
            sse_done.set()

    task = asyncio.create_task(stream())
    await asyncio.sleep(0.5)
    return task, sse_done


# ──────────────────────────────────────────────
# 3. Trigger audit
# ──────────────────────────────────────────────
async def step_trigger(client: httpx.AsyncClient) -> str | None:
    print("\n[3] Trigger audit")
    payload = {"prompt": "Cek kondisi lingkungan di Ubud Bali untuk deforestasi."}
    try:
        r = await client.post("/api/trigger", json=payload, timeout=10)
        data = r.json()
        check("POST /api/trigger → 200", r.status_code == 200, f"got {r.status_code}")
        check("status == queued", data.get("status") == "queued", str(data))
        sid = data.get("session_id")
        check("session_id present", bool(sid), str(data))
        return sid
    except Exception as e:
        log(f"Trigger failed: {e}", False)
        return None


# ──────────────────────────────────────────────
# 4. Wait for events
# ──────────────────────────────────────────────
async def step_wait(sse_task: asyncio.Task, sse_done: asyncio.Event, timeout: int = TIMEOUT):
    print(f"\n[4] Collecting events (timeout: {timeout}s)")
    deadline = time.monotonic() + timeout
    last_event_count = 0

    while time.monotonic() < deadline:
        await asyncio.sleep(1)
        delta = len(EVENTS_RECEIVED) - last_event_count
        if delta:
            print(f"     {len(EVENTS_RECEIVED)} events received (+{delta})")
            last_event_count = len(EVENTS_RECEIVED)

        for evt in EVENTS_RECEIVED:
            if (
                evt.get("node_type") == "Manager"
                and evt.get("state") == "DONE"
            ):
                print(f"     Manager DONE received. Audit complete.")
                sse_task.cancel()
                try:
                    await sse_task
                except (asyncio.CancelledError, Exception):
                    pass
                return True

    sse_task.cancel()
    try:
        await sse_task
    except (asyncio.CancelledError, Exception):
        pass
    print(f"     Timeout ({timeout}s). {len(EVENTS_RECEIVED)} events.")
    return len(EVENTS_RECEIVED) > 0


# ──────────────────────────────────────────────
# 5. Validate events
# ──────────────────────────────────────────────
def step_validate():
    print(f"\n[5] Validate events ({len(EVENTS_RECEIVED)} total)")

    if not EVENTS_RECEIVED:
        log("No events received", False)
        return

    # Each event must have required fields
    required_fields = ["trace_id", "node_id", "node_type", "state", "narrative", "timestamp"]
    valid_node_types = {"Manager", "SubAgent", "Module"}
    valid_states = {"IDLE", "THINKING", "SPAWNING", "EXECUTING", "DONE", "ERROR"}

    for i, evt in enumerate(EVENTS_RECEIVED):
        evt_id = f"event[{i}] ({evt.get('node_id','?')}/{evt.get('state','?')})"

        # Required fields
        for field in required_fields:
            if field not in evt:
                log(f"{evt_id} missing field '{field}'", False)
                break
        else:
            # Validate enums
            nt = evt.get("node_type")
            if nt not in valid_node_types:
                log(f"{evt_id} invalid node_type '{nt}'", False)

            st = evt.get("state")
            if st not in valid_states:
                log(f"{evt_id} invalid state '{st}'", False)

        # Metadata if present
        meta = evt.get("metadata")
        if meta:
            if not isinstance(meta, dict):
                log(f"{evt_id} metadata not a dict", False)
            else:
                dur = meta.get("duration_ms")
                if dur is not None and (not isinstance(dur, (int, float)) or dur < 0):
                    log(f"{evt_id} invalid duration_ms={dur}", False)

    # Check required event types
    node_types_seen = {e.get("node_type") for e in EVENTS_RECEIVED}
    check("Manager events present", "Manager" in node_types_seen)
    if "SubAgent" not in node_types_seen:
        print(f"     ⚠ No SubAgent events (LLM may have responded directly)")


    # Check state transitions
    manager_events = [e for e in EVENTS_RECEIVED if e.get("node_type") == "Manager"]
    manager_states = [e.get("state") for e in manager_events]

    check("Manager THINKING seen", "THINKING" in manager_states)
    check("Manager DONE seen", "DONE" in manager_states)

    # Check narrative is not empty
    empty_narratives = [e for e in EVENTS_RECEIVED if not e.get("narrative")]
    check(f"No empty narratives (0 = clean)", len(empty_narratives) == 0, f"{len(empty_narratives)} empty")

    # Check timestamp is plausible
    now_ts = int(time.time())
    bad_ts = [e for e in EVENTS_RECEIVED if not isinstance(e.get("timestamp"), int) or abs(e["timestamp"] - now_ts) > 86400]
    check("Timestamps are valid", len(bad_ts) == 0, f"{len(bad_ts)} bad timestamps")

    # Check trace_id is consistent
    trace_ids = {e.get("trace_id") for e in EVENTS_RECEIVED if e.get("trace_id")}
    if trace_ids:
        check(f"Consistent trace_id ({len(trace_ids)} unique)", len(trace_ids) <= 2, str(trace_ids))

    # Module events should have SubAgent parent
    module_events = [e for e in EVENTS_RECEIVED if e.get("node_type") == "Module"]
    subagent_ids = {
        e.get("node_id") for e in EVENTS_RECEIVED if e.get("node_type") == "SubAgent"
    }
    if module_events and not subagent_ids:
        log("Module events without SubAgent parent", False)

    # Narratives should be descriptive (not just hardcoded patterns)
    llm_narratives = [e for e in EVENTS_RECEIVED if e.get("node_type") in ("SubAgent", "Module") and e.get("state") == "EXECUTING"]
    if llm_narratives:
        has_llm_text = any(len(e.get("narrative", "")) > 40 for e in llm_narratives)
        check("LLM narrative used ( >40 chars)", has_llm_text)


# ──────────────────────────────────────────────
# 6. Print summary report
# ──────────────────────────────────────────────
def print_report(session_id: str | None, duration: float):
    print(f"\n{'═' * 60}")
    print("  INTEGRATION TEST REPORT")
    print(f"{'═' * 60}")
    print(f"  Session ID : {session_id or 'N/A'}")
    print(f"  Duration   : {duration:.1f}s")
    print(f"  Events     : {len(EVENTS_RECEIVED)}")
    print(f"  Pass       : {PASS}")
    print(f"  Fail       : {FAIL}")

    if EVENTS_RECEIVED:
        print(f"\n  Event Timeline:")
        print(f"  {'─' * 60}")
        for evt in EVENTS_RECEIVED:
            ts = evt.get("timestamp", 0)
            nt = evt.get("node_type", "?")
            nid = evt.get("node_id", "?")
            st = evt.get("state", "?")
            nar = evt.get("narrative", "")[:60]
            print(f"  {nt:8s} | {nid:20s} | {st:10s} | {nar}")

    print(f"\n  {'═' * 60}")
    if FAIL == 0:
        print(f"  STATUS: ✅ ALL PASSED")
    else:
        print(f"  STATUS: ❌ {FAIL} FAILURES")
    print(f"{'═' * 60}\n")


# ──────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────
async def main():
    print(f"{'═' * 60}")
    print("  PEMALI — SSE Integration Test")
    print(f"  Target  : {BASE_URL}")
    print(f"  Timeout : {TIMEOUT}s")
    print(f"{'═' * 60}")
    print("  Make sure the backend is running:")
    print("    uvicorn backend.main:app --host 127.0.0.1 --port 8000")
    print(f"{'═' * 60}")

    start = time.monotonic()

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=TIMEOUT) as client:
        # 1. Health
        if not await step_health(client):
            print("\n⚠ Backend not reachable. Start it and retry.")
            sys.exit(1)

        # 2. SSE
        sse_task, sse_done = await step_sse(client)

        # 3. Trigger
        session_id = await step_trigger(client)

        # 4. Wait
        await step_wait(sse_task, sse_done)

    duration = time.monotonic() - start

    # 5. Validate
    step_validate()

    # 6. Report
    print_report(session_id, duration)

    sys.exit(0 if FAIL == 0 else 1)


if __name__ == "__main__":
    asyncio.run(main())
