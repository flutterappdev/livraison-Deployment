from django.contrib import admin
from app.models import OrganisationUser

class OrganisationAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at', 'get_users_count', 'has_proxy')
    list_display_links = ('name',)
    search_fields = ('name',)
    list_filter = ('is_active',)
    list_per_page = 20
    ordering = ('name',)
    
    def get_fieldsets(self, request, obj=None):
        if not request.user.is_authenticated:
            return []
            
        if request.user.is_superuser:
            return [
                ('Informations générales', {
                    'fields': ('name', 'is_active')
                }),
                ('Configuration du proxy', {
                    'fields': ('proxy',),
                    'description': 'Format: username:password@host:port',
                    'classes': ('collapse',)
                })
            ]
        else:
            return [
                ('Configuration du proxy', {
                    'fields': ('proxy',),
                    'description': 'Format: username:password@host:port'
                })
            ]

    def has_view_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return OrganisationUser.objects.filter(
            user=request.user,
            organisation=obj,
            role='admin'
        ).exists()

    def has_change_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        if obj is None:
            return False
        return OrganisationUser.objects.filter(
            user=request.user,
            organisation=obj,
            role='admin'
        ).exists()

    def has_module_permission(self, request):
        if not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return OrganisationUser.objects.filter(
            user=request.user,
            role='admin'
        ).exists()

    def has_add_permission(self, request):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if not request.user.is_authenticated:
            return False
        return request.user.is_superuser

    def get_queryset(self, request):
        if not request.user.is_authenticated:
            return self.model.objects.none()
            
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs.prefetch_related('organisationuser_set')
        return qs.filter(
            organisationuser__user=request.user,
            organisationuser__role='admin'
        ).prefetch_related('organisationuser_set')

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser:
            return []
        return ['name', 'is_active']

    def get_users_count(self, obj):
        """Obtenir le nombre d'utilisateurs de l'organisation"""
        return obj.organisationuser_set.count()
    get_users_count.short_description = "Nombre d'utilisateurs"
    get_users_count.admin_order_field = 'organisationuser__count'

    def has_proxy(self, obj):
        """Vérifie si l'organisation a un proxy configuré"""
        return bool(obj.proxy)
    has_proxy.boolean = True
    has_proxy.short_description = "Proxy configuré" 