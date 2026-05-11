#!/usr/bin/env python3
"""
PEMALI Playground TUI — Chat interface untuk ngobrol dengan agent.
Prompt → real-time narrative stream → final report.
"""

import asyncio
import json
import time
import os
import sys
import httpx
from datetime import datetime
from collections import deque
from typing import Dict, Optional

from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.style import Style
from rich import box

# ─── Config ──────────────────────────────────────────────────
BACKEND_URL = "http://localhost:8000"
REFRESH_INTERVAL = 0.2
console = Console()


# ─── State ──────────────────────────────────────────────────
class ChatState:
    def __init__(self):
        self.connected = False
        self.start_time = time.time()
        self.trace_id: Optional[str] = None
        self.lines: deque = deque(maxlen=500)
        self.prompt_sent = ""
        self.waiting_response = False
        self.final_report: Optional[str] = None
        self.worker_active = False

    @property
    def uptime(self) -> str:
        secs = int(time.time() - self.start_time)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

    def add_user(self, text: str):
        self.lines.append({"type": "user", "text": text, "time": datetime.now()})
        self.prompt_sent = text
        self.waiting_response = True
        self.final_report = None

    def add_event(self, data: dict):
        if not self.trace_id:
            self.trace_id = data.get("trace_id")
        node_type = data.get("node_type", "?")
        node_id = data.get("node_id", "?")
        state = data.get("state", "?")
        narrative = data.get("narrative", "")
        meta = data.get("metadata") or {}

        label = f"{node_type}·{node_id}"
        duration = meta.get("duration_ms")
        tool = meta.get("tool_name")

        line = {"type": "event", "state": state, "node": label,
                "text": narrative, "time": datetime.now(),
                "duration": duration, "tool": tool}

        # Check if it's the final DONE from manager
        if state == "DONE" and node_type == "Manager":
            self.waiting_response = False

        self.lines.append(line)

    def set_report(self, report: str):
        self.final_report = report
        self.lines.append({"type": "report", "text": report, "time": datetime.now()})
        self.waiting_response = False

    def update_status(self, data: dict):
        self.worker_active = data.get("worker_active", False)


# ─── Styles ──────────────────────────────────────────────────
STATE_STYLES = {
    "THINKING": Style(color="#8B5CF6", bold=True),
    "SPAWNING": Style(color="#3B82F6", bold=True),
    "EXECUTING": Style(color="#10B981", bold=True),
    "DONE": Style(color="#6EE7B7"),
    "ERROR": Style(color="#EF4444", bold=True),
}

STATE_LABEL = {
    "THINKING": " THK ", "SPAWNING": " SPN ",
    "EXECUTING": " EXE ", "DONE": " DON ",
    "ERROR": " ERR ",
}


