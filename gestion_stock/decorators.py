from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps

from gestion_stock.models import ProfilUtilisateur

def role_requis(*roles):
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            try:
                profil = request.user.profilutilisateur
                if profil.role in roles:
                    return view_func(request, *args, **kwargs)
                else:
                    # Rediriger vers le dashboard avec un message d'erreur
                    from django.contrib import messages
                    messages.error(request, 'Vous n\'avez pas les permissions nécessaires.')
                    return redirect('dashboard')
            except ProfilUtilisateur.DoesNotExist:
                return redirect('login')
        return _wrapped_view
    return decorator

# Décorateurs spécifiques
admin_required = role_requis('admin')
gestionnaire_required = role_requis('admin', 'gestionnaire')
vendeur_required = role_requis('admin', 'gestionnaire', 'vendeur')