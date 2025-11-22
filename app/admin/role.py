from django.contrib import admin
from app.models import Organisation

class OrganisationRoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'organisation', 'get_permissions_count')
    list_filter = ('organisation',)
    filter_horizontal = ('permissions',)

    def get_permissions_count(self, obj):
        return obj.permissions.count()
    get_permissions_count.short_description = "Nombre de permissions"

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(organisation__organisationuser__user=request.user)
        return qs

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "organisation" and not request.user.is_superuser:
            kwargs["queryset"] = Organisation.objects.filter(
                organisationuser__user=request.user
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs) 