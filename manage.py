#!/usr/bin/env python
"""
Point d'entrée CLI pour le projet Django.

Ce fichier est utilisé par les commandes Django (runserver, migrate, shell, ...).
Le comportement par défaut est fourni par Django via
`django.core.management.execute_from_command_line`.

Ne modifiez pas ce fichier sauf si vous savez ce que vous faites ;
préférez configurer les variables d'environnement ou `stock/settings.py`.
"""
import os
import sys


def main():
    """Exécute les commandes d'administration Django.

    - Définit la variable d'environnement `DJANGO_SETTINGS_MODULE` si absente.
    - Importe la fonction d'exécution de commandes de Django et l'appelle
    en lui passant les arguments de la ligne de commande.
    """
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        # Erreur claire si Django n'est pas installé ou l'environnement virtuel
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
