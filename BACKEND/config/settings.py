"""
Django settings for projeto_frota_senai project.
"""

from pathlib import Path
from decouple import config, Csv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.0/howto/deployment/checklist/

SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me')

# Chave do HMAC que sela a cadeia de auditoria. Deve ser estável: trocá-la faz
# todos os registros já gravados falharem na verificação de integridade.
AUDITORIA_CHAVE_INTEGRIDADE = config('AUDITORIA_CHAVE_INTEGRIDADE', default=SECRET_KEY)

# Limite da imagem de referência do veículo (JPG, PNG ou WebP).
VEICULO_IMAGEM_TAMANHO_MAXIMO_MB = config('VEICULO_IMAGEM_TAMANHO_MAXIMO_MB', default=5, cast=int)
VEICULO_IMAGEM_MAXIMO_FOTOS = config('VEICULO_IMAGEM_MAXIMO_FOTOS', default=8, cast=int)

DEBUG = config('DEBUG', default=True, cast=bool)

# Em desenvolvimento (DEBUG), aceita qualquer Host para o celular acessar
# a API pelo IP da LAN (ex.: 192.168.x.x:8000). Em produção, só a lista do .env.
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())
if DEBUG:
    ALLOWED_HOSTS = ['*']

# Origens explícitas (localhost no dev; URL do frontend no Render).
CORS_ALLOWED_ORIGINS = config(
    'CORS_ALLOWED_ORIGINS',
    default='http://localhost:3000,http://localhost:5173',
    cast=Csv(),
)

# Origens confiáveis para CSRF (Django Admin e formulários).
# Ex.: http://localhost,https://frota.exemplo.local — lista vazia se omitido.
CSRF_TRUSTED_ORIGINS = [
    origin for origin in config('CSRF_TRUSTED_ORIGINS', default='', cast=Csv())
    if origin
]

# Em desenvolvimento, permite origens do frontend na rede privada (RFC 1918)
# nas portas do Vite/CRA, sem cadastrar IP manualmente e sem CORS_ALLOW_ALL.
# Em produção (DEBUG=False) isso fica desligado — só CORS_ALLOWED_ORIGINS vale.
CORS_ALLOW_LAN = config('CORS_ALLOW_LAN', default=DEBUG, cast=bool)
CORS_ALLOWED_ORIGIN_REGEXES = []
if CORS_ALLOW_LAN:
    CORS_ALLOWED_ORIGIN_REGEXES = [
        r'^https?://('
        r'localhost|127\.0\.0\.1|'
        r'192\.168(?:\.\d{1,3}){2}|'
        r'10(?:\.\d{1,3}){3}|'
        r'172\.(?:1[6-9]|2\d|3[0-1])(?:\.\d{1,3}){2}'
        r'):(3000|5173)$',
    ]

from corsheaders.defaults import default_headers

CORS_ALLOW_HEADERS = (
    *default_headers,
    'x-client-form-factor',
)

# Atrás de reverse proxy (Nginx): usar Host / esquema do proxy nas URLs absolutas.
USE_X_FORWARDED_HOST = config('USE_X_FORWARDED_HOST', default=False, cast=bool)
if config('SECURE_PROXY_SSL_HEADER', default=False, cast=bool):
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    'usuarios',
    'veiculos',
    'reservas',
    'vistorias',
    'termos',
    'auditoria',
    'relatorios',
]

AUTH_USER_MODEL = 'usuarios.Usuario'

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'
ASGI_APPLICATION = 'config.asgi.application'


# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases
#
# Padrões preservam o ambiente atual (Supabase pooler + SSL).
# Em Docker interno use DB_HOST=db, DB_PORT=5432, DB_SSLMODE=disable
# e DB_DISABLE_SERVER_SIDE_CURSORS=False.

DATABASES = {
    'default': {
        'ENGINE': config('DB_ENGINE', default='django.db.backends.postgresql'),
        'NAME': config('DB_NAME', default='postgres'),
        'USER': config('DB_USER', default=''),
        'PASSWORD': config('DB_PASSWORD', default=''),
        'HOST': config('DB_HOST', default=''),
        'PORT': config('DB_PORT', default='6543'),
        'OPTIONS': {
            # Supabase exige SSL; rede Docker interna tipicamente usa disable.
            'sslmode': config('DB_SSLMODE', default='require'),
        },
        # Pooler (pgbouncer, transaction mode) não suporta server-side cursors.
        'DISABLE_SERVER_SIDE_CURSORS': config(
            'DB_DISABLE_SERVER_SIDE_CURSORS',
            default=True,
            cast=bool,
        ),
    }
}


# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True


# Static files (CSS, JavaScript, Images)
# Barra inicial obrigatória atrás do Nginx (/static/...).
STATIC_URL = config('STATIC_URL', default='/static/')
STATIC_ROOT = Path(config('STATIC_ROOT', default=str(BASE_DIR / 'staticfiles')))

# Media files (uploads) — volume persistente em Docker (MEDIA_ROOT=/app/media).
MEDIA_URL = config('MEDIA_URL', default='/media/')
MEDIA_ROOT = Path(config('MEDIA_ROOT', default=str(BASE_DIR / 'media')))
MEDIA_ROOT.mkdir(parents=True, exist_ok=True)

# Storage: local FileSystemStorage por padrão.
# Com USE_SUPABASE_STORAGE=True, usa o bucket S3-compatível do Supabase
# (necessário com banco remoto compartilhado — uploads locais não ficam
# acessíveis em outra máquina / após redeploy).
USE_SUPABASE_STORAGE = config('USE_SUPABASE_STORAGE', default=False, cast=bool)

if USE_SUPABASE_STORAGE:
    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3.S3Storage',
            'OPTIONS': {
                'access_key': config('SUPABASE_S3_ACCESS_KEY_ID'),
                'secret_key': config('SUPABASE_S3_SECRET_ACCESS_KEY'),
                'bucket_name': config('SUPABASE_S3_BUCKET_NAME'),
                'endpoint_url': config('SUPABASE_S3_ENDPOINT_URL'),
                'region_name': config('SUPABASE_S3_REGION', default='sa-east-1'),
                'default_acl': None,
                'querystring_auth': True,
                'querystring_expire': config(
                    'SUPABASE_S3_URL_EXPIRE', default=3600, cast=int
                ),
                'file_overwrite': False,
                'signature_version': 's3v4',
                'addressing_style': 'path',
            },
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
else:
    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
            'OPTIONS': {
                'location': str(MEDIA_ROOT),
                'base_url': MEDIA_URL,
            },
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
        'usuarios.permissions.ExigeSenhaDefinida',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# JWT Settings
from datetime import timedelta

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=8),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_TOKEN_CLASSES': ('rest_framework_simplejwt.tokens.AccessToken',),
    'USER_AUTHENTICATION_RULE': 'usuarios.auth.user_authentication_rule',
}

# E-mail complementar. Padrão: desligado. Não envia nada até a TI autorizar
# SMTP institucional (FROTA_EMAIL_ENABLED=True) e preencher EMAIL_HOST*.
FROTA_EMAIL_ENABLED = config('FROTA_EMAIL_ENABLED', default=False, cast=bool)
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.dummy.EmailBackend',
)
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@localhost')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simples': {
            'format': '{levelname} {name} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'simples',
        },
    },
    'loggers': {
        'vistorias.desempenho': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'reservas.operacoes': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
