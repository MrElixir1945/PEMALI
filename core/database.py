import os
import datetime
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime, Text, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Format: postgresql://user:password@host:port/dbname
DEFAULT_DB_URL = "postgresql://admin:pemalipass@localhost:5432/pemali_db"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB_URL)

try:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    print(f"[Database] Error creating engine: {e}")
    engine = None
    SessionLocal = None

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
    if engine:
        Base.metadata.create_all(bind=engine)
    else:
        raise Exception("Database engine not initialized. Check DATABASE_URL.")