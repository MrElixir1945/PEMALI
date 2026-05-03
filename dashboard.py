import time
from rich.live import Live
from rich.table import Table
from rich.layout import Layout
from rich.panel import Panel
from rich.console import Console
from rich.text import Text
from core.database import SessionLocal, AuditLog, AutonomousTask, AgentMemory

console = Console()

def get_stats_data():
    db = SessionLocal()
    
    # 1. Fetch Latest Session ID agar log gak campur aduk
    latest_mem = db.query(AgentMemory).order_by(AgentMemory.id.desc()).first()
    target_session = latest_mem.session_id if latest_mem else None

    # 2. Table Tasks
    task_table = Table(expand=True, border_style="dim")
    task_table.add_column("ID", style="cyan", width=3)
    task_table.add_column("Status", style="bold")
    tasks = db.query(AutonomousTask).order_by(AutonomousTask.id.desc()).limit(5).all()
    for t in tasks:
        color = "green" if t.status == "completed" else "yellow"
        task_table.add_row(str(t.id), f"[{color}]{t.status}[/]")

    # 3. Table Logs
    log_table = Table(expand=True, border_style="dim")
    log_table.add_column("Loc", style="yellow")
    log_table.add_column("Issue", style="red")
    logs = db.query(AuditLog).order_by(AuditLog.id.desc()).limit(5).all()
    for l in logs:
        log_table.add_row(l.location, l.issue_type[:10]+"..")

    # 4. FULL REASONING LOG (The Core)
    thought_text = Text()
    if target_session:
        # Ambil SEMUA memori untuk session ini, urutkan dari yang lama ke baru
        memories = db.query(AgentMemory).filter(AgentMemory.session_id == target_session).order_by(AgentMemory.id.asc()).all()
        
        for m in memories:
            if m.role == "system":
                continue # Skip system prompt biar gak penuh
                
            icon = "👤 USER" if m.role == "user" else "🤖 AGENT"
            color = "white" if m.role == "user" else "cyan"
            
            thought_text.append(f"\n{icon}: ", style=f"bold {color}")
            thought_text.append(f"{m.content}\n", style=color)
            thought_text.append("." * 60, style="dim black")
    else:
        thought_text.append("Waiting for agent activity...", style="italic dim")
    
    db.close()
    return task_table, log_table, thought_text, target_session

def run_dashboard():
    # Gunakan screen=True untuk full terminal app feel
    with Live(refresh_per_second=1, screen=True) as live:
        while True:
            t_table, l_table, thoughts, session_id = get_stats_data()
            
            layout = Layout()
            layout.split_column(
                Layout(Panel(f"PEMALI COMMAND CENTER | Active Session: [bold yellow]{session_id}[/]", style="bold white on blue"), size=3),
                Layout(name="upper", size=10),
                Layout(name="lower")
            )
            
            layout["upper"].split_row(
                Layout(Panel(t_table, title="Queue Status")),
                Layout(Panel(l_table, title="Recent Audits"))
            )
            
            # Panel bawah dibikin gede buat scroll-like view
            layout["lower"].update(
                Panel(thoughts, title="[bold green]Sequence Reasoning Log[/]", border_style="green", padding=(1, 2))
            )
            
            live.update(layout)
            time.sleep(1)

if __name__ == "__main__":
    run_dashboard()
