from django.db import models
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
from encrypted_model_fields.fields import EncryptedCharField
from django.contrib.auth.models import User, Permission
from django_countries.fields import CountryField
from django.utils import timezone
import re
import logging
from .utils.constants import (
    CANDIDAT_STATUS_CHOICES, CANDIDAT_CATEGORY_CHOICES,
    CANDIDAT_VISA_CHOICES, CANDIDAT_LOCATION_CHOICES,
    PASSPORT_TYPES, PHONE_REGEX, PASSPORT_NUMBER_REGEX,
    SCHENGEN_COUNTRIES, JOURNEY_PURPOSE_CHOICES, CANDIDAT_VISA_SUBTYPE_CHOICES, MARITAL_STATUS_CHOICES, ENTRIES_CHOICES
)
from .utils.validators import (
    validate_photo_size, validate_photo_extension,
    validate_passport_dates
)

logger = logging.getLogger(__name__)

# Utility functions
def profile_photo_path(instance, filename):
    """Générer le chemin pour sauvegarder la photo"""
    return f'photos/user_{instance.id}/{filename}'

# Ajout du modèle de base
class BaseModel(models.Model):
    """Modèle de base avec champs communs"""
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Créé le")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Modifié le")

    class Meta:
        abstract = True

class Organisation(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nom de l'organisation")
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    # Configuration du proxy
    proxy = models.CharField(
        max_length=255,
        verbose_name="Configuration du proxy",
        help_text="Format: username:password@host:port",
        blank=True,
        null=True
    )
    
    def save(self, *args, **kwargs):
        # Si l'organisation est désactivée
        if not self.is_active and self.pk:
            # Désactiver tous les utilisateurs de l'organisation
            User.objects.filter(
                organisationuser__organisation=self
            ).update(is_active=False)
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} ({'Actif' if self.is_active else 'Inactif'})"
    
    class Meta:
        verbose_name = "Organisation"
        verbose_name_plural = "Organisations"

