from celery import Celery
from app.config import CELERY_BROKER

celery_app = Celery("ocean_acoustic", broker=CELERY_BROKER)
celery_app.conf.result_backend = CELERY_BROKER
