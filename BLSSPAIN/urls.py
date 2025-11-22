"""
URL configuration for BLSSPAIN project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include
from app.admin import (
    CustomAdminSite, 
    CandidatAdmin, 
    OrganisationAdmin, 
    CustomUserAdmin,
    OrganisationRoleAdmin,
    ScrapingTaskAdmin
)
from app.models import Organisation, Candidat, OrganisationRole, ScrapingTask
from django.contrib.auth.models import User
from django.contrib import admin

# Créer l'instance de CustomAdminSite
admin_site = CustomAdminSite(name='custom_admin')

# Appliquer les paramètres à notre instance personnalisée
admin_site.site_header = settings.ADMIN_SITE_HEADER
admin_site.site_title = settings.ADMIN_SITE_TITLE
admin_site.index_title = settings.ADMIN_INDEX_TITLE

# Enregistrer les modèles dans l'ordre souhaité
admin_site.register(User, CustomUserAdmin)
admin_site.register(Organisation, OrganisationAdmin)
admin_site.register(Candidat, CandidatAdmin)
admin_site.register(OrganisationRole, OrganisationRoleAdmin)
admin_site.register(ScrapingTask, ScrapingTaskAdmin)

urlpatterns = [
    path('', admin_site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
