"""
WSGI config for kannammal_agro project.
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kannammal_agro.settings')

application = get_wsgi_application()