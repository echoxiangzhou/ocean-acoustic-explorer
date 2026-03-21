from fastapi import APIRouter, Query, HTTPException
from app.services.sound_speed import compute_profile

router = APIRouter()


@router.get("/trends")
async def get_trends(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
    src_depth: float = Query(50.0, ge=0, le=1000),
):
    """
    Get acoustic feature seasonal cycle at a given location.
    Uses WOA23 12-month climatology to show monthly variation.

    Returns monthly time series of 4 key acoustic features.
    """
    try:
        months = list(range(1, 13))
        channel_axis = []
        surface_duct = []
        delta_c = []
        surface_speed = []

        for m in months:
            result = compute_profile(lat, lon, m, "woa23", "teos10")
            f = result["features"]
            channel_axis.append(f["channel_axis_depth"])
            surface_duct.append(f["surface_duct_thickness"])
            delta_c.append(f["delta_c"])
            surface_speed.append(f["surface_speed"])

        return {
            "lat": result["lat"],
            "lon": result["lon"],
            "months": months,
            "channel_axis_depth": channel_axis,
            "surface_duct_thickness": surface_duct,
            "delta_c": delta_c,
            "surface_speed": surface_speed,
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
