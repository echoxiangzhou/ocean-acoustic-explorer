from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import profiles, acoustic, trends, scenarios

app = FastAPI(title="OceanAcoustic Explorer API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(profiles.router, prefix="/api")
app.include_router(acoustic.router, prefix="/api")
app.include_router(trends.router, prefix="/api")
app.include_router(scenarios.router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
