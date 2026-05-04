import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def reset():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn:
        print("Resetting database...")
        conn.execute(text("TRUNCATE agent_memory, audit_logs, autonomous_tasks RESTART IDENTITY CASCADE"))
        print("Database reset successfully.")

if __name__ == "__main__":
    reset()
