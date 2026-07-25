"""
Configuration WSGI du projet `stock`.

Ce fichier expose la variable `application` utilisée par les serveurs WSGI
(Gunicorn, uWSGI, etc.) pour déployer l'application en production.

Il suffit de définir `DJANGO_SETTINGS_MODULE` et d'appeler
`get_wsgi_application()` fourni par Django.
"""

import os

from django.core.wsgi import get_wsgi_application

# Définit le module de settings si non fourni dans l'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock.settings')

# Application WSGI exportée (entrée pour le serveur WSGI)
application = get_wsgi_application()
