from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User, Permission
from django.contrib.contenttypes.models import ContentType
from django import forms
from app.models import OrganisationUser, Candidat

class OrganisationUserInline(admin.StackedInline):
    model = OrganisationUser
    extra = 1
    verbose_name = "Organisation"
    verbose_name_plural = "Organisations"

class CustomUserAdminForm(forms.ModelForm):
    candidat_permissions = forms.MultipleChoiceField(
        required=False,
        widget=forms.CheckboxSelectMultiple,
        choices=[
            ('add_candidat', 'Peut ajouter des candidats'),
            ('change_candidat', 'Peut modifier des candidats'),
            ('delete_candidat', 'Peut supprimer des candidats'),
            ('view_candidat', 'Peut voir les candidats'),
        ]
    )

    class Meta:
        model = User
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            current_perms = self.instance.user_permissions.values_list('codename', flat=True)
            self.initial['candidat_permissions'] = [
                perm for perm in ['add_candidat', 'change_candidat', 'delete_candidat', 'view_candidat']
                if perm in current_perms
            ]

class CustomUserAdmin(UserAdmin):
    form = CustomUserAdminForm
    list_display = ('username', 'email', 'get_organisations', 'get_permissions_display')
    list_filter = ('is_staff', 'is_superuser', 'organisationuser__organisation')
    inlines = [OrganisationUserInline]

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        
        if 'candidat_permissions' in form.cleaned_data:
            content_type = ContentType.objects.get_for_model(Candidat)
            
            candidat_perms = Permission.objects.filter(
                content_type=content_type,
                codename__in=['add_candidat', 'change_candidat', 'delete_candidat', 'view_candidat']
            )
            
            obj.user_permissions.remove(*candidat_perms)
            
            selected_perms = form.cleaned_data['candidat_permissions']
            if selected_perms:
                new_perms = Permission.objects.filter(
                    content_type=content_type,
                    codename__in=selected_perms
                )
                obj.user_permissions.add(*new_perms)

    def get_fieldsets(self, request, obj=None):
        if not obj:
            return self.add_fieldsets
        
        if request.user.is_superuser:
            return (
                (None, {'fields': ('username', 'password')}),
                ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email')}),
                ('Permissions', {
                    'fields': ('is_active', 'is_staff'),
                    'classes': ('wide',),
                    'description': "Gérer les permissions de l'utilisateur"
                }),
            )
        return (
            (None, {'fields': ('username', 'password')}),
            ('Informations personnelles', {'fields': ('first_name', 'last_name', 'email')}),
        )

    def get_organisations(self, obj):
        return ", ".join([ou.organisation.name for ou in obj.organisationuser_set.all()])
    get_organisations.short_description = "Organisations"

    def get_permissions_display(self, obj):
        perms = obj.user_permissions.values_list('codename', flat=True)
        return ", ".join(perms)
    get_permissions_display.short_description = "Permissions"

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return obj is not None and obj.id == request.user.id

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        return obj is not None and obj.id == request.user.id

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(id=request.user.id) 