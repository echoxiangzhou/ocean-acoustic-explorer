import math
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import json

from app.api import profiles, acoustic, trends, scenarios


class NaNSafeEncoder(json.JSONEncoder):
    """JSON encoder that converts NaN/Inf to null."""
    def default(self, obj):
        return super().default(obj)

    def encode(self, o):
        return super().encode(self._sanitize(o))

    def _sanitize(self, obj):
        if isinstance(obj, float):
            if math.isnan(obj) or math.isinf(obj):
                return None
            return obj
        if isinstance(obj, dict):
            return {k: self._sanitize(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._sanitize(v) for v in obj]
        return obj


class NaNSafeJSONResponse(JSONResponse):
    def render(self, content) -> bytes:
        return json.dumps(
            content,
            cls=NaNSafeEncoder,
            ensure_ascii=False,
        ).encode("utf-8")


app = FastAPI(
    title="OceanAcoustic Explorer API",
    version="0.1.0",
    default_response_class=NaNSafeJSONResponse,
)

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
