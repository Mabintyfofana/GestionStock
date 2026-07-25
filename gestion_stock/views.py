import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Q, Sum, Count, F, ExpressionWrapper, DecimalField
from django.utils import timezone
from datetime import datetime, timedelta
import csv
from django.http import HttpResponse, JsonResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .decorators import *
from .models import *
from .forms import *
from .utils import *

def redirection_par_role(request):
    """Redirige l'utilisateur vers le dashboard approprié selon son rôle"""
    if not request.user.is_authenticated:
        return redirect('login')
    
    try:
        profil = request.user.profilutilisateur
        if profil.role == 'admin':
            return redirect('dashboard_admin')
        elif profil.role == 'gestionnaire':
            return redirect('dashboard_gestionnaire')
        else:  # vendeur
            return redirect('dashboard')
    except:
        # Si pas de profil, rediriger vers login
        return redirect('login')
    return render(request, 'gestion_stock/profil/detail.html')

@login_required
def dashboard(request):
    """Dashboard pour vendeur"""
    # Récupérer les statistiques
    total_articles = Article.objects.filter(actif=True).count()
    total_stock = Stock.objects.aggregate(total=Sum('quantite'))['total'] or 0
    
    # Calculer la valeur totale du stock
    valeur_totale = Stock.objects.annotate(
        valeur=ExpressionWrapper(F('quantite') * F('article__prix_achat'), output_field=DecimalField(max_digits=12, decimal_places=2))
    ).aggregate(total=Sum('valeur'))['total'] or 0
    
    # Alertes
    alertes_stock = Article.objects.filter(
        stock__quantite__lte=F('seuil_alerte'),
        stock__quantite__gt=0,
        actif=True
    ).count()
    
    alertes_peremption = Article.objects.filter(
        date_peremption__lte=timezone.now().date() + timedelta(days=30),
        date_peremption__gte=timezone.now().date(),
        actif=True
    ).count()
    
    # Derniers mouvements
    derniers_mouvements = MouvementStock.objects.select_related('article', 'utilisateur').order_by('-date_mouvement')[:10]
    
    # Articles en rupture
    articles_rupture = Article.objects.filter(stock__quantite=0, actif=True)[:5]

    # --- DONNÉES GRAPHIQUES RÉELLES ---

    # 1. Stock par catégorie (Donut)
    categories_stock = (
        Categorie.objects.annotate(
            total_qte=Sum('article__stock__quantite')
        ).filter(total_qte__gt=0).values('nom', 'total_qte')
    )
    chart_categories_labels = json.dumps([c['nom'] for c in categories_stock])
    chart_categories_data   = json.dumps([int(c['total_qte']) for c in categories_stock])

    # 2. Mouvements des 7 derniers jours (Barres)
    jours_labels = []
    entrees_data = []
    sorties_data = []
    for i in range(6, -1, -1):
        jour = timezone.now().date() - timedelta(days=i)
        jours_labels.append(jour.strftime('%a %d/%m'))
        entrees_data.append(
            MouvementStock.objects.filter(
                type_mouvement='entree',
                date_mouvement__date=jour
            ).aggregate(total=Sum('quantite'))['total'] or 0
        )
        sorties_data.append(
            MouvementStock.objects.filter(
                type_mouvement='sortie',
                date_mouvement__date=jour
            ).aggregate(total=Sum('quantite'))['total'] or 0
        )
    chart_jours_labels  = json.dumps(jours_labels)
    chart_entrees_data  = json.dumps(entrees_data)
    chart_sorties_data  = json.dumps(sorties_data)

    # 3. Top 5 articles les plus en stock (Barres horizontales)
    top_articles = (
        Stock.objects.select_related('article')
        .order_by('-quantite')[:5]
        .values('article__designation', 'quantite')
    )
    chart_top_labels = json.dumps([a['article__designation'][:25] for a in top_articles])
    chart_top_data   = json.dumps([a['quantite'] for a in top_articles])

    context = {
        'total_articles': total_articles,
        'total_stock': total_stock,
        'valeur_totale': valeur_totale,
        'alertes_stock': alertes_stock,
        'alertes_peremption': alertes_peremption,
        'derniers_mouvements': derniers_mouvements,
        'articles_rupture': articles_rupture,
        # Données graphiques
        'chart_categories_labels': chart_categories_labels,
        'chart_categories_data': chart_categories_data,
        'chart_jours_labels': chart_jours_labels,
        'chart_entrees_data': chart_entrees_data,
        'chart_sorties_data': chart_sorties_data,
        'chart_top_labels': chart_top_labels,
        'chart_top_data': chart_top_data,
    }
    
    return render(request, 'gestion_stock/dashboard.html', context)