class OrganisationUser(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('staff', 'Staff'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES,
        default='staff'
    )
    
    class Meta:
        unique_together = ('user', 'organisation')


class Candidat(BaseModel):
    # Informations personnelles
    first_name = models.CharField(
        max_length=100,
        verbose_name="Prénom"
    )
    last_name = models.CharField(
        max_length=100,
        verbose_name="Nom de famille"
    )
    email = models.EmailField(
        verbose_name="Email", 
        unique=True
    )
    phone_number = models.CharField(
        max_length=20,
        verbose_name="Numéro de téléphone",
        validators=[
            RegexValidator(
                regex=PHONE_REGEX,
                message="Le numéro doit commencer par +212 et être suivi de 9 chiffres. Ex: +212612345678"
            )
        ],
        help_text="Format: +212612345678"
    )
    date_of_birth = models.DateField(
        verbose_name="Date de naissance",
        null=False,
        blank=False
    )
    profile_photo = models.ImageField(
        upload_to=profile_photo_path,
        verbose_name="Photo de profil",
        help_text="Format accepté : JPG, PNG. Taille max : 2MB",
        validators=[validate_photo_size, validate_photo_extension],
        null=True,
        blank=True
    )

    # Informations de visa
    category = models.CharField(
        max_length=50,
        choices=CANDIDAT_CATEGORY_CHOICES,
        verbose_name="Catégorie"
    )
    location = models.CharField(
        max_length=100,
        choices=CANDIDAT_LOCATION_CHOICES,
        verbose_name="Localisation"
    )
    visa = models.CharField(
        max_length=100,
        choices=CANDIDAT_VISA_CHOICES,
        verbose_name="Type de visa"
    )
    visa_subtype = models.CharField(
        max_length=100,
        choices=CANDIDAT_VISA_SUBTYPE_CHOICES,
        verbose_name="Sous-type de visa",
        default='casa1'
    )

    # Informations de passeport
    passport_number = models.CharField(
        max_length=9,
        validators=[
            RegexValidator(
                regex=PASSPORT_NUMBER_REGEX,
                message="Le numéro de passeport doit contenir 2 lettres majuscules suivies de 7 chiffres (ex: AB1234567)"
            )
        ],
        help_text="Format requis : 2 lettres majuscules suivies de 7 chiffres (ex: AB1234567)"
    )
    passport_type = models.CharField(
        max_length=120,
        choices=PASSPORT_TYPES,
        verbose_name="Type de passeport",
        default='ordinary'
    )
    passport_issue_date = models.DateField(
        verbose_name="Date d'émission du passeport"
    )
    passport_expiry_date = models.DateField(
        verbose_name="Date d'expiration du passeport"
    )
    passport_issue_country = CountryField(
        verbose_name="Pays d'émission du passeport",
        default='MA'
    )
    passport_issue_place = models.CharField(
        max_length=100,
        verbose_name="Lieu d'émission du passeport"
    )
    country_of_residence = CountryField(
        verbose_name="Pays de résidence",
        default='MA'
    )

    # Statut et rendez-vous
    status = models.CharField(
        max_length=100,
        choices=CANDIDAT_STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    appointment_date = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date du rendez-vous"
    )
    appointment_details = models.TextField(
        blank=True,
        verbose_name="Détails du rendez-vous"
    )

    # Nouveaux champs pour les informations personnelles détaillées
    surname_at_birth = models.CharField(
        max_length=100,
        verbose_name="Nom de naissance",
        blank=True,
        null=True
    )
    
    place_of_birth = models.CharField(
        max_length=100,
        verbose_name="Lieu de naissance",
        blank=True
    )
    
    country_of_birth = CountryField(
        verbose_name="Pays de naissance",
        default='MA'
    )
    
    nationality_at_birth = CountryField(
        verbose_name="Nationalité à la naissance",
        default='MA',
        blank=True,
        null=True
    )
    
    current_nationality = CountryField(
        verbose_name="Nationalité actuelle",
        default='MA'
    )
    
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]
    gender = models.CharField(
        max_length=10,
        choices=GENDER_CHOICES,
        verbose_name="Genre",
        default='Male'
    )
    
    marital_status = models.CharField(
        max_length=10,
        choices=MARITAL_STATUS_CHOICES,
        verbose_name="État civil",
        default='single'
    )

    # Informations de voyage
    purpose_of_journey = models.CharField(
        max_length=50,
        choices=JOURNEY_PURPOSE_CHOICES,
        verbose_name="But du voyage",
        help_text="Objectif principal du voyage",
        default='Tourism'
    )

    member_state_destination = models.CharField(
        max_length=50,
        choices=SCHENGEN_COUNTRIES,
        verbose_name="Pays de destination principal",
        default='Spain'
    )

    member_state_second_destination = models.CharField(
        max_length=50,
        choices=SCHENGEN_COUNTRIES,
        verbose_name="Pays de destination secondaire",
        default='Spain',
        blank=True,
        null=True
    )

    member_state_first_entry = models.CharField(
        max_length=50,
        choices=SCHENGEN_COUNTRIES,
        verbose_name="Pays de première entrée",
        default='Spain',
        blank=True,
        null=True
    )


    number_of_entries = models.CharField(
        max_length=1,
        choices=ENTRIES_CHOICES,
        verbose_name="Nombre d'entrées demandées",
        default='1'
    )

    intended_stay_duration = models.PositiveIntegerField(
        verbose_name="Durée prévue du séjour",
        help_text="Durée en jours",
        null=True,
        blank=True
    )

    # Relations
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        verbose_name="Organisation"
    )

    travel_date = models.DateField(
        verbose_name="Date de voyage",
        null=True,
        blank=True,
        help_text="Date prévue du voyage"
    )

    def __init__(self, *args, **kwargs):
        self._skip_signal = kwargs.pop('_skip_signal', False)
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"

    def _validate_phone_number(self):
        """Valide le format du numéro de téléphone"""
        if not self.phone_number.startswith('+212'):
            raise ValidationError({
                'phone_number': "Le numéro de téléphone doit commencer par +212"
            })
        
        if len(self.phone_number) != 13:
            raise ValidationError({
                'phone_number': "Le numéro doit contenir exactement 12 caractères (+212 + 9 chiffres)"
            })

    def _validate_passport(self):
        """Valide le numéro de passeport"""
        if self.passport_number:
            self.passport_number = self.passport_number.upper()
            if not re.match(PASSPORT_NUMBER_REGEX, self.passport_number):
                raise ValidationError({
                    'passport_number': "Le numéro de passeport doit contenir 2 lettres majuscules suivies de 7 chiffres (ex: AB1234567)"
                })

    def _validate_passport_dates(self):
        """Valide les dates du passeport"""
        validate_passport_dates(self.passport_issue_date, self.passport_expiry_date)

    def clean(self):
        """Validation personnalisée du modèle"""
        super().clean()
        
        self._validate_phone_number()
        self._validate_passport()
        self._validate_passport_dates()

    def save(self, *args, **kwargs):
        """Sauvegarde du modèle avec validation"""
        is_new = self.pk is None
        
        try:
            if not self.date_of_birth:
                raise ValidationError("La date de naissance est obligatoire")
            
            self.full_clean()
            super().save(*args, **kwargs)
            
            # Vérification après sauvegarde
            Candidat.objects.get(pk=self.pk)

            # --- CORRECTION : DÉSACTIVER L'ANCIENNE LOGIQUE ---
            # if is_new and not getattr(self, '_skip_signal', False):
            #     self._create_scraping_task()
            
        except Exception as e:
            print(f"Erreur lors de la sauvegarde: {str(e)}")  # Debug
            raise

    def _create_scraping_task(self):
        """Crée et lance une tâche de scraping"""
        from .tasks import run_scraping_task
        task = ScrapingTask.objects.create(candidat=self)
        run_scraping_task.delay(task.id)

    def delete(self, *args, **kwargs):
        # Supprimer le fichier image lors de la suppression de l'instance
        if self.profile_photo:
            storage = self.profile_photo.storage
            if storage.exists(self.profile_photo.name):
                storage.delete(self.profile_photo.name)
        super().delete(*args, **kwargs)

    def get_full_name(self):
        """Retourne le nom complet du candidat"""
        return f"{self.first_name} {self.last_name}"

    class Meta:
        verbose_name = "Demandeur de visa"
        verbose_name_plural = "Demandeurs de visa"

