from celery import shared_task
from django.utils import timezone
from .models import ScrapingTask
from .scraping.bls_bot import BLSSpainBot
import logging
from django.contrib.auth.models import User

logger = logging.getLogger(__name__)

@shared_task(
    bind=True,
    max_retries=1,
    ignore_result=True,
    soft_time_limit=900,
    task_track_started=True
)
def run_scraping_task(self, task_id, user_id=None):
    logger.info(f"=== DÉMARRAGE DE LA TÂCHE {task_id} ===")
    task = None
    try:
        # Récupérer et verrouiller la tâche
        from django.db import transaction
        with transaction.atomic():
            task = ScrapingTask.objects.select_for_update().get(id=task_id)
            if task.status == 'running':
                logger.warning(f"La tâche {task_id} est déjà en cours d'exécution")
                return
                
            task.status = 'running'
            task.last_run = timezone.now()
            task.attempts += 1
            task.save()

        logger.info(f"Tâche trouvée pour le candidat: {task.candidat.email}")
        
        # Mettre à jour le statut du candidat
        task.candidat.status = 'processing'
        task.candidat.save()
        
        # Exécuter le bot
        logger.info("Initialisation du bot...")
        user = User.objects.get(id=user_id) if user_id else None
        bot = BLSSpainBot(task.candidat, user=user)
        logger.info("Lancement du scraping...")
        success = bot.run()
        
        if success:
            logger.info("Scraping réussi!")
            task.candidat.status = 'inscription_set'
            task.status = 'completed'
            task.success = True
        else:
            logger.warning("Échec du scraping")
            #task.candidat.status = 'failed'
            task.status = 'failed'
            task.success = False

    except Exception as e:
        logger.error(f"Erreur critique: {str(e)}", exc_info=True)
        if task:
            task.status = 'failed'
            task.success = False
            task.error_message = str(e)
            task.save()
            
            if task.candidat:
                task.candidat.status = 'failed'
                task.candidat.save()
        raise

    finally:
        if task:
            task.save()
            task.candidat.save()
            logger.info(f"=== FIN DE LA TÂCHE {task_id} ===") 

@shared_task(
    bind=True,
    max_retries=1,
    ignore_result=True,
    soft_time_limit=300,
    task_track_started=True
)
def bls_take_appointment_task(self, task_id):
    """Tâche Celery pour gérer la connexion BLS"""
    try:
        task = ScrapingTask.objects.get(id=task_id)
        candidat = task.candidat
        
        # Vérifier que le mot de passe existe
        if not task.new_password:
            logger.error("Pas de mot de passe trouvé dans la base de données")
            task.status = 'failed'
            candidat.status = 'failed'
            task.error_message = "Mot de passe non trouvé. Veuillez d'abord effectuer l'inscription BLS."
            task.save()
            candidat.save()
            return False
        
        # Créer le bot qui configure automatiquement le proxy
        bot = BLSSpainBot(candidat)
        
        try:
            # Initialiser le driver
            driver = bot.browser_handler.initialize_driver()
            if not driver:
                raise Exception("Échec de l'initialisation du driver")
            
            # Se connecter à BLS
            base_url = "https://www.blsspainmorocco.net"
            driver.get(f"{base_url}/MAR/account/Login")
            if not bot.page_handler.connect_to_bls(driver):
                return False

            # Utiliser le mot de passe stocké au lieu du mot de passe temporaire
            task.temp_password = task.new_password  # Utiliser le mot de passe stocké
            if not bot.page_handler.handle_temp_password(driver):
                return False
            
            # aller dans la page pour remplir le formulaire complet de ce candidat
            if not bot.page_handler.go_to_applicant_management(driver):
                return False
            # Remplir le formulaire
            if not bot.page_handler.fill_applicant_form(driver):
                return False
            
            # Book a new appointment
            if not bot.page_handler.book_new_appointment(driver):
                return False
            

            task.status = 'completed'
            candidat.status = 'connected'
            task.success = True
            task.save()
            candidat.save()
            
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la connexion BLS: {str(e)}")
            task.status = 'failed'
            task.error_message = str(e)
            task.save()
            return False

    except ScrapingTask.DoesNotExist:
        logger.error(f"Tâche {task_id} non trouvée")
        return False 
    

