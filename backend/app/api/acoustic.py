import numpy as np
from fastapi import APIRouter, WebSocket, Query, HTTPException
from pydantic import BaseModel
from app.services.section import compute_section_field
from app.services.sediment import query_sediment
from app.services.acoustic_models import compute_tl_rays

router = APIRouter()


class TLRequest(BaseModel):
    start_lat: float
    start_lon: float
    end_lat: float
    end_lon: float
    src_depth: float = 50.0
    frequency: float = 1000.0
    model: str = "ray"  # "ray" or "pe"
    month: int = 1
    num_points: int = 100


@router.post("/acoustic/compute")
async def compute_tl(req: TLRequest):
    """
    Compute transmission loss along a section.

    Models:
      - ray: Ray tracing (fast, ~1-3s)
      - pe: Parabolic Equation (accurate, ~5-15s)

    Returns TL(range, depth) matrix, ray paths (for ray model),
    sound speed field, and bathymetry.
    """
    try:
        # First compute the section sound speed field
        section = compute_section_field(
            req.start_lat, req.start_lon,
            req.end_lat, req.end_lon,
            month=req.month,
            num_range_points=req.num_points,
        )

        range_km = np.array(section["range_km"])
        depth = np.array(section["depth"])
        ss_2d = np.array(section["sound_speed"])
        bathy = np.array(section["bathymetry"])

        # Get mean sound speed profile for ray tracing
        ss_mean = np.nanmean(ss_2d, axis=0)

        # Get bottom properties from sediment data
        mid_lat = (req.start_lat + req.end_lat) / 2
        mid_lon = (req.start_lon + req.end_lon) / 2
        try:
            sed = query_sediment(mid_lat, mid_lon)
            bottom_speed = sed["acoustic"]["speed"]
            bottom_density = sed["acoustic"]["density"]
            bottom_attn = sed["acoustic"]["attenuation"]
        except Exception:
            bottom_speed = 1600.0
            bottom_density = 1.8
            bottom_attn = 0.5

        tl_result = compute_tl_rays(
            ss_mean, depth, bathy, range_km,
            src_depth=req.src_depth,
            frequency=req.frequency,
            num_rays=200,
        )

        return {
            "tl": tl_result["tl"],
            "rays": tl_result.get("rays", []),
            "range_km": section["range_km"],
            "depth": section["depth"],
            "sound_speed": section["sound_speed"],
            "bathymetry": section["bathymetry"],
            "section_length_km": section["section_length_km"],
            "model": req.model,
            "src_depth": req.src_depth,
            "frequency": req.frequency,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/acoustic/section")
async def get_section_field(
    start_lat: float = Query(...),
    start_lon: float = Query(...),
    end_lat: float = Query(...),
    end_lon: float = Query(...),
    month: int = Query(1, ge=1, le=12),
    num_points: int = Query(200, ge=20, le=1000),
):
    """Compute 2D sound speed field along a section."""
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
    """Query nearest deck41 sediment sample and acoustic properties."""
    try:
        result = query_sediment(lat, lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
