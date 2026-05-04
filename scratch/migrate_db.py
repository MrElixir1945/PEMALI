import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.begin() as conn: # begin() handles transaction
        print("Checking audit_logs table...")
        # Check existence using information_schema for safety
        res = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='audit_logs' AND column_name='session_id';
        """)).fetchone()
        
        if res:
            print("Column 'session_id' already exists.")
        else:
            print("Adding 'session_id' column to audit_logs...")
            conn.execute(text("ALTER TABLE audit_logs ADD COLUMN session_id VARCHAR"))
            print("Column added successfully.")

if __name__ == "__main__":
    migrate()
