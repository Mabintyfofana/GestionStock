from django.urls import path
from django.contrib.auth.decorators import login_required
from . import views
from .decorators import *

urlpatterns = [
    # Authentification
    path('', views.redirection_par_role, name='redirection_par_role'),
    path('register/', views.register, name='register'),
    
    # Dashboard (différent selon rôle)
    path('dashboard/', login_required(vendeur_required(views.dashboard)), name='dashboard'),
    path('dashboard-admin/', login_required(admin_required(views.dashboard_admin)), name='dashboard_admin'),
    path('dashboard-gestionnaire/', login_required(gestionnaire_required(views.dashboard_gestionnaire)), name='dashboard_gestionnaire'),
    
    # Articles
    path('articles/', login_required(vendeur_required(views.liste_articles)), name='liste_articles'),
    path('articles/ajouter/', login_required(gestionnaire_required(views.ajouter_article)), name='ajouter_article'),
    path('articles/modifier/<int:pk>/', login_required(gestionnaire_required(views.modifier_article)), name='modifier_article'),
    path('articles/supprimer/<int:pk>/', login_required(admin_required(views.supprimer_article)), name='supprimer_article'),
    path('articles/detail/<int:pk>/', login_required(vendeur_required(views.detail_article)), name='detail_article'),
    path('articles/import/', login_required(admin_required(views.import_articles)), name='import_articles'),
    path('articles/export/', login_required(gestionnaire_required(views.export_articles)), name='export_articles'),
    
    # Stock
    path('stock/mouvement/', login_required(gestionnaire_required(views.mouvement_stock)), name='mouvement_stock'),
    path('stock/ajuster/', login_required(gestionnaire_required(views.ajuster_stock)), name='ajuster_stock'),
    path('stock/inventaire/', login_required(gestionnaire_required(views.inventaire_stock)), name='inventaire_stock'),
    
    # Mouvements
    path('mouvements/', login_required(gestionnaire_required(views.historique_mouvements)), name='historique_mouvements'),
    path('mouvements/<int:pk>/', login_required(gestionnaire_required(views.detail_mouvement)), name='detail_mouvement'),
    
    # Fournisseurs
    path('fournisseurs/', login_required(gestionnaire_required(views.liste_fournisseurs)), name='liste_fournisseurs'),
    path('fournisseurs/ajouter/', login_required(gestionnaire_required(views.ajouter_fournisseur)), name='ajouter_fournisseur'),
    path('fournisseurs/modifier/<int:pk>/', login_required(gestionnaire_required(views.modifier_fournisseur)), name='modifier_fournisseur'),
    
    # Commandes
    path('commandes/', login_required(gestionnaire_required(views.liste_commandes)), name='liste_commandes'),
    path('commandes/ajouter/', login_required(gestionnaire_required(views.ajouter_commande)), name='ajouter_commande'),
    path('commandes/detail/<int:pk>/', login_required(gestionnaire_required(views.detail_commande)), name='detail_commande'),
    path('commandes/pdf/<int:pk>/', login_required(gestionnaire_required(views.generer_bon_commande_pdf)), name='generer_bon_commande_pdf'),
    
    # Alertes
    path('alertes/', login_required(vendeur_required(views.alertes)), name='alertes'),
    path('alertes/marquer-lu/<str:pk>/', login_required(vendeur_required(views.marquer_alerte_lue)), name='marquer_alerte_lue'),
    
    # Reporting
    path('reporting/', login_required(vendeur_required(views.reporting)), name='reporting'),
    path('reporting/etat-stock/', login_required(gestionnaire_required(views.etat_stock)), name='etat_stock'),
    path('reporting/valeur-stock/', login_required(gestionnaire_required(views.valeur_stock)), name='valeur_stock'),
    path('reporting/mouvements-periodes/', login_required(gestionnaire_required(views.mouvements_periodes)), name='mouvements_periodes'),
    path('reporting/articles-vendus/', login_required(gestionnaire_required(views.articles_vendus)), name='articles_vendus'),
    path('reporting/generer-pdf/', login_required(gestionnaire_required(views.generer_etat_stock_pdf)), name='generer_etat_stock_pdf'),
    
    # Audit
    path('audit/', login_required(gestionnaire_required(views.journal_audit)), name='journal_audit'),
    
    # API
    path('api/recherche-globale/', login_required(views.api_recherche_globale), name='api_recherche_globale'),
    path('api/article/<str:code_barre>/', login_required(views.api_recherche_article), name='api_recherche_article'),
    path('api/stock-actuel/', login_required(views.api_stock_actuel), name='api_stock_actuel'),
    
    # Utilisateurs (Admin seulement)
    path('utilisateurs/', login_required(admin_required(views.liste_utilisateurs)), name='liste_utilisateurs'),
    path('utilisateurs/ajouter/', login_required(admin_required(views.ajouter_utilisateur)), name='ajouter_utilisateur'),
    path('utilisateurs/modifier/<int:pk>/', login_required(admin_required(views.modifier_utilisateur)), name='modifier_utilisateur'),
    
    # Profil
    path('profil/', login_required(views.profil), name='profil'),
    path('profil/modifier/', login_required(views.modifier_profil), name='modifier_profil'),
    
    # QR Code
   # path('article/<int:pk>/qrcode/', login_required(views.generer_qrcode), name='generer_qrcode'),
]