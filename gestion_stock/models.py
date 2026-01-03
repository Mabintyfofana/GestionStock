from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
from datetime import datetime, timedelta

class ProfilUtilisateur(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Administrateur'),
        ('gestionnaire', 'Gestionnaire'),
        ('vendeur', 'Vendeur'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='vendeur')
    nom_complet = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20, blank=True)
    date_embauche = models.DateField(auto_now_add=True)
    actif = models.BooleanField(default=True)
    
    def __str__(self):
        return f"{self.nom_complet} ({self.get_role_display()})"

class Categorie(models.Model):
    nom = models.CharField(max_length=50, unique=True)
    description = models.TextField(blank=True)
    
    def __str__(self):
        return self.nom
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"

class Fournisseur(models.Model):
    code = models.CharField(max_length=20, unique=True)
    nom = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    telephone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    adresse = models.TextField(blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.nom} ({self.code})"

class Article(models.Model):
    UNITE_CHOICES = [
        ('unite', 'Unité'),
        ('kg', 'Kilogramme'),
        ('litre', 'Litre'),
        ('paquet', 'Paquet'),
        ('carton', 'Carton'),
    ]
    
    code_article = models.CharField(max_length=50, unique=True, verbose_name="Code article")
    code_barre = models.CharField(max_length=100, blank=True, unique=True, verbose_name="Code-barres")
    designation = models.CharField(max_length=200)
    categorie = models.ForeignKey(Categorie, on_delete=models.SET_NULL, null=True)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.SET_NULL, null=True, blank=True)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2)
    seuil_alerte = models.IntegerField(default=10)
    unite = models.CharField(max_length=20, choices=UNITE_CHOICES, default='unite')
    emplacement = models.CharField(max_length=50, blank=True, help_text="Rayon/Étagère")
    date_peremption = models.DateField(null=True, blank=True, verbose_name="Date de péremption")
    actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.designation} ({self.code_article})"
    
    @property
    def quantite_stock(self):
        stock = self.stock_set.first()
        return stock.quantite if stock else 0
    
    @property
    def valeur_stock(self):
        return self.quantite_stock * self.prix_achat
    
    @property
    def alerte_stock_faible(self):
        return self.quantite_stock <= self.seuil_alerte
    
    @property
    def alerte_peremption(self):
        if self.date_peremption:
            jours_restants = (self.date_peremption - timezone.now().date()).days
            return jours_restants <= 30  # Alerte si moins de 30 jours
        return False
    
    class Meta:
        verbose_name = "Article"
        verbose_name_plural = "Articles"

class Stock(models.Model):
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    quantite = models.IntegerField(default=0)
    quantite_min = models.IntegerField(default=0)
    quantite_max = models.IntegerField(default=1000)
    emplacement = models.CharField(max_length=100)
    date_derniere_entree = models.DateTimeField(null=True, blank=True)
    date_derniere_sortie = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.article.designation} - {self.quantite} en stock"
    
    class Meta:
        verbose_name = "Stock"
        verbose_name_plural = "Stocks"

class MouvementStock(models.Model):
    TYPE_CHOICES = [
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
        ('inventaire', 'Inventaire'),
        ('ajustement', 'Ajustement'),
        ('retour', 'Retour'),
    ]
    
    type_mouvement = models.CharField(max_length=20, choices=TYPE_CHOICES)
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    quantite = models.IntegerField()
    quantite_avant = models.IntegerField()
    quantite_apres = models.IntegerField()
    motif = models.TextField(blank=True)
    reference = models.CharField(max_length=100, blank=True)  # Facture, BL, etc.
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_mouvement = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.type_mouvement} - {self.article.designation} - {self.quantite}"
    
    def save(self, *args, **kwargs):
        # Mettre à jour le stock de l'article
        stock, created = Stock.objects.get_or_create(article=self.article)
        
        if self.type_mouvement == 'entree':
            stock.quantite += self.quantite
            stock.date_derniere_entree = timezone.now()
        elif self.type_mouvement in ['sortie', 'retour']:
            stock.quantite -= self.quantite
            stock.date_derniere_sortie = timezone.now()
        elif self.type_mouvement == 'ajustement':
            stock.quantite = self.quantite_apres
        
        stock.save()
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Mouvement de stock"
        verbose_name_plural = "Mouvements de stock"

