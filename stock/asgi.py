"""
Configuration ASGI du projet `stock`.

Ce fichier expose la variable `application` utilisée par les serveurs ASGI
(uvicorn, daphne, etc.) pour démarrer l'application Django en mode asynchrone.

Conserver la logique minimale: définir la variable d'environnement
`DJANGO_SETTINGS_MODULE` puis récupérer l'application via
`get_asgi_application()` fournie par Django.
"""

import os

from django.core.asgi import get_asgi_application

# Définit le module de settings si non fourni dans l'environnement
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'stock.settings')

# Application ASGI exportée (entrée pour le serveur ASGI)
application = get_asgi_application()
