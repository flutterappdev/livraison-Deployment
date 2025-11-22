# Constants for model choices
CANDIDAT_STATUS_CHOICES = [
    ('pending', 'En attente de traitement'),
    ('processing', 'En cours de traitement'),
    ('waiting_otp', 'En attente OTP'),
    ('waiting_password', 'En attente mot de passe'),
    ('inscription_set', 'Inscription BLS réussie'),
    ('appointment_booked', 'Rendez-vous pris'), # <-- AJOUTER CETTE LIGNE
    ('failed', 'Échec'),
    ('connected', 'Connecté'),
    ('waiting_data_protection', 'En attente URL de protection des données'),
    ('passport_already_used', ' Erreur - Passeport déjà utilisé '),
    ('mobile_number_already_used', ' Erreur - Numéro de téléphone déjà utilisé '),
]

CANDIDAT_CATEGORY_CHOICES = [
    ('normal', 'Normal'),
    ('premium', 'Premium'),
    ('prime_time', 'Prime Time'),
]

MARITAL_STATUS_CHOICES = [
        ('Single', 'Single'),
        ('Married', 'Married'),
        ('Divorced', 'Divorced'),
        ('Widowed', 'Widowed'),
        ('Separated', 'Separated'),
    ]

ENTRIES_CHOICES = [
        ('1', 'Single Entry'),
        ('2', 'Double Entry'),
        ('M', 'Multiple Entry'),
    ]
# Tous les choix combinés pour le modèle
CANDIDAT_VISA_CHOICES = [
    ('sch', 'Schengen Visa'),
    ('std', 'Étudiant'),
    ('famr', 'Regroupement familial'),
    ('nat', 'National Visa'),
    ('work', 'Travail'),
    ('casa1', 'Casa 1'),
    ('casa2', 'Casa 2'),
    ('casa3', 'Casa 3'),
]

CANDIDAT_VISA_SUBTYPE_CHOICES = [
    ('casa1', 'Casa 1'),
    ('casa2', 'Casa 2'),
    ('casa3', 'Casa 3'),
    ('nat', 'National Visa'),
    ('sch', 'Schengen Visa'),
    ('std', 'Étudiant'),
    ('famr', 'Regroupement familial'),
    ('work', 'Travail'),
]

CANDIDAT_LOCATION_CHOICES = [
    ('rabat', 'Rabat'),
    ('casa', 'Casablanca'),
    ('tangier', 'Tangier'),
    ('tetouan', 'Tetouan'),
    ('nador', 'Nador'),
    ('agadir', 'Agadir'),
]

PASSPORT_TYPES = [
    ('Ordinary Passport', 'Ordinary Passport'),
    ('Collective Passport', 'Collective Passport'),
    ('Diplomatic Passport', 'Diplomatic Passport'),
    ('D. Viaje Apatridas C. New York', 'D. Viaje Apatridas C. New York'),
    ('Government official on duty', '   '),
    ('National laissez-passer', 'National laissez-passer'),
    ('Official Passport', 'Official Passport'),
    ('Passport of foreigners', 'Passport of foreigners'),
    ('Protection passport', 'Protection passport'),
    ('Refugee Travel Document (Geneva Convention)', 'Refugee Travel Document (Geneva Convention)'),
    ('Seaman book', 'Seaman book'),
    ('UN laissez-passer', 'UN laissez-passer'),
]

# Validation constants
PHONE_REGEX = r'^\+212[5-7][0-9]{8}$'
PASSPORT_NUMBER_REGEX = r'^[A-Z]{2}\d{7}$'
MAX_PHOTO_SIZE = 2 * 1024 * 1024  # 2MB
ALLOWED_PHOTO_EXTENSIONS = ['.jpg', '.jpeg', '.png'] 

# Mapping des codes pays vers les noms complets pour BLS
SCHENGEN_COUNTRIES = [
    ('Spain', 'Spain'),
    ('France', 'France'),
    ('Germany', 'Germany'),
    ('Italy', 'Italy'),
    ('Portugal', 'Portugal'),
    ('Netherlands', 'Netherlands'),
    ('Belgium', 'Belgium'),
    ('Luxembourg', 'Luxembourg'),
    ('Switzerland', 'Switzerland'),
    ('Austria', 'Austria'),
    ('Denmark', 'Denmark'),
    ('Sweden', 'Sweden'),
    ('Norway', 'Norway'),
    ('Finland', 'Finland'),
    ('Iceland', 'Iceland'),
    ('Greece', 'Greece'),
    ('Czech Republic', 'Czech Republic'),
    ('Hungary', 'Hungary'),
    ('Poland', 'Poland'),
    ('Estonia', 'Estonia'),
    ('Latvia', 'Latvia'),
    ('Lithuania', 'Lithuania'),
    ('Malta', 'Malta'),
    ('Slovenia', 'Slovenia'),
    ('Slovakia', 'Slovakia'),
]

# Mapping pour les types de voyage
JOURNEY_PURPOSE_CHOICES = [
    ('Tourism', 'Tourism'),
    ('Airport Transit', 'Airport Transit'),
    ('Business', 'Business'),
    ('Study', 'Study'),
    ('Cultural reasons', 'Cultural reasons'),
    ('Sports', 'Sports'),
    ('Official visit', 'Official visit'),
    ('Medical reasons', 'Medical reasons'),
    ('Transit', 'Transit'),
    ('Visiting family', 'Visiting family'),
    ('Others', 'Others')
] 