@login_required
@admin_required
def dashboard_admin(request):
    """Dashboard spécifique pour l'administrateur"""
    # Statistiques avancées pour admin
    total_utilisateurs = User.objects.count()
    utilisateurs_actifs = User.objects.filter(is_active=True).count()
    
    # Alertes système
    alertes_systeme = Alerte.objects.filter(lu=False).count()
    
    # Récupérer les données du dashboard normal
    total_articles = Article.objects.count()
    total_stock = Stock.objects.aggregate(total=Sum('quantite'))['total'] or 0
    
    valeur_totale = Stock.objects.annotate(
        valeur=ExpressionWrapper(F('quantite') * F('article__prix_achat'), output_field=DecimalField(max_digits=12, decimal_places=2))
    ).aggregate(total=Sum('valeur'))['total'] or 0
    
    # Mouvements des 24 dernières heures
    date_limite = timezone.now() - timedelta(hours=24)
    mouvements_24h = MouvementStock.objects.filter(date_mouvement__gte=date_limite).count()
    
    # Derniers utilisateurs connectés
    derniers_connectes = User.objects.filter(last_login__isnull=False).order_by('-last_login')[:10]
    
    context = {
        'total_utilisateurs': total_utilisateurs,
        'utilisateurs_actifs': utilisateurs_actifs,
        'alertes_systeme': alertes_systeme,
        'total_articles': total_articles,
        'total_stock': total_stock,
        'valeur_totale': valeur_totale,
        'mouvements_24h': mouvements_24h,
        'derniers_connectes': derniers_connectes,
    }
    
    return render(request, 'gestion_stock/dashboard_admin.html', context)

@login_required
@gestionnaire_required
def dashboard_gestionnaire(request):
    """Dashboard spécifique pour le gestionnaire"""
    # Statistiques pour gestionnaire
    commandes_en_attente = CommandeFournisseur.objects.filter(statut='envoyee').count()
    ajustements_recents = AjustementStock.objects.filter(
        date_ajustement__gte=timezone.now() - timedelta(days=7)
    ).count()
    
    # Récupérer les données du dashboard normal
    total_articles = Article.objects.filter(actif=True).count()
    total_stock = Stock.objects.aggregate(total=Sum('quantite'))['total'] or 0
    
    valeur_totale = Stock.objects.annotate(
        valeur=ExpressionWrapper(F('quantite') * F('article__prix_achat'), output_field=DecimalField(max_digits=12, decimal_places=2))
    ).aggregate(total=Sum('valeur'))['total'] or 0
    
    context = {
        'commandes_en_attente': commandes_en_attente,
        'ajustements_recents': ajustements_recents,
        'total_articles': total_articles,
        'total_stock': total_stock,
        'valeur_totale': valeur_totale,
    }
    
    return render(request, 'gestion_stock/dashboard_gestionnaire.html', context)

def register(request):
    """Inscription d'un nouvel utilisateur (admin seulement)"""
    if not request.user.is_authenticated:
        messages.error(request, 'Vous devez être connecté pour accéder à cette page.')
        return redirect('login')
    
    if request.user.profilutilisateur.role != 'admin':
        messages.error(request, 'Seul l\'administrateur peut créer des comptes.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utilisateur créé avec succès!')
            return redirect('liste_utilisateurs')
    else:
        form = InscriptionForm()
    
    return render(request, 'gestion_stock/register.html', {'form': form})

@login_required
@gestionnaire_required
def liste_articles(request):
    form = RechercheArticleForm(request.GET or None)
    articles = Article.objects.select_related('categorie', 'fournisseur').all()
    
    if form.is_valid():
        recherche = form.cleaned_data.get('recherche')
        categorie = form.cleaned_data.get('categorie')
        
        if recherche:
            articles = articles.filter(
                Q(code_article__icontains=recherche) |
                Q(designation__icontains=recherche) |
                Q(code_barre__icontains=recherche)
            )
        
        if categorie:
            articles = articles.filter(categorie=categorie)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(articles, 20)
    
    try:
        articles_page = paginator.page(page)
    except PageNotAnInteger:
        articles_page = paginator.page(1)
    except EmptyPage:
        articles_page = paginator.page(paginator.num_pages)
    
    context = {
        'articles': articles_page,
        'form': form,
    }
    return render(request, 'gestion_stock/articles/liste.html', context)

@login_required
@gestionnaire_required
def ajouter_article(request):
    if request.method == 'POST':
        form = ArticleForm(request.POST)
        if form.is_valid():
            article = form.save()
            
            # Créer le stock initial
            Stock.objects.create(
                article=article,
                quantite=0,
                emplacement=article.emplacement or 'Défaut'
            )
            
            messages.success(request, 'Article ajouté avec succès!')
            return redirect('liste_articles')
    else:
        form = ArticleForm()
    
    return render(request, 'gestion_stock/articles/ajouter.html', {'form': form})

@login_required
@gestionnaire_required
def modifier_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if request.method == 'POST':
        form = ArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'Article modifié avec succès!')
            return redirect('detail_article', pk=article.pk)
    else:
        form = ArticleForm(instance=article)
    
    # Préparer les données pour le template
    from .models import Categorie
    
    context = {
        'form': form,
        'article': article,
        'categories': Categorie.objects.all(),
        'unite_choices': Article.UNITE_CHOICES,
    }
    
    return render(request, 'gestion_stock/articles/modifier.html', context)

@login_required
@admin_required
def supprimer_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Article supprimé avec succès!')
        return redirect('liste_articles')
    
    return render(request, 'gestion_stock/articles/supprimer.html', {'article': article})

@login_required
def detail_article(request, pk):
    article = get_object_or_404(Article, pk=pk)
    
    # Récupérer les mouvements récents
    mouvements_recents = MouvementStock.objects.filter(article=article).order_by('-date_mouvement')[:10]
    
    # Calculer les statistiques
    date_limite = timezone.now() - timedelta(days=30)
    entrees_30j = MouvementStock.objects.filter(
        article=article,
        type_mouvement='entree',
        date_mouvement__gte=date_limite
    ).aggregate(total=Sum('quantite'))['total'] or 0
    
    sorties_30j = MouvementStock.objects.filter(
        article=article,
        type_mouvement='sortie',
        date_mouvement__gte=date_limite
    ).aggregate(total=Sum('quantite'))['total'] or 0
    
    context = {
        'article': article,
        'mouvements_recents': mouvements_recents,
        'entrees_30j': entrees_30j,
        'sorties_30j': sorties_30j,
    }
    
    return render(request, 'gestion_stock/articles/detail.html', context)

