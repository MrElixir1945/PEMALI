import os
import json
import time
import glob
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict

logger = logging.getLogger("PEMALI.SessionLogger")

LOG_DIR = os.path.join(os.path.dirname(__file__), "..", "logs", "sessions")
LOG_DIR = os.path.abspath(LOG_DIR)
MAX_LOG_FILES = 100
WITA = timezone(timedelta(hours=8))


def _ts_to_wita(epoch: float | int) -> str:
    return datetime.fromtimestamp(epoch, tz=WITA).strftime("%Y-%m-%d %H:%M:%S WITA")


def _cleanup_old_logs():
    files = sorted(
        glob.glob(os.path.join(LOG_DIR, "*.log")),
        key=os.path.getmtime,
    )
    while len(files) > MAX_LOG_FILES:
        oldest = files.pop(0)
        try:
            os.remove(oldest)
            logger.info(f"[SessionLogger] Cleanup: removed {os.path.basename(oldest)}")
        except OSError as e:
            logger.warning(f"[SessionLogger] Cleanup failed for {oldest}: {e}")


def _infer_indent(node_type: str) -> str:
    if node_type == "Manager":
        return ""
    elif node_type == "SubAgent":
        return "  "
    elif node_type == "Module":
        return "    "
    return "  "


def _format_header(trace_id: str, session_id: str, prompt: str, started_at: float,
                   ended_at: float, total_events: int) -> str:
    duration = round(ended_at - started_at, 1)
    lines = []
    lines.append("╔" + "═" * 78 + "╗")
    lines.append(f"║  PEMALI AUDIT SESSION LOG".ljust(79) + "║")
    lines.append("╠" + "═" * 78 + "╣")
    lines.append(f"║  Trace:    {trace_id}".ljust(79) + "║")
    lines.append(f"║  Session:  {session_id}".ljust(79) + "║")
    lines.append(f"║  Prompt:   {prompt[:60]}{'...' if len(prompt) > 60 else ''}".ljust(79) + "║")
    lines.append(f"║  Started:  {_ts_to_wita(started_at)}".ljust(79) + "║")
    lines.append(f"║  Ended:    {_ts_to_wita(ended_at)}".ljust(79) + "║")
    lines.append(f"║  Duration: {duration}s  |  {total_events} events".ljust(79) + "║")
    lines.append("╚" + "═" * 78 + "╝")
    return "\n".join(lines)


def _format_event(ev: dict, indent: str = "") -> str:
    node_id = ev.get("node_id", "?")
    state = ev.get("state", "?")
    
    # Format JSON with indent
    json_str = json.dumps(ev, indent=2, ensure_ascii=False)
    indented_json = "\n".join(indent + "    " + line for line in json_str.split("\n"))
    
    return f"{indent}[{node_id}] {state}\n{indented_json}"


def _compute_summary(events: List[dict]) -> dict:
    agents = set()
    agents_done = set()
    agents_error = set()
    tool_calls = 0
    tool_success = 0
    tool_errors = 0
    phases_seen = set()
    VALID_PHASES = {"planning", "execute", "validate", "synthesis", "done"}

    for ev in events:
        ntype = ev.get("node_type", "")
        if ntype == "Manager":
            phase = (ev.get("metadata") or {}).get("phase", "")
            if phase and phase in VALID_PHASES:
                phases_seen.add(phase)
        
        nid = ev.get("node_id", "")
        state = ev.get("state", "")
        
        if ntype == "SubAgent" and nid != "manager":
            agents.add(nid)
            if state == "DONE":
                agents_done.add(nid)
            if state == "ERROR":
                agents_done.discard(nid)
                agents_error.add(nid)
        
        if ntype == "Module":
            if state == "EXECUTING":
                tool_calls += 1
            if state == "DONE":
                meta = ev.get("metadata") or {}
                status = meta.get("status")
                if status == 200 or status == "success":
                    tool_success += 1
                else:
                    tool_errors += 1
            if state == "ERROR":
                tool_errors += 1

    return {
        "agents_spawned": len(agents),
        "agents_success": len(agents_done),
        "agents_failed": len(agents) - len(agents_done),
        "tool_calls": tool_calls,
        "tool_success": tool_success,
        "tool_errors": tool_errors,
        "phases": sorted(phases_seen) if phases_seen else ["planning", "execute", "validate", "synthesis", "done"],
    }


class SessionLogger:
    def __init__(self, trace_id: str, session_id: str, prompt: str):
        self.trace_id = trace_id
        self.session_id = session_id
        self.prompt = prompt
        self.started_at = time.time()
        self.events: List[dict] = []
        os.makedirs(LOG_DIR, exist_ok=True)
        _cleanup_old_logs()

    def add(self, event_data: dict):
        self.events.append(event_data)

    def write(self):
        try:
            ended_at = time.time()
            filepath = os.path.join(LOG_DIR, f"{self.trace_id}.log")
            
            # Group events: first pass to determine current phase
            current_phase = "planning"
            lines = []
            
            lines.append(_format_header(
                self.trace_id, self.session_id, self.prompt,
                self.started_at, ended_at, len(self.events)
            ))
            lines.append("")
            
            for ev in self.events:
                ntype = ev.get("node_type", "")
                phase = (ev.get("metadata") or {}).get("phase", "")
                indent = _infer_indent(ntype)
                
                # Phase separator: only for Manager pipeline phases
                VALID_PHASES = {"planning", "execute", "validate", "synthesis", "done"}
                if phase and phase in VALID_PHASES and (ntype == "Manager" or ntype == "System"):
                    if phase != current_phase:
                        current_phase = phase
                        lines.append("")
                        lines.append("═" * 78)
                        lines.append(f"  PHASE: {phase}")
                        lines.append("═" * 78)
                        lines.append("")
                
                lines.append(_format_event(ev, indent))
                lines.append("")
            
            # Summary
            summary = _compute_summary(self.events)
            duration = round(ended_at - self.started_at, 1)
            
            lines.append("")
            lines.append("═" * 78)
            lines.append("  SUMMARY")
            lines.append("═" * 78)
            lines.append(f"  Session:   {self.session_id}")
            lines.append(f"  Phases:    {', '.join(summary['phases'])}")
            lines.append(f"  Events:    {len(self.events)} total")
            lines.append(f"  Agents:    {summary['agents_spawned']} spawned | {summary['agents_success']} success | {summary['agents_failed']} failed")
            lines.append(f"  Tools:     {summary['tool_calls']} calls | {summary['tool_success']} success | {summary['tool_errors']} errors")
            lines.append(f"  Duration:  {duration}s")
            lines.append("═" * 78)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            
            logger.info(f"[SessionLogger] Log written: {filepath} ({len(self.events)} events, {duration}s)")
        
        except Exception as e:
            logger.warning(f"[SessionLogger] Failed to write log: {e}")
