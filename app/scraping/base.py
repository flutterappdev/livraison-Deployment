from abc import ABC, abstractmethod
from selenium import webdriver
from selenium_authenticated_proxy import SeleniumAuthenticatedProxy
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

class BaseScrapingBot(ABC):
    def __init__(self, headless=False):
        self.options = webdriver.ChromeOptions()

         # --- CONFIGURATION D'OPTIONS ANTI-DÉTECTION AVANCÉE ---

        # 1. Masquer les indicateurs Selenium de base (vous les avez déjà, c'est bien)
        self.options.add_argument('--disable-blink-features=AutomationControlled')
        self.options.add_experimental_option('useAutomationExtension', False)
        self.options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])

        # 2. Options pour imiter un navigateur normal
        self.options.add_argument('--no-sandbox')
        self.options.add_argument('--disable-dev-shm-usage')
        self.options.add_argument('--disable-infobars')
        self.options.add_argument('--disable-gpu')
        self.options.add_argument("--window-size=1920,1080")
        self.options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36")
        
        # 3. Désactiver les fonctionnalités qui peuvent fuiter des informations
        # WebRTC peut révéler votre IP réelle (même derrière un proxy)
        self.options.add_argument("--disable-webrtc")
        self.options.add_argument("--disable-notifications")
        self.options.add_argument("--disable-geolocation")


        if headless:
            self.options.add_argument('--headless=new')
        
        

    def setup_proxy(self, organisation):
        """Configure le proxy avec authentification"""
        if not organisation.proxy:
            return False

        try:
            proxy_string = organisation.proxy
            
            if '@' not in proxy_string:
                logger.error("Format de proxy invalide: @ manquant")
                return False
            
            tmp_folder = os.path.join(tempfile.gettempdir(), 'selenium_proxy')
            os.makedirs(tmp_folder, exist_ok=True)
            
            proxy_helper = SeleniumAuthenticatedProxy(
                proxy_url=f"http://{proxy_string}",
                tmp_folder=tmp_folder
            )
            
            proxy_helper.enrich_chrome_options(self.options)
            return True
            
        except Exception as e:
            logger.error(f"Erreur lors de la configuration du proxy: {str(e)}")
            return False

    @abstractmethod
    def _start_registration(self, driver):
        pass

        
    @abstractmethod
    def _submit_registration(self, driver):
        pass 