class AjustementStock(models.Model):
    RAISON_CHOICES = [
        ('inventaire', 'Inventaire'),
        ('casse', 'Casse'),
        ('vol', 'Vol'),
        ('erreur', 'Erreur de saisie'),
        ('autre', 'Autre'),
    ]
    
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    quantite_reelle = models.IntegerField()
    quantite_systeme = models.IntegerField()
    difference = models.IntegerField()
    raison = models.CharField(max_length=20, choices=RAISON_CHOICES)
    description = models.TextField(blank=True)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    date_ajustement = models.DateTimeField(auto_now_add=True)
    
    def save(self, *args, **kwargs):
        self.difference = self.quantite_reelle - self.quantite_systeme
        super().save(*args, **kwargs)
        
        # Créer un mouvement d'ajustement
        MouvementStock.objects.create(
            type_mouvement='ajustement',
            article=self.article,
            quantite=self.difference,
            quantite_avant=self.quantite_systeme,
            quantite_apres=self.quantite_reelle,
            motif=f"{self.get_raison_display()}: {self.description}",
            utilisateur=self.utilisateur
        )
    
    def __str__(self):
        return f"Ajustement {self.article} - Différence: {self.difference}"
    
    class Meta:
        verbose_name = "Ajustement de stock"
        verbose_name_plural = "Ajustements de stock"

class Alerte(models.Model):
    TYPE_ALERTE_CHOICES = [
        ('stock_faible', 'Stock faible'),
        ('peremption', 'Péremption proche'),
        ('rupture', 'Rupture de stock'),
        ('autre', 'Autre'),
    ]
    
    type_alerte = models.CharField(max_length=20, choices=TYPE_ALERTE_CHOICES)
    article = models.ForeignKey(Article, on_delete=models.CASCADE, null=True, blank=True)
    message = models.TextField()
    priorite = models.IntegerField(default=1, choices=[(1, 'Basse'), (2, 'Moyenne'), (3, 'Haute')])
    lu = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_lu = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"Alerte {self.get_type_alerte_display()} - {self.article if self.article else 'Système'}"
    
    class Meta:
        ordering = ['-date_creation']

class CommandeFournisseur(models.Model):
    STATUT_CHOICES = [
        ('brouillon', 'Brouillon'),
        ('envoyee', 'Envoyée'),
        ('recue', 'Reçue'),
        ('annulee', 'Annulée'),
    ]
    
    numero = models.CharField(max_length=50, unique=True)
    fournisseur = models.ForeignKey(Fournisseur, on_delete=models.CASCADE)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    date_commande = models.DateField(auto_now_add=True)
    date_reception = models.DateField(null=True, blank=True)
    montant_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    notes = models.TextField(blank=True)
    utilisateur = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    
    def __str__(self):
        return f"Commande {self.numero} - {self.fournisseur.nom}"
    
    def calculer_total(self):
        total = sum(ligne.total for ligne in self.lignes.all())
        self.montant_total = total
        self.save()
    
    class Meta:
        verbose_name = "Commande fournisseur"
        verbose_name_plural = "Commandes fournisseur"

class LigneCommande(models.Model):
    commande = models.ForeignKey(CommandeFournisseur, on_delete=models.CASCADE, related_name='lignes')
    article = models.ForeignKey(Article, on_delete=models.CASCADE)
    quantite = models.IntegerField()
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    
    def save(self, *args, **kwargs):
        self.total = self.quantite * self.prix_unitaire
        super().save(*args, **kwargs)
        self.commande.calculer_total()
    
    def __str__(self):
        return f"{self.article.designation} - {self.quantite} x {self.prix_unitaire}"
    
    class Meta:
        verbose_name = "Ligne de commande"
        verbose_name_plural = "Lignes de commande"