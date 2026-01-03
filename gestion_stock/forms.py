from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm
from django.contrib.auth.models import User
from .models import *

class CustomAuthenticationForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom d\'utilisateur'})
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Mot de passe'})
    )

class InscriptionForm(UserCreationForm):
    email = forms.EmailField(required=True)
    nom_complet = forms.CharField(max_length=100)
    role = forms.ChoiceField(choices=ProfilUtilisateur.ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'nom_complet', 'role', 'password1', 'password2']
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            profil = ProfilUtilisateur.objects.create(
                user=user,
                nom_complet=self.cleaned_data['nom_complet'],
                role=self.cleaned_data['role']
            )
        return user

class ModifierUtilisateurForm(UserChangeForm):
    email = forms.EmailField(required=True)
    nom_complet = forms.CharField(max_length=100)
    role = forms.ChoiceField(choices=ProfilUtilisateur.ROLE_CHOICES)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'nom_complet', 'role', 'is_active']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Supprimer le champ de mot de passe
        self.fields.pop('password', None)
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Mettre à jour le profil
            profil, created = ProfilUtilisateur.objects.get_or_create(
                user=user,
                defaults={
                    'nom_complet': self.cleaned_data['nom_complet'],
                    'role': self.cleaned_data['role']
                }
            )
            if not created:
                profil.nom_complet = self.cleaned_data['nom_complet']
                profil.role = self.cleaned_data['role']
                profil.save()
        return user

class ModifierProfilForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, label='Prénom')
    last_name = forms.CharField(max_length=30, required=True, label='Nom')
    
    class Meta:
        model = User
        fields = ['email', 'first_name', 'last_name']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance:
            try:
                profil = self.instance.profilutilisateur
                # On pourrait ajouter des champs du profil ici si nécessaire
            except ProfilUtilisateur.DoesNotExist:
                pass
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            # Mettre à jour le nom complet dans le profil
            try:
                profil = user.profilutilisateur
                profil.nom_complet = f"{self.cleaned_data['first_name']} {self.cleaned_data['last_name']}"
                profil.save()
            except ProfilUtilisateur.DoesNotExist:
                pass
        
        return user

class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = '__all__'
        widgets = {
            'code_article': forms.TextInput(attrs={'class': 'form-control'}),
            'code_barre': forms.TextInput(attrs={'class': 'form-control'}),
            'designation': forms.TextInput(attrs={'class': 'form-control'}),
            'categorie': forms.Select(attrs={'class': 'form-control'}),
            'fournisseur': forms.Select(attrs={'class': 'form-control'}),
            'prix_achat': forms.NumberInput(attrs={'class': 'form-control'}),
            'prix_vente': forms.NumberInput(attrs={'class': 'form-control'}),
            'seuil_alerte': forms.NumberInput(attrs={'class': 'form-control'}),
            'unite': forms.Select(attrs={'class': 'form-control'}),
            'emplacement': forms.TextInput(attrs={'class': 'form-control'}),
            'date_peremption': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'actif': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Optionnel: personnaliser les queryset si nécessaire
        self.fields['categorie'].queryset = Categorie.objects.all().order_by('nom')
        self.fields['fournisseur'].queryset = Fournisseur.objects.all().order_by('nom')

class MouvementStockForm(forms.ModelForm):
    class Meta:
        model = MouvementStock
        fields = ['type_mouvement', 'article', 'quantite', 'motif', 'reference']
        widgets = {
            'type_mouvement': forms.Select(attrs={'class': 'form-control'}),
            'article': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'motif': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Motif du mouvement...'}),
            'reference': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'N° facture, bon de livraison, etc.'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les articles actifs seulement
        self.fields['article'].queryset = Article.objects.filter(actif=True).order_by('designation')
        
        # Ajouter des classes CSS spécifiques selon le type de mouvement
        if 'type_mouvement' in self.data:
            type_mvt = self.data.get('type_mouvement')
            if type_mvt == 'entree':
                self.fields['quantite'].widget.attrs['class'] += ' border-success'
            elif type_mvt == 'sortie':
                self.fields['quantite'].widget.attrs['class'] += ' border-warning'

class AjustementStockForm(forms.ModelForm):
    class Meta:
        model = AjustementStock
        fields = ['article', 'quantite_reelle', 'raison', 'description']
        widgets = {
            'article': forms.Select(attrs={'class': 'form-control'}),
            'quantite_reelle': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'raison': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description détaillée de l\'ajustement...'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtrer les articles actifs seulement
        self.fields['article'].queryset = Article.objects.filter(actif=True).order_by('designation')

class FournisseurForm(forms.ModelForm):
    class Meta:
        model = Fournisseur
        fields = ['code', 'nom', 'contact', 'telephone', 'email', 'adresse']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'FOUR-001'}),
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom du fournisseur'}),
            'contact': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Personne de contact'}),
            'telephone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+33 1 23 45 67 89'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'contact@fournisseur.com'}),
            'adresse': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Adresse complète'}),
        }
    
    def clean_code(self):
        code = self.cleaned_data['code']
        # Vérifier l'unicité du code (sauf pour l'instance en cours de modification)
        if self.instance and self.instance.pk:
            if Fournisseur.objects.filter(code=code).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('Ce code est déjà utilisé par un autre fournisseur.')
        else:
            if Fournisseur.objects.filter(code=code).exists():
                raise forms.ValidationError('Ce code est déjà utilisé.')
        return code

