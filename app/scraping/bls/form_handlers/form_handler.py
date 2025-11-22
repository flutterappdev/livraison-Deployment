import logging

logger = logging.getLogger(__name__)

class BLSFormHandler:
    def __init__(self, ui_handler):
        self.ui_handler = ui_handler

    def fill_form(self, driver, candidat):
        """Remplit le formulaire complet avec les données du candidat"""
        try:
            logger.info("Début du remplissage du formulaire")
            
            self._fill_personal_info(driver, candidat)
            self._fill_passport_info(driver, candidat)
            self._fill_contact_info(driver, candidat)

            logger.info("Formulaire rempli avec succès")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du remplissage du formulaire: {str(e)}")
            return False

    def _fill_personal_info(self, driver, candidat):
        """Remplit les informations personnelles"""
        self.ui_handler.fill_field(driver, "SurName", candidat.last_name)
        self.ui_handler.fill_field(driver, "FirstName", candidat.first_name)
        self.ui_handler.fill_field(driver, "LastName", candidat.first_name)

        birth_date = candidat.date_of_birth.strftime("%Y-%m-%d")
        self.ui_handler.fill_date_field(driver, "DateOfBirth", birth_date)

    def _fill_passport_info(self, driver, candidat):
        """Remplit les informations du passeport"""
        self.ui_handler.fill_field(driver, "ppNo", candidat.passport_number)
        
        issue_date = candidat.passport_issue_date.strftime("%Y-%m-%d")
        expiry_date = candidat.passport_expiry_date.strftime("%Y-%m-%d")
        
        self.ui_handler.fill_date_field(driver, "PassportIssueDate", issue_date)
        self.ui_handler.fill_date_field(driver, "PassportExpiryDate", expiry_date)
        
        passport_type = self._get_passport_type(candidat.passport_type)
        self.ui_handler.select_dropdown(driver, "PassportType", passport_type)
        self.ui_handler.fill_field(driver, "IssuePlace", candidat.passport_issue_place)

    def _fill_contact_info(self, driver, candidat):
        """Remplit les informations de contact"""
        self.ui_handler.select_dropdown(driver, "CountryOfResidence", "Morocco")
        
        phone = candidat.phone_number[4:]  # Enlever l'indicatif pays
        self.ui_handler.fill_field(driver, "Mobile", phone)
        self.ui_handler.fill_field(driver, "Email", candidat.email)

    @staticmethod
    def _get_passport_type(passport_type):
        """Convertit le type de passeport pour le formulaire BLS"""
        passport_types = {
            'ordinary': 'Ordinary Passport',
            'collective': 'Collective Passport',
            'diplomatic': 'Diplomatic Passport',
            'apatridas': 'D. Viaje Apatridas C. New York',
            'government': 'Government official on duty',
            'national': 'National laissez-passer',
            'official': 'Official Passport',
            'foreigners': 'Passport of foreigners',
            'protection': 'Protection passport',
            'refugee': 'Refugee Travel Document (Geneva Convention)',
            'seaman': 'Seaman book',
            'un': 'UN laissez-passer'
        }
        return passport_types.get(passport_type, 'Ordinary Passport') 