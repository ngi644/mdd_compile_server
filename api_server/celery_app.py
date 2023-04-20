# api_server/celery_app.py

from celery import Celery
from shared.celery_config import broker_url, result_backend

app = Celery("tasks", broker=broker_url, backend=result_backend)
app.config_from_object("shared.celery_config") # load settings form 'shared/celery_config.py'
