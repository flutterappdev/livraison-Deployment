from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib import messages
from django.http import HttpResponseRedirect
from app.models import Candidat

class ScrapingTaskAdmin(admin.ModelAdmin):
    list_display = ['candidat', 'get_status_display', 'success', 'last_run', 'attempts']
    list_filter = ['status', 'success']
    
    def get_fieldsets(self, request, obj=None):
        if obj and obj.status == 'waiting_otp':
            return [
                ('Saisie du code OTP', {
                    'fields': ['otp'],
                    'description': mark_safe(
                        '<div class="alert alert-warning" style="padding: 10px; '
                        'background-color: #fff3cd; border: 1px solid #ffeeba; '
                        'border-radius: 4px; margin-bottom: 10px;">'
                        '<strong>⚠️ Action requise :</strong> '
                        'Un code OTP a été envoyé par email. '
                        'Veuillez le saisir ci-dessous pour continuer le processus.'
                        '</div>'
                    )
                }),
                ('Données sensibles', {
                    'fields': ['temp_password', 'new_password', 'data_protection_url'],
                    'description': "Historique des données sensibles"
                })
            ]
        elif obj and obj.status == 'waiting_password':
            return [
                ('Saisie des mots de passe', {
                    'fields': ['temp_password', 'new_password'],
                    'description': mark_safe(
                        '<div class="alert alert-warning" style="padding: 10px; '
                        'background-color: #fff3cd; border: 1px solid #ffeeba; '
                        'border-radius: 4px; margin-bottom: 10px;">'
                        '<strong>⚠️ Action requise :</strong> '
                        'Veuillez saisir le mot de passe temporaire reçu par email '
                        'ainsi que le nouveau mot de passe à définir.'
                        '</div>'
                    )
                }),
                ('Autres données', {
                    'fields': ['otp', 'data_protection_url'],
                })
            ]
        elif obj and obj.status == 'waiting_data_protection':
            return [
                ('URL de protection des données', {
                    'fields': ['data_protection_url'],
                    'description': mark_safe(
                        '<div class="alert alert-warning" style="padding: 10px; '
                        'background-color: #fff3cd; border: 1px solid #ffeeba; '
                        'border-radius: 4px; margin-bottom: 10px;">'
                        '<strong>⚠️ Action requise :</strong> '
                        'Veuillez saisir l\'URL de confirmation reçue par email.'
                        '</div>'
                    )
                }),
                ('Données précédentes', {
                    'fields': ['otp', 'temp_password', 'new_password'],
                })
            ]
        return [
            ('Informations générales', {
                'fields': ['candidat', 'status', 'success']
            }),
            ('Données sensibles', {
                'fields': ['otp', 'temp_password', 'new_password', 'data_protection_url'],
                'description': "Historique complet des données sensibles"
            }),
            ('Détails', {
                'fields': ['error_message', 'attempts', 'last_run', 'next_run'],
                'classes': ('collapse',)
            }),
        ]

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.status == 'waiting_otp':
            form.base_fields['otp'].widget.attrs.update({
                'autofocus': True,
                'style': 'font-size: 20px; padding: 10px; width: 200px; text-align: center;'
            })
        return form

    def response_change(self, request, obj):
        if obj.status == 'waiting_otp' and obj.otp:
            messages.success(request, "Code OTP enregistré avec succès !")
            return HttpResponseRedirect("../")
        return super().response_change(request, obj)

    def changelist_view(self, request, extra_context=None):
        waiting_otp_tasks = self.get_queryset(request).filter(status='waiting_otp')
        if waiting_otp_tasks.exists():
            for task in waiting_otp_tasks:
                messages.warning(
                    request, 
                    format_html(
                        '<strong>Action requise :</strong> Tâche en attente d\'OTP pour {} - '
                        '<a href="{}">Saisir l\'OTP</a>',
                        task.candidat.email,
                        f'/app/scrapingtask/{task.id}/change/'
                    )
                )
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        obj = self.get_object(request, object_id)
        if obj and obj.status == 'waiting_otp':
            messages.warning(
                request,
                "Cette tâche attend un code OTP. Veuillez saisir le code reçu par email."
            )
            extra_context = extra_context or {}
            extra_context['show_save'] = True
            extra_context['show_save_and_continue'] = False
        return super().change_view(
            request, object_id, form_url, extra_context=extra_context
        )

    def get_status_display(self, obj):
        status_colors = {
            'pending': 'gray',
            'running': 'blue',
            'waiting_otp': 'orange',
            'waiting_password': 'orange',
            'waiting_data_protection': 'orange',
            'completed': 'green',
            'failed': 'red',
        }
        color = status_colors.get(obj.status, 'gray')
        
        if obj.status in ['waiting_otp', 'waiting_password', 'waiting_data_protection']:
            actions = {
                'waiting_otp': 'Saisir OTP',
                'waiting_password': 'Saisir mot de passe',
                'waiting_data_protection': 'Saisir URL de protection des données'
            }
            action = actions.get(obj.status)
            return format_html(
                '<span style="color: {};">● {}</span> '
                '<span style="color: {}"><strong>(Action requise : {})</strong></span>',
                color, obj.get_status_display(), color, action
            )
        
        return format_html(
            '<span style="color: {};">● {}</span>',
            color,
            obj.get_status_display()
        )
    get_status_display.short_description = "Statut"

    def has_view_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.candidat.organisation.organisationuser_set.filter(user=request.user).exists()

    def has_change_permission(self, request, obj=None):
        if request.user.is_superuser:
            return True
        if obj is None:
            return True
        return obj.candidat.organisation.organisationuser_set.filter(user=request.user).exists()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(candidat__organisation__organisationuser__user=request.user)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "candidat" and not request.user.is_superuser:
            kwargs["queryset"] = Candidat.objects.filter(
                organisation__organisationuser__user=request.user
            )
        return super().formfield_for_foreignkey(db_field, request, **kwargs) 