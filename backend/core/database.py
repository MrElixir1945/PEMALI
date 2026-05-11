import os
import datetime
from sqlalchemy import create_engine, Column, String, Integer, JSON, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker, declarative_base
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "config", ".env"))
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://admin:pemalipass@localhost:5432/pemali_db")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_utc_now():
    return datetime.datetime.now(datetime.timezone.utc)

class AgentMemory(Base):
    __tablename__ = "agent_memory"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    tool_call_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    created_at = Column(DateTime, default=get_utc_now)

class AutonomousTask(Base):
    __tablename__ = "autonomous_tasks"
    id = Column(Integer, primary_key=True, index=True)
    execute_at = Column(DateTime, index=True)
    intent_description = Column(Text)
    context_snapshot = Column(JSON)
    status = Column(String, default="pending")
    created_at = Column(DateTime, default=get_utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True, nullable=True)
    location = Column(String, index=True) # Optimized: Added index
    issue_type = Column(String, index=True) # Optimized: Added index
    narrative_report = Column(Text)
    thk_alignment = Column(String)
    metadata_json = Column(JSON)
    created_at = Column(DateTime, default=get_utc_now)

class RawSensorData(Base):
    __tablename__ = "raw_sensor_data"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String, index=True)
    tool_name = Column(String, index=True)
    raw_payload = Column(JSON)
    created_at = Column(DateTime, default=get_utc_now)

class MemoryNode(Base):
    __tablename__ = "memory_nodes"
    id = Column(Integer, primary_key=True, index=True)
    node_type = Column(String(50), index=True)  # 'location', 'issue', 'metric'
    label = Column(String(255), index=True)
    properties = Column(JSON)
    session_id = Column(String, index=True)
    first_seen = Column(DateTime, default=get_utc_now)
    last_updated = Column(DateTime, default=get_utc_now, onupdate=get_utc_now)

class MemoryEdge(Base):
    __tablename__ = "memory_edges"
    id = Column(Integer, primary_key=True, index=True)
    source_label = Column(String(255))
    target_label = Column(String(255))
    relation_type = Column(String(50))  # 'caused_by', 'occurred_during', 'escalated_to'
    temporal_context = Column(JSON)
    weight = Column(Integer, default=0)
    created_at = Column(DateTime, default=get_utc_now)

    # Link to the primary node in memory_nodes
    memory_node_id = Column(Integer, index=True)

def init_db():
    Base.metadata.create_all(bind=engine)