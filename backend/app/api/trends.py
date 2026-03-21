from fastapi import APIRouter, Query, HTTPException

router = APIRouter()


@router.get("/trends")
async def get_trends(
    lat: float = Query(..., ge=-90, le=90),
    lon: float = Query(..., ge=-180, le=360),
):
    """Get acoustic feature time series (1980-2022) from SODA."""
    # TODO: Read from SODA Zarr precomputed trends
    return {
        "years": [],
        "channel_axis": [],
        "surface_duct_months": [],
        "cz_distance": [],
        "delta_c": [],
    }
