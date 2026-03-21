from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import numpy as np
from app.services.sound_speed import compute_profile
from app.services.bathymetry import get_depth
from app.services.sediment import query_sediment


router = APIRouter()


class ScenarioRequest(BaseModel):
    src_type: str = "point"
    src_depth: float = 50.0
    recv_depth: float = 100.0
    frequency: float = 1000.0
    lat: float = 20.0
    lon: float = 120.0
    month: int = 1


class CompareRequest(BaseModel):
    lat: float = 20.0
    lon: float = 120.0
    src_depth: float = 50.0
    frequency: float = 1000.0
    month_a: int = 1
    month_b: int = 7


@router.post("/scenarios/evaluate")
async def evaluate_scenario(req: ScenarioRequest):
    """
    Evaluate detection scenario at a given location.
    Loads local sound speed profile, estimates detection range,
    optimal receiver depth, and convergence zone usage.
    """
    try:
        profile = compute_profile(req.lat, req.lon, req.month, "woa23", "teos10")
        ocean_depth = get_depth(req.lat, req.lon)
        sediment = query_sediment(req.lat, req.lon)

        f = profile["features"]
        depth = np.array(profile["depth"])
        ss = np.array(profile["sound_speed"])

        # Find optimal receiver depth (near channel axis for max range)
        axis_depth = f["channel_axis_depth"]
        optimal_recv = axis_depth if axis_depth < ocean_depth else ocean_depth * 0.7

        # Simple detection range estimate based on TL = 20*log10(R) + alpha*R
        # For spherical spreading + absorption
        alpha = _absorption_coeff(req.frequency)  # dB/km
        src_idx = int(np.abs(depth - req.src_depth).argmin())
        src_speed = float(ss[src_idx])

        # Source level - noise level threshold (simplified)
        sl_minus_nl = 120  # dB typical for medium source
        # Solve: sl_minus_nl = 20*log10(R*1000) + alpha*R
        detection_range = _estimate_range(sl_minus_nl, alpha)

        # CZ utilization
        cz_ranges = []
        cz_dist = f.get("cz_distance_km")
        if cz_dist and not np.isnan(cz_dist):
            for n in range(1, 4):
                r = cz_dist * n
                if r < 200:
                    cz_ranges.append(round(r, 1))

        recommendations = []
        if f["surface_duct_thickness"] > 30:
            recommendations.append(
                "存在 %.0fm 表面声道，浅源可利用表面声道传播" % f["surface_duct_thickness"]
            )
        if cz_ranges:
            recommendations.append(
                "会聚区距离 %.1fkm，可在 %s km 处利用 CZ 效应" % (
                    cz_dist, "/".join(str(r) for r in cz_ranges)
                )
            )
        if axis_depth < ocean_depth:
            recommendations.append(
                "声道轴在 %.0fm，接收器部署在此深度可获最佳效果" % axis_depth
            )

        return {
            "lat": profile["lat"],
            "lon": profile["lon"],
            "ocean_depth_m": ocean_depth,
            "detection_range_km": round(detection_range, 1),
            "optimal_recv_depth_m": round(optimal_recv, 0),
            "cz_ranges_km": cz_ranges,
            "channel_axis_depth_m": axis_depth,
            "surface_duct_m": f["surface_duct_thickness"],
            "delta_c": f["delta_c"],
            "sediment": sediment.get("lith1", "unknown"),
            "recommendations": recommendations,
            "profile": {
                "depth": profile["depth"],
                "sound_speed": profile["sound_speed"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scenarios/compare")
async def compare_scenarios(req: CompareRequest):
    """Compare acoustic conditions between two months (e.g. summer vs winter)."""
    try:
        profile_a = compute_profile(req.lat, req.lon, req.month_a, "woa23", "teos10")
        profile_b = compute_profile(req.lat, req.lon, req.month_b, "woa23", "teos10")

        return {
            "lat": profile_a["lat"],
            "lon": profile_a["lon"],
            "scenario_a": {
                "month": req.month_a,
                "depth": profile_a["depth"],
                "sound_speed": profile_a["sound_speed"],
                "features": profile_a["features"],
            },
            "scenario_b": {
                "month": req.month_b,
                "depth": profile_b["depth"],
                "sound_speed": profile_b["sound_speed"],
                "features": profile_b["features"],
            },
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _absorption_coeff(freq_hz: float) -> float:
    """Thorp absorption coefficient in dB/km."""
    f_khz = freq_hz / 1000.0
    # Thorp formula (valid 100 Hz - 10 kHz)
    alpha = (0.11 * f_khz**2 / (1 + f_khz**2)
             + 44 * f_khz**2 / (4100 + f_khz**2)
             + 2.75e-4 * f_khz**2 + 0.003)
    return alpha


def _estimate_range(sl_minus_nl: float, alpha: float) -> float:
    """Estimate detection range by iterating TL = 20*log10(R) + alpha*R/1000."""
    for r_km in np.arange(1, 300, 0.5):
        tl = 20 * np.log10(r_km * 1000) + alpha * r_km
        if tl >= sl_minus_nl:
            return float(r_km)
    return 300.0
