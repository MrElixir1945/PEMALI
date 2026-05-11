#!/usr/bin/env python3
"""
PEMALI TUI — Terminal dashboard untuk monitoring agent real-time via SSE.
Skalabel otomatis mengikuti ukuran terminal.
"""

import asyncio
import json
import time
import os
import sys
import httpx
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.align import Align
from rich.style import Style
from rich import box

# ─── Config ──────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"
REFRESH_INTERVAL = 0.3
console = Console()

# ─── State ──────────────────────────────────────────────────
class AppState:
    def __init__(self):
        self.connected = False
        self.start_time = time.time()
        self.trace_id: Optional[str] = None
        self.narratives: deque = deque(maxlen=200)
        self.dag_nodes: Dict[str, str] = {}
        self.dag_order: List[str] = []
        self.latest_module: Optional[Dict] = None
        self.worker_active = False
        self.last_tick: Optional[str] = None

    @property
    def uptime(self) -> str:
        secs = int(time.time() - self.start_time)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def handle_event(self, data: dict):
        if not self.trace_id:
            self.trace_id = data.get("trace_id")
        node_id = data.get("node_id", "?")
        node_type = data.get("node_type", "?")
        state = data.get("state", "?")
        narrative = data.get("narrative", "")
        metadata = data.get("metadata") or {}
        ts = datetime.fromtimestamp(data.get("timestamp", time.time()))

        if node_id not in self.dag_order:
            self.dag_order.append(node_id)
        self.dag_nodes[node_id] = state

        self.narratives.append({
            "time": ts.strftime("%H:%M:%S"),
            "node": f"{node_type}·{node_id}",
            "state": state,
            "text": narrative,
            "tool": metadata.get("tool_name"),
            "duration": metadata.get("duration_ms"),
            "phase": metadata.get("phase"),
        })

        if node_type == "Module" and state in ("DONE", "ERROR"):
            self.latest_module = {
                "node": node_id,
                "state": state,
                "tool": metadata.get("tool_name"),
                "duration": metadata.get("duration_ms"),
                "status": metadata.get("status"),
                "error": metadata.get("error"),
            }

    def update_status(self, data: dict):
        self.worker_active = data.get("worker_active", False)
        self.last_tick = data.get("last_tick")


# ─── Styles ──────────────────────────────────────────────────
STATE_STYLES = {
    "THINKING": Style(color="#8B5CF6", bold=True),
    "SPAWNING": Style(color="#3B82F6", bold=True),
    "EXECUTING": Style(color="#10B981", bold=True),
    "DONE": Style(color="#6EE7B7"),
    "ERROR": Style(color="#EF4444", bold=True),
    "IDLE": Style(color="#52525B"),
}

STATE_LABEL = {
    "THINKING": "THK", "SPAWNING": "SPN",
    "EXECUTING": "EXE", "DONE": "DON",
    "ERROR": "ERR", "IDLE": "IDL",
}

DAG_ICON = {"DONE": "●", "ERROR": "✗", "EXECUTING": "◉", "THINKING": "◎"}
DAG_COLOR = {"DONE": "green", "ERROR": "red", "EXECUTING": "cyan", "THINKING": "magenta"}


def state_badge(state: str) -> Text:
    s = STATE_STYLES.get(state, STATE_STYLES["IDLE"])
    return Text(f" {STATE_LABEL.get(state, state)} ", style=s + Style(bgcolor="#3a3a3a"))


# ─── Render ──────────────────────────────────────────────────
def term_size() -> tuple:
    sz = os.get_terminal_size()
    return sz.columns, sz.lines


