import os

MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ocean-acoustic")

REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
CELERY_BROKER = os.getenv("CELERY_BROKER", "redis://redis:6379/1")

# Data paths (inside container, mapped from NAS or MinIO)
DATA_DIR = os.getenv("DATA_DIR", "/data")
WOA23_DIR = os.getenv("WOA23_DIR", f"{DATA_DIR}/woa23")
GEBCO_PATH = os.getenv("GEBCO_PATH", f"{DATA_DIR}/gebco/gebco_025deg.nc")
SODA_DIR = os.getenv("SODA_DIR", f"{DATA_DIR}/soda")
HYCOM_DIR = os.getenv("HYCOM_DIR", f"{DATA_DIR}/hycom")
