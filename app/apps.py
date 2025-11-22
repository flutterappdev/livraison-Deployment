from django.apps import AppConfig


class BLSSpainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'app'
    verbose_name = 'BLS SPAIN'

    def ready(self):
        """
        Cette méthode est appelée par Django lorsque l'application est prête.
        C'est l'endroit recommandé pour importer les signaux.
        """
        import app.signals  # <-- AJOUTER CETTE LIGNE IMPORTANTE