def render(state: AppState) -> Layout:
    tw, th = term_size()

    # ── Dynamic sizes ──
    header_h = 4
    footer_h = 3
    body_h = th - header_h - footer_h - 2
    dag_ratio = max(1, tw // 6)
    nar_ratio = max(1, tw - dag_ratio - 4)
    max_nar = max(1, body_h - 8)
    nar_h_ratio = max(1, body_h - 8)

    # ── Layout ──
    layout = Layout()
    layout.split_column(
        Layout(name="header", size=header_h),
        Layout(name="body"),
        Layout(name="footer", size=footer_h),
    )
    if tw < 80:
        layout["body"].split_column(
            Layout(name="dag", ratio=1),
            Layout(name="right", ratio=3),
        )
    else:
        layout["body"].split_row(
            Layout(name="dag", ratio=1),
            Layout(name="right", ratio=3),
        )
    layout["right"].split_column(
        Layout(name="narrative"),
        Layout(name="module", size=6),
    )

    # ── Header ──
    status = "● LIVE" if state.connected else "○ DISCONNECTED"
    sc = "bold green" if state.connected else "bold red"
    info = Text.assemble(
        (" ◆ PEMALI ", "bold white"),
        ("AGENT MONITOR", "dim white"),
    )
    info.append(f"  {status}  ", sc)
    info.append(f"⏱ {state.uptime}  ", "dim")
    if state.trace_id:
        info.append(f"#{state.trace_id[-12:]}", "dim blue")
    info.append(f"  {tw}x{th}", "dim black")
    layout["header"].update(Panel(info, box=box.ROUNDED, style="bright_black"))

    # ── DAG Panel ──
    dag_table = Table.grid(padding=(0, 1))
    dag_table.add_column()
    if not state.dag_order:
        dag_table.add_row(Text(" ∅ menunggu event", style="dim italic"))
    else:
        for nid in state.dag_order:
            st = state.dag_nodes.get(nid, "IDLE")
            label = nid.replace("_", " ").title()
            icon = DAG_ICON.get(st, "○")
            color = DAG_COLOR.get(st, "grey")
            dag_table.add_row(Text(f"{icon} {label}", style=color))
    layout["dag"].update(Panel(
        Align.left(dag_table), title="[bold]DAG[/]",
        box=box.ROUNDED, border_style="bright_black",
    ))

    # ── Narrative Panel ──
    nar_items = list(state.narratives)[-max_nar:]
    nar_lines = []
    if not nar_items:
        nar_lines.append(Text("  Belum ada aktivitas agent...", style="dim italic"))
    for ev in nar_items:
        badge = state_badge(ev["state"])
        max_w = max(30, tw - dag_ratio - 22)
        text_clean = ev["text"][:max_w]
        line = Text.assemble(
            badge,
            (f" {ev['node']:<18}", "bold white"),
            (f" {text_clean}", "grey70"),
        )
        if ev.get("duration"):
            line.append(f" {ev['duration']:.0f}ms", "dim cyan")
        nar_lines.append(line)
    layout["narrative"].update(Panel(
        Group(*nar_lines) if nar_lines else Text(""),
        title="[bold]Narrative Stream[/]",
        box=box.ROUNDED, border_style="bright_black",
    ))

    # ── Module Panel ──
    mod_lines = [Text("  Menunggu output modul...", style="dim italic")]
    if state.latest_module:
        m = state.latest_module
        mod_lines = [
            Text(f"  {m['node']}", style="bold white"),
            Text(f"  Status: {m['state']}", style="green" if m['state'] == 'DONE' else 'red'),
        ]
        if m.get("tool"):
            mod_lines.append(Text(f"  Tool: {m['tool']}", style="cyan"))
        if m.get("duration"):
            mod_lines.append(Text(f"  Duration: {m['duration']:.0f}ms", style="dim"))
        if m.get("error"):
            mod_lines.append(Text(f"  Error: {m['error'][:60]}", style="red"))
    layout["module"].update(Panel(
        Group(*mod_lines), title="[bold]Module[/]",
        box=box.ROUNDED, border_style="bright_black",
    ))

    # ── Footer ──
    worker = "● Active" if state.worker_active else "○ Idle"
    wc = "green" if state.worker_active else "grey"
    footer = Text.assemble(
        (" Worker: ", "dim"), (worker, wc),
        (" │ Model: deepseek/deepseek-v4-flash ", "dim"),
        ("│ Events: ", "dim"), (str(len(state.narratives)), "bold"),
        (" │ Nodes: ", "dim"), (str(len(state.dag_nodes)), "bold"),
    )
    layout["footer"].update(Panel(footer, box=box.ROUNDED, style="bright_black"))

    return layout


# ─── SSE Consumer ────────────────────────────────────────────
async def sse_loop(state: AppState):
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{BACKEND_URL}/api/telemetry") as resp:
                    state.connected = True
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                state.handle_event(json.loads(line[6:]))
                            except json.JSONDecodeError:
                                pass
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            state.connected = False
        await asyncio.sleep(3)


async def status_loop(state: AppState):
    while True:
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                resp = await client.get(f"{BACKEND_URL}/api/status")
                if resp.status_code == 200:
                    state.update_status(resp.json())
                    state.connected = True
        except httpx.ConnectError:
            state.connected = False
        await asyncio.sleep(5)


# ─── Input ──────────────────────────────────────────────────
async def send_prompt(text: str):
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            await client.post(f"{BACKEND_URL}/api/trigger", json={"prompt": text})
    except httpx.ConnectError:
        pass


async def input_loop(state: AppState):
    loop = asyncio.get_event_loop()
    bg_tasks = set()

    tw = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    h = "─" * min(60, tw - 2)
    print(f"\n{h}")
    print("  PEMALI TUI — Ketik perintah audit, atau:")
    print(f"    /status, /clear, /quit")
    print(f"{h}\n")

    while True:
        try:
            line = await loop.run_in_executor(None, input, "  > ")
            cmd = line.strip()
            if not cmd:
                continue
            if cmd == "/quit":
                raise KeyboardInterrupt
            elif cmd == "/clear":
                state.narratives.clear()
                state.dag_nodes.clear()
                state.dag_order.clear()
                state.latest_module = None
            else:
                state.narratives.clear()
                state.dag_nodes.clear()
                state.dag_order.clear()
                state.latest_module = None
                t = asyncio.ensure_future(send_prompt(cmd))
                bg_tasks.add(t)
                t.add_done_callback(bg_tasks.discard)
        except (EOFError, KeyboardInterrupt):
            raise


# ─── Main ──────────────────────────────────────────────────
async def display_loop(state: AppState):
    with Live(render(state), refresh_per_second=1 / REFRESH_INTERVAL, screen=True) as live:
        while True:
            await asyncio.sleep(REFRESH_INTERVAL)
            live.update(render(state))


async def main():
    state = AppState()
    print("\033[2J\033[H", end="")

    tasks = [
        asyncio.create_task(sse_loop(state)),
        asyncio.create_task(status_loop(state)),
        asyncio.create_task(input_loop(state)),
        asyncio.create_task(display_loop(state)),
    ]
    try:
        await asyncio.gather(*tasks)
    except (KeyboardInterrupt, asyncio.CancelledError):
        for t in tasks:
            t.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n  ✕ TUI stopped.")
