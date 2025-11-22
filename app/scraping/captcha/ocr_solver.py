import logging
import base64
import io
import numpy as np
from PIL import Image
from selenium.webdriver.common.by import By
import time
from selenium.webdriver.support import expected_conditions as EC

# --- NEW IMPORTS ---
import keras_ocr

logger = logging.getLogger(__name__)

class OCRCaptchaSolver:
    def __init__(self, wait_for):
        """Initializes the OCR solver with Keras-OCR."""
        # Keras-OCR will automatically download models on first use.
        # It's better to initialize it once.
        self.pipeline = keras_ocr.pipeline.Pipeline()
        self.wait_for = wait_for
        logger.info("Keras-OCR pipeline initialized.")

    # --- get_captcha_grid and get_target_number methods remain the SAME ---
    def get_captcha_grid(self, driver):
        # ... (this method does not need changes)
        try:
        # JavaScript pour récupérer toutes les informations nécessaires en une seule exécution
            script = """
                const containers = Array.from(document.querySelectorAll("div.row div.col-4"));
                const visibleContainers = containers.filter(container => {
                    const img = container.querySelector('.captcha-img');
                    const style = window.getComputedStyle(container);
                    return container.offsetParent !== null && img && img.offsetParent !== null;
                }).map(container => {
                    const img = container.querySelector('.captcha-img');
                    const rect = container.getBoundingClientRect();
                    const style = window.getComputedStyle(container);
                    return {
                        top: parseInt(rect.top),
                        left: parseInt(rect.left),
                        zIndex: parseInt(style.zIndex) || 0,
                        imgSrc: img ? img.src : null
                    };
                });
                return visibleContainers;
            """
            
            containers_data = driver.execute_script(script)
            logger.info(f"Conteneurs trouvés et filtrés: {len(containers_data)}")
            
            if not containers_data:
                return []
            
            # Grouper par position verticale (top)
            from collections import defaultdict
            rows = defaultdict(list)
            for data in containers_data:
                rows[data['top']].append(data)
            
            # Trier les lignes par 'top'
            sorted_top_keys = sorted(rows.keys())
            
            grid_images = []
            for top in sorted_top_keys:
                row = rows[top]
                # Trier par z-index décroissant et prendre les 3 premiers
                row_sorted_z = sorted(row, key=lambda x: x['zIndex'], reverse=True)[:3]
                # Trier par 'left' croissant
                row_sorted = sorted(row_sorted_z, key=lambda x: x['left'])
                for item in row_sorted:
                    grid_images.append({
                        'imgSrc': item['imgSrc']
                    })
            
            logger.info(f"Images dans la grille finale: {len(grid_images)}")
            return grid_images
    
                
        except Exception as e:
            logger.error(f"Erreur lors de la récupération de la grille: {str(e)}")
            return []


    def get_target_number(self, driver):
        # ... (this method does not need changes)
        try:
            labels = self.wait_for(driver).until(
                EC.presence_of_all_elements_located((By.CLASS_NAME, "box-label"))
            )
            visible_labels = []
            
            for label in labels:
                if label.is_displayed():
                    try:
                        z_index = int(label.value_of_css_property('z-index') or 0)
                        visible_labels.append((label, z_index))
                    except ValueError:
                        continue
            
            if not visible_labels:
                logger.error("Aucun label visible trouvé")
                return None
                
            visible_labels.sort(key=lambda x: x[1], reverse=True)
            visible_label = visible_labels[0][0]
            
            target_number = visible_label.text.split()[-1]
            logger.info(f"Numéro cible trouvé: {target_number}")
            return target_number

        except Exception as e:
            logger.error(f"Erreur lors de la récupération du numéro cible: {str(e)}")
            return None


    # --- solve method remains the SAME ---
    def solve(self, driver):
        # ... (this method does not need changes, as it calls the updated recognize_number_from_src)
        try:
            # Récupérer la grille et le numéro cible
            grid_items = self.get_captcha_grid(driver)
            target_number = self.get_target_number(driver)
            
            if not target_number or not grid_items:
                logger.error("Impossible de récupérer le numéro cible ou la grille")
                return False

            # Traiter chaque image
            for item in grid_items:
                number = self.recognize_number_from_src(item['imgSrc'])
                time.sleep(0.1)
                if number:
                    logger.info(f"Numéro trouvé: {number}")
                    if number == target_number:
                        # Trouver et cliquer sur l'image correspondante
                        img_element = driver.find_element(
                            By.CSS_SELECTOR, 
                            f"img[src='{item['imgSrc']}']"
                        )
                        img_element.click()
            
            if "RegisterUser" in driver.current_url:
                submit_btn = self.wait_for(driver).until(
                EC.element_to_be_clickable((By.ID, "submit"))
                )
                submit_btn.click()
                logger.info("Clic sur Submit effectué")
            return True

        except Exception as e:
            logger.error(f"Erreur lors de la résolution du captcha: {str(e)}")
            return False

    # --- recognize_number_from_src is UPDATED ---
    def recognize_number_from_src(self, img_src):
        """Recognizes the number from the image source using Keras-OCR."""
        try:
            # Decode the base64 image
            if ',' not in img_src:
                logger.warning("Image source is not a valid base64 string.")
                return None
            img_data = base64.b64decode(img_src.split(',')[1])
            img = Image.open(io.BytesIO(img_data)).convert('RGB')
            img_array = np.array(img)

            # Use the Keras-OCR pipeline to recognize text
            # It returns a list of (text, box) tuples.
            prediction_groups = self.pipeline.recognize([img_array])

            # The result is a list containing results for each image. We sent one image.
            if not prediction_groups or not prediction_groups[0]:
                logger.debug("Keras-OCR a retourné aucune prédiction.")
                return None

            # Extract all recognized digits
            all_digits = ""
            for text, box in prediction_groups[0]:
                all_digits += "".join(filter(str.isdigit, text))

            # We are looking for a 3-digit number.
            if len(all_digits) == 3:
                logger.info(f"Numéro à 3 chiffres trouvé: {all_digits}")
                return all_digits
            else:
                logger.debug(f"Numéro trouvé '{all_digits}' n'a pas 3 chiffres. Ignoré.")
                return None

        except Exception as e:
            logger.error(f"Erreur lors de la reconnaissance du numéro avec Keras-OCR: {e}", exc_info=True)
            return None