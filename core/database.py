from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime

# Format: postgresql://user:password@host:port/dbname
DATABASE_URL = "postgresql://admin:pemalipass@localhost:5432/pemali_db"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AgentMemory(Base):
    """Menyimpan history percakapan dan tool calls (Short-term memory)."""
    __tablename__ = "agent_memory"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True) # ID untuk membedakan job otonom vs manual
    role = Column(String) # system, user, assistant, tool
    content = Column(Text)
    tool_call_id = Column(String, nullable=True)
    name = Column(String, nullable=True) # Nama tool jika role == tool
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class AutonomousTask(Base):
    """Menyimpan 'Future Intent' untuk self-scheduling."""
    __tablename__ = "autonomous_tasks"
    id = Column(Integer, primary_key=True, index=True)
    execute_at = Column(DateTime, index=True)
    intent_description = Column(Text) # Alasan kenapa agen mau jalan lagi
    context_snapshot = Column(JSON) # Data penting dari sesi sebelumnya
    status = Column(String, default="pending") # pending, completed, failed
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class AuditLog(Base):
    """Final reports and critical observations."""
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    location = Column(String)
    issue_type = Column(String)
    narrative_report = Column(Text)
    thk_alignment = Column(String)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

def init_db():
    Base.metadata.create_all(bind=engine)