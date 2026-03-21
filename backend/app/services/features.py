"""
Acoustic feature extraction from sound speed profiles.

Computes the 6 global feature layers (Module A):
  1. Sound channel axis depth (m)
  2. Surface duct thickness (m)
  3. Thermocline sound speed gradient (s^-1)
  4. Convergence zone distance (km) - requires src_depth
  5. Shadow zone onset distance (km) - requires src_depth
  6. Sound field type classification

Uses WOA23 data (verified):
  - t_an: objectively analyzed temperature, (time=1, depth=57, lat=720, lon=1440), 0.25°
  - s_an: salinity, same structure
  - depth: 57 levels, 0-1500m
  - Must open with decode_times=False (time units = "months since 1991-01-01")
"""

import numpy as np
import gsw


# Sound field type codes
FIELD_TYPE_DEEP_CZ = 1       # Deep sea CZ type (convergence zone)
FIELD_TYPE_SHALLOW_DUCT = 2  # Shallow water waveguide
FIELD_TYPE_POLAR = 3         # Polar/Arctic channel
FIELD_TYPE_MIXED = 4         # Mixed type


def extract_all_features(
    depth: np.ndarray,
    sound_speed: np.ndarray,
    lat: float,
    ocean_depth: float,
    src_depth: float = 50.0,
) -> dict:
    """
    Extract all 6 acoustic features from a sound speed profile.

    Args:
        depth: depth levels (m), e.g. WOA23 57 levels 0-1500m
        sound_speed: sound speed values (m/s)
        lat: latitude (for CZ estimation)
        ocean_depth: total ocean depth from GEBCO (m, positive)
        src_depth: source depth (m) for CZ/shadow zone calculation

    Returns:
        dict with all 6 features
    """
    valid = ~np.isnan(sound_speed)
    d = depth[valid]
    c = sound_speed[valid]

    if len(c) < 3:
        return _empty_features()

    # Surface speed
    surface_speed = float(c[0])

    # 1. Sound channel axis: depth of minimum sound speed
    min_idx = int(np.argmin(c))
    channel_axis_depth = float(d[min_idx])
    channel_axis_speed = float(c[min_idx])

    # Delta c: surface speed - channel axis speed
    delta_c = surface_speed - channel_axis_speed

    # 2. Surface duct thickness
    surface_duct = _surface_duct_thickness(d, c)

    # 3. Thermocline gradient: max negative dc/dz in the thermocline
    thermo_gradient = _thermocline_gradient(d, c)

    # 4. Convergence zone distance estimation
    cz_distance = _estimate_cz_distance(d, c, src_depth, ocean_depth)

    # 5. Shadow zone onset distance
    shadow_zone = _estimate_shadow_zone(d, c, src_depth)

    # 6. Sound field type classification
    field_type = _classify_field_type(
        d, c, channel_axis_depth, surface_duct, ocean_depth, lat
    )

    return {
        "channel_axis_depth": channel_axis_depth,
        "channel_axis_speed": channel_axis_speed,
        "surface_speed": surface_speed,
        "delta_c": delta_c,
        "surface_duct_thickness": surface_duct,
        "thermocline_gradient": thermo_gradient,
        "cz_distance_km": cz_distance,
        "shadow_zone_km": shadow_zone,
        "field_type": field_type,
    }


def _empty_features() -> dict:
    return {
        "channel_axis_depth": np.nan,
        "channel_axis_speed": np.nan,
        "surface_speed": np.nan,
        "delta_c": 0.0,
        "surface_duct_thickness": 0.0,
        "thermocline_gradient": 0.0,
        "cz_distance_km": np.nan,
        "shadow_zone_km": np.nan,
        "field_type": 0,
    }


def _surface_duct_thickness(depth: np.ndarray, c: np.ndarray) -> float:
    """Find surface duct: region near surface where speed increases with depth."""
    for i in range(1, len(c)):
        if c[i] < c[i - 1]:
            return float(depth[i - 1])
    return 0.0


def _thermocline_gradient(depth: np.ndarray, c: np.ndarray) -> float:
    """
    Maximum negative sound speed gradient (dc/dz) in the thermocline.
    Returns absolute value in s^-1.
    """
    if len(c) < 2:
        return 0.0
    dc = np.diff(c)
    dz = np.diff(depth)
    dz[dz == 0] = 1.0
    gradient = dc / dz
    # Thermocline has negative gradient (speed decreasing with depth)
    neg_grad = gradient[gradient < 0]
    if len(neg_grad) == 0:
        return 0.0
    return float(np.abs(np.min(neg_grad)))


def _estimate_cz_distance(
    depth: np.ndarray, c: np.ndarray,
    src_depth: float, ocean_depth: float,
) -> float:
    """
    Estimate first convergence zone distance using ray theory approximation.

    CZ occurs when rays from source depth refract back to surface.
    Simplified: CZ distance ≈ 2 * sqrt(2 * R * delta_z)
    where R = Earth radius, delta_z = depth where c(z) = c(src_depth).

    Returns distance in km, or NaN if no CZ exists.
    """
    if ocean_depth < 1000:
        return np.nan  # Too shallow for CZ

    # Find sound speed at source depth
    src_idx = int(np.abs(depth - src_depth).argmin())
    c_src = c[src_idx]

    # Find the depth below channel axis where c equals c_src (critical depth)
    min_idx = int(np.argmin(c))
    below_axis = c[min_idx:]
    depth_below = depth[min_idx:]

    critical_depth = np.nan
    for i in range(1, len(below_axis)):
        if below_axis[i] >= c_src:
            # Linear interpolation
            frac = (c_src - below_axis[i - 1]) / (below_axis[i] - below_axis[i - 1])
            critical_depth = depth_below[i - 1] + frac * (depth_below[i] - depth_below[i - 1])
            break

    if np.isnan(critical_depth):
        return np.nan

    # If critical depth > ocean depth, bottom-limited: no full CZ
    if critical_depth > ocean_depth:
        return np.nan

    # Simplified CZ distance estimation
    # Using Snell's law approximation: R_cz ≈ 2 * sqrt(2 * delta_c / c_min * R_earth * H)
    c_min = float(np.min(c))
    delta_c = c_src - c_min
    if delta_c <= 0:
        return np.nan

    R_earth = 6371.0  # km
    H = critical_depth / 1000.0  # km
    cz_dist = 2.0 * np.sqrt(2.0 * delta_c / c_min * R_earth * H)

    # Typical CZ: 30-70 km
    if 10 < cz_dist < 200:
        return float(cz_dist)
    return np.nan


def _estimate_shadow_zone(
    depth: np.ndarray, c: np.ndarray, src_depth: float,
) -> float:
    """
    Estimate shadow zone onset distance.
    Shadow zone begins where the limiting ray (grazing the channel axis) surfaces.

    Simplified estimation based on profile curvature.
    Returns distance in km.
    """
    src_idx = int(np.abs(depth - src_depth).argmin())
    c_src = c[src_idx]

    # Find gradient at source depth
    if src_idx == 0:
        dc_dz = (c[1] - c[0]) / (depth[1] - depth[0]) if len(c) > 1 else 0
    else:
        dc_dz = (c[src_idx] - c[src_idx - 1]) / (depth[src_idx] - depth[src_idx - 1])

    if dc_dz >= 0:
        return np.nan  # No shadow zone if gradient is positive at source

    # Shadow zone distance ~ c_src / |dc/dz| * tan(grazing_angle)
    # Simplified: R_shadow ~ 2 * src_depth * c_src / (abs(dc_dz) * 1000)
    R_shadow = 2.0 * src_depth * c_src / (abs(dc_dz) * 1000.0)

    if 1 < R_shadow < 100:
        return float(R_shadow)
    return np.nan


def _classify_field_type(
    depth: np.ndarray, c: np.ndarray,
    channel_axis_depth: float,
    surface_duct: float,
    ocean_depth: float,
    lat: float,
) -> int:
    """
    Classify sound field type:
      1 = Deep sea CZ type
      2 = Shallow water waveguide
      3 = Polar/Arctic channel (axis near surface)
      4 = Mixed type
    """
    if ocean_depth < 200:
        return FIELD_TYPE_SHALLOW_DUCT

    # Polar channel: axis near surface (< 100m) at high latitudes
    if abs(lat) > 50 and channel_axis_depth < 100:
        return FIELD_TYPE_POLAR

    # Deep CZ: axis > 500m and ocean > 3000m
    if channel_axis_depth > 500 and ocean_depth > 3000:
        return FIELD_TYPE_DEEP_CZ

    # Surface duct dominant
    if surface_duct > 50 and channel_axis_depth < 300:
        return FIELD_TYPE_MIXED

    return FIELD_TYPE_DEEP_CZ  # Default for deep ocean
