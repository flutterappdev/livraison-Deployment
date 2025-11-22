from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction  # <-- Importer transaction
from django.contrib.auth.models import User
from .models import Candidat, ScrapingTask, OrganisationUser

@receiver(post_save, sender=Candidat)
def create_scraping_task_on_commit(sender, instance, created, **kwargs): # Renommer pour la clarté
    if created and not getattr(instance, '_skip_signal', False): # Garder la vérification _skip_signal
        
        # --- SOLUTION ---
        # Ne pas lancer la tâche directement.
        # La programmer pour qu'elle s'exécute après le commit de la transaction.
        def launch_task():
            # Créer la tâche ici, à l'intérieur de la fonction qui sera appelée
            task = ScrapingTask.objects.create(candidat=instance)
            
            # Récupérer l'admin de l'organisation
            org_admin = OrganisationUser.objects.filter(
                organisation=instance.organisation,
                role='admin'
            ).first()
            
            if org_admin:
                from .tasks import run_scraping_task
                # Lancer la tâche Celery avec l'ID de la tâche nouvellement créée
                run_scraping_task.delay(task.id, user_id=org_admin.user.id)

        # Programmer l'exécution de launch_task après le commit
        transaction.on_commit(launch_task)