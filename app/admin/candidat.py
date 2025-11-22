from django.contrib import admin
from django import forms
from django.core.exceptions import ValidationError
from django.contrib import messages
import re
from datetime import date
import calendar
from app.models import Candidat, CarteBancaire, OrganisationUser, ScrapingTask
from app.utils.constants import CANDIDAT_VISA_CHOICES
from app.actions import bls_take_appointment
from app.tasks import run_scraping_task
from django.utils.html import format_html
from django.shortcuts import redirect
from copy import deepcopy

class ExpiryDateWidget(forms.TextInput):
    def __init__(self, attrs=None):
        default_attrs = {
            'placeholder': 'MM/YY',
            'pattern': '(0[1-9]|1[0-2])/[0-9]{2}',
            'class': 'expiry-date-input'
        }
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def format_value(self, value):
        if isinstance(value, date):
            return value.strftime('%m/%y')
        return value or ''

class CarteBancaireForm(forms.ModelForm):
    date_expiration = forms.CharField(
        widget=ExpiryDateWidget(),
        help_text="Format: MM/YY (ex: 05/25)"
    )

    class Meta:
        model = CarteBancaire
        fields = '__all__'

    def clean_date_expiration(self):
        value = self.cleaned_data['date_expiration']
        if not value:
            return None

        try:
            if not re.match(r'^(0[1-9]|1[0-2])/[0-9]{2}$', value):
                raise ValidationError("Format invalide. Utilisez MM/YY (ex: 05/25)")

            month, year = value.split('/')
            month = int(month)
            year = int('20' + year)

            last_day = calendar.monthrange(year, month)[1]
            expiry_date = date(year, month, last_day)

            if expiry_date < date.today():
                raise ValidationError("La carte est expirée")

            return expiry_date

        except ValueError:
            raise ValidationError("Format invalide. Utilisez MM/YY (ex: 05/25)")

class CarteBancaireInline(admin.StackedInline):
    model = CarteBancaire
    form = CarteBancaireForm
    can_delete = False
    min_num = 1
    max_num = 1
    
    fieldsets = [
        ('Informations de paiement', {
            'fields': [
                'numero',
                'date_expiration',
                'cvv',
                'nom_titulaire'
            ]
        })
    ]

class CandidatAdminForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
            
        self.fields['visa'].choices = CANDIDAT_VISA_CHOICES

        self.fields['visa'].required = True
        self.fields['visa'].empty_label = None

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    class Meta:
        model = Candidat
        fields = '__all__'
        widgets = {
            'passport_number': forms.TextInput(attrs={
                'placeholder': 'AB1234567',
                'style': 'text-transform:uppercase;'
            }),
            'date_of_birth': forms.DateInput(
                attrs={
                    'type': 'date',
                    'placeholder': 'AAAA-MM-JJ',
                    'pattern': r'\d{4}-\d{2}-\d{2}'
                },
                format='%Y-%m-%d'
            )
        }

    class Media:
        css = {
            'all': ('admin/css/custom.css',)
        }