@login_required
@gestionnaire_required
def mouvement_stock(request):
    if request.method == 'POST':
        form = MouvementStockForm(request.POST)
        if form.is_valid():
            mouvement = form.save(commit=False)
            mouvement.utilisateur = request.user
            
            # Récupérer le stock actuel
            stock, created = Stock.objects.get_or_create(
                article=mouvement.article,
                defaults={'quantite': 0, 'emplacement': mouvement.article.emplacement or 'Défaut'}
            )
            mouvement.quantite_avant = stock.quantite
            
            if mouvement.type_mouvement == 'entree':
                mouvement.quantite_apres = stock.quantite + mouvement.quantite
            else:
                # Vérifier si le stock est suffisant pour les sorties
                if mouvement.quantite > stock.quantite:
                    messages.error(request, 'Stock insuffisant!')
                    return render(request, 'gestion_stock/stock/mouvement.html', {'form': form})
                mouvement.quantite_apres = stock.quantite - mouvement.quantite
            
            mouvement.save()
            
            messages.success(request, 'Mouvement enregistré avec succès!')
            return redirect('historique_mouvements')
    else:
        form = MouvementStockForm()
        
        # Pré-remplir les valeurs depuis l'URL
        if 'type' in request.GET:
            form.fields['type_mouvement'].initial = request.GET.get('type')
        if 'article' in request.GET:
            form.fields['article'].initial = request.GET.get('article')
    
    return render(request, 'gestion_stock/stock/mouvement.html', {'form': form})

@login_required
@gestionnaire_required
def ajuster_stock(request):
    if request.method == 'POST':
        form = AjustementStockForm(request.POST)
        if form.is_valid():
            ajustement = form.save(commit=False)
            ajustement.utilisateur = request.user
            
            # Récupérer le stock système
            stock, created = Stock.objects.get_or_create(
                article=ajustement.article,
                defaults={'quantite': 0, 'emplacement': ajustement.article.emplacement or 'Défaut'}
            )
            ajustement.quantite_systeme = stock.quantite
            
            ajustement.save()
            
            messages.success(request, 'Ajustement effectué avec succès!')
            return redirect('historique_mouvements')
    else:
        form = AjustementStockForm()
        
        # Pré-remplir l'article depuis l'URL
        if 'article' in request.GET:
            form.fields['article'].initial = request.GET.get('article')
    
    return render(request, 'gestion_stock/stock/ajuster.html', {'form': form})

@login_required
@gestionnaire_required
def inventaire_stock(request):
    if request.method == 'POST':
        # Logique pour enregistrer un inventaire
        articles_ids = request.POST.getlist('articles[]')
        quantites_reelles = request.POST.getlist('quantites_reelles[]')
        
        for article_id, quantite_reelle in zip(articles_ids, quantites_reelles):
            try:
                article = Article.objects.get(id=article_id)
                stock = Stock.objects.get(article=article)
                
                if int(quantite_reelle) != stock.quantite:
                    # Créer un ajustement
                    AjustementStock.objects.create(
                        article=article,
                        quantite_reelle=int(quantite_reelle),
                        quantite_systeme=stock.quantite,
                        raison='inventaire',
                        description='Inventaire physique',
                        utilisateur=request.user
                    )
            except (Article.DoesNotExist, Stock.DoesNotExist):
                continue
        
        messages.success(request, 'Inventaire enregistré avec succès!')
        return redirect('historique_mouvements')
    
    # GET request: afficher la liste des articles pour inventaire
    articles = Article.objects.prefetch_related('stock_set').filter(actif=True)
    context = {
        'articles': articles,
    }
    return render(request, 'gestion_stock/stock/inventaire.html', context)

@login_required
@gestionnaire_required
def historique_mouvements(request):
    mouvements = MouvementStock.objects.select_related('article', 'utilisateur').order_by('-date_mouvement')
    
    # Filtres
    type_mvt = request.GET.get('type')
    date_debut = request.GET.get('date_debut')
    date_fin = request.GET.get('date_fin')
    article_id = request.GET.get('article')
    
    if type_mvt:
        mouvements = mouvements.filter(type_mouvement=type_mvt)
    
    if date_debut:
        mouvements = mouvements.filter(date_mouvement__date__gte=date_debut)
    
    if date_fin:
        mouvements = mouvements.filter(date_mouvement__date__lte=date_fin)
    
    if article_id:
        mouvements = mouvements.filter(article_id=article_id)
    
    # Pagination
    page = request.GET.get('page', 1)
    paginator = Paginator(mouvements, 50)
    
    try:
        mouvements_page = paginator.page(page)
    except PageNotAnInteger:
        mouvements_page = paginator.page(1)
    except EmptyPage:
        mouvements_page = paginator.page(paginator.num_pages)
    
    context = {
        'mouvements': mouvements_page,
        'types_mouvement': MouvementStock.TYPE_CHOICES,
        'articles': Article.objects.all(),
    }
    return render(request, 'gestion_stock/mouvements/historique.html', context)

