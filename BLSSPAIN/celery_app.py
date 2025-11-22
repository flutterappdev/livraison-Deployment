import os
from celery import Celery
import logging

logger = logging.getLogger(__name__)

# Définir les variables d'environnement Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BLSSPAIN.settings')

# Créer l'instance Celery
app = Celery('BLSSPAIN')

# Configuration de base
app.config_from_object('django.conf:settings', namespace='CELERY')

# Configuration avancée
app.conf.update(
    worker_max_tasks_per_child=1,
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_track_started=True
)

# Découverte automatique des tâches
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    logger.info(f'Request: {self.request!r}') 