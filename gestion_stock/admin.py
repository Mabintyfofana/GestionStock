from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import *
from import_export.admin import ImportExportModelAdmin
from import_export import resources

class ProfilUtilisateurInline(admin.StackedInline):
    model = ProfilUtilisateur
    can_delete = False

class CustomUserAdmin(UserAdmin):
    inlines = [ProfilUtilisateurInline]
    list_display = ['username', 'email', 'nom_complet', 'role', 'is_staff']
    
    def nom_complet(self, obj):
        return obj.profilutilisateur.nom_complet if hasattr(obj, 'profilutilisateur') else ''
    
    def role(self, obj):
        return obj.profilutilisateur.get_role_display() if hasattr(obj, 'profilutilisateur') else ''

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)

class ArticleResource(resources.ModelResource):
    class Meta:
        model = Article
        import_id_fields = ['code_article']
        fields = ('code_article', 'designation', 'categorie', 'prix_achat', 'prix_vente', 'seuil_alerte')

@admin.register(Article)
class ArticleAdmin(ImportExportModelAdmin):
    resource_class = ArticleResource
    list_display = ['code_article', 'designation', 'categorie', 'prix_achat', 'prix_vente', 'quantite_stock', 'alerte_stock']
    list_filter = ['categorie', 'actif']
    search_fields = ['code_article', 'designation', 'code_barre']
    readonly_fields = ['date_creation', 'date_modification']
    fieldsets = (
        ('Information Générale', {
            'fields': ('code_article', 'code_barre', 'designation', 'categorie', 'unite')
        }),
        ('Prix et Stock', {
            'fields': ('prix_achat', 'prix_vente', 'seuil_alerte', 'emplacement')
        }),
        ('Péremption', {
            'fields': ('date_peremption',)
        }),
        ('Fournisseur', {
            'fields': ('fournisseur',)
        }),
        ('Statut', {
            'fields': ('actif', 'date_creation', 'date_modification')
        }),
    )
    
    def alerte_stock(self, obj):
        if obj.alerte_stock_faible:
            return '<span style="color:red;">⚠ Stock faible</span>'
        return 'OK'
    alerte_stock.allow_tags = True
    alerte_stock.short_description = 'Alerte'

@admin.register(Stock)
class StockAdmin(admin.ModelAdmin):
    list_display = ['article', 'quantite', 'emplacement', 'date_derniere_entree', 'date_derniere_sortie']
    list_filter = ['emplacement']
    search_fields = ['article__designation', 'article__code_article']
    readonly_fields = ['date_derniere_entree', 'date_derniere_sortie']

@admin.register(MouvementStock)
class MouvementStockAdmin(admin.ModelAdmin):
    list_display = ['date_mouvement', 'type_mouvement', 'article', 'quantite', 'utilisateur']
    list_filter = ['type_mouvement', 'date_mouvement']
    search_fields = ['article__designation', 'reference']
    readonly_fields = ['quantite_avant', 'quantite_apres', 'date_mouvement']
    date_hierarchy = 'date_mouvement'

@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'contact', 'telephone', 'email']
    search_fields = ['nom', 'contact']

@admin.register(CommandeFournisseur)
class CommandeFournisseurAdmin(admin.ModelAdmin):
    list_display = ['numero', 'fournisseur', 'statut', 'date_commande', 'montant_total']
    list_filter = ['statut', 'date_commande']
    search_fields = ['numero', 'fournisseur__nom']
    readonly_fields = ['montant_total']
    
class LigneCommandeInline(admin.TabularInline):
    model = LigneCommande
    extra = 1

@admin.register(Alerte)
class AlerteAdmin(admin.ModelAdmin):
    list_display = ['type_alerte', 'article', 'message', 'priorite', 'lu', 'date_creation']
    list_filter = ['type_alerte', 'priorite', 'lu']
    search_fields = ['article__designation', 'message']
    actions = ['marquer_comme_lu']
    
    def marquer_comme_lu(self, request, queryset):
        updated = queryset.update(lu=True, date_lu=timezone.now())
        self.message_user(request, f'{updated} alertes marquées comme lues.')
    marquer_comme_lu.short_description = "Marquer les alertes sélectionnées comme lues"

@admin.register(Categorie)
class CategorieAdmin(admin.ModelAdmin):
    list_display = ['nom', 'description']
    search_fields = ['nom']