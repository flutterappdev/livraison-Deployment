#!/bin/sh

# Sortir immédiatement si une commande échoue
set -e

# Attendre que la base de données PostgreSQL soit prête
echo "Attente de PostgreSQL..."
# Utilisation des variables d'environnement directement
while ! pg_isready -h "$SQL_HOST" -p "$SQL_PORT" -q -U "$SQL_USER"; do
  sleep 2
done
echo "PostgreSQL est prêt !"

# Appliquer les migrations de la base de données
echo "Application des migrations de la base de données..."
python manage.py migrate --noinput

# Collecter les fichiers statiques
echo "Collecte des fichiers statiques..."
python manage.py collectstatic --noinput --clear

# Créer un superutilisateur si les variables sont définies
# Le script est maintenant dans un fichier séparé, donc la syntaxe est simple
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] ; then
    echo "Création du superutilisateur (si nécessaire)..."
    python manage.py create_superuser_if_not_exists \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "$DJANGO_SUPERUSER_EMAIL" \
        --password "$DJANGO_SUPERUSER_PASSWORD"
fi

# Démarrer le processus principal passé en argument à ce script
# Cela permet au `command` de docker-compose de prendre le relais.
echo "Lancement de la commande principale : $@"
exec "$@"