class CommandeFournisseurForm(forms.ModelForm):
    class Meta:
        model = CommandeFournisseur
        fields = ['fournisseur', 'notes']
        widgets = {
            'fournisseur': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class LigneCommandeForm(forms.ModelForm):
    class Meta:
        model = LigneCommande
        fields = ['article', 'quantite']
        widgets = {
            'article': forms.Select(attrs={'class': 'form-control'}),
            'quantite': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
        }

class CategorieForm(forms.ModelForm):
    class Meta:
        model = Categorie
        fields = ['nom', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nom de la catégorie'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Description de la catégorie...'}),
        }

class ImportArticlesForm(forms.Form):
    fichier = forms.FileField(
        label='Fichier CSV/Excel',
        help_text='Format: code_article,designation,categorie,prix_achat,prix_vente,seuil_alerte',
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )
    
    def clean_fichier(self):
        fichier = self.cleaned_data.get('fichier')
        if fichier:
            # Vérifier l'extension du fichier
            if not fichier.name.endswith('.csv'):
                raise forms.ValidationError('Seuls les fichiers CSV sont acceptés.')
            # Vérifier la taille du fichier (max 5MB)
            if fichier.size > 5 * 1024 * 1024:
                raise forms.ValidationError('Le fichier est trop volumineux (max 5MB).')
        return fichier

class RechercheArticleForm(forms.Form):
    recherche = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Rechercher un article...'
        })
    )
    categorie = forms.ModelChoiceField(
        queryset=Categorie.objects.all(),
        required=False,
        empty_label='Toutes les catégories',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    actif = forms.ChoiceField(
        required=False,
        choices=[('', 'Tous'), ('1', 'Actifs seulement'), ('0', 'Inactifs seulement')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class FiltreMouvementForm(forms.Form):
    TYPE_CHOICES = [('', 'Tous')] + list(MouvementStock.TYPE_CHOICES)
    
    type_mouvement = forms.ChoiceField(
        choices=TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    article = forms.ModelChoiceField(
        queryset=Article.objects.filter(actif=True),
        required=False,
        empty_label='Tous les articles',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    date_debut = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_fin = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    utilisateur = forms.ModelChoiceField(
        queryset=User.objects.filter(is_active=True),
        required=False,
        empty_label='Tous les utilisateurs',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class FiltreReportingForm(forms.Form):
    PERIODE_CHOICES = [
        ('7j', '7 derniers jours'),
        ('30j', '30 derniers jours'),
        ('90j', '90 derniers jours'),
        ('annee', 'Cette année'),
        ('personnalise', 'Période personnalisée'),
    ]
    
    periode = forms.ChoiceField(
        choices=PERIODE_CHOICES,
        initial='30j',
        widget=forms.Select(attrs={'class': 'form-control', 'onchange': 'toggleCustomDates()'})
    )
    date_debut_perso = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    date_fin_perso = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'form-control', 'type': 'date'})
    )
    categorie = forms.ModelChoiceField(
        queryset=Categorie.objects.all(),
        required=False,
        empty_label='Toutes les catégories',
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class ChangePasswordForm(forms.Form):
    ancien_mot_de_passe = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Ancien mot de passe'})
    )
    nouveau_mot_de_passe = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Nouveau mot de passe'})
    )
    confirmation_mot_de_passe = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirmer le nouveau mot de passe'})
    )
    
    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
    
    def clean_ancien_mot_de_passe(self):
        ancien = self.cleaned_data.get('ancien_mot_de_passe')
        if not self.user.check_password(ancien):
            raise forms.ValidationError('L\'ancien mot de passe est incorrect.')
        return ancien
    
    def clean(self):
        cleaned_data = super().clean()
        nouveau = cleaned_data.get('nouveau_mot_de_passe')
        confirmation = cleaned_data.get('confirmation_mot_de_passe')
        
        if nouveau and confirmation and nouveau != confirmation:
            raise forms.ValidationError('Les mots de passe ne correspondent pas.')
        
        return cleaned_data

class ScanCodeBarreForm(forms.Form):
    code_barre = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Scanner ou saisir le code-barres',
            'autofocus': 'autofocus'
        })
    )
    
    def clean_code_barre(self):
        code_barre = self.cleaned_data.get('code_barre')
        if code_barre:
            # Supprimer les espaces et caractères spéciaux
            code_barre = code_barre.strip()
            # Vérifier si l'article existe
            if not Article.objects.filter(code_barre=code_barre).exists():
                raise forms.ValidationError('Aucun article trouvé avec ce code-barres.')
        return code_barre

class QuickMouvementForm(forms.Form):
    TYPE_CHOICES = [
        ('entree', 'Entrée'),
        ('sortie', 'Sortie'),
    ]
    
    type_mouvement = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    article = forms.ModelChoiceField(
        queryset=Article.objects.filter(actif=True),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    quantite = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

class NotificationSettingsForm(forms.Form):
    NOTIFICATION_CHOICES = [
        ('email', 'Notifications par email'),
        ('in_app', 'Notifications dans l\'application'),
        ('both', 'Les deux'),
        ('none', 'Aucune'),
    ]
    
    notifications_stock_faible = forms.ChoiceField(
        choices=NOTIFICATION_CHOICES,
        initial='in_app',
        label='Alertes de stock faible',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notifications_peremption = forms.ChoiceField(
        choices=NOTIFICATION_CHOICES,
        initial='in_app',
        label='Alertes de péremption',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notifications_commandes = forms.ChoiceField(
        choices=NOTIFICATION_CHOICES,
        initial='in_app',
        label='Mises à jour des commandes',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    seuil_alerte_perso = forms.IntegerField(
        min_value=1,
        initial=10,
        label='Seuil d\'alerte personnel',
        help_text='Nombre minimum d\'articles pour recevoir une alerte',
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )