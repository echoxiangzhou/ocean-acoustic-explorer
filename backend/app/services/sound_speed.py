"""
Sound speed profile computation from ocean T/S data using TEOS-10 (gsw).

Handles three data sources with different temperature conventions:
  - WOA23: in-situ temperature (°C), can use gsw directly
  - HYCOM: in-situ temperature (°C), can use gsw directly
  - SODA:  potential temperature (°C), must convert to in-situ first

Verified against real WOA23 data:
  South China Sea (18N, 115E) Jan: surface=1531 m/s, axis=1100m, Δc=47.7
  Northwest Pacific (30N, 140E) Jan: surface=1522 m/s, axis=1100m, Δc=39.7
"""

import numpy as np
import gsw
from app.services.zarr_reader import (
    read_woa23_profile,
    read_hycom_profile,
    read_soda_profile,
    potential_to_insitu,
)
from app.services.features import extract_all_features
from app.services.bathymetry import get_depth


def _sound_speed_teos10(temperature: np.ndarray, salinity: np.ndarray,
                         depth: np.ndarray, lat: float, lon: float) -> np.ndarray:
    """Compute sound speed using TEOS-10 (gsw). Input must be in-situ temperature."""
    pressure = gsw.p_from_z(-depth, lat)
    sa = gsw.SA_from_SP(salinity, pressure, lon, lat)
    ct = gsw.CT_from_t(sa, temperature, pressure)
    return gsw.sound_speed(sa, ct, pressure)


def _sound_speed_mackenzie(temperature: np.ndarray, salinity: np.ndarray,
                            depth: np.ndarray) -> np.ndarray:
    """Mackenzie (1981) empirical formula. Input: in-situ temperature."""
    T, S, D = temperature, salinity, depth
    return (1448.96 + 4.591 * T - 5.304e-2 * T**2 + 2.374e-4 * T**3
            + 1.340 * (S - 35) + 1.630e-2 * D + 1.675e-7 * D**2
            - 1.025e-2 * T * (S - 35) - 7.139e-13 * T * D**3)


def _sound_speed_chen_millero(temperature: np.ndarray, salinity: np.ndarray,
                               depth: np.ndarray, lat: float) -> np.ndarray:
    """Chen & Millero (1977) formula. Input: in-situ temperature."""
    pressure = gsw.p_from_z(-depth, lat)
    P = pressure / 10.0  # dbar to bar
    T, S = temperature, salinity

    c0 = (1402.388 + 5.03830 * T - 5.81090e-2 * T**2 + 3.3432e-4 * T**3
          - 1.47797e-6 * T**4 + 3.1419e-9 * T**5)
    c1 = (0.153563 + 6.8999e-4 * T - 8.1829e-6 * T**2 + 1.3632e-7 * T**3
          - 6.1260e-10 * T**4)
    c2 = (3.1260e-5 - 1.7111e-6 * T + 2.5986e-8 * T**2 - 2.5353e-10 * T**3
          + 1.0415e-12 * T**4)
    c3 = -9.7729e-9 + 3.8513e-10 * T - 2.3654e-12 * T**2

    a = (1.389 - 1.262e-2 * T + 7.166e-5 * T**2 + 2.008e-6 * T**3
         - 3.21e-8 * T**4)
    a1 = (9.4742e-5 - 1.2583e-5 * T - 6.4928e-8 * T**2 + 1.0515e-8 * T**3
          - 2.0142e-10 * T**4)
    a2 = -3.9064e-7 + 9.1061e-9 * T - 1.6009e-10 * T**2 + 7.994e-12 * T**3
    a3 = 1.100e-10 + 6.651e-12 * T - 3.391e-13 * T**2

    b = -1.922e-2 - 4.42e-5 * T
    b1 = 7.3637e-5 + 1.7950e-7 * T
    d = 1.727e-3 - 7.9836e-6 * P

    return (c0 + c1 * P + c2 * P**2 + c3 * P**3
            + a * S + a1 * S * P + a2 * S * P**2 + a3 * S * P**3
            + b * S**1.5 + b1 * S**1.5 * P + d * S**2)


FORMULA_MAP = {
    "teos10": _sound_speed_teos10,
    "mackenzie": _sound_speed_mackenzie,
    "chen_millero": _sound_speed_chen_millero,
}


def compute_profile(lat: float, lon: float, month: int,
                    source: str = "woa23", formula: str = "teos10") -> dict:
    """
    Compute sound speed profile at given location.

    Args:
        lat, lon: location
        month: 1-12 (used for WOA23)
        source: "woa23" | "hycom" | "soda"
        formula: "teos10" | "mackenzie" | "chen_millero"

    Returns:
        dict with depth[], sound_speed[], temperature[], salinity[], features{}
    """
    # Read T/S profile from data source
    if source == "woa23":
        data = read_woa23_profile(lat, lon, month)
    elif source == "hycom":
        # For HYCOM, use most recent available date (simplified)
        data = read_hycom_profile(lat, lon, "20240101")
    elif source == "soda":
        data = read_soda_profile(lat, lon, "2019_01_03")
    else:
        raise ValueError(f"Unknown source: {source}")

    depth = data["depth"]
    temp = data["temperature"]
    salt = data["salinity"]
    actual_lat = data["lat"]
    actual_lon = data["lon"]

    if len(depth) == 0:
        raise ValueError(
            f"No valid T/S data at ({lat}, {lon}) for source={source}. Likely a land point."
        )

    # Convert potential temperature to in-situ if needed (SODA)
    if data["temp_type"] == "potential":
        temp = potential_to_insitu(temp, salt, depth, actual_lat, actual_lon)

    # Compute sound speed
    if formula == "teos10":
        ss = _sound_speed_teos10(temp, salt, depth, actual_lat, actual_lon)
    elif formula == "mackenzie":
        ss = _sound_speed_mackenzie(temp, salt, depth)
    elif formula == "chen_millero":
        ss = _sound_speed_chen_millero(temp, salt, depth, actual_lat)
    else:
        raise ValueError(f"Unknown formula: {formula}")

    # Get ocean depth from GEBCO for feature extraction
    ocean_depth = get_depth(actual_lat, actual_lon)

    # Extract acoustic features
    features = extract_all_features(depth, ss, actual_lat, ocean_depth)

    return {
        "lat": actual_lat,
        "lon": actual_lon,
        "depth": depth.tolist(),
        "sound_speed": ss.tolist(),
        "temperature": temp.tolist(),
        "salinity": salt.tolist(),
        "features": features,
        "source": source,
        "formula": formula,
    }
