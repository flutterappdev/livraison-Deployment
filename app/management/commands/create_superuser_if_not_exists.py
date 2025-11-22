from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
import os

class Command(BaseCommand):
    """
    Crée un superutilisateur s'il n'existe pas déjà.
    Prend les informations depuis les variables d'environnement si non fournies en arguments.
    """
    help = "Crée un superutilisateur s'il n\'en existe pas déjà un avec le même nom d\'utilisateur."

    def add_arguments(self, parser):
        parser.add_argument('--username', help='Nom d\'utilisateur du superutilisateur.')
        parser.add_argument('--email', help='Email du superutilisateur.')
        parser.add_argument('--password', help='Mot de passe du superutilisateur.')
        parser.add_argument('--no-input', action='store_true', help='Crée le superutilisateur sans interaction.')

    def handle(self, *args, **options):
        User = get_user_model()
        username = options['username'] or os.getenv('DJANGO_SUPERUSER_USERNAME')
        email = options['email'] or os.getenv('DJANGO_SUPERUSER_EMAIL')
        password = options['password'] or os.getenv('DJANGO_SUPERUSER_PASSWORD')

        if not username or not password:
            self.stdout.write(self.style.ERROR('Le nom d\'utilisateur et le mot de passe doivent être fournis.'))
            return

        if not User.objects.filter(username=username).exists():
            self.stdout.write(self.style.SUCCESS(f"Création du superutilisateur '{username}'..."))
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f"Superutilisateur '{username}' créé avec succès."))
        else:
            self.stdout.write(self.style.WARNING(f"Le superutilisateur '{username}' existe déjà. Aucune action effectuée."))