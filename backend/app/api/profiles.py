from fastapi import APIRouter, Query, HTTPException
from app.services.sound_speed import compute_profile
from app.services.bathymetry import get_depth, get_section_bathymetry

router = APIRouter()


@router.get("/profiles")
async def get_profile(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
    month: int = Query(1, ge=1, le=12),
    source: str = Query("woa23", pattern="^(woa23|hycom|soda)$"),
    formula: str = Query("teos10", pattern="^(teos10|mackenzie|chen_millero)$"),
):
    """
    Get sound speed profile at a given location.

    Returns depth[], sound_speed[], temperature[], salinity[], and features{}.
    Data sources: woa23 (default), hycom, soda.
    Formulas: teos10 (default), mackenzie, chen_millero.
    """
    try:
        result = compute_profile(lat, lon, month, source, formula)
        return result
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bathymetry")
async def get_bathymetry_point(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
):
    """Get ocean depth at a point from GEBCO 2024."""
    try:
        depth = get_depth(lat, lon)
        return {"lat": lat, "lon": lon, "depth_m": depth}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/bathymetry/section")
async def get_bathymetry_section(
    start_lat: float = Query(...),
    start_lon: float = Query(...),
    end_lat: float = Query(...),
    end_lon: float = Query(...),
    num_points: int = Query(500, ge=10, le=2000),
):
    """Get bathymetry profile along a section line."""
    try:
        result = get_section_bathymetry(
            start_lat, start_lon, end_lat, end_lon, num_points
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/features")
async def get_features_at_point(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
    month: int = Query(1, ge=1, le=12),
    src_depth: float = Query(50.0, ge=0, le=1000),
):
    """
    Get all 6 acoustic features at a point (for tooltip).
    Uses precomputed feature data if available, otherwise computes on-the-fly.
    """
    try:
        result = compute_profile(lat, lon, month, "woa23", "teos10")
        return {
            "lat": result["lat"],
            "lon": result["lon"],
            "month": month,
            "features": result["features"],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