class CarteBancaire(models.Model):
    candidat = models.OneToOneField(
        Candidat,
        on_delete=models.CASCADE,
        verbose_name="Candidat"
    )
    numero = EncryptedCharField(
        max_length=16,
        verbose_name="Numéro de carte"
    )
    date_expiration = models.DateField(
        verbose_name="Date d'expiration",
        help_text="Format: MM/YY (ex: 05/25)"
    )
    cvv = EncryptedCharField(
        max_length=4,
        verbose_name="Code CVV"
    )
    nom_titulaire = models.CharField(
        max_length=100,
        verbose_name="Nom du titulaire"
    )

    def clean(self):
        super().clean()
        if self.date_expiration:
            # Vérifier que la date n'est pas expirée
            today = timezone.now().date()
            if self.date_expiration.replace(day=1) < today.replace(day=1):
                raise ValidationError({
                    'date_expiration': "La carte est expirée"
                })

    class Meta:
        verbose_name = "Carte bancaire"
        verbose_name_plural = "Cartes bancaires"

    def __str__(self):
        return f"Carte de {self.nom_titulaire} (**** **** **** {self.numero[-4:]})"

class OrganisationRole(models.Model):
    name = models.CharField(max_length=100)
    permissions = models.ManyToManyField(Permission)
    organisation = models.ForeignKey(Organisation, on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Rôle d'organisation"
        verbose_name_plural = "Rôles d'organisation"
        unique_together = ('name', 'organisation')

    def __str__(self):
        return f"{self.name} ({self.organisation.name})"

class ScrapingTask(BaseModel):
    STATUS_CHOICES = [
        ('pending', 'En attente'),
        ('running', 'En cours'),
        ('waiting_otp', 'En attente OTP'),
        ('waiting_password', 'En attente mot de passe'),
        ('waiting_data_protection', 'En attente URL de protection des données'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]

    candidat = models.OneToOneField(
        Candidat,
        on_delete=models.CASCADE,
        related_name='scraping_task',
        verbose_name="Candidat"
    )
    status = models.CharField(
        max_length=50,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name="Statut"
    )
    last_run = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Dernière exécution"
    )
    next_run = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="Prochaine exécution"
    )
    error_message = models.TextField(
        blank=True,
        verbose_name="Message d'erreur"
    )
    attempts = models.IntegerField(
        default=0,
        verbose_name="Tentatives"
    )
    success = models.BooleanField(
        default=False,
        verbose_name="Succès"
    )
    otp = models.CharField(
        max_length=10, 
        blank=True, 
        null=True,
        help_text="Code OTP reçu"
    )
    temp_password = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        verbose_name="Mot de passe temporaire"
    )
    new_password = models.CharField(
        max_length=50, 
        blank=True, 
        null=True,
        help_text="Nouveau mot de passe BLS"
    )
    data_protection_url = models.URLField(
        verbose_name="URL de confirmation protection des données",
        blank=True,
        null=True,
        max_length=2000
    )

    class Meta:
        verbose_name = "Tâche de rendez-vous"
        verbose_name_plural = "Tâches de rendez-vous"

    def __str__(self):
        return f"Tâche pour {self.candidat.get_full_name()} ({self.get_status_display()})"
