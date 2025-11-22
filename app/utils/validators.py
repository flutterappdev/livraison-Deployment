import os
from django.core.exceptions import ValidationError
from django.utils import timezone
from .constants import MAX_PHOTO_SIZE, ALLOWED_PHOTO_EXTENSIONS

def validate_photo_size(photo):
    """Valider la taille de la photo"""
    if photo.size > MAX_PHOTO_SIZE:
        raise ValidationError("La taille de l'image ne doit pas dépasser 2MB")

def validate_photo_extension(photo):
    """Valider l'extension de la photo"""
    ext = os.path.splitext(photo.name)[1].lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValidationError("Seuls les formats JPG et PNG sont acceptés")

def validate_passport_dates(issue_date, expiry_date):
    """Valider les dates du passeport"""
    today = timezone.now().date()
    
    if issue_date > today:
        raise ValidationError("La date de délivrance du passeport ne peut pas être dans le futur")
    
    if expiry_date < today:
        raise ValidationError("Le passeport est expiré")
    
    if expiry_date <= issue_date:
        raise ValidationError("La date d'expiration doit être après la date de délivrance du passeport") 