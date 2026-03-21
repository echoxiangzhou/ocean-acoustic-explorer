from fastapi import APIRouter, WebSocket, Query, HTTPException
from pydantic import BaseModel
from app.services.section import compute_section_field
from app.services.sediment import query_sediment

router = APIRouter()


class ComputeRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    src_depth: float = 50.0
    frequency: float = 1000.0
    model: str = "bellhop"
    max_range: float | None = None


@router.post("/acoustic/compute")
async def submit_compute(req: ComputeRequest):
    """Submit acoustic propagation computation (async via Celery)."""
    # TODO: Submit to Celery worker for Bellhop/RAM computation
    return {"task_id": "placeholder", "status": "pending"}


@router.get("/acoustic/result/{task_id}")
async def get_result(task_id: str):
    """Get computation result by task ID."""
    # TODO: Fetch from Celery result backend
    return {"task_id": task_id, "status": "pending", "progress": 0}


@router.websocket("/acoustic/progress/{task_id}")
async def progress_ws(websocket: WebSocket, task_id: str):
    """WebSocket endpoint for computation progress updates."""
    await websocket.accept()
    await websocket.send_json({"progress": 0, "status": "pending"})
    await websocket.close()


@router.get("/acoustic/section")
async def get_section_field(
    start_lat: float = Query(...),
    start_lon: float = Query(...),
    end_lat: float = Query(...),
    end_lon: float = Query(...),
    month: int = Query(1, ge=1, le=12),
    num_points: int = Query(200, ge=20, le=1000),
):
    """
    Compute 2D sound speed field along a section.
    Returns c(range, depth), T(range, depth), S(range, depth), and bathymetry.
    """
    try:
        result = compute_section_field(
            start_lat, start_lon, end_lat, end_lon,
            month=month, num_range_points=num_points,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/acoustic/sediment")
async def get_sediment(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
):
    """
    Query nearest deck41 sediment sample and acoustic properties.
    Used for bottom boundary conditions in acoustic models.
    """
    try:
        result = query_sediment(lat, lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
