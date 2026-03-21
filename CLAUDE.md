# OceanAcoustic Explorer

## Tech Stack
- **Frontend**: React 19 + TypeScript + CesiumJS + Plotly.js + Zustand
- **Backend**: FastAPI + gsw + xarray + netCDF4
- **WMS**: xpublish + xpublish-wms
- **Infra**: Docker Compose + Nginx + Redis

## Data (ocean-server:/data/nas_data/ocean_acoustic/)
- WOA23 T/S: `t_an`/`s_an`, 0.25°, 57 levels, `decode_times=False`
- GEBCO 2024: `elevation` int16, negative = ocean depth
- Features: 12 months × 6 layers, precomputed from WOA23+GEBCO
- Deck41: CSV point data, `LITH1`/`LITH2` text fields

## Key Code Patterns
- Sound speed: TEOS-10 (gsw) default, also Mackenzie/Chen-Millero
- WOA23 temperature is in-situ; if adding SODA (potential temp), convert first
- All xarray opens of WOA23 must use `decode_times=False`

## Docker Compose
- `docker compose up` on ocean-server
- Data mounted from NAS via bind mount at `/data`
- Nginx routes: `/` → frontend, `/api/` → backend, `/wms` → wms-server