@login_required
def detail_mouvement(request, pk):
    mouvement = get_object_or_404(MouvementStock, pk=pk)
    return render(request, 'gestion_stock/mouvements/detail.html', {'mouvement': mouvement})

@login_required
@gestionnaire_required
def liste_fournisseurs(request):
    fournisseurs = Fournisseur.objects.all()
    return render(request, 'gestion_stock/fournisseurs/liste.html', {'fournisseurs': fournisseurs})

@login_required
@gestionnaire_required
def ajouter_fournisseur(request):
    if request.method == 'POST':
        form = FournisseurForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur ajouté avec succès!')
            return redirect('liste_fournisseurs')
    else:
        form = FournisseurForm()
    
    return render(request, 'gestion_stock/fournisseurs/ajouter.html', {'form': form})

@login_required
@gestionnaire_required
def modifier_fournisseur(request, pk):
    fournisseur = get_object_or_404(Fournisseur, pk=pk)
    
    if request.method == 'POST':
        form = FournisseurForm(request.POST, instance=fournisseur)
        if form.is_valid():
            form.save()
            messages.success(request, 'Fournisseur modifié avec succès!')
            return redirect('liste_fournisseurs')
    else:
        form = FournisseurForm(instance=fournisseur)
    
    return render(request, 'gestion_stock/fournisseurs/modifier.html', {'form': form, 'fournisseur': fournisseur})

@login_required
@gestionnaire_required
def liste_commandes(request):
    commandes = CommandeFournisseur.objects.select_related('fournisseur').all()
    return render(request, 'gestion_stock/commandes/liste.html', {'commandes': commandes})

@login_required
@gestionnaire_required
def ajouter_commande(request):
    if request.method == 'POST':
        form = CommandeFournisseurForm(request.POST)
        if form.is_valid():
            commande = form.save(commit=False)
            commande.utilisateur = request.user
            commande.numero = f"CMD-{timezone.now().strftime('%Y%m%d')}-{CommandeFournisseur.objects.count() + 1:04d}"
            commande.save()
            messages.success(request, 'Commande créée avec succès!')
            return redirect('detail_commande', pk=commande.pk)
    else:
        form = CommandeFournisseurForm()
    
    return render(request, 'gestion_stock/commandes/ajouter.html', {'form': form})

@login_required
@gestionnaire_required
def detail_commande(request, pk):
    commande = get_object_or_404(CommandeFournisseur, pk=pk)
    
    if request.method == 'POST':
        # Ajouter une ligne de commande
        article_id = request.POST.get('article')
        quantite = request.POST.get('quantite')
        
        try:
            article = Article.objects.get(id=article_id)
            LigneCommande.objects.create(
                commande=commande,
                article=article,
                quantite=quantite,
                prix_unitaire=article.prix_achat
            )
            messages.success(request, 'Ligne ajoutée avec succès!')
        except Article.DoesNotExist:
            messages.error(request, 'Article non trouvé!')
    
    return render(request, 'gestion_stock/commandes/detail.html', {'commande': commande})

@login_required
def alertes(request):
    # Utiliser prefetch_related au lieu de select_related pour 'stock'
    articles = Article.objects.filter(actif=True).select_related('categorie').prefetch_related('stock_set')
    
    # Filtrer en Python plutôt qu'en base de données
    alertes_rupture = []
    alertes_stock = []
    alertes_peremption = []
    
    today = timezone.now().date()
    
    for article in articles:
        stock = article.stock_set.first()
        if not stock:
            continue
            
        # Rupture
        if stock.quantite == 0:
            alertes_rupture.append(article)
        
        # Stock faible
        elif stock.quantite <= article.seuil_alerte:
            alertes_stock.append(article)
        
        # Péremption
        if article.date_peremption:
            jours_restants = (article.date_peremption - today).days
            if 0 <= jours_restants <= 30:
                alertes_peremption.append(article)
    
    context = {
        'alertes_rupture': alertes_rupture,
        'alertes_stock': alertes_stock,
        'alertes_peremption': alertes_peremption,
    }
    
    return render(request, 'gestion_stock/alertes/liste.html', context)
@login_required
def marquer_alerte_lue(request, pk):
    if pk == 'all':
        Alerte.objects.filter(lu=False).update(lu=True, date_lu=timezone.now())
        messages.success(request, 'Toutes les alertes ont été marquées comme lues.')
    else:
        alerte = get_object_or_404(Alerte, pk=pk)
        alerte.lu = True
        alerte.date_lu = timezone.now()
        alerte.save()
        messages.success(request, 'Alerte marquée comme lue.')
    
    return redirect('alertes')

# @login_required
# def reporting(request):
#     # Statistiques globales
#     total_articles = Article.objects.filter(actif=True).count()
#     total_valeur = Stock.objects.annotate(
#         valeur=ExpressionWrapper(F('quantite') * F('article__prix_achat'), output_field=DecimalField(max_digits=12, decimal_places=2))
#     ).aggregate(total=Sum('valeur'))['total'] or 0
    
#     # Préparer les données pour les graphiques
#     # Mouvements par jour (7 derniers jours)
#     date_debut = timezone.now() - timedelta(days=7)
#     mouvements_par_jour = MouvementStock.objects.filter(
#         date_mouvement__gte=date_debut
#     ).values('date_mouvement__date').annotate(
#         total_entrees=Sum('quantite', filter=Q(type_mouvement='entree')),
#         total_sorties=Sum('quantite', filter=Q(type_mouvement='sortie'))
#     ).order_by('date_mouvement__date')
    
