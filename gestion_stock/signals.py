from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .models import Alerte
from django.utils import timezone

@receiver(post_save, sender=Alerte)
def envoyer_notification_alerte(sender, instance, created, **kwargs):
    """Envoie un e-mail aux administrateurs lorsqu'une nouvelle alerte est créée."""
    if created and settings.ADMIN_EMAILS:
        # Préparer le contexte pour le template
        if instance.type_alerte == 'stock_faible':
            titre = "Alerte de Stock Faible"
            niveau = "warning"
            colonne_extra = "Emplacement"
            valeur_extra = instance.article.emplacement if instance.article else "N/A"
        elif instance.type_alerte == 'rupture':
            titre = "Alerte de Rupture de Stock"
            niveau = "danger"
            colonne_extra = "Emplacement"
            valeur_extra = instance.article.emplacement if instance.article else "N/A"
        elif instance.type_alerte == 'peremption':
            titre = "Alerte de Péremption Proche"
            niveau = "warning"
            colonne_extra = "Date de péremption"
            valeur_extra = instance.article.date_peremption.strftime('%d/%m/%Y') if instance.article and instance.article.date_peremption else "N/A"
        else:
            titre = "Nouvelle Alerte Système"
            niveau = "info"
            colonne_extra = ""
            valeur_extra = ""

        # Simuler un objet "article" avec les attributs attendus par le template
        article_data = []
        if instance.article:
            article_data.append({
                'designation': instance.article.designation,
                'quantite_stock': instance.article.quantite_stock,
                'seuil_alerte': instance.article.seuil_alerte,
                'valeur_extra': valeur_extra
            })

        context = {
            'type_alerte': instance.get_type_alerte_display(),
            'titre': titre,
            'niveau': niveau,
            'message': instance.message,
            'articles': article_data,
            'colonne_extra': colonne_extra,
            'app_url': 'http://127.0.0.1:8000/dashboard/',  # À adapter en production
            'date_envoi': timezone.now().strftime('%d/%m/%Y %H:%M'),
        }

        # Rendu du HTML et texte
        html_content = render_to_string('gestion_stock/emails/alerte_stock.html', context)
        text_content = strip_tags(html_content)

        # Création et envoi de l'e-mail
        email = EmailMultiAlternatives(
            subject=f"[StockMaster] {titre}",
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=settings.ADMIN_EMAILS,
        )
        email.attach_alternative(html_content, "text/html")
        
        try:
            email.send(fail_silently=True)
        except Exception as e:
            print(f"Erreur lors de l'envoi de l'e-mail: {e}")
