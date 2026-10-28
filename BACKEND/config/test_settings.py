"""
Settings usados apenas por `manage.py test --settings=config.test_settings`.
Isola os testes do PostgreSQL/Supabase de desenvolvimento.
"""
from .settings import *  # noqa: F401, F403

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'test_db.sqlite3',  # noqa: F405
    }
}

# Testes usam sempre disco local (não dependem do bucket Supabase).
USE_SUPABASE_STORAGE = False
FROTA_EMAIL_ENABLED = False
EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
        'OPTIONS': {
            'location': str(MEDIA_ROOT),  # noqa: F405
            'base_url': MEDIA_URL,  # noqa: F405
        },
    },
    'staticfiles': {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    },
}
