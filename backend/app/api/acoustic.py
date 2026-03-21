from fastapi import APIRouter, WebSocket
from pydantic import BaseModel

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
    # TODO: Submit to Celery worker
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
    # TODO: Poll Celery task state and push progress
    await websocket.send_json({"progress": 0, "status": "pending"})
    await websocket.close()
