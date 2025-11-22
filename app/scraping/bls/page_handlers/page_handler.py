import logging
import time
from datetime import datetime # Assurez-vous d'importer datetime

from selenium.common import TimeoutException, JavascriptException, WebDriverException, ElementClickInterceptedException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from django.apps import apps
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.keys import Keys
from selenium.common.exceptions import NoSuchElementException
from app.scraping.bls.ui_handlers.kendo_ui import KendoUIHandler
from app.scraping.captcha.ocr_solver import OCRCaptchaSolver
import random # <-- Ajoutez cet import en haut
from app.utils.constants import CANDIDAT_VISA_CHOICES, CANDIDAT_LOCATION_CHOICES, CANDIDAT_VISA_SUBTYPE_CHOICES, \
    CANDIDAT_CATEGORY_CHOICES

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self, candidat, user=None):
        self.candidat = candidat
        self._task = None
        self.user = user  # L'utilisateur connecté passé en paramètre

    def get_task(self):
        if not self._task:
            ScrapingTask = apps.get_model('app', 'ScrapingTask')
            # Utiliser get_or_create pour éviter les erreurs si la tâche n'existe pas encore
            # Bien que dans ce flux, elle devrait déjà exister.
            self._task, _ = ScrapingTask.objects.get_or_create(candidat=self.candidat)
        return self._task

    def update_status(self, task_status, candidat_status=None):
        task = self.get_task()
        task.status = task_status
        task.save(update_fields=['status']) # Optimisation: ne met à jour que le champ status
        
        if candidat_status:
            self.candidat.status = candidat_status
            self.candidat.save(update_fields=['status']) # Optimisation

    def wait_for_input(self, field_name, max_attempts=30, interval=10):
        try:
            task = self.get_task()
            
            for attempt in range(max_attempts):
                task.refresh_from_db() # Important pour obtenir la dernière version de la tâche
                value = getattr(task, field_name)
                if value:
                    logger.info(f"{field_name} reçu ('{value}')")
                    return value
                logger.debug(f"En attente de {field_name}... Tentative {attempt + 1}/{max_attempts}")
                time.sleep(interval)
            
            logger.error(f"Timeout en attendant {field_name} pour la tâche {task.id}")
            return None

        except Exception as e:
            logger.error(f"Erreur en attendant {field_name} pour la tâche (probable ID: {getattr(self._task, 'id', 'N/A')}): {str(e)}")
            return None

