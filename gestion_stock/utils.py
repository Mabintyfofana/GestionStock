import random
import string
from datetime import datetime
from django.db.models import Q
from django.utils import timezone

def generer_code_article():
    """Génère un code article unique"""
    prefixe = 'ART'
    timestamp = datetime.now().strftime('%y%m%d')
    random_part = ''.join(random.choices(string.digits, k=4))
    return f"{prefixe}{timestamp}{random_part}"

def generer_code_barre():
    """Génère un code-barres EAN-13"""
    # Pour simplifier, on génère un code factice
    # En production, utiliser une bibliothèque dédiée
    return '5' + ''.join(random.choices(string.digits, k=12))

def verifier_alertes():
    """Vérifie et crée les alertes automatiques"""
    from .models import Article, Alerte
    
    # Alertes de stock faible
    articles_stock_faible = Article.objects.filter(
        stock__quantite__lte=F('seuil_alerte'),
        stock__quantite__gt=0
    )
    
    for article in articles_stock_faible:
        Alerte.objects.get_or_create(
            type_alerte='stock_faible',
            article=article,
            defaults={
                'message': f"Stock faible pour {article.designation}: {article.quantite_stock} unités",
                'priorite': 2,
            }
        )
    
    # Alertes de péremption
    date_limite = timezone.now().date() + timezone.timedelta(days=30)
    articles_peremption = Article.objects.filter(
        date_peremption__lte=date_limite,
        date_peremption__gte=timezone.now().date()
    )
    
    for article in articles_peremption:
        jours_restants = (article.date_peremption - timezone.now().date()).days
        Alerte.objects.get_or_create(
            type_alerte='peremption',
            article=article,
            defaults={
                'message': f"Péremption proche pour {article.designation}: {jours_restants} jours",
                'priorite': 3 if jours_restants <= 7 else 2,
            }
        )
    
    # Alertes de rupture
    articles_rupture = Article.objects.filter(stock__quantite=0)
    
    for article in articles_rupture:
        Alerte.objects.get_or_create(
            type_alerte='rupture',
            article=article,
            defaults={
                'message': f"Rupture de stock pour {article.designation}",
                'priorite': 3,
            }
        )

def calculer_statistiques():
    """Calcule les statistiques pour le dashboard"""
    from .models import Article, Stock, MouvementStock
    
    stats = {
        'total_articles': Article.objects.count(),
        'articles_actifs': Article.objects.filter(actif=True).count(),
        'valeur_stock_total': 0,
        'alertes': 0,
    }
    
    # Calcul de la valeur totale du stock
    stocks = Stock.objects.select_related('article')
    stats['valeur_stock_total'] = sum(
        stock.quantite * stock.article.prix_achat for stock in stocks
    )
    
    # Nombre d'alertes
    stats['alertes'] = Article.objects.filter(
        Q(stock__quantite__lte=F('seuil_alerte')) |
        Q(date_peremption__lte=timezone.now().date() + timezone.timedelta(days=30))
    ).count()
    
    return stats

def exporter_articles_csv():
    """Exporte les articles en format CSV"""
    import csv
    from io import StringIO
    from .models import Article
    
    output = StringIO()
    writer = csv.writer(output)
    
    # En-tête
    writer.writerow([
        'code_article', 'designation', 'categorie', 
        'prix_achat', 'prix_vente', 'stock', 'seuil_alerte'
    ])
    
    # Données
    articles = Article.objects.select_related('categorie', 'stock').all()
    for article in articles:
        writer.writerow([
            article.code_article,
            article.designation,
            article.categorie.nom if article.categorie else '',
            str(article.prix_achat),
            str(article.prix_vente),
            article.quantite_stock,
            article.seuil_alerte,
        ])
    
    return output.getvalue()

def generer_qr_code_article(article):
    """Génère les données pour le QR code d'un article"""
    data = {
        'code': article.code_article,
        'designation': article.designation,
        'prix': str(article.prix_vente),
        'categorie': article.categorie.nom if article.categorie else '',
    }
    return data

def enregistrer_audit(utilisateur, action, type_element, description, request=None):
    """Enregistre une action dans le journal d'audit"""
    from .models import JournalAudit
    ip_address = None
    if request:
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip_address = x_forwarded_for.split(',')[0]
        else:
            ip_address = request.META.get('REMOTE_ADDR')
            
    JournalAudit.objects.create(
        utilisateur=utilisateur if utilisateur and utilisateur.is_authenticated else None,
        action=action,
        type_element=type_element,
        description=description,
        ip_address=ip_address
    )