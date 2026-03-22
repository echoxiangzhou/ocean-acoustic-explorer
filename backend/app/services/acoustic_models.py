"""
Acoustic propagation models for transmission loss (TL) computation.
Pure Python, numpy-vectorized for performance.
"""

import numpy as np
from scipy.interpolate import interp1d


def compute_tl_rays(
    sound_speed_profile: np.ndarray,
    depth_levels: np.ndarray,
    bathymetry: np.ndarray,
    range_km: np.ndarray,
    src_depth: float = 50.0,
    frequency: float = 1000.0,
    num_rays: int = 200,
    max_angles_deg: float = 30.0,
    bottom_loss_db: float = 5.0,
) -> dict:
    """
    Vectorized ray tracing: all rays computed in parallel using numpy.
    """
    nr = len(range_km)
    nz = len(depth_levels)
    max_range_m = range_km[-1] * 1000.0

    # Interpolate sound speed
    valid = ~np.isnan(sound_speed_profile)
    c_interp = interp1d(depth_levels[valid], sound_speed_profile[valid],
                        kind='linear', fill_value='extrapolate')

    c_src = float(c_interp(src_depth))

    # Absorption (Thorp)
    f_khz = frequency / 1000.0
    alpha = (0.11 * f_khz**2 / (1 + f_khz**2)
             + 44 * f_khz**2 / (4100 + f_khz**2)
             + 2.75e-4 * f_khz**2 + 0.003)

    # Launch angles
    angles = np.linspace(-max_angles_deg, max_angles_deg, num_rays) * np.pi / 180.0

    # Vectorized: trace all rays simultaneously
    # State: z[num_rays], r[num_rays], theta[num_rays], bounces[num_rays]
    z = np.full(num_rays, src_depth)
    r = np.zeros(num_rays)
    theta = angles.copy()
    bounces = np.zeros(num_rays)
    active = np.ones(num_rays, dtype=bool)

    # TL accumulator
    energy = np.zeros((nr, nz), dtype=np.float64)

    # Ray paths for visualization (store subset)
    ray_indices = np.linspace(0, num_rays - 1, min(20, num_rays)).astype(int)
    ray_paths = {i: {"r": [0.0], "z": [src_depth]} for i in ray_indices}

    dr = max_range_m / 500  # ~500 steps total
    step = 0
    max_steps = 600

    while np.any(active) and step < max_steps:
        step += 1

        # Sound speed at current depths
        z_clipped = np.clip(z, depth_levels[0], depth_levels[-1])
        c_z = c_interp(z_clipped)

        # Ray parameter (Snell's law): cos(theta)/c = const = cos(theta0)/c_src
        p = np.cos(angles) / c_src  # constant per ray
        cos_theta = p * c_z
        cos_theta = np.clip(cos_theta, -0.9999, 0.9999)
        sin_theta = np.sqrt(1.0 - cos_theta**2)
        sin_theta[theta < 0] *= -1

        # Advance
        dz = sin_theta * dr
        z_new = z + dz
        r_new = r + np.abs(cos_theta) * dr

        # Bottom reflection
        bathy_idx = np.clip((r_new / max_range_m * (nr - 1)).astype(int), 0, nr - 1)
        bottom = bathymetry[bathy_idx]
        hit_bottom = z_new >= bottom
        z_new[hit_bottom] = 2 * bottom[hit_bottom] - z_new[hit_bottom]
        theta[hit_bottom] = -theta[hit_bottom]
        bounces[hit_bottom] += 1

        # Surface reflection
        hit_surface = z_new <= 0
        z_new[hit_surface] = -z_new[hit_surface]
        theta[hit_surface] = -theta[hit_surface]

        # Update angles from Snell's law
        z_clipped_new = np.clip(z_new, depth_levels[0], depth_levels[-1])
        c_new = c_interp(z_clipped_new)
        new_cos = p * c_new
        valid_cos = np.abs(new_cos) < 1.0
        theta[valid_cos] = np.arccos(np.clip(new_cos[valid_cos], -1, 1))
        # Preserve sign
        neg_mask = (sin_theta < 0) & valid_cos
        theta[neg_mask] = -theta[neg_mask]

        z = z_new
        r = r_new

        # Mark finished rays
        active = r < max_range_m

        # Accumulate energy
        r_idx = np.clip((r / max_range_m * (nr - 1)).astype(int), 0, nr - 1)
        z_idx = np.array([np.abs(depth_levels - zi).argmin() for zi in z])

        for i in range(num_rays):
            if 0 <= r_idx[i] < nr and 0 <= z_idx[i] < nz:
                spreading = max(r[i], 1.0)
                abs_loss = alpha * (r[i] / 1000.0)
                bounce_loss = bounces[i] * bottom_loss_db
                ray_energy = 1.0 / spreading * 10**(-abs_loss / 10) * 10**(-bounce_loss / 10)
                energy[r_idx[i], z_idx[i]] += ray_energy

        # Store ray paths
        for i in ray_indices:
            if active[i] and len(ray_paths[i]["r"]) < 500:
                ray_paths[i]["r"].append(float(r[i] / 1000.0))
                ray_paths[i]["z"].append(float(z[i]))

    # Convert energy to TL
    energy[energy == 0] = 1e-30
    tl = -10 * np.log10(energy / energy.max())
    tl = np.clip(tl, 30, 150)

    rays_out = [{"range_km": ray_paths[i]["r"], "depth": ray_paths[i]["z"]}
                for i in ray_indices]

    return {
        "tl": tl.tolist(),
        "rays": rays_out,
        "range_km": range_km.tolist(),
        "depth": depth_levels.tolist(),
    }
