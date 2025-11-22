import os
import datetime
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from .base import BaseScrapingBot
from .captcha.ocr_solver import OCRCaptchaSolver
from .bls.ui_handlers.kendo_ui import KendoUIHandler
from .bls.form_handlers.form_handler import BLSFormHandler
from .bls.page_handlers.page_handler import BLSPageHandler
from .bls.browser.browser_handler import BrowserHandler
import logging
from django.conf import settings
import time
from selenium.webdriver.common.alert import Alert



logger = logging.getLogger(__name__)

class BLSSpainBot(BaseScrapingBot):
    def __init__(self, candidat, user=None):
        is_docker = os.getenv('IS_DOCKER_CONTAINER', 'False') == 'True'
        super().__init__(headless=is_docker) # Forcer headless si dans Docker
        self.candidat = candidat
        self.user = user  # L'utilisateur connecté
        self.wait_timeout = 120
        
        # Initialisation des handlers
        self.browser_handler = BrowserHandler(timeout=self.wait_timeout, implicit_wait=self.wait_timeout)
        self.captcha_solver = OCRCaptchaSolver(self.wait_for)
        self.ui_handler = KendoUIHandler(self.wait_for)
        self.form_handler = BLSFormHandler(self.ui_handler)
        self.page_handler = BLSPageHandler(
            self.wait_for, 
            settings.VISA_SERVICES['blsspain']['base_url'],
            user=self.user  # Passer l'utilisateur
        )
        self.page_handler.set_candidat(self.candidat)

        # Configuration du proxy avec la méthode de la classe de base
        if candidat.organisation:
            try:
                self.setup_proxy(candidat.organisation)
                self.browser_handler.options = self.options
                logger.info(f"Proxy configuré pour {candidat.organisation.name}")
            except Exception as e:
                logger.error(f"Erreur de configuration du proxy: {str(e)}")
    
    def save_debug_screenshot(self, driver, filename_prefix):
        """
        Sauvegarde un screenshot et le code source de la page pour le débogage
        directement dans un dossier à la racine du projet.
        """
        try:
            # --- MODIFICATION ---
            # Le chemin du projet à l'intérieur du conteneur est /app
            # C'est ce chemin que nous utilisons.
            project_dir = "/app"
            debug_dir = os.path.join(project_dir, 'debug_screenshots')
            # --------------------
            
            # Créer le répertoire de débogage s'il n'existe pas
            os.makedirs(debug_dir, exist_ok=True)

            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            # Nom de fichier unique
            candidat_id = self.candidat.id if self.candidat else "unknown"
            filename_base = f"{filename_prefix}_{candidat_id}_{timestamp}"
            
            # Sauvegarder le screenshot
            screenshot_path = os.path.join(debug_dir, f"{filename_base}.png")
            driver.save_screenshot(screenshot_path)
            # Utiliser un chemin relatif pour le message de log pour que ce soit plus clair
            log_path_screenshot = os.path.join('debug_screenshots', f"{filename_base}.png")
            logger.info(f"Screenshot de débogage sauvegardé dans : {log_path_screenshot}")

            # Sauvegarder le code source HTML
            html_path = os.path.join(debug_dir, f"{filename_base}.html")
            with open(html_path, 'w', encoding='utf-8') as f:
                f.write(driver.page_source)
            log_path_html = os.path.join('debug_screenshots', f"{filename_base}.html")
            logger.info(f"Source HTML de débogage sauvegardée dans : {log_path_html}")
            
        except Exception as e:
            logger.error(f"Impossible de sauvegarder le screenshot de débogage : {e}")

    def wait_for(self, driver):
        """Crée un WebDriverWait avec le timeout configuré"""
        return WebDriverWait(driver, self.wait_timeout)

    def _start_registration(self, driver):
        """Implémentation de la méthode abstraite"""
        return self.page_handler.start_registration(driver)

    def _submit_registration(self, driver):
        """Implémentation de la méthode abstraite"""
        try:
            # 1. Cliquer sur le bouton Verify
            verify_button = self.wait_for(driver).until(
                EC.element_to_be_clickable((By.ID, "btnVerify"))
            )
            driver.execute_script("arguments[0].click();", verify_button)
            logger.info("Clic sur le bouton Verify effectué")

            # 2. Résoudre le captcha
            if not self.solve_image_captcha(driver):
                return False
            logger.info("Captcha résolu avec succès")

            # 3. Gérer l'OTP
            if not self.page_handler.handle_otp(driver):
                logger.error("Échec de la gestion de l'OTP")
                return False
            logger.info("OTP traité avec succès")

            # 4. Gérer le mot de passe temporaire
            if not self.page_handler.handle_temp_password(driver):
                logger.error("Échec de la gestion du mot de passe temporaire")
                return False
            logger.info("Mot de passe temporaire traité avec succès")

            # 5. Gérer le changement de mot de passe
            if not self.page_handler.handle_password_change(driver):
                logger.error("Échec de la gestion du changement de mot de passe")
                return False
            logger.info("Changement de mot de passe traité avec succès")

            return True

        except Exception as e:
            logger.error(f"Erreur lors de la soumission: {str(e)}")
            return False

    def run(self):
        """Exécute le processus de scraping"""
        driver = None
        try:
            # Initialisation du driver
            driver = self.browser_handler.initialize_driver()
            
            if not driver:
                logger.error("Échec de l'initialisation du driver")
                return False

            # Initialiser la session
             # Au lieu de retourner False, on lève une exception pour que le bloc except la gère
            self.save_debug_screenshot(driver, "init")
            if not self.page_handler.initialize_session(driver):
                raise Exception("Échec de l'initialisation de la session")

            self.save_debug_screenshot(driver, "init")
            if not self._start_registration(driver):
                 raise Exception("Échec du démarrage de l'inscription (_start_registration)")

            self.save_debug_screenshot(driver, "register")
            if not self.page_handler.wait_for_form(driver):
                raise Exception("Timeout en attente du formulaire d'inscription")
            logger.info("Navigation vers la page d'inscription réussie")

            self.save_debug_screenshot(driver, "wait_form")
            if not self.form_handler.fill_form(driver, self.candidat):
                raise Exception("Echec de remplissage du formulaire d'inscription")
            logger.info("Formulaire rempli")

            self.save_debug_screenshot(driver, "fill_form")
            # Soumettre l'inscription (inclut maintenant le captcha et l'OTP)
            if not self._submit_registration(driver):
                return False
            logger.info("Inscription complète")

            driver.quit()

            return True

        except Exception as e:
            logger.error(f"Erreur lors du processus de scraping: {str(e)}")
            if driver:
                # --- AJOUT ---
                # Prendre un screenshot au moment de l'erreur
                self.save_debug_screenshot(driver, "scraping_error")
            return False

        finally:
            if driver:
                self.browser_handler.quit_driver(driver)

    def solve_image_captcha(self, driver):
        """Résout le captcha d'images avec vérification explicite."""
        try:
            max_attempts = 99  # Nombre maximum de tentatives
            for attempt in range(max_attempts):
                try:
                    # Vérifier si l'iframe du CAPTCHA existe
                    iframe = driver.find_element(By.CSS_SELECTOR, ".k-content-frame")
                except NoSuchElementException:
                    # Si l'iframe n'existe pas, le CAPTCHA est déjà résolu
                    logger.info("Captcha déjà résolu (iframe non trouvé)")
                    return True

                # Basculer dans l'iframe
                driver.switch_to.frame(iframe)
                logger.info("Basculé dans l'iframe du captcha")

                try:
                    # Attendre que le conteneur du CAPTCHA soit présent
                    captcha_div = self.wait_for(driver).until(
                        EC.presence_of_element_located((By.ID, "captcha-main-div"))
                    )

                    # Vérifier si le CAPTCHA est visible
                    if not captcha_div.is_displayed():
                        logger.info("Captcha déjà résolu (div non visible)")
                        return True

                    # Tenter de résoudre le CAPTCHA
                    logger.info(f"Tentative {attempt + 1} de résolution du captcha...")
                    if not self.captcha_solver.solve(driver):
                        logger.error(f"Tentative {attempt + 1}: Échec de la résolution du captcha")
                        continue

                    # Re-vérifier la visibilité du CAPTCHA
                    try:
                        WebDriverWait(driver, 5).until(EC.alert_is_present())
                        alert = Alert(driver)
                        alert.accept()
                        print("Captcha non résolu, on réessaye...")
                        continue
                    except Exception:
                        return True

                finally:
                    # Revenir au contenu principal du document
                    driver.switch_to.default_content()

            # Si toutes les tentatives échouent
            logger.error("Échec de la résolution du captcha après plusieurs tentatives")
            return False

        except Exception as e:
            logger.error(f"Erreur fonction solve_image_captcha: {str(e)}")
            return False