#     # Préparer les labels et données pour le graphique
#     mouvement_labels = []
#     entrees_data = []
#     sorties_data = []
    
#     for i in range(7):
#         date = (timezone.now() - timedelta(days=i)).date()
#         mouvement_labels.insert(0, date.strftime('%d/%m'))
        
#         mouvements_jour = mouvements_par_jour.filter(date_mouvement__date=date).first()
#         if mouvements_jour:
#             entrees_data.insert(0, mouvements_jour['total_entrees'] or 0)
#             sorties_data.insert(0, mouvements_jour['total_sorties'] or 0)
#         else:
#             entrees_data.insert(0, 0)
#             sorties_data.insert(0, 0)
    
#     # Articles les plus vendus (30 derniers jours)
#     date_debut = timezone.now() - timedelta(days=30)
#     articles_vendus = MouvementStock.objects.filter(
#         type_mouvement='sortie',
#         date_mouvement__gte=date_debut
#     ).values('article__designation', 'article__code_article', 'article__categorie__nom', 'article__stock__quantite', 'article__seuil_alerte').annotate(
#         total_vendu=Sum('quantite')
#     ).order_by('-total_vendu')[:10]
    
#     # Valeur par catégorie
#     valeur_par_categorie = Stock.objects.values('article__categorie__nom').annotate(
#         valeur=Sum(F('quantite') * F('article__prix_achat'))
#     ).order_by('-valeur')
    
#     # Préparer les données pour le graphique en camembert
#     category_labels = []
#     category_values = []
    
#     for categorie in valeur_par_categorie[:5]:  # Limiter à 5 catégories principales
#         if categorie['article__categorie__nom']:
#             category_labels.append(categorie['article__categorie__nom'])
#             category_values.append(float(categorie['valeur'] or 0))
    
#     # Alertes par priorité
#     alertes_total = Alerte.objects.filter(lu=False).count()
#     alertes_haute = Alerte.objects.filter(lu=False, priorite=3).count()
#     alertes_moyenne = Alerte.objects.filter(lu=False, priorite=2).count()
#     alertes_basse = Alerte.objects.filter(lu=False, priorite=1).count()
    
#     # Articles avec stock nul
#     articles_stock_nul = Article.objects.filter(stock__quantite=0, actif=True).count()
    
#     # Calculer les mouvements des 30 derniers jours
#     mouvements_30j = MouvementStock.objects.filter(
#         date_mouvement__gte=timezone.now() - timedelta(days=30)
#     ).count()
    
#     context = {
#         'total_articles': total_articles,
#         'total_valeur': total_valeur,
#         'mouvements_par_jour': list(mouvements_par_jour),
#         'articles_vendus': articles_vendus,
#         'valeur_par_categorie': valeur_par_categorie,
#         'alertes_total': alertes_total,
#         'alertes_haute': alertes_haute,
#         'alertes_moyenne': alertes_moyenne,
#         'alertes_basse': alertes_basse,
#         'articles_stock_nul': articles_stock_nul,
#         'mouvements_30j': mouvements_30j,
#         'mouvement_labels': mouvement_labels,
#         'entrees_data': entrees_data,
#         'sorties_data': sorties_data,
#         'category_labels': category_labels,
#         'category_values': category_values,
#     }
    
#     return render(request, 'gestion_stock/reporting/dashboard.html', context)
@login_required
def reporting(request):
    # Statistiques globales
    total_articles = Article.objects.filter(actif=True).count()
    
    # Calculer la valeur totale du stock
    total_valeur = 0
    stocks = Stock.objects.select_related('article').all()
    for stock in stocks:
        total_valeur += stock.quantite * stock.article.prix_achat
    
    # Mouvements des 30 derniers jours
    date_30j = timezone.now() - timedelta(days=30)
    mouvements_30j = MouvementStock.objects.filter(
        date_mouvement__gte=date_30j
    ).count()
    
    # Articles les plus vendus (30 derniers jours)
    articles_vendus = MouvementStock.objects.filter(
        type_mouvement='sortie',
        date_mouvement__gte=date_30j
    ).values(
        'article__designation', 
        'article__code_article',
        'article__categorie__nom',
        'article__prix_vente'
    ).annotate(
        total_vendu=Sum('quantite')
    ).order_by('-total_vendu')[:10]
    
    # Valeur par catégorie
    valeur_par_categorie = []
    categories = Categorie.objects.all()
    for categorie in categories:
        valeur = 0
        stocks_cat = Stock.objects.filter(article__categorie=categorie)
        for stock in stocks_cat:
            valeur += stock.quantite * stock.article.prix_achat
        if valeur > 0:
            valeur_par_categorie.append({
                'nom': categorie.nom,
                'valeur': valeur
            })
    
    # Alertes
    alertes_total = Article.objects.filter(
        stock__quantite__lte=F('seuil_alerte'),
        actif=True
    ).count()
    
    # Articles avec stock nul
    articles_stock_nul = Article.objects.filter(
        stock__quantite=0,
        actif=True
    ).count()
    
    # Données pour les graphiques (7 derniers jours)
    mouvement_labels = []
    entrees_data = []
    sorties_data = []
    
    for i in range(7):
        date = timezone.now().date() - timedelta(days=6-i)
        mouvement_labels.append(date.strftime('%d/%m'))
        
        # Entrées du jour
        entrees = MouvementStock.objects.filter(
            type_mouvement='entree',
            date_mouvement__date=date
        ).aggregate(total=Sum('quantite'))['total'] or 0
        entrees_data.append(entrees)
        
        # Sorties du jour
        sorties = MouvementStock.objects.filter(
            type_mouvement='sortie',
            date_mouvement__date=date
        ).aggregate(total=Sum('quantite'))['total'] or 0
        sorties_data.append(sorties)
    
    # Données pour le graphique des catégories
    category_labels = [cat['nom'] for cat in valeur_par_categorie[:5]]
    category_values = [float(cat['valeur']) for cat in valeur_par_categorie[:5]]
    
    # Alertes par priorité (simplifié)
    alertes_haute = Article.objects.filter(
        stock__quantite=0,
        actif=True
    ).count()
    
    alertes_moyenne = Article.objects.filter(
        stock__quantite__lte=F('seuil_alerte'),
        stock__quantite__gt=0,
        actif=True
    ).count()
    
    context = {
        'total_articles': total_articles,
        'total_valeur': total_valeur,
        'mouvements_30j': mouvements_30j,
        'articles_vendus': articles_vendus,
        'valeur_par_categorie': valeur_par_categorie,
        'alertes_total': alertes_total,
        'articles_stock_nul': articles_stock_nul,
        'alertes_haute': alertes_haute,
        'alertes_moyenne': alertes_moyenne,
        'alertes_basse': 0,  # À implémenter si besoin
        'mouvement_labels': mouvement_labels,
        'entrees_data': entrees_data,
        'sorties_data': sorties_data,
        'category_labels': category_labels,
        'category_values': category_values,
    }
    
    return render(request, 'gestion_stock/reporting/dashboard.html', context)