class BLSPageHandler:
    def __init__(self, wait_for, base_url, user=None):
        self.wait_for = wait_for
        self.base_url = base_url
        self.candidat = None
        self.captcha_solver = OCRCaptchaSolver(wait_for)
        self.task_manager = None
        self.ui_handler = KendoUIHandler(wait_for)
        self.user = user  # L'utilisateur connecté

    def set_candidat(self, candidat):
        """Initialise le candidat et le task manager"""
        self.candidat = candidat
        self.task_manager = TaskManager(candidat, self.user)

    def start_registration(self, driver):
        """Commence le processus d'inscription"""
        try:
            driver.get(f"{self.base_url}/MAR/account/RegisterUser")
            logger.info(f"Page d'inscription ouverte: {driver.current_url}")

            # Accepter les cookies et la protection des données
            try:
                # 1. Accepter les cookies
                # Chercher le bouton d'acceptation des cookies de manière plus robuste
                cookie_buttons = driver.find_elements(By.CSS_SELECTOR, "button.btn.btn-success.btn-block")
                if cookie_buttons:
                    accept_button = self.wait_for(driver).until(
                        EC.element_to_be_clickable(cookie_buttons[0]) # Prendre le premier s'il y en a plusieurs
                    )
                    driver.execute_script("arguments[0].click();", accept_button)
                    logger.info("Cookies acceptés (si présents)")
                else:
                    logger.info("Pas de bouton de cookies trouvé ou déjà accepté.")

                # Attendre un peu que le modal de protection des données apparaisse potentiellement
                time.sleep(1) 

                # 2. Accepter la protection des données (si le modal est présent)
                modals_protection = driver.find_elements(By.CSS_SELECTOR, "div.modal.show #dataProtection")
                if modals_protection:
                    modal_protection = modals_protection[0]
                    self.wait_for(driver).until(EC.visibility_of(modal_protection))
                    logger.info("Modal de protection des données visible")

                    modal_body = modal_protection.find_element(By.CSS_SELECTOR, "div.modal-body")
                    driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal_body)

                    # Le bouton est dans ce modal spécifique
                    protect_data_button = modal_protection.find_element(
                        By.CSS_SELECTOR, 
                        "button.btn.btn-success.btn-block"
                    )
                    driver.execute_script("arguments[0].click();", protect_data_button)
                    logger.info("Protection des données acceptée")
                else:
                    logger.info("Pas de modal de protection des données trouvé ou déjà accepté.")


            except TimeoutException:
                logger.info("Timeout lors de l'acceptation des cookies/data protection (peut-être non présents).")
            except Exception as e:
                logger.info(f"Erreur mineure lors de l'acceptation des cookies/data protection: {str(e)}")

            return True

        except Exception as e:
            logger.error(f"Erreur majeure au démarrage de l'inscription: {str(e)}")
            return False


    def wait_for_form(self, driver):
        """Attend que le formulaire soit chargé"""
        try:
            self.wait_for(driver).until(
                EC.presence_of_element_located((By.ID, "SurName"))
            )
            logger.info("Formulaire d'inscription (champ SurName) est présent.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de l'attente du formulaire d'inscription: {str(e)}")
            return False

    def initialize_session(self, driver):
        """Initialise la session en allant sur une page BLS."""
        try:
            # Utiliser une page moins susceptible de provoquer des popups initiaux si possible
            # Mais newappointment est souvent la page cible pour démarrer
            driver.get(f"{self.base_url}/MAR/appointment/newappointment")
            # --- AJOUTER UN COMPORTEMENT HUMAIN ---
            # Attendre un temps aléatoire court pour simuler le temps de lecture
            time.sleep(random.uniform(2.5, 5.0))
            # ------------------------------------
            logger.info("Page BLS chargée et attente initiale effectuée.")
            logger.info(f"Page BLS chargée pour initialisation: {driver.current_url}")
            # Gérer les popups initiaux ici aussi, au cas où
            self._handle_initial_popups(driver)
            return True
        except Exception as e:
            if self.candidat: # Vérifier si candidat est initialisé
                self.candidat.status = 'failed'
                self.candidat.save(update_fields=['status'])
            logger.error(f"Erreur lors de l'initialisation de la session: {str(e)}")
            return False
            
    def _handle_initial_popups(self, driver):
        """Gère les popups de cookies et de protection des données."""
        try:
            # Attendre un court instant pour que les popups apparaissent
            time.sleep(1) # Ajuster si nécessaire

            # Accepter les cookies si le bouton est présent et cliquable
            cookie_buttons = driver.find_elements(By.XPATH, "//button[contains(text(), 'Accept') or contains(text(), 'Accepter') or contains(@class, 'cookie-accept')]") # Sélecteur plus générique
            for btn in cookie_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        driver.execute_script("arguments[0].click();", btn)
                        logger.info("Bouton de cookies cliqué.")
                        time.sleep(0.5) # Attendre que le popup disparaisse
                        break 
                    except Exception:
                        pass # Continuer si un bouton n'est pas cliquable

            # Accepter la protection des données si le modal est présent
            # Chercher un modal qui contient "data protection" ou "protection des données"
            data_protection_modals = driver.find_elements(By.CSS_SELECTOR, "div.modal.show")
            for modal in data_protection_modals:
                if "data protection" in modal.text.lower() or "protection des données" in modal.text.lower():
                    if modal.is_displayed():
                        logger.info("Modal de protection des données trouvé.")
                        try:
                            modal_body = modal.find_element(By.CSS_SELECTOR, "div.modal-body")
                            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", modal_body)
                            
                            accept_button_protection = modal.find_element(By.CSS_SELECTOR, "button.btn-success, button.btn-primary") # Chercher un bouton de succès ou primaire
                            driver.execute_script("arguments[0].click();", accept_button_protection)
                            logger.info("Bouton d'acceptation de la protection des données cliqué.")
                            time.sleep(0.5)
                            break
                        except Exception:
                            logger.warning("Impossible de gérer le modal de protection des données.")
                            
        except Exception as e:
            logger.info(f"Erreur mineure lors de la gestion des popups initiaux: {str(e)}")


    def handle_otp(self, driver):
        """Gère le processus OTP"""
        try:
            driver.execute_script("window.scrollBy(0, 200);")
            generate_btn = self.wait_for(driver).until(EC.element_to_be_clickable((By.ID, "btnGenerate")))
            generate_btn.click()
            logger.info("Bouton Generate OTP cliqué")

            try:
                validation_summary = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.validation-summary.text-danger")) # Plus générique pour les erreurs
                )
                error_messages = validation_summary.find_elements(By.CSS_SELECTOR, "ul > li")
                if error_messages:
                    for error in error_messages:
                        error_text = error.text
                        logger.error(f"Erreur de validation BLS : {error_text}")
                        if 'passport number you entered is already exists' in error_text.lower():
                            self.task_manager.update_status('failed', 'passport_already_used')
                        elif 'mobile number already exist' in error_text.lower():
                            self.task_manager.update_status('failed', 'mobile_number_already_used')
                        else:
                            self.task_manager.update_status('failed', 'failed')
                    return False
            except TimeoutException:
                logger.info("Aucun message d'erreur de validation trouvé après avoir cliqué sur Generate OTP.")
            
            # Attendre que le modal de confirmation OTP soit visible (souvent un popup simple)
            # Le site BLS utilise souvent des alertes JS pour cela, ou un simple message.
            # S'il y a un vrai modal :
            try:
                modal_otp_confirm = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.CSS_SELECTOR, "div.modal-content #OTPGenerateModalLabel")) # Exemple, à adapter
                )
                logger.info("Modal de confirmation d'envoi OTP visible.")
                ok_button = modal_otp_confirm.find_element(By.XPATH, ".//button[contains(text(),'OK') or @data-dismiss='modal']")
                ok_button.click()
                logger.info("Modal de confirmation d'envoi OTP fermé.")
            except TimeoutException:
                logger.info("Pas de modal de confirmation d'envoi OTP trouvé, ou il s'est fermé rapidement.")

            self.task_manager.update_status('waiting_otp', 'waiting_otp')
            otp = self.task_manager.wait_for_input('otp')
            if not otp:
                logger.error("Pas d'OTP reçu de l'admin après l'attente.")
                self.task_manager.update_status('failed', 'failed')
                return False

            otp_input = self.wait_for(driver).until(EC.presence_of_element_located((By.ID, "EmailOtp")))
            otp_input.clear()
            otp_input.send_keys(otp)
            logger.info("OTP saisi.")
            
            submit_btn_otp = self.wait_for(driver).until(EC.element_to_be_clickable((By.ID, "btnSubmit"))) # Souvent ID=btnSubmit ou btnVerify
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_btn_otp)
            time.sleep(0.5) # Laisser le scroll finir
            submit_btn_otp.click()
            logger.info("Formulaire OTP soumis.")

            # Attendre le bouton "Go to login page" ou une redirection
            try:
                cont_btn = WebDriverWait(driver, 10).until(EC.element_to_be_clickable((By.ID, "contBtn")))
                cont_btn.click()
                logger.info("Clic sur 'Go to login page' effectué.")
            except TimeoutException:
                logger.info("Pas de bouton 'Go to login page' explicite, vérification de l'URL pour la page de login.")
                if "/MAR/account/Login" not in driver.current_url: # Si on n'est pas redirigé
                    logger.error("Redirection vers la page de login échouée après soumission OTP.")
                    # Vérifier s'il y a un message d'erreur OTP invalide
                    try:
                        error_otp_msg = driver.find_element(By.CSS_SELECTOR, ".validation-summary-errors, .text-danger") # Exemple
                        if "invalid otp" in error_otp_msg.text.lower(): # Adapter le message
                             logger.error(f"Erreur OTP invalide: {error_otp_msg.text}")
                             self.task_manager.update_status('failed', 'failed') # Ou un statut plus spécifique
                             return False
                    except NoSuchElementException:
                        pass # Pas de message d'erreur spécifique trouvé

                    self.task_manager.update_status('failed', 'failed')
                    return False
            
            # Sur la page de login, entrer l'email et cliquer sur "Verify" ou "Continue"
            self.wait_for(driver).until(lambda d: "/MAR/account/Login" in d.current_url) # Attendre d'être sur la page de login
            
            email_inputs_login = self.wait_for(driver).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='text'].form-control, input[name='Email']")) # Sélecteurs plus larges
            )
            email_field_found_login = False
            for input_field in email_inputs_login:
                if input_field.is_displayed() and input_field.is_enabled():
                    try:
                        input_field.clear()
                        input_field.send_keys(self.candidat.email)
                        logger.info(f"Email saisi sur la page de login: {self.candidat.email}")
                        email_field_found_login = True
                        break
                    except Exception as e_fill:
                        logger.warning(f"Impossible de remplir un champ email potentiel: {e_fill}")
            
            if not email_field_found_login:
                logger.error("Aucun champ email utilisable trouvé sur la page de login.")
                self.task_manager.update_status('failed', 'failed')
                return False

            verify_button_login = self.wait_for(driver).until(
                EC.element_to_be_clickable((By.ID, "btnVerify")) # Ou autre ID/sélecteur
            )
            verify_button_login.click()
            logger.info("Bouton 'Verify' sur la page de login cliqué.")
            return True

        except Exception as e:
            logger.error(f"Erreur majeure lors du processus d'OTP: {str(e)}", exc_info=True)
            self.task_manager.update_status('failed', 'failed')
            return False

    def wait_for_otp_input(self):
        """Attend la saisie de l'OTP"""
        # Le statut est déjà mis à jour par handle_otp avant d'appeler cette méthode
        return self.task_manager.wait_for_input('otp')
    
    def connect_to_bls(self, driver):
        """Connecte le candidat à BLS (partie login après redirection)"""
        try:
            self.wait_for(driver).until(lambda d: "/MAR/account/Login" in d.current_url) # S'assurer qu'on est sur la page de login
            logger.info(f"Tentative de connexion à BLS sur {driver.current_url}")
            self._handle_initial_popups(driver) # Gérer les popups au cas où

            email_inputs = self.wait_for(driver).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "input[type='text'].form-control, input[name='Email']"))
            )
            email_field_found = False
            for input_field in email_inputs:
                if input_field.is_displayed() and input_field.is_enabled():
                    try:
                        input_field.clear()
                        input_field.send_keys(self.candidat.email)
                        logger.info(f"Email saisi pour la connexion: {self.candidat.email}")
                        email_field_found = True
                        break
                    except Exception as e_fill:
                        logger.warning(f"Impossible de remplir un champ email potentiel pour la connexion: {e_fill}")
            
            if not email_field_found:
                logger.error("Aucun champ email utilisable trouvé pour la connexion.")
                return False

            verify_btn = self.wait_for(driver).until(EC.element_to_be_clickable((By.ID, "btnVerify"))) # Ajuster si l'ID est différent
            verify_btn.click()
            logger.info("Bouton 'Verify' cliqué pour la connexion.")
            return True
        except Exception as e:
            logger.error(f"Erreur lors de la connexion (phase email) à BLS: {str(e)}")
            return False

    def handle_temp_password(self, driver):
        """Gère la saisie du mot de passe et la résolution du captcha."""
        try:
            logger.info("Attente du champ mot de passe et du captcha...")
            # Attendre que la page de saisie du mot de passe soit chargée (souvent avec un captcha)
            self.wait_for(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
            self.wait_for(driver).until(EC.visibility_of_element_located((By.ID, "captcha-main-div"))) # Ou le sélecteur du captcha

            self.task_manager.update_status('waiting_password', 'waiting_password') # Statut pour l'admin
            
            # Le mot de passe attendu ici est celui qui sera utilisé pour se connecter
            # Dans le flux d'inscription, c'est le mot de passe temporaire reçu par email.
            # Dans le flux de prise de RDV, c'est le `new_password` stocké après l'inscription.
            task = self.task_manager.get_task()
            password_to_use = task.temp_password # temp_password est mis à jour avec new_password dans la tâche Celery avant d'appeler ceci pour la prise de RDV.

            if not password_to_use:
                logger.error("Aucun mot de passe (temporaire ou nouveau) à utiliser n'est disponible.")
                self.task_manager.update_status('failed', 'failed')
                return False

            max_login_attempts = 5 # Nombre de tentatives pour le login (mot de passe + captcha)
            for attempt in range(max_login_attempts):
                logger.info(f"Tentative de login {attempt + 1}/{max_login_attempts} avec le mot de passe et captcha.")
                
                password_input = self.wait_for(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                password_input.clear()
                password_input.send_keys(password_to_use)
                logger.info("Mot de passe saisi.")

                # Déclencher les événements JS après la saisie
                driver.execute_script(
                    "arguments[0].dispatchEvent(new Event('input', { bubbles: true }));"
                    "arguments[0].dispatchEvent(new Event('change', { bubbles: true }));",
                    password_input
                )

                if not self.captcha_solver.solve(driver): # Le solveur doit gérer le clic sur le submit du captcha
                    logger.warning(f"Tentative {attempt + 1}: Échec de la résolution du captcha. Réessai...")
                    # Recharger la page ou le captcha si nécessaire (le solveur peut le faire)
                    try:
                        refresh_captcha_btn = driver.find_element(By.ID, "captcha-refresh-button") # Exemple
                        refresh_captcha_btn.click()
                        time.sleep(1)
                    except NoSuchElementException:
                        driver.refresh() # Si pas de bouton de refresh, recharger la page
                        self.wait_for(driver).until(EC.visibility_of_element_located((By.CSS_SELECTOR, "input[type='password']")))
                        self.wait_for(driver).until(EC.visibility_of_element_located((By.ID, "captcha-main-div")))
                    continue # Recommencer la boucle de tentative de login

                # Après que captcha_solver.solve() a soumis, vérifier si on a quitté la page de login
                try:
                    WebDriverWait(driver, 5).until_not(
                        EC.url_contains("/MAR/account/Login") # Attendre de ne plus être sur la page de login
                    )
                    logger.info("Login (mot de passe + captcha) réussi. Redirection effectuée.")
                    self.task_manager.update_status('running', 'processing') # Mettre à jour si ce n'est pas le flux d'inscription
                    return True
                except TimeoutException:
                    logger.warning(f"Tentative {attempt + 1}: Toujours sur la page de login après soumission captcha. Vérification des erreurs...")
                    # Vérifier les messages d'erreur (mot de passe incorrect, captcha incorrect)
                    try:
                        error_login_msg = driver.find_element(By.CSS_SELECTOR, ".validation-summary-errors, .text-danger, #errorMsg") # Exemples de sélecteurs
                        if error_login_msg.is_displayed():
                            logger.error(f"Message d'erreur de login: {error_login_msg.text}")
                            if "invalid password" in error_login_msg.text.lower() or "incorrect password" in error_login_msg.text.lower():
                                self.task_manager.update_status('failed', 'failed') # Ou un statut plus spécifique
                                return False # Mot de passe incorrect, inutile de réessayer
                            # Si c'est une erreur de captcha, la boucle de tentative continue
                    except NoSuchElementException:
                        logger.info("Aucun message d'erreur spécifique trouvé. Le captcha était peut-être incorrect.")
                    
                    # Si on est toujours sur la page de login, le captcha était probablement incorrect, ou un autre problème.
                    # La boucle va recommencer.
            
            logger.error(f"Échec du login après {max_login_attempts} tentatives.")
            self.task_manager.update_status('failed', 'failed')
            return False

        except Exception as e:
            logger.error(f"Erreur majeure lors de la gestion du mot de passe temporaire/login: {str(e)}", exc_info=True)
            self.task_manager.update_status('failed', 'failed')
            return False

    def handle_password_change(self, driver):
        """Gère le processus de changement de mot de passe (uniquement dans le flux d'inscription)."""
        try:
            # S'assurer qu'on est sur la page de changement de mot de passe
            self.wait_for(driver).until(EC.url_contains("/MAR/account/ChangeUserPassword"))
            logger.info("Sur la page de changement de mot de passe.")

            # Le statut waiting_password est déjà mis par handle_temp_password si c'est ce flux.
            # Sinon, si on arrive directement ici (peu probable), il faudrait le mettre.
            
            task = self.task_manager.get_task()
            temp_password_from_email = task.temp_password # Le mot de passe temporaire initial
            new_password_chosen_by_admin = task.new_password # Le nouveau mot de passe défini par l'admin

            if not temp_password_from_email or not new_password_chosen_by_admin:
                logger.error("Mots de passe temporaire ou nouveau non disponibles pour le changement.")
                self.task_manager.update_status('failed', 'failed')
                return False

            current_password_field = self.wait_for(driver).until(EC.visibility_of_element_located((By.NAME, "CurrentPassword")))
            new_password_field = driver.find_element(By.NAME, "NewPassword")
            confirm_password_field = driver.find_element(By.NAME, "ConfirmPassword")

            current_password_field.send_keys(temp_password_from_email)
            new_password_field.send_keys(new_password_chosen_by_admin)
            confirm_password_field.send_keys(new_password_chosen_by_admin)
            logger.info("Champs de changement de mot de passe remplis.")

            submit_btn_change_pwd = driver.find_element(By.CSS_SELECTOR, "form[action='/MAR/account/ChangeUserPassword'] button[type='submit']")
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_btn_change_pwd)
            time.sleep(0.5)
            submit_btn_change_pwd.click()
            logger.info("Formulaire de changement de mot de passe soumis.")
            
            # Attendre la redirection ou un message de succès.
            # Par exemple, attendre d'être redirigé vers le tableau de bord (myappointments)
            WebDriverWait(driver, 15).until(EC.url_contains("/MAR/appointmentdata/myappointments"))
            logger.info("Changement de mot de passe réussi et redirection vers le tableau de bord.")
            
            # À ce stade, le statut de la tâche est toujours 'running' (venant de handle_temp_password),
            # et le statut du candidat 'processing'. La tâche Celery mettra à jour à 'completed' et 'inscription_set'.
            return True

        except Exception as e:
            logger.error(f"Erreur lors du changement de mot de passe: {str(e)}", exc_info=True)
            self.task_manager.update_status('failed', 'failed')
            return False

    def go_to_applicant_management(self, driver):
        """Aller à la page de gestion des candidats et ouvrir le modal de modification."""
        try:
            target_url = f"{self.base_url}/MAR/appointmentdata/myappointments"
            if driver.current_url != target_url:
                 driver.get(target_url)
            logger.info("Page de gestion des candidats (myappointments) chargée.")
            self._handle_initial_popups(driver)

            edit_link = self.wait_for(driver).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[title='Edit/Complete Applicant Details']"))
            )
            
            onclick_attr = edit_link.get_attribute('onclick')
            # Regex plus robuste pour extraire l'ID, supposant qu'il est entre guillemets simples
            import re
            match = re.search(r"ManageApplicant\('([^']+)'", onclick_attr)
            if not match:
                logger.error("Impossible d'extraire applicant_id de l'attribut onclick.")
                return False
            applicant_id = match.group(1)
            
            driver.execute_script(f"ManageApplicant('{applicant_id}','','');")
            logger.info(f"Fonction ManageApplicant appelée avec ID: {applicant_id}")

            # Attendre que le modal (fenêtre Kendo) soit visible et que son contenu soit chargé
            modal_kendo_window = self.wait_for(driver).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.k-window-content.k-content.k-window-iframecontent"))
            )
            self.wait_for(driver).until(lambda d: modal_kendo_window.get_attribute("data-role") == "window") # S'assurer que Kendo l'a initialisé
            
            logger.info("Modal Kendo (Edit Applicant) détecté.")
            
            # Sélection des options dans le modal (Location, VisaType)
            # Cette partie est souvent à l'extérieur de l'iframe du formulaire principal
            location_mapping = dict(CANDIDAT_LOCATION_CHOICES)
            visa_mapping = dict(CANDIDAT_VISA_CHOICES)

            location_value_to_select = location_mapping.get(self.candidat.location)
            if location_value_to_select:
                if not self.ui_handler.select_dropdown(driver, "LocationId", location_value_to_select): # ID du dropdown
                    logger.error(f"Échec de la sélection de la localisation: {location_value_to_select}")
                    return False
                logger.info(f"Localisation sélectionnée : {location_value_to_select}")
            else:
                logger.error(f"Valeur de localisation non trouvée dans le mapping pour : {self.candidat.location}")
                return False


            visa_type_value_to_select = visa_mapping.get(self.candidat.visa)
            if visa_type_value_to_select:
                if not self.ui_handler.select_dropdown(driver, "VisaType", visa_type_value_to_select): # ID du dropdown
                    logger.error(f"Échec de la sélection du type de visa: {visa_type_value_to_select}")
                    return False
                logger.info(f"Type de visa sélectionné : {visa_type_value_to_select}")
            else:
                logger.error(f"Valeur de type de visa non trouvée dans le mapping pour : {self.candidat.visa}")
                return False

            # Cliquer sur "Proceed" ou "Continuer"
            # Le bouton peut avoir un ID, un onclick spécifique, ou être identifié par son texte
            proceed_buttons = driver.find_elements(By.XPATH, "//button[contains(text(),'Proceed') or contains(text(),'Continuer') or @onclick='VisaTypeProceed();']")
            proceed_button_found = False
            for btn in proceed_buttons:
                if btn.is_displayed() and btn.is_enabled():
                    try:
                        self.wait_for(driver).until(EC.element_to_be_clickable(btn))
                        driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", btn)
                        time.sleep(0.5)
                        btn.click()
                        logger.info("Bouton 'Proceed/Continuer' cliqué.")
                        proceed_button_found = True
                        break
                    except ElementClickInterceptedException:
                        logger.warning("Bouton 'Proceed' intercepté, tentative de clic JS.")
                        driver.execute_script("arguments[0].click();", btn)
                        proceed_button_found = True
                        break
                    except Exception as e_click:
                        logger.warning(f"Impossible de cliquer sur un bouton Proceed potentiel: {e_click}")
            
            if not proceed_button_found:
                logger.error("Bouton 'Proceed/Continuer' non trouvé ou non cliquable.")
                return False
                
            return True

        except Exception as e:
            logger.error(f"Erreur majeure lors de la navigation vers la gestion du candidat: {str(e)}", exc_info=True)
            return False
    
    def fill_applicant_form(self, driver):
        """Remplit le formulaire détaillé du candidat à l'intérieur de l'iframe Kendo."""
        try:
            # Attendre et basculer vers l'iframe Kendo pour le formulaire
            kendo_iframe = self.wait_for(driver).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.k-window-content iframe.k-content-frame"))
            )
            driver.switch_to.frame(kendo_iframe)
            logger.info("Basculé dans l'iframe Kendo du formulaire Applicant.")

            # Attendre un champ clé du formulaire pour s'assurer qu'il est chargé
            self.wait_for(driver).until(EC.visibility_of_element_located((By.ID, "PlaceOfBirth")))

            form_fields = {
                "PlaceOfBirth": self.candidat.place_of_birth,
                "GenderId": self.candidat.gender,
                "MaritalStatusId": self.candidat.marital_status,
                "PassportNo": self.candidat.passport_number,
                "PassportType": self.candidat.passport_type,
                "IssueDate": self.candidat.passport_issue_date.strftime("%Y-%m-%d"), # Kendo attend souvent YYYY-MM-DD
                "ExpiryDate": self.candidat.passport_expiry_date.strftime("%Y-%m-%d"),
                "IssuePlace": self.candidat.passport_issue_place,
                "TravelDate": self.candidat.travel_date.strftime("%Y-%m-%d") if self.candidat.travel_date else None,
                "PurposeOfJourneyId": self.candidat.purpose_of_journey,
                "MemberStateDestinationId": self.candidat.member_state_destination,
                "MemberStateFirstEntryId": self.candidat.member_state_first_entry,
                "MemberStateSecondDestinationId": self.candidat.member_state_second_destination,
            }

            dropdown_field_ids = {
                "GenderId", "MaritalStatusId", "PassportType", 
                "PurposeOfJourneyId", "MemberStateDestinationId", 
                "MemberStateFirstEntryId", "MemberStateSecondDestinationId"
            }
            date_field_ids = {"IssueDate", "ExpiryDate", "TravelDate"}

            for field_id, value in form_fields.items():
                if value is None and field_id in date_field_ids: # Ne pas remplir les dates optionnelles si None
                    logger.info(f"Champ date optionnel {field_id} est None, non rempli.")
                    continue
                if not value and field_id not in date_field_ids: # Ne pas remplir les autres champs s'ils sont vides et non obligatoires
                     # Il faudrait une logique pour savoir si le champ est obligatoire sur BLS
                    logger.info(f"Champ {field_id} est vide, non rempli (à vérifier si obligatoire).")
                    continue

                try:
                    if field_id in dropdown_field_ids:
                        if not self.ui_handler.select_dropdown(driver, field_id, value): # select_dropdown gère l'attente
                            logger.warning(f"Impossible de sélectionner la valeur '{value}' pour le dropdown {field_id}.")
                            # Décider si c'est une erreur bloquante ou non
                    elif field_id in date_field_ids:
                        if not self.ui_handler.fill_date_field(driver, field_id, value):
                             logger.warning(f"Impossible de remplir le champ date {field_id} avec '{value}'.")
                    else:
                        if not self.ui_handler.fill_field(driver, field_id, value): # fill_field gère l'attente
                            logger.warning(f"Impossible de remplir le champ {field_id} avec '{value}'.")
                    # logger.info(f"Champ {field_id} traité avec valeur: '{value}'") # Log déjà dans les handlers
                except Exception as e_field:
                    logger.error(f"Erreur lors du traitement du champ {field_id} avec valeur '{value}': {str(e_field)}")
                    # Potentiellement retourner False si un champ crucial échoue
            
            logger.info("Tous les champs du formulaire Applicant ont été traités.")

            # Soumettre le formulaire
            submit_button_applicant = self.wait_for(driver).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")) # Sélecteur générique
            )
            driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_button_applicant)
            time.sleep(0.5)
            submit_button_applicant.click()
            logger.info("Bouton Submit du formulaire Applicant cliqué.")

            # Gérer l'alerte de confirmation (si elle existe)
            try:
                alert = WebDriverWait(driver, 5).until(EC.alert_is_present())
                alert_text = alert.text
                logger.info(f"Alerte JS après soumission du formulaire Applicant : '{alert_text}'")
                alert.accept()
                logger.info("Alerte JS acceptée.")
            except TimeoutException:
                logger.info("Pas d'alerte JS après soumission du formulaire Applicant, ou elle s'est fermée rapidement.")

            # Revenir au contexte principal
            driver.switch_to.default_content()
            logger.info("Retour au contenu principal après le formulaire Applicant.")
            
            # Attendre que le modal Kendo se ferme ou qu'un signe de succès apparaisse sur la page principale
            WebDriverWait(driver, 10).until_not(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.k-window-content iframe.k-content-frame"))
            )
            logger.info("Modal Kendo du formulaire Applicant fermé.")

            return True

        except Exception as e:
            logger.error(f"Erreur majeure lors du remplissage du formulaire Applicant: {str(e)}", exc_info=True)
            driver.switch_to.default_content() # S'assurer de sortir de l'iframe en cas d'erreur
            return False

    def book_new_appointment(self, driver):
        """Gère le processus complet de réservation d'un nouveau rendez-vous, incluant la sélection du créneau."""
        try:
            # 1. Cliquer sur "Book New Appointment" ou naviguer directement
            target_booking_url = f"{self.base_url}/MAR/appointment/newappointment"
            if driver.current_url != target_booking_url:
                try:
                    book_button = self.wait_for(driver).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, "a.btn.btn-success[href='/MAR/appointment/newappointment']"))
                    )
                    logger.info("Bouton 'Book New Appointment' trouvé.")
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", book_button)
                    time.sleep(0.5)
                    book_button.click()
                except TimeoutException:
                    logger.info("Bouton 'Book New Appointment' non trouvé, navigation directe.")
                    driver.get(target_booking_url)
            
            logger.info(f"Navigation vers la page de réservation initiée/confirmée: {driver.current_url}")
            self._handle_initial_popups(driver) # Gérer les popups

            # 2. Gérer la confirmation de la protection des données (si nécessaire)
            if "DataProtectionEmailSent" in driver.current_url:
                logger.info("Confirmation de la protection des données requise (email envoyé).")
                self.task_manager.update_status('waiting_data_protection', 'waiting_data_protection')
                
                confirmation_url = self.task_manager.wait_for_input('data_protection_url')
                if not confirmation_url:
                    logger.error("Pas d'URL de confirmation de protection des données reçue.")
                    return None # Retourner None car ce n'est pas un échec de RDV, mais une attente

                driver.get(confirmation_url)
                logger.info(f"Navigation vers l'URL de confirmation: {confirmation_url}")

                try:
                    # Attendre un message de succès sur la page de confirmation
                    self.wait_for(driver).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, "p.alert.alert-success"))
                    )
                    logger.info("Protection des données confirmée avec succès via URL.")
                    # Après confirmation, BLS redirige souvent ou propose un lien retour.
                    # Il faut re-naviguer vers la prise de RDV.
                    driver.get(target_booking_url)
                    logger.info(f"Retour à la page de réservation: {target_booking_url}")
                    self._handle_initial_popups(driver)
                except TimeoutException:
                    logger.error("Échec de la confirmation de protection des données (pas de message de succès trouvé).")
                    return None # Ou False si c'est un échec bloquant

            # 3. Gérer le captcha sur la page de sélection du type de visa (si présent)
            # Cette page est souvent /MAR/appointment/VisaType ou similaire
            # Si on n'est pas sur la page de VisaType, et qu'il y a un captcha, on le résout.
            if "/Appointment/VisaType" not in driver.current_url:
                try:
                    # Attendre explicitement le captcha s'il doit apparaître ici
                    WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "captcha-main-div")))
                    logger.info("Captcha trouvé avant la sélection du type de visa.")
                    if not self.solve_captcha_with_retry(driver, max_attempts=3): # Limiter les tentatives ici
                        logger.error("Échec de la résolution du captcha avant la sélection du type de visa.")
                        return None # Échec
                except TimeoutException:
                    logger.info("Pas de captcha trouvé avant la sélection du type de visa (ou déjà sur la page VisaType).")

            # 4. Sélectionner le type de visa, la catégorie, etc.
            # La méthode select_visa_type retourne True si la page de sélection de créneau est atteinte, False sinon.
            # Elle ne retourne PAS les détails du RDV.
            visa_type_selection_successful = self.select_visa_type(driver)
            
            if visa_type_selection_successful:
                # Si select_visa_type a réussi, on est sur la page de sélection de créneau.
                # Maintenant, appeler la méthode pour sélectionner et confirmer le créneau.
                logger.info("Sélection du type de visa réussie, passage à la sélection du créneau.")
                return self.select_and_confirm_appointment_slot(driver) # Nouvelle méthode dédiée
            else:
                logger.error("Échec lors de la sélection du type de visa ou de la navigation vers la sélection de créneau.")
                return None # Retourner None pour indiquer un échec dans cette phase

        except Exception as e:
            logger.error(f"Erreur majeure lors du processus de réservation (book_new_appointment): {str(e)}", exc_info=True)
            return None # Retourner None pour indiquer un échec
            
    def select_and_confirm_appointment_slot(self, driver):
        """Gère la sélection d'un créneau horaire, la confirmation et la récupération des détails."""
        try:
            self.wait_for(driver).until(EC.url_contains("/MAR/Appointment/SlotSelection"))
            logger.info("Sur la page de sélection de créneau (SlotSelection).")
            self._handle_initial_popups(driver)

            # 1. Attendre que le calendrier soit visible
            # Sélecteur typique pour le conteneur du calendrier datepicker
            datepicker_days_container = self.wait_for(driver).until(
                EC.visibility_of_element_located((By.CSS_SELECTOR, "div.datepicker-days table tbody"))
            )
            logger.info("Calendrier des jours trouvé.")

            # 2. Trouver et cliquer sur le premier jour disponible
            # Les jours non désactivés, pas 'old' ou 'new' (mois précédents/suivants)
            # On va essayer de cliquer sur plusieurs si le premier échoue (ex: pas de slots)
            available_day_elements = datepicker_days_container.find_elements(By.CSS_SELECTOR, "td.day:not(.disabled):not(.old):not(.new)")
            if not available_day_elements:
                logger.warning("Aucun jour potentiellement disponible trouvé dans le calendrier.")
                return None

            appointment_details = None
            for day_element in available_day_elements:
                try:
                    day_text = day_element.text
                    logger.info(f"Tentative avec le jour disponible : {day_text}.")
                    # S'assurer que le jour est cliquable avant de cliquer
                    self.wait_for(driver).until(EC.element_to_be_clickable(day_element))
                    day_element.click()
                    logger.info(f"Jour {day_text} cliqué.")
                    
                    # 3. Attendre l'apparition des créneaux horaires
                    time.sleep(1.5) # Pause pour le chargement AJAX des créneaux
                    
                    # Le conteneur des slots est souvent identifié par un ID ou une classe spécifique
                    # Adapter ce sélecteur à ce que BLS utilise
                    time_slots_container_id = "bls-time-slot-container" # EXEMPLE, À VÉRIFIER
                    time_slots_container = self.wait_for(driver).until(
                        EC.visibility_of_element_located((By.ID, time_slots_container_id)) 
                    )
                    
                    # Les créneaux sont souvent des liens <a> ou des boutons <button> avec une classe spécifique
                    # Adapter ce sélecteur
                    available_time_elements = time_slots_container.find_elements(By.CSS_SELECTOR, "a.available-slot, button.time-slot:not(:disabled)") 
                    
                    if not available_time_elements:
                        logger.info(f"Aucun créneau horaire disponible pour le jour {day_text}. Essai du jour suivant si possible.")
                        continue # Essayer le jour suivant dans la boucle

                    first_available_time_element = available_time_elements[0]
                    time_text = first_available_time_element.text
                    logger.info(f"Premier créneau horaire disponible trouvé : {time_text}. Clic...")
                    self.wait_for(driver).until(EC.element_to_be_clickable(first_available_time_element))
                    first_available_time_element.click()
                    
                    # 4. Confirmer le rendez-vous (souvent un bouton "Continue" ou "Confirm")
                    # Adapter le sélecteur
                    confirm_slot_button_id = "btnBook" # EXEMPLE, À VÉRIFIER
                    confirm_slot_button = self.wait_for(driver).until(
                        EC.element_to_be_clickable((By.ID, confirm_slot_button_id))
                    )
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", confirm_slot_button)
                    time.sleep(0.5)
                    confirm_slot_button.click()
                    logger.info("Bouton de confirmation du créneau cliqué.")

                    # 5. Gérer l'alerte JS de confirmation (très commun)
                    try:
                        alert = WebDriverWait(driver, 10).until(EC.alert_is_present())
                        alert_message = alert.text
                        logger.info(f"Alerte de confirmation de RDV: '{alert_message}'")
                        alert.accept()
                        logger.info("Alerte de confirmation de RDV acceptée.")
                    except TimeoutException:
                        logger.warning("Pas d'alerte JS trouvée après confirmation du créneau, ou elle s'est fermée.")
                        # Cela peut être OK si le site ne montre pas d'alerte.

                    # 6. Attendre la page de succès et récupérer les détails
                    # Adapter le sélecteur pour le conteneur de confirmation
                    confirmation_page_container_selector = "div#BookingConfirmation, div.booking-success" # EXEMPLE
                    confirmation_container = self.wait_for(driver).until(
                        EC.visibility_of_element_located((By.CSS_SELECTOR, confirmation_page_container_selector))
                    )
                    logger.info("Page de confirmation du rendez-vous atteinte.")
                    
                    # Adapter ces sélecteurs pour extraire les détails du RDV
                    ref_element = confirmation_container.find_element(By.CSS_SELECTOR, "span#lblAppRefNo, .reference-number")
                    date_element = confirmation_container.find_element(By.CSS_SELECTOR, "span#lblAppDate, .appointment-date")
                    time_element = confirmation_container.find_element(By.CSS_SELECTOR, "span#lblAppTime, .appointment-time")
                    location_element = confirmation_container.find_element(By.CSS_SELECTOR, "span#lblVACName, .appointment-location")

                    reference_no = ref_element.text.strip()
                    date_str = date_element.text.strip() # ex: "25/12/2024"
                    time_str = time_element.text.strip() # ex: "10:30 AM" ou "10:30"
                    location_name = location_element.text.strip()
                    
                    # Parser la date et l'heure
                    # Attention au format de l'heure (AM/PM, 24h) et de la date (DD/MM/YYYY, MM/DD/YYYY)
                    # Exemple pour DD/MM/YYYY et HH:MM (potentiellement avec AM/PM)
                    datetime_str_to_parse = f"{date_str} {time_str}"
                    datetime_format = "%d/%m/%Y %I:%M %p" # Pour 10:30 AM
                    try:
                        appointment_datetime_obj = datetime.strptime(datetime_str_to_parse, datetime_format)
                    except ValueError:
                        datetime_format = "%d/%m/%Y %H:%M" # Pour 10:30 (24h)
                        appointment_datetime_obj = datetime.strptime(datetime_str_to_parse, datetime_format)
                    
                    appointment_details = {
                        "reference": reference_no,
                        "datetime": appointment_datetime_obj,
                        "location": location_name,
                        "raw_date": date_str,
                        "raw_time": time_str
                    }
                    logger.info(f"Détails du rendez-vous récupérés avec succès : {appointment_details}")
                    return appointment_details # Succès, sortir de la boucle et de la méthode

                except TimeoutException:
                    logger.warning(f"Timeout lors de la tentative avec le jour {day_text}. Peut-être pas de créneaux ou page lente.")
                except NoSuchElementException as nse:
                    logger.warning(f"Élément non trouvé lors de la tentative avec le jour {day_text}: {nse}")
                except Exception as e_day_loop:
                    logger.error(f"Erreur inattendue lors de la tentative avec le jour {day_text}: {e_day_loop}", exc_info=True)
                
                # Si on arrive ici, la tentative avec ce jour a échoué, la boucle des jours continue
            
            # Si la boucle des jours se termine sans retourner de détails
            logger.error("Aucun créneau n'a pu être réservé après avoir essayé tous les jours disponibles.")
            return None

        except Exception as e:
            logger.error(f"Erreur majeure lors de la sélection ou confirmation du créneau : {e}", exc_info=True)
            return None

    def select_visa_type(self, driver):
        """Sélectionne le type de visa, la catégorie etc., et retourne True si la page de SlotSelection est atteinte."""
        try:
            max_main_loops = 5 # Pour éviter une boucle infinie si on est coincé
            current_loop = 0
            while current_loop < max_main_loops:
                current_loop += 1
                try:
                    current_url = driver.current_url
                    page_source_lower = driver.page_source.lower() # Obtenir une seule fois par itération

                    if "too many requests" in page_source_lower:
                        logger.warning("Erreur 'Too Many Requests' détectée. Attente de 15 secondes...")
                        time.sleep(15)
                        driver.get(f"{self.base_url}/MAR/appointment/newappointment")
                        self._handle_initial_popups(driver)
                        continue

                    if "captcha" in current_url.lower() and "/Appointment/VisaType" not in current_url.lower():
                        logger.info("Page de captcha détectée avant la sélection du visa.")
                        if not self.solve_captcha_with_retry(driver, max_attempts=3):
                            logger.warning("Échec de la résolution du captcha, réessai de la navigation.")
                            driver.get(f"{self.base_url}/MAR/appointment/newappointment")
                            self._handle_initial_popups(driver)
                            continue
                        # Après résolution, on devrait être redirigé ou pouvoir continuer
                        time.sleep(1) # Attendre une potentielle redirection
                        continue # Re-vérifier l'URL

                    if "/MAR/account/Login" in current_url.lower():
                        logger.info("Redirection vers la page de login détectée. Tentative de reconnexion...")
                        if not self.connect_to_bls(driver): # connect_to_bls entre l'email et clique Verify
                            logger.error("Échec de la reconnexion (phase email).")
                            return False # Échec bloquant
                        # Après connect_to_bls, on est sur la page de saisie du mot de passe/captcha
                        if not self.handle_temp_password(driver): # handle_temp_password gère mot de passe + captcha
                            logger.error("Échec de la reconnexion (phase mot de passe/captcha).")
                            return False # Échec bloquant
                        # Si réussi, on est loggué. Il faut retourner à la prise de RDV.
                        driver.get(f"{self.base_url}/MAR/appointment/newappointment")
                        self._handle_initial_popups(driver)
                        continue
                    
                    # S'assurer qu'on est sur la page de sélection du type de visa
                    if "/MAR/Appointment/VisaType" not in current_url:
                        logger.info(f"Pas sur la page VisaType (actuellement sur {current_url}). Tentative de navigation...")
                        driver.get(f"{self.base_url}/MAR/appointment/newappointment") # Peut être redondant mais sûr
                        self._handle_initial_popups(driver)
                        WebDriverWait(driver,10).until(EC.url_contains("/MAR/Appointment/VisaType")) # Attendre d'arriver
                        current_url = driver.current_url # Mettre à jour l'URL après navigation
                        # Continuer pour la sélection des dropdowns

                    logger.info("Sur la page de sélection du type de visa.")
                    location_mapping = dict(CANDIDAT_LOCATION_CHOICES)
                    visa_mapping = dict(CANDIDAT_VISA_CHOICES)
                    visa_subtype_mapping = dict(CANDIDAT_VISA_SUBTYPE_CHOICES)
                    category_mapping = dict(CANDIDAT_CATEGORY_CHOICES)

                    # Sélectionner les dropdowns
                    # Le KendoUIHandler devrait gérer les attentes pour chaque dropdown
                    if not self.ui_handler.select_dropdown_value_by_label(driver, "Location", location_mapping.get(self.candidat.location)): return False
                    if not self.ui_handler.select_dropdown_value_by_label(driver, "Visa Type", visa_mapping.get(self.candidat.visa)): return False
                    
                    # Sous-type de visa et catégorie peuvent être optionnels ou ne pas exister pour toutes les combinaisons
                    sub_type_val = visa_subtype_mapping.get(self.candidat.visa_subtype)
                    if sub_type_val: # S'il y a une valeur à sélectionner
                        if not self.ui_handler.select_dropdown_value_by_label(driver, "Visa Sub Type", sub_type_val, optional=True):
                             # Si optional=True, l'échec n'est pas bloquant si le dropdown n'est pas trouvé.
                             # Si le dropdown est trouvé mais la valeur non, c'est un problème. Adapter la logique du handler.
                             pass # Ou return False si c'est toujours requis
                    
                    category_val = category_mapping.get(self.candidat.category)
                    if category_val:
                        if not self.ui_handler.select_dropdown_value_by_label(driver, "Category", category_val, optional=True):
                            pass # Ou return False

                    # Sélectionner "Individual"
                    individual_radio = self.wait_for(driver).until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='radio'][value='Individual']")))
                    driver.execute_script("arguments[0].click();", individual_radio) # Clic JS plus fiable pour les radios
                    logger.info("Type de rendez-vous 'Individual' sélectionné.")
                    
                    # Soumettre le formulaire de type de visa
                    submit_visa_type_btn = self.wait_for(driver).until(EC.element_to_be_clickable((By.ID, "btnSubmit"))) # Ou un autre sélecteur
                    driver.execute_script("arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", submit_visa_type_btn)
                    time.sleep(0.5)
                    submit_visa_type_btn.click()
                    logger.info("Formulaire de type de visa soumis.")

                    # Après soumission, vérifier si un captcha apparaît
                    try:
                        WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.ID, "captcha-main-div")))
                        logger.info("Captcha détecté après soumission du formulaire de type de visa.")
                        if not self.solve_captcha_with_retry(driver, max_attempts=3):
                            logger.warning("Échec de la résolution du captcha. Réessai du processus de sélection de visa.")
                            driver.get(f"{self.base_url}/MAR/appointment/newappointment") # Recommencer
                            self._handle_initial_popups(driver)
                            continue 
                    except TimeoutException:
                        logger.info("Pas de captcha immédiatement après soumission du type de visa.")

                    # Attendre la redirection vers SlotSelection ou un message d'erreur "no slots"
                    WebDriverWait(driver, 20).until(
                        lambda d: "/MAR/Appointment/SlotSelection" in d.current_url or \
                                  d.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no slots available') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aucun créneau disponible')]")
                    )

                    if "/MAR/Appointment/SlotSelection" in driver.current_url:
                        logger.info("Redirection vers la page de sélection de créneau (SlotSelection) réussie.")
                        return True # Succès, la méthode appelante gérera la sélection du slot

                    # Vérifier explicitement le message "no slots"
                    no_slots_elements = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'no slots available') or contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), 'aucun créneau disponible')]")
                    if no_slots_elements and no_slots_elements[0].is_displayed():
                        logger.info("Message 'Pas de créneaux disponibles' trouvé. Réessai après une pause...")
                        time.sleep(10) # Pause avant de réessayer
                        # Tenter de cliquer sur un bouton "Try Again" ou de re-naviguer
                        try:
                            try_again_btn = driver.find_element(By.XPATH, "//a[contains(@href,'newappointment') and (contains(text(),'Try Again') or contains(text(),'Réessayer'))]")
                            try_again_btn.click()
                        except NoSuchElementException:
                            driver.get(f"{self.base_url}/MAR/appointment/newappointment")
                        self._handle_initial_popups(driver)
                        continue # Recommencer la boucle principale de select_visa_type
                    
                    # Si on n'est ni sur SlotSelection ni sur un message "no slots", situation inattendue
                    logger.error(f"Situation inattendue après soumission du type de visa. URL: {driver.current_url}")
                    return False # Échec

                except TimeoutException as toe:
                    logger.warning(f"Timeout dans la boucle de sélection de visa (loop {current_loop}): {toe}. Réessai...")
                    driver.get(f"{self.base_url}/MAR/appointment/newappointment") # Tentative de récupération
                    self._handle_initial_popups(driver)
                    continue
                except Exception as e_loop:
                    logger.error(f"Erreur inattendue dans la boucle de sélection de visa (loop {current_loop}): {e_loop}", exc_info=True)
                    return False # Échec bloquant
            
            logger.error(f"Échec de la sélection du type de visa après {max_main_loops} boucles principales.")
            return False # Échec après toutes les tentatives

        except Exception as e_main:
            logger.error(f"Erreur majeure lors de la sélection du type de visa: {e_main}", exc_info=True)
            return False

    def solve_captcha_with_retry(self, driver, max_attempts=5): # Réduit pour des cycles plus rapides
        """Résout le captcha (qui soumet souvent le formulaire parent aussi)."""
        for attempt in range(max_attempts):
            try:
                logger.info(f"Tentative de résolution du captcha {attempt + 1}/{max_attempts}")
                # Le solveur doit gérer l'attente du captcha et sa soumission.
                # Il retourne True si le captcha est soumis (pas forcément correctement résolu).
                if not self.captcha_solver.solve(driver):
                    logger.warning(f"Tentative {attempt + 1}: captcha_solver.solve() a retourné False.")
                    # Recharger le captcha ou la page si nécessaire
                    try:
                        driver.find_element(By.ID, "captcha_image_id_refresh_button").click() # Exemple
                    except:
                        if "/MAR/account/Login" in driver.current_url or "/MAR/appointment/VisaType" in driver.current_url :
                             # Ne pas rafraîchir la page entière si on est sur login ou visa type, juste le captcha
                            pass # Le solveur devrait réessayer
                        else:
                            driver.refresh()
                            WebDriverWait(driver, 5).until(EC.visibility_of_element_located((By.ID, "captcha-main-div")))

                    time.sleep(1) # Pause avant la prochaine tentative de solve()
                    continue
                
                # Après que solve() a soumis, vérifier si le captcha est toujours là
                # ou si une erreur est affichée (par exemple, "captcha incorrect")
                try:
                    WebDriverWait(driver, 3).until_not(
                        EC.visibility_of_element_located((By.ID, "captcha-main-div")) # Ou un autre indicateur de captcha
                    )
                    logger.info(f"Tentative {attempt + 1}: Captcha semble résolu (n'est plus visible).")
                    return True # Captcha n'est plus visible
                except TimeoutException:
                    logger.warning(f"Tentative {attempt + 1}: Captcha toujours visible après soumission.")
                    # Vérifier un message d'erreur "captcha incorrect"
                    try:
                        error_captcha_msg = driver.find_element(By.CSS_SELECTOR, ".captcha-error-message") # Exemple
                        if error_captcha_msg.is_displayed():
                            logger.info(f"Message d'erreur captcha: {error_captcha_msg.text}")
                    except NoSuchElementException:
                        pass # Pas de message d'erreur spécifique
                    # La boucle de tentative continuera.
                    
            except Exception as e_captcha:
                logger.error(f"Erreur lors de la tentative {attempt + 1} de résolution du captcha: {str(e_captcha)}")
                # Laisser la boucle continuer pour les prochaines tentatives
            
        logger.error(f"Échec de la résolution du captcha après {max_attempts} tentatives.")
        return False