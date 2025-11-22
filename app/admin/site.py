from django.contrib import admin
from app.models import OrganisationUser

class CustomAdminSite(admin.AdminSite):
    @staticmethod
    def get_organisation_name(request):
        """Obtenir le nom de l'organisation de l'utilisateur connecté"""
        if not request.user.is_authenticated:
            return None
        if request.user.is_superuser:
            return "BLS Rapido"
        try:
            org_user = OrganisationUser.objects.get(user=request.user)
            return f"BLS Rapido - {org_user.organisation.name}"
        except OrganisationUser.DoesNotExist:
            return None

    def each_context(self, request):
        """Surcharge pour personnaliser le contexte de chaque page"""
        context = super().each_context(request)
        org_name = self.get_organisation_name(request)
        
        if org_name:
            if request.user.is_superuser:
                context['site_header'] = 'BLS Rapido - Administration'
                context['site_title'] = 'BLS Rapido'
                context['index_title'] = 'Administration Générale'
            else:
                context['site_header'] = org_name
                context['site_title'] = 'BLS Rapido'
                context['index_title'] = 'Gestion des rendez-vous'
        
        return context

    def has_permission(self, request):
        # Vérifier si l'utilisateur est actif et son organisation est active
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        try:
            org_user = OrganisationUser.objects.get(user=request.user)
            return request.user.is_staff and request.user.is_active and org_user.organisation.is_active
        except OrganisationUser.DoesNotExist:
            return False