# ./download_models.py
import keras_ocr

# Cette simple ligne va déclencher le téléchargement des modèles
# de détection et de reconnaissance dans le cache par défaut.
print("Téléchargement des modèles Keras-OCR...")
pipeline = keras_ocr.pipeline.Pipeline()
print("Téléchargement terminé.")