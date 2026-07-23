"""
Django settings for reserva_baep project.
SIS LOGÍSTICA 2º BAEP — Sistema Integrado de Controle Logístico
Versão 2.2 | Produção
"""

import os
import logging
from pathlib import Path
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv
import dj_database_url

# ---------------------------------------------------------------------------
# Diretório base do projeto
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# Carrega variáveis de ambiente do arquivo .env (se existir)
load_dotenv(BASE_DIR / '.env')

# ---------------------------------------------------------------------------
# Segurança
# ---------------------------------------------------------------------------
SECRET_KEY = os.getenv(
    'SECRET_KEY',
    'django-insecure-lts*=avsuyh#-f3nir&6$rp5ob#1=068_851j2(y#i)!%g_o_+'
)

DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

if not DEBUG and SECRET_KEY == 'django-insecure-lts*=avsuyh#-f3nir&6$rp5ob#1=068_851j2(y#i)!%g_o_+':
    raise ImproperlyConfigured('SECRET_KEY must be set as an environment variable in production.')

_allowed_raw = os.getenv('ALLOWED_HOSTS', '*')
ALLOWED_HOSTS = [h.strip() for h in _allowed_raw.split(',') if h.strip()]

# CSRF — origens confiáveis (separadas por vírgula no .env)
_csrf_raw = os.getenv(
    'CSRF_TRUSTED_ORIGINS',
    'http://127.0.0.1:8000,http://localhost:8000,'
    'https://127.0.0.1:8000,https://localhost:8000,'
    'http://10.43.19.224:8000,https://10.43.19.224:8000,'
    'http://10.43.19.225:8000,https://10.43.19.225:8000'
)
CSRF_TRUSTED_ORIGINS = [o.strip() for o in _csrf_raw.split(',') if o.strip()]

# ---------------------------------------------------------------------------
# Cabeçalhos de segurança (recomendados para produção)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'SAMEORIGIN'
    # Habilite HSTS apenas se usar HTTPS de ponta a ponta
    # SECURE_HSTS_SECONDS = 31536000
    # SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    # SECURE_SSL_REDIRECT = True
    # SESSION_COOKIE_SECURE = True
    # CSRF_COOKIE_SECURE = True
else:
    X_FRAME_OPTIONS = 'SAMEORIGIN'

# ---------------------------------------------------------------------------
# Aplicativos instalados
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Bibliotecas de terceiros
    'crispy_forms',
    'crispy_bootstrap5',
    'simple_history',

    # Módulos do sistema
    'materiais',
    'policiais',
    'movimentacoes',
    'municoes',
    'usuarios',
    'relatorios',
    'estoque',
    'viaturas',
    'patrimonio',
    'telematica',
    'solicitacoes.apps.SolicitacoesConfig',
    'licenciamento',
    'material_belico.apps.MaterialBelicoConfig',
    'administracao',
]

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',   # Arquivos estáticos em produção
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'licenciamento.middleware.LicenseCheckMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'simple_history.middleware.HistoryRequestMiddleware',
]

ROOT_URLCONF = 'reserva_baep.urls'

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'reserva_baep.wsgi.application'

# ---------------------------------------------------------------------------
# Banco de Dados
# ---------------------------------------------------------------------------
DATABASE_URL = os.getenv('DJANGO_DATABASE_URL') or os.getenv('DATABASE_URL')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')

# O Coolify pode expor um URL público em DATABASE_URL; considere apenas conexões postgres/sqlite válidas.
if DATABASE_URL and not DATABASE_URL.startswith(('postgres://', 'postgresql://', 'sqlite://')):
    DATABASE_URL = None

if DATABASE_URL and DATABASE_URL.startswith(('postgres://', 'postgresql://')):
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600
        )
    }
elif DATABASE_URL and DATABASE_URL.startswith('sqlite://'):
    DATABASES = {
        'default': dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=600
        )
    }
elif POSTGRES_HOST:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': os.getenv('POSTGRES_DB', 'postgres'),
            'USER': os.getenv('POSTGRES_USER', 'postgres'),
            'PASSWORD': os.getenv('POSTGRES_PASSWORD', ''),
            'HOST': POSTGRES_HOST,
            'PORT': os.getenv('POSTGRES_PORT', '5432'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
            'OPTIONS': {
                'timeout': 20,
            },
        }
    }

# ---------------------------------------------------------------------------
# Validação de senhas
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ---------------------------------------------------------------------------
# Internacionalização
# ---------------------------------------------------------------------------
LANGUAGE_CODE = 'pt-br'
TIME_ZONE = 'America/Sao_Paulo'
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Arquivos estáticos e de mídia
# ---------------------------------------------------------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT = BASE_DIR / 'staticfiles'

# WhiteNoise — compressão e cache de estáticos em produção
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# ---------------------------------------------------------------------------
# Chave primária padrão
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---------------------------------------------------------------------------
# Crispy Forms (Bootstrap 5)
# ---------------------------------------------------------------------------
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# ---------------------------------------------------------------------------
# URLs de autenticação
# ---------------------------------------------------------------------------
LOGIN_REDIRECT_URL = 'home'
LOGOUT_REDIRECT_URL = 'usuarios:login'
LOGIN_URL = 'usuarios:login'

# ---------------------------------------------------------------------------
# E-mail
# ---------------------------------------------------------------------------
EMAIL_BACKEND = os.getenv(
    'EMAIL_BACKEND',
    'django.core.mail.backends.console.EmailBackend'   # console em dev, smtp em produção
)
EMAIL_HOST = os.getenv('EMAIL_HOST', 'localhost')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', '1025'))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'False').lower() == 'true'
EMAIL_USE_SSL = os.getenv('EMAIL_USE_SSL', 'False').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
DEFAULT_FROM_EMAIL = os.getenv(
    'DEFAULT_FROM_EMAIL',
    'SIS LOGÍSTICA 2º BAEP <noreply@reservabaep.com.br>'
)

# ---------------------------------------------------------------------------
# Sessões
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = 28800          # 8 horas (padrão operacional)
SESSION_EXPIRE_AT_BROWSER_CLOSE = False

# ---------------------------------------------------------------------------
# Logging (produção registra warnings+ em arquivo, dev exibe no console)
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)
# Log file permission check for local execution
log_file_path = LOG_DIR / 'baep_sistema.log'
try:
    log_file_writable = True
    with open(log_file_path, 'a', encoding='utf-8') as f:
        pass
except (PermissionError, OSError):
    log_file_writable = False

_handlers = ['console', 'file'] if log_file_writable else ['console']

_handlers_dict = {
    'console': {
        'class': 'logging.StreamHandler',
        'formatter': 'simple',
    },
}
if log_file_writable:
    _handlers_dict['file'] = {
        'class': 'logging.handlers.RotatingFileHandler',
        'filename': log_file_path,
        'maxBytes': 10 * 1024 * 1024,   # 10 MB
        'backupCount': 5,
        'formatter': 'verbose',
        'encoding': 'utf-8',
    }

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {asctime} {message}',
            'style': '{',
        },
    },
    'handlers': _handlers_dict,
    'root': {
        'handlers': _handlers,
        'level': 'WARNING' if not DEBUG else 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': _handlers,
            'level': 'WARNING',
            'propagate': False,
        },
        'django.request': {
            'handlers': _handlers,
            'level': 'ERROR',
            'propagate': False,
        },
    },
}
