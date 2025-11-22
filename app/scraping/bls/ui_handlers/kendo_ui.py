import logging
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

class KendoUIHandler:
    def __init__(self, wait_for):
        self.wait_for = wait_for

    def select_dropdown(self, driver, field_id, value):
        """Sélectionner une valeur dans un menu déroulant Kendo UI"""
        try:
            # Trouver le conteneur du dropdown
            dropdown_container = self.wait_for(driver).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, f"span.k-dropdown[aria-owns='{field_id}_listbox']"))
            )
            dropdown_button = dropdown_container.find_element(By.CSS_SELECTOR, ".k-select")

            # Ouvrir le dropdown
            driver.execute_script("arguments[0].click();", dropdown_button)
            logger.info(f"Dropdown {field_id} ouvert")

            # Sélectionner l'option
            option = self.wait_for(driver).until(
                EC.presence_of_element_located((By.XPATH, f"//ul[@id='{field_id}_listbox']//li[text()='{value}']"))
            )
            driver.execute_script("arguments[0].click();", option)

            logger.info(f"Option '{value}' sélectionnée pour {field_id}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la sélection dans {field_id}: {str(e)}")
            return False

    def fill_field(self, driver, field_id, value):
        """Remplir un champ avec JavaScript"""
        try:
            self.wait_for(driver).until(
                EC.presence_of_element_located((By.ID, field_id))
            )

            script = f"""
                var element = document.getElementById('{field_id}');
                element.value = '{value}';
                element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                element.dispatchEvent(new Event('input', {{ bubbles: true }}));
            """
            driver.execute_script(script)
            logger.info(f"Champ {field_id} rempli avec la valeur: {value}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du remplissage du champ {field_id}: {str(e)}")
            return False 

    @staticmethod
    def fill_date_field(driver, field_id, value):
        """Remplir un champ de date avec JavaScript en utilisant l'API Kendo UI"""
        try:
            script = f"""
                var dateInput = $('#{field_id}').data('kendoDatePicker');
                if (dateInput) {{
                    dateInput.value(new Date('{value}'));
                    dateInput.trigger('change');
                }} else {{
                    var element = document.getElementById('{field_id}');
                    element.value = '{value}';
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                }}
            """
            driver.execute_script(script)
            logger.info(f"Champ date {field_id} rempli avec la valeur: {value}")
            return True

        except Exception as e:
            logger.error(f"Erreur lors du remplissage du champ date {field_id}: {str(e)}")
            return False


    @staticmethod
    def get_dropdown_by_label(driver, label_text):
        """
        Trouve un dropdown Kendo UI visible en se basant sur son label
        """
        try:
            # 1. Trouver tous les labels visibles contenant le texte
            labels = driver.find_elements(
                By.XPATH,
                f"//label[contains(text(), '{label_text}')]"
            )

            # 2. Parcourir les labels pour trouver celui qui est réellement visible
            for label in labels:
                try:
                    # Vérifier si le label et ses parents sont visibles
                    if not (label.is_displayed() and driver.execute_script("""
                        var element = arguments[0];
                        while (element) {
                            var style = window.getComputedStyle(element);
                            if (style.display === 'none' || style.visibility === 'hidden') {
                                return false;
                            }
                            element = element.parentElement;
                        }
                        return true;
                    """, label)):
                        continue

                    # Obtenir l'ID du champ associé
                    field_id = label.get_attribute('for')
                    if not field_id:
                        continue

                    # Trouver le dropdown associé
                    dropdown = driver.find_element(
                        By.CSS_SELECTOR,
                        f"span.k-dropdown[aria-owns='{field_id}_listbox']"
                    )

                    # Vérifier que le dropdown est visible
                    if dropdown.is_displayed() and driver.execute_script("""
                        var element = arguments[0];
                        var style = window.getComputedStyle(element);
                        return style.display !== 'none' && style.visibility !== 'hidden';
                    """, dropdown):
                        logger.info(f"Dropdown visible trouvé pour le label: {label_text}")
                        print(f"Label trouvé: {label.text}")
                        print(f"Field ID: {field_id}")
                        print(f"Dropdown visible: {dropdown.is_displayed()}")
                        return dropdown

                except Exception as e:
                    logger.debug(f"Erreur lors de la vérification d'un label: {str(e)}")
                    continue

            logger.error(f"Aucun dropdown visible trouvé pour le label: {label_text}")
            return None

        except Exception as e:
            logger.error(f"Erreur lors de la recherche du dropdown {label_text}: {str(e)}")
            return None

    @staticmethod
    def select_dropdown_value(dropdown_element, value, driver):
        try:
            dropdown_id = dropdown_element.get_attribute('aria-owns').replace('_listbox', '')
            print(f"ID du dropdown: {dropdown_id}")
            print(f"Valeur à sélectionner: {value}")
            
            # 1. Sélectionner la valeur sans Promise
            script = f"""
                var dropdown = $('#{dropdown_id}').data('kendoDropDownList');
                if (!dropdown) return false;
                
                // Forcer l'ouverture
                dropdown.open();
                
                // Attendre que les données soient chargées
                var items = dropdown.dataSource.data();
                var foundItem = items.find(item => item.Name === '{value}');
                
                if (foundItem) {{
                    // Sélectionner la valeur
                    dropdown.select(items.indexOf(foundItem));
                    dropdown.value(foundItem.Id);
                    dropdown.trigger('change');
                    return true;
                }}
                
                return false;
            """
            
            success = driver.execute_script(script)
            if not success:
                logger.error(f"Valeur '{value}' non trouvée dans le dropdown")
                return False

            
            # 3. Vérifier la sélection
            verify_script = f"""
                var dropdown = $('#{dropdown_id}').data('kendoDropDownList');
                return dropdown ? dropdown.text() === '{value}' : false;
            """
            
            if driver.execute_script(verify_script):
                logger.info(f"Valeur '{value}' sélectionnée avec succès")
                return True
            else:
                logger.warning(f"La sélection n'a pas été prise en compte")
                return False

        except Exception as e:
            logger.error(f"Erreur lors de la sélection de la valeur '{value}': {str(e)}")
            return False
