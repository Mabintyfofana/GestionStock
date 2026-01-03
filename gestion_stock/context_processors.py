from .models import Alerte

def notification_context(request):
    """Ajoute les notifications aux contextes de tous les templates"""
    context = {}
    
    if request.user.is_authenticated:
        try:
            # Nombre d'alertes non lues
            alertes_non_lues = Alerte.objects.filter(lu=False).count()
            context['alertes_non_lues'] = alertes_non_lues
            
            # Récupérer le profil utilisateur
            if hasattr(request.user, 'profilutilisateur'):
                context['user_role'] = request.user.profilutilisateur.role
                context['user_profile'] = request.user.profilutilisateur
        except:
            pass
    
    return context