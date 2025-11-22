from django.conf import settings
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth # <-- Importer


logger = logging.getLogger(__name__)

class BrowserHandler:
    def __init__(self, timeout=30, implicit_wait=0):
        self.timeout = timeout
        self.implicit_wait = implicit_wait
        self.options = None  # Sera configuré par BLSSpainBot

    def initialize_driver(self, headless=None):
        """Initialise et configure le driver Chrome"""
        try:
            if not self.options:
                self.options = webdriver.ChromeOptions()
                self.options.add_argument('--no-sandbox')
                self.options.add_argument('--disable-dev-shm-usage')
                
                # Utiliser DEBUG pour déterminer le mode headless si non spécifié
                if headless is None:
                    headless = not settings.DEBUG
                
                if headless:
                    self.options.add_argument('--headless')
                    logger.info("Mode headless activé (production)")
                else:
                    logger.info("Mode headless désactivé (développement)")

            service = Service(ChromeDriverManager().install())
            
            driver = webdriver.Chrome(
                service=service,
                options=self.options
            )

            # --- SOLUTION ANTI-DÉTECTION (partie 2) ---
            # Exécuter un script via le Chrome DevTools Protocol pour masquer Selenium
            driver.execute_cdp_cmd(
                "Page.addScriptToEvaluateOnNewDocument",
                {
                    "source": """
                        Object.defineProperty(navigator, 'webdriver', {
                          get: () => undefined
                        })
                    """
                },
            )
            # ---------------------------------------------

             # --- APPLICATION DE SELENIUM-STEALTH ---
            # Doit être appliqué APRÈS l'initialisation du driver
            stealth(driver,
                    languages=["fr-FR", "fr"],
                    vendor="Google Inc.",
                    platform="Win32", # Se faire passer pour Windows
                    webgl_vendor="Intel Inc.",
                    renderer="Intel Iris OpenGL Engine",
                    fix_hairline=True,
            )
            logger.info("Patchs Selenium-Stealth appliqués pour masquer l'automatisation.")
            # ----------------------------------------



            driver.set_page_load_timeout(self.timeout)
            driver.implicitly_wait(self.implicit_wait)

            logger.info("Driver Chrome initialisé avec succès")
            return driver

        except Exception as e:
            logger.error(f"Erreur lors de l'initialisation du driver: {str(e)}")
            return None

    @staticmethod
    def quit_driver(driver):
        """Ferme proprement le driver"""
        try:
            if driver:
                #driver.quit()
                logger.info("Driver fermé avec succès")
        except Exception as e:
            logger.error(f"Erreur lors de la fermeture du driver: {str(e)}") 