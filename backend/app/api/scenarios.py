from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()


class ScenarioRequest(BaseModel):
    src_type: str = "point"
    src_depth: float = 50.0
    recv_depth: float = 100.0
    frequency: float = 1000.0
    lat: float = 20.0
    lon: float = 120.0


@router.post("/scenarios/evaluate")
async def evaluate_scenario(req: ScenarioRequest):
    """Evaluate detection scenario: estimate range, optimal depth, CZ usage."""
    # TODO: Load local profile, run acoustic model, compute sonar equation
    return {
        "detection_range_km": 0,
        "optimal_recv_depth_m": 0,
        "cz_ranges_km": [],
        "recommendation": "Pending implementation",
    }
