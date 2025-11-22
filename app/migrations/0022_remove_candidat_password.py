from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('app', '0021_alter_candidat_date_of_birth'),  # Mise à jour vers la dernière migration
    ]

    operations = [
        migrations.RemoveField(
            model_name='candidat',
            name='password',
        ),
    ] 