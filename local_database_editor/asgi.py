import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "local_database_editor.settings")
application = get_asgi_application()