@login_required
def generer_etat_stock_pdf(request):
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    
    # Titre
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, "État des Stocks")
    p.drawString(100, 780, f"Date : {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    
    # En-tête du tableau
    p.setFont("Helvetica-Bold", 10)
    y = 750
    p.drawString(50, y, "Code")
    p.drawString(100, y, "Article")
    p.drawString(300, y, "Catégorie")
    p.drawString(400, y, "Stock")
    p.drawString(450, y, "Prix Achat")
    p.drawString(530, y, "Valeur")
    
    # Données
    p.setFont("Helvetica", 9)
    y = 730
    stocks = Stock.objects.select_related('article__categorie').all()
    
    for stock in stocks:
        if y < 50:  # Nouvelle page
            p.showPage()
            p.setFont("Helvetica", 9)
            y = 750
        
        valeur = stock.quantite * stock.article.prix_achat
        p.drawString(50, y, stock.article.code_article)
        p.drawString(100, y, stock.article.designation[:30])
        p.drawString(300, y, stock.article.categorie.nom if stock.article.categorie else "")
        p.drawString(400, y, str(stock.quantite))
        p.drawString(450, y, f"{stock.article.prix_achat:.2f}")
        p.drawString(530, y, f"{valeur:.2f}")
        y -= 20
    
    # Total
    p.setFont("Helvetica-Bold", 10)
    p.drawString(450, y-20, "TOTAL:")
    total_valeur = sum(stock.quantite * stock.article.prix_achat for stock in stocks)
    p.drawString(530, y-20, f"{total_valeur:.2f}")
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="etat_stock.pdf"'
    return response

@login_required
@gestionnaire_required
def generer_bon_commande_pdf(request, pk):
    commande = get_object_or_404(CommandeFournisseur, pk=pk)
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    # En-tête Entreprise
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, "STOCKMASTER PRO")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 65, "Système de Gestion de Stock")
    
    # Titre du document
    p.setFont("Helvetica-Bold", 14)
    p.drawString(200, height - 100, f"BON DE COMMANDE N° {commande.numero}")
    
    # Informations Fournisseur
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, height - 140, "FOURNISSEUR :")
    p.setFont("Helvetica", 10)
    p.drawString(50, height - 155, f"Nom : {commande.fournisseur.nom}")
    p.drawString(50, height - 170, f"Contact : {commande.fournisseur.contact}")
    p.drawString(50, height - 185, f"Téléphone : {commande.fournisseur.telephone}")
    if commande.fournisseur.email:
        p.drawString(50, height - 200, f"Email : {commande.fournisseur.email}")
    
    # Informations Commande
    p.setFont("Helvetica-Bold", 10)
    p.drawString(350, height - 140, "DÉTAILS COMMANDE :")
    p.setFont("Helvetica", 10)
    p.drawString(350, height - 155, f"Date : {commande.date_commande.strftime('%d/%m/%Y')}")
    p.drawString(350, height - 170, f"Statut : {commande.get_statut_display()}")
    
    # Tableau Lignes de Commande
    y = height - 240
    p.setFont("Helvetica-Bold", 10)
    p.drawString(50, y, "Article")
    p.drawString(300, y, "Quantité")
    p.drawString(380, y, "Prix Unitaire")
    p.drawString(480, y, "Total")
    
    p.line(50, y - 5, 550, y - 5)
    
    y -= 20
    p.setFont("Helvetica", 10)
    lignes = commande.lignes.all()
    for ligne in lignes:
        if y < 100:  # Nouvelle page si besoin
            p.showPage()
            p.setFont("Helvetica", 10)
            y = height - 50
        
        p.drawString(50, y, ligne.article.designation[:40])
        p.drawString(300, y, str(ligne.quantite))
        p.drawString(380, y, f"{ligne.prix_unitaire:.2f}")
        p.drawString(480, y, f"{ligne.total:.2f}")
        y -= 20
        
    p.line(50, y, 550, y)
    
    # Montant Total
    y -= 20
    p.setFont("Helvetica-Bold", 12)
    p.drawString(350, y, "TOTAL COMMANDE :")
    p.drawString(480, y, f"{commande.montant_total:.2f} GNF")
    
    p.save()
    buffer.seek(0)
    
    response = HttpResponse(buffer, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="bon_commande_{commande.numero}.pdf"'
    return response

# API pour le scan de code-barres
@login_required
def api_recherche_article(request, code_barre):
    try:
        article = Article.objects.get(code_barre=code_barre)
        stock = Stock.objects.get(article=article)
        
        data = {
            'code_article': article.code_article,
            'designation': article.designation,
            'prix_achat': str(article.prix_achat),
            'prix_vente': str(article.prix_vente),
            'stock': stock.quantite,
            'seuil_alerte': article.seuil_alerte,
            'alerte': stock.quantite <= article.seuil_alerte,
        }
        return JsonResponse(data)
    except Article.DoesNotExist:
        return JsonResponse({'error': 'Article non trouvé'}, status=404)

@login_required
def api_stock_actuel(request):
    article_id = request.GET.get('article')
    try:
        article = Article.objects.get(id=article_id)
        stock = Stock.objects.get(article=article)
        
        data = {
            'quantite': stock.quantite,
            'prix_achat': str(article.prix_achat),
            'prix_vente': str(article.prix_vente),
            'seuil_alerte': article.seuil_alerte,
        }
        return JsonResponse(data)
    except (Article.DoesNotExist, Stock.DoesNotExist):
        return JsonResponse({'error': 'Article ou stock non trouvé'}, status=404)

# Import d'articles depuis CSV
@login_required
@admin_required
def import_articles(request):
    if request.method == 'POST':
        form = ImportArticlesForm(request.POST, request.FILES)
        if form.is_valid():
            fichier = request.FILES['fichier']
            
            if fichier.name.endswith('.csv'):
                # Traitement CSV
                decoded_file = fichier.read().decode('utf-8').splitlines()
                reader = csv.DictReader(decoded_file)
                
                articles_importes = 0
                for row in reader:
                    try:
                        # Chercher ou créer la catégorie
                        categorie, _ = Categorie.objects.get_or_create(
                            nom=row.get('categorie', 'Divers'),
                            defaults={'description': row.get('categorie', 'Divers')}
                        )
                        
                        # Créer l'article
                        article, created = Article.objects.get_or_create(
                            code_article=row['code_article'],
                            defaults={
                                'designation': row['designation'],
                                'categorie': categorie,
                                'prix_achat': row.get('prix_achat', 0),
                                'prix_vente': row.get('prix_vente', 0),
                                'seuil_alerte': row.get('seuil_alerte', 10),
                            }
                        )
                        
                        if created:
                            # Créer le stock initial
                            Stock.objects.create(
                                article=article,
                                quantite=row.get('quantite_initial', 0),
                                emplacement=row.get('emplacement', 'Défaut')
                            )
                            articles_importes += 1
                    except Exception as e:
                        messages.warning(request, f"Erreur avec l'article {row.get('code_article', 'N/A')}: {str(e)}")
                
                messages.success(request, f"{articles_importes} articles importés avec succès!")
                return redirect('liste_articles')
    
    else:
        form = ImportArticlesForm()
    
    return render(request, 'gestion_stock/articles/import.html', {'form': form})

@login_required
@gestionnaire_required
def export_articles(request):
    # Créer une réponse HTTP avec le type CSV
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="articles_export.csv"'
    
    writer = csv.writer(response)
    # En-tête
    writer.writerow(['code_article', 'designation', 'categorie', 'prix_achat', 'prix_vente', 'seuil_alerte', 'stock_actuel'])
    
    # Données
    articles = Article.objects.select_related('categorie', 'stock').all()
    for article in articles:
        writer.writerow([
            article.code_article,
            article.designation,
            article.categorie.nom if article.categorie else '',
            str(article.prix_achat),
            str(article.prix_vente),
            str(article.seuil_alerte),
            str(article.quantite_stock),
        ])
    
    return response

@login_required
@admin_required
def liste_utilisateurs(request):
    utilisateurs = User.objects.select_related('profilutilisateur').all()
    return render(request, 'gestion_stock/utilisateurs/liste.html', {'utilisateurs': utilisateurs})

@login_required
@admin_required
def ajouter_utilisateur(request):
    if request.method == 'POST':
        form = InscriptionForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Utilisateur créé avec succès!')
            return redirect('liste_utilisateurs')
    else:
        form = InscriptionForm()
    
    return render(request, 'gestion_stock/utilisateurs/ajouter.html', {'form': form})

@login_required
@admin_required
def modifier_utilisateur(request, pk):
    utilisateur = get_object_or_404(User, pk=pk)
    profil = utilisateur.profilutilisateur
    
    if request.method == 'POST':
        form = ModifierUtilisateurForm(request.POST, instance=utilisateur)
        if form.is_valid():
            user = form.save(commit=False)
            user.save()
            
            # Mettre à jour le profil
            profil.role = form.cleaned_data['role']
            profil.nom_complet = form.cleaned_data['nom_complet']
            profil.save()
            
            messages.success(request, 'Utilisateur modifié avec succès!')
            return redirect('liste_utilisateurs')
    else:
        form = ModifierUtilisateurForm(instance=utilisateur, initial={
            'role': profil.role,
            'nom_complet': profil.nom_complet,
        })
    
    return render(request, 'gestion_stock/utilisateurs/modifier.html', {'form': form, 'utilisateur': utilisateur})

@login_required
def profil(request):
    return render(request, 'gestion_stock/profil/detail.html')

@login_required
def modifier_profil(request):
    if request.method == 'POST':
        form = ModifierProfilForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profil modifié avec succès!')
            return redirect('profil')
    else:
        form = ModifierProfilForm(instance=request.user)
    
    return render(request, 'gestion_stock/profil/modifier.html', {'form': form})

@login_required
# def generer_qrcode(request, pk):
#     article = get_object_or_404(Article, pk=pk)
    
#     # Générer le QR code avec les informations de l'article
#     import qrcode
#     from io import BytesIO
#     import base64
    
#     # Données à encoder dans le QR code
#     data = f"""
#     Article: {article.designation}
#     Code: {article.code_article}
#     Prix: {article.prix_vente}€
#     Stock: {article.quantite_stock}
#     """
    
#     # Générer le QR code
#     qr = qrcode.QRCode(
#         version=1,
#         error_correction=qrcode.constants.ERROR_CORRECT_L,
#         box_size=10,
#         border=4,
#     )
#     qr.add_data(data)
#     qr.make(fit=True)
    
#     img = qr.make_image(fill_color="black", back_color="white")
    
#     # Sauvegarder l'image dans un buffer
#     buffer = BytesIO()
#     img.save(buffer, format="PNG")
#     buffer.seek(0)
    
#     # Encoder en base64 pour l'affichage dans le template
#     image_base64 = base64.b64encode(buffer.getvalue()).decode()
    
#     context = {
#         'article': article,
#         'qr_code': image_base64,
#     }
    
#     return render(request, 'gestion_stock/articles/qrcode.html', context)

# Vues pour les états de reporting spécifiques
@login_required
@gestionnaire_required
def etat_stock(request):
    articles = Article.objects.select_related('categorie', 'stock').filter(actif=True)
    return render(request, 'gestion_stock/reporting/etat_stock.html', {'articles': articles})

@login_required
@gestionnaire_required
def valeur_stock(request):
    # Calculer la valeur par catégorie
    valeur_par_categorie = Stock.objects.values('article__categorie__nom').annotate(
        valeur=Sum(F('quantite') * F('article__prix_achat'))
    ).order_by('-valeur')
    
    # Valeur totale
    valeur_totale = Stock.objects.annotate(
        valeur=ExpressionWrapper(F('quantite') * F('article__prix_achat'), output_field=DecimalField(max_digits=12, decimal_places=2))
    ).aggregate(total=Sum('valeur'))['total'] or 0
    
    context = {
        'valeur_par_categorie': valeur_par_categorie,
        'valeur_totale': valeur_totale,
    }
    
    return render(request, 'gestion_stock/reporting/valeur_stock.html', context)

@login_required
@gestionnaire_required
def mouvements_periodes(request):
    # Récupérer la période depuis les paramètres GET
    periode = request.GET.get('periode', '7j')
    
    if periode == '30j':
        date_debut = timezone.now() - timedelta(days=30)
    elif periode == '90j':
        date_debut = timezone.now() - timedelta(days=90)
    else:  # 7j par défaut
        date_debut = timezone.now() - timedelta(days=7)
    
    mouvements = MouvementStock.objects.filter(
        date_mouvement__gte=date_debut
    ).select_related('article', 'utilisateur').order_by('-date_mouvement')
    
    # Statistiques
    total_entrees = mouvements.filter(type_mouvement='entree').aggregate(total=Sum('quantite'))['total'] or 0
    total_sorties = mouvements.filter(type_mouvement='sortie').aggregate(total=Sum('quantite'))['total'] or 0
    
    context = {
        'mouvements': mouvements,
        'periode': periode,
        'total_entrees': total_entrees,
        'total_sorties': total_sorties,
        'date_debut': date_debut,
        'date_fin': timezone.now(),
    }
    
    return render(request, 'gestion_stock/reporting/mouvements_periodes.html', context)

@login_required
@gestionnaire_required
def articles_vendus(request):
    # Récupérer la période depuis les paramètres GET
    periode = request.GET.get('periode', '30j')
    
    if periode == '7j':
        date_debut = timezone.now() - timedelta(days=7)
    elif periode == '90j':
        date_debut = timezone.now() - timedelta(days=90)
    else:  # 30j par défaut
        date_debut = timezone.now() - timedelta(days=30)
    
    articles_vendus = MouvementStock.objects.filter(
        type_mouvement='sortie',
        date_mouvement__gte=date_debut
    ).values('article__designation', 'article__code_article', 'article__categorie__nom').annotate(
        quantite_vendue=Sum('quantite'),
        chiffre_affaires=Sum(F('quantite') * F('article__prix_vente'))
    ).order_by('-quantite_vendue')[:20]
    
    # Chiffre d'affaires total
    ca_total = sum(article['chiffre_affaires'] or 0 for article in articles_vendus)
    
    context = {
        'articles_vendus': articles_vendus,
        'periode': periode,
        'ca_total': ca_total,
        'date_debut': date_debut,
        'date_fin': timezone.now(),
    }
    
    return render(request, 'gestion_stock/reporting/articles_vendus.html', context)