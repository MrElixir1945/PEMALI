from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agents.orchestrator import PEMALIOrchestrator
from data.mock_data import MOCK_REGIONS

app = FastAPI(
    title="PEMALI API",
    description="Platform Ekologi Modular Agentic berbasis Artificial Intelligence",
    version="0.1.0-prototype"
)

# Enable CORS untuk Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

orchestrator = PEMALIOrchestrator()

@app.get("/")
def read_root():
    return {"message": "Welcome to PEMALI API", "status": "active"}

@app.get("/regions")
def get_regions():
    return {"regions": MOCK_REGIONS}

@app.get("/audit/all")
def run_all_audits():
    results = []
    for region in MOCK_REGIONS:
        results.append(orchestrator.run_audit(region))
    return results

@app.get("/audit/{region}")
def run_audit(region: str):
    if region not in MOCK_REGIONS:
        raise HTTPException(status_code=404, detail="Region not found")
    return orchestrator.run_audit(region)