def render(state: ChatState) -> Layout:
    tw, th = os.get_terminal_size()
    header_h = 4
    footer_h = 3
    content_h = th - header_h - footer_h - 2
    max_visible = max(1, content_h - 2)

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=header_h),
        Layout(name="body"),
        Layout(name="footer", size=footer_h),
    )

    # ── Header ──
    status = "● LIVE" if state.connected else "○ DISCONNECTED"
    sc = "bold green" if state.connected else "bold red"
    title = Text.assemble(
        (" ◆ PEMALI ", "bold white"),
        ("PLAYGROUND", "dim white"),
    )
    title.append(f"  {status}  ", sc)
    title.append(f"⏱ {state.uptime}  ", "dim")
    if state.trace_id:
        title.append(f"#{state.trace_id[-12:]}", "dim blue")
    layout["header"].update(Panel(title, box=box.ROUNDED, style="bright_black"))

    # ── Body (chat log) ──
    chat_lines = []
    visible = list(state.lines)[-max_visible:]

    if not visible:
        chat_lines.append(Text("  Belum ada percakapan. Ketik prompt di bawah.", style="dim italic"))
        chat_lines.append(Text(""))
        chat_lines.append(Text("  Contoh: Audit kawasan Ubud", style="dim cyan"))
        chat_lines.append(Text("  Contoh: Cek perubahan hutan di Jatiluwih", style="dim cyan"))

    for line in visible:
        t = line["time"].strftime("%H:%M")

        if line["type"] == "user":
            chat_lines.append(Text(f"  ┌─ {t} ─────────────────────────────", style="bold white"))
            chat_lines.append(Text(f"  │ {line['text']}", style="bold white"))
            chat_lines.append(Text(f"  └──────────────────────────────────", style="bold white"))

        elif line["type"] == "event":
            st = line["state"]
            s_style = STATE_STYLES.get(st, Style())
            label = STATE_LABEL.get(st, f" {st} ")
            dur = f" {line['duration']:.0f}ms" if line.get("duration") else ""
            tool = f" [{line['tool']}]" if line.get("tool") else ""
            chat_lines.append(Text.assemble(
                (f"  {t} ", "dim"),
                (label, s_style + Style(bgcolor="#3a3a3a")),
                (f" {line['node']:<20}", "bold white"),
                (tool, "cyan"),
                (dur, "dim"),
            ))
            tw_clean = max(30, tw - 10)
            narrative_clean = line["text"][:tw_clean]
            chat_lines.append(Text(f"     {narrative_clean}", style="grey70"))
            chat_lines.append(Text(""))

        elif line["type"] == "report":
            chat_lines.append(Text(f"  ── HASIL AUDIT ──", style="bold cyan"))
            raw = line["text"]
            try:
                parsed = json.loads(raw)
                formatted = json.dumps(parsed, indent=2, ensure_ascii=False)
                report_text = formatted
            except (json.JSONDecodeError, TypeError):
                report_text = raw
            tw_clean = max(40, tw - 6)
            for chunk in report_text.split("\n"):
                while len(chunk) > tw_clean:
                    chat_lines.append(Text(f"  {chunk[:tw_clean]}", style="green"))
                    chunk = chunk[tw_clean:]
                chat_lines.append(Text(f"  {chunk}", style="green"))
            chat_lines.append(Text(""))

    if state.waiting_response:
        dots = "." * (int(time.time() * 2) % 4)
        chat_lines.append(Text(f"  Agent sedang berpikir{dots}", style="yellow italic"))

    body = Panel(
        Group(*chat_lines) if chat_lines else Text(""),
        box=box.ROUNDED, border_style="bright_black",
    )
    layout["body"].update(body)

    # ── Footer ──
    worker = "● Active" if state.worker_active else "○ Idle"
    wc = "green" if state.worker_active else "grey"
    prompt_label = state.prompt_sent[:40] + "..." if len(state.prompt_sent) > 40 else state.prompt_sent
    ftext = Text.assemble(
        (" Worker: ", "dim"), (worker, wc),
        (" │ Model: deepseek/deepseek-v4-flash ", "dim"),
        ("│ Prompt: ", "dim"),
        (f"{prompt_label}", "bold cyan") if prompt_label else ("(none)", "dim"),
    )
    layout["footer"].update(Panel(ftext, box=box.ROUNDED, style="bright_black"))

    return layout


# ─── SSE Consumer ────────────────────────────────────────────
async def sse_loop(state: ChatState):
    while True:
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", f"{BACKEND_URL}/api/telemetry") as resp:
                    state.connected = True
                    async for line in resp.aiter_lines():
                        if line.startswith("data: "):
                            try:
                                data = json.loads(line[6:])
                                state.add_event(data)
                            except json.JSONDecodeError:
                                pass
        except (httpx.ConnectError, httpx.RemoteProtocolError):
            state.connected = False
        await asyncio.sleep(3)


async def status_loop(state: ChatState):
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


# ─── Input / Trigger ────────────────────────────────────────
async def send_prompt(text: str, state: ChatState):
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                f"{BACKEND_URL}/api/trigger",
                json={"prompt": text},
            )
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, str):
                    state.set_report(data)
    except httpx.ConnectError:
        pass


async def input_loop(state: ChatState):
    loop = asyncio.get_event_loop()
    bg_tasks = set()

    tw = os.get_terminal_size().columns if sys.stdout.isatty() else 80
    h = "─" * min(60, tw - 2)
    print(f"\n{h}")
    print("  PEMALI Playground — Ketik prompt audit, atau:")
    print(f"    /clear, /status, /quit")
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
                state.lines.clear()
                state.trace_id = None
                state.prompt_sent = ""
                state.final_report = None
                state.waiting_response = False
            elif cmd == "/status":
                pass
            else:
                state.add_user(cmd)
                t = asyncio.ensure_future(send_prompt(cmd, state))
                bg_tasks.add(t)
                t.add_done_callback(bg_tasks.discard)
        except (EOFError, KeyboardInterrupt):
            raise


# ─── Display Loop ──────────────────────────────────────────
async def display_loop(state: ChatState):
    with Live(render(state), refresh_per_second=1 / REFRESH_INTERVAL, screen=True) as live:
        while True:
            await asyncio.sleep(REFRESH_INTERVAL)
            live.update(render(state))


# ─── Main ──────────────────────────────────────────────────
async def main():
    state = ChatState()
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
        print("\n  ✕ Playground stopped.")