class CandidatAdmin(admin.ModelAdmin):
    list_display = (
        'get_full_name', 'email', 'location', 'visa', 
        'get_status_display',
        'created_at',
        'appointment_date'
    )
    list_filter = (
        'location', 'visa',
        'category', 'scraping_task__status'
    )
    readonly_fields = ('status', 'appointment_date', 'appointment_details')
    actions = ["start_scraping", "duplicate_candidate", bls_take_appointment]
    inlines = [CarteBancaireInline]
    form = CandidatAdminForm
    
    fieldsets = [
        ('Informations personnelles', {
            'fields': (
                ('first_name', 'last_name'),
                'surname_at_birth',
                'email',
                'phone_number',
                'date_of_birth',
                'place_of_birth',
                'country_of_birth',
                'current_nationality',
                'nationality_at_birth',
                'gender',
                'marital_status',
                'profile_photo',
            )
        }),
        ('Informations de voyage', {
            'fields': (
                'travel_date',
                'purpose_of_journey',
                'member_state_destination',
                'member_state_second_destination',
                'member_state_first_entry',
                'number_of_entries',
                'intended_stay_duration',
            )
        }),
        ('Informations de visa', {
            'fields': (
                'category',
                'location',
                'visa',
                'visa_subtype',
            )
        }),
        ('Informations de passeport', {
            'fields': (
                'passport_number',
                'passport_type',
                'passport_issue_date',
                'passport_expiry_date',
                'passport_issue_place',
            )
        }),
    ]

    def has_module_permission(self, request):
        if request.user.is_superuser:
            return False
        return True

    def has_view_permission(self, request, obj=None):
        if not request.user.is_active:
            return False
        if request.user.is_superuser:
            return False
        if obj is None:
            return True
        return OrganisationUser.objects.filter(
            user=request.user,
            organisation=obj.organisation,
            organisation__is_active=True
        ).exists()

    def has_change_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        return self.has_view_permission(request, obj)
    
    def has_add_permission(self, request):
        if request.user is not None:
            return True
        return False

    def save_model(self, request, obj, form, change):
        if not change:  # Si c'est une création
            if not request.user.is_superuser:
                try:
                    org_user = OrganisationUser.objects.get(user=request.user)
                    obj.organisation = org_user.organisation
                except OrganisationUser.DoesNotExist:
                    raise ValidationError("Vous devez être associé à une organisation.")
            elif not obj.organisation:
                raise ValidationError("L'organisation est obligatoire.")
        
        super().save_model(request, obj, form, change)

    def start_scraping(self, request, queryset):
        for candidat in queryset:
            try:
                task = ScrapingTask.objects.get_or_create(candidat=candidat)[0]
                run_scraping_task.delay(task.id, user_id=request.user.id)
                self.message_user(
                    request,
                    f"Tâche lancée pour {candidat.get_full_name()}",
                    messages.SUCCESS
                )
            except Exception as e:
                self.message_user(
                    request,
                    f"Erreur pour {candidat.get_full_name()}: {str(e)}",
                    messages.ERROR
                )

    start_scraping.short_description = "Lancer l'inscription BLS"

    def get_appointment_info(self, obj):
        if obj.appointment_date:
            return f"{obj.appointment_date.strftime('%d/%m/%Y %H:%M')} - {obj.appointment_details or ''}"
        return "-"
    get_appointment_info.short_description = "Rendez-vous"

    def duplicate_candidate(self, request, queryset):
        if len(queryset) != 1:
            self.message_user(
                request,
                "Veuillez sélectionner un seul candidat à dupliquer.",
                messages.ERROR
            )
            return

        original = queryset.first()
        new_candidate = deepcopy(original)
        new_candidate.pk = None  # Réinitialiser la clé primaire

        # Modifier les champs uniques pour éviter les doublons
        new_candidate.first_name = f"{original.first_name} (copie)"
        new_candidate.last_name = f"{original.last_name}"
        new_candidate.email = f"copie_{original.email}"  # email doit être unique
        new_candidate.phone_number = original.phone_number[:-1] + "1"  # Modifier le dernier chiffre
        
        # Modifier le numéro de passeport (format: AB1234567)
        passport_base = original.passport_number[:-1]  # Prendre tout sauf le dernier caractère
        last_digit = int(original.passport_number[-1])
        new_digit = (last_digit + 1) % 10  # Incrémenter le dernier chiffre (revenir à 0 si 9)
        new_candidate.passport_number = passport_base + str(new_digit)
        
        new_candidate.profile_photo = None
        
        try:
            new_candidate.save()
            
            # Copier la carte bancaire associée
            if hasattr(original, 'cartebancaire'):
                original_cb = original.cartebancaire
                new_cb = deepcopy(original_cb)
                new_cb.pk = None
                new_cb.candidat = new_candidate
                new_cb.save()

            self.message_user(
                request,
                format_html(
                    'Candidat dupliqué avec succès. <a href="{}">Modifier le nouveau candidat</a>',
                    f"../candidat/{new_candidate.pk}/change/"
                ),
                messages.SUCCESS
            )
            
            return redirect(f"../candidat/{new_candidate.pk}/change/")
            
        except Exception as e:
            self.message_user(
                request,
                f"Erreur lors de la duplication : {str(e)}",
                messages.ERROR
            )

    duplicate_candidate.short_description = "Dupliquer le candidat sélectionné" 