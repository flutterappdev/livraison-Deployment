from django.contrib import messages
from app.tasks import bls_take_appointment_task
from app.models import ScrapingTask
import logging

logger = logging.getLogger(__name__)

def bls_take_appointment(modeladmin, request, queryset):
    """Action admin pour lancer la connexion BLS"""
    count = 0
    errors = []
    
    for candidat in queryset:
        try:
            # Créer ou récupérer la tâche
            task = ScrapingTask.objects.get_or_create(
                candidat=candidat,
                defaults={
                    'status': 'pending',
                    'success': False,
                    'attempts': 0
                }
            )[0]
            
            # Réinitialiser la tâche
            task.status = 'pending'
            task.success = False
            task.error_message = ''
            task.save()
            
            # Lancer la tâche Celery
            result = bls_take_appointment_task.apply_async(
                args=[task.id],
                countdown=0,
                expires=300
            )
            
            logger.info(f"Tâche de connexion {result.id} lancée pour {candidat.email}")
            count += 1
            
        except Exception as e:
            error_msg = f"Erreur lors du lancement de la connexion pour {candidat.email}: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)
    
    # Afficher les messages de succès/erreur
    if count > 0:
        modeladmin.message_user(
            request,
            f"{count} tâche(s) de connexion lancée(s) avec succès.",
            messages.SUCCESS
        )
    
    if errors:
        for error in errors:
            modeladmin.message_user(request, error, messages.ERROR)
            
    if count == 0 and not errors:
        modeladmin.message_user(
            request,
            "Aucune tâche de connexion n'a pu être lancée.",
            messages.WARNING
        )

bls_take_appointment.short_description = "Prendre RDV BLS"

