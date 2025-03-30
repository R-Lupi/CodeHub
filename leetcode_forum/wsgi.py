# leetcode_forum/wsgi.py
import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'leetcode_forum.settings')

application = get_wsgi_application()