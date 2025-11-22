from django.contrib import admin
from django.contrib.auth.models import User, Group
from app.models import (
    Organisation, 
    OrganisationUser, 
    Candidat, 
    OrganisationRole, 
    ScrapingTask
)
from .admin.site import CustomAdminSite
from .admin.organisation import OrganisationAdmin
from .admin.candidat import CandidatAdmin
from .admin.user import CustomUserAdmin
from .admin.role import OrganisationRoleAdmin
from .admin.task import ScrapingTaskAdmin

# Créer l'instance de CustomAdminSite
admin_site = CustomAdminSite(name='custom_admin')

# Enregistrer les modèles avec l'admin site personnalisé
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Candidat, CandidatAdmin)
admin_site.register(OrganisationRole, OrganisationRoleAdmin)
admin_site.register(ScrapingTask, ScrapingTaskAdmin)

# Désenregistrer les modèles par défaut
admin.site.unregister(User)
admin.site.unregister(Group)

# Enregistrer notre version personnalisée de UserAdmin
admin.site.register(User, CustomUserAdmin)

