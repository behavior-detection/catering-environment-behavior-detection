"""
Django settings for backend project.
"""

from pathlib import Path
import os
import sys
from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# 加载环境变量
load_dotenv(os.path.join(BASE_DIR, '.env'))

# Janus AI服务配置
JANUS_SERVICE_URL = os.environ.get('JANUS_SERVICE_URL', 'http://localhost:5001')
JANUS_TIMEOUT = 300  # 5分钟超时
AI_CACHE_DURATION = 3600  # 1小时缓存

# 性能优化配置
MAX_FILES_PER_QUERY = 20  # 每次查询最多处理的文件数
MAX_RECORDS_PER_FILE = 1000  # 每个文件最多处理的记录数
MAX_FILE_SIZE = 10 * 1024 * 1024  # 最大文件大小 10MB

# 将 apps 和 apps/login 添加到 Python 路径
sys.path.insert(0, os.path.join(BASE_DIR, 'apps'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("DJANGO_SECRET_KEY environment variable is required")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() == 'true'

# 从环境变量读取允许的主机
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

# Application definition
INSTALLED_APPS = [
    'daphne',
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    
    'channels',

    # 第三方应用
    'rest_framework',
    'corsheaders',

    # 实时监测
    'detection',

    # 本地应用
    'apps.monitor',
    'apps.login.authentication',
    'apps.login.face_recognition',
    'apps.login.api'
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    'corsheaders.middleware.CorsMiddleware',  # CORS 中间件
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    #"django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Celery配置
CELERY_BROKER_URL = "redis://127.0.0.1:6379/0"
CELERY_RESULT_BACKEND = "redis://127.0.0.1:6379/1"
CELERY_TASK_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]

# YOLO配置
YOLO_MODEL_PATH = str(BASE_DIR / "detection" / "yolo" / "weights" / "best.pt")
DETECTION_FRAME_RATE = 8
DETECTION_CONFIDENCE_THRESHOLD = 0.5
DETECTION_IOU_THRESHOLD = 0.45

WSGI_APPLICATION = "core.wsgi.application"

# 添加ASGI配置
ASGI_APPLICATION = "core.asgi.application"

# Database - 使用 MySQL
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv('DB_NAME', 'kitchen_detection_system'),
        "USER": os.getenv('DB_USER', 'root'),
        "PASSWORD": os.getenv('DB_PASSWORD', ''),
        "HOST": os.getenv('DB_HOST', 'localhost'),
        "PORT": os.getenv('DB_PORT', '3306'),
        'OPTIONS': {
            'charset': 'utf8mb4',
        },
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Internationalization
LANGUAGE_CODE = os.getenv('LANGUAGE_CODE', 'zh-hans')
TIME_ZONE = os.getenv('TIME_ZONE', 'Asia/Shanghai')
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

# 媒体文件配置
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# 人脸识别图片路径
FACE_IMAGES_ROOT = os.path.join(MEDIA_ROOT, 'Registration_Images')

# 企业/员工档案路径
ENTERPRISE_ARCHIVES_ROOT = os.path.join(BASE_DIR, 'enterprise_archives')
EMPLOYEE_ARCHIVES_ROOT = os.path.join(BASE_DIR, 'employee_archives')

# 确保必要目录存在
os.makedirs(MEDIA_ROOT, exist_ok=True)
os.makedirs(ENTERPRISE_ARCHIVES_ROOT, exist_ok=True)
os.makedirs(EMPLOYEE_ARCHIVES_ROOT, exist_ok=True)

# JSON检测结果目录
DETECTION_JSON_DIR = os.path.join(MEDIA_ROOT, "json")
os.makedirs(DETECTION_JSON_DIR, exist_ok=True)

# Default primary key field type
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# REST Framework 配置
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

# CORS 配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5174",
    "http://127.0.0.1:5174",
    "http://localhost:3000",
    "http://localhost:5175",
    "http://127.0.0.1:5175",
    "http://localhost:8000",
]
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = DEBUG  # 开发环境允许所有来源

# CSRF 配置
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8000',
    'http://127.0.0.1:8000',
    'http://localhost:5174',
    'http://127.0.0.1:5174',
    "http://localhost:5175",
    "http://127.0.0.1:5175",
]

# 邮件配置
EMAIL_HOST_USER = os.getenv('EMAIL_USER')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_PASS')

if EMAIL_HOST_USER and EMAIL_HOST_PASSWORD:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
    EMAIL_HOST = 'smtp.qq.com'
    EMAIL_PORT = 587
    EMAIL_USE_TLS = True
    DEFAULT_FROM_EMAIL = f'系统通知 <{EMAIL_HOST_USER}>'
else:
    # 如果没有配置邮箱，使用控制台后端（开发环境）
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
    DEFAULT_FROM_EMAIL = 'noreply@localhost'

# 微服务端口配置
PYTHON_APP_PORT = int(os.getenv('PYTHON_APP_PORT', 5000))
JAVA_OCR_PORT = int(os.getenv('JAVA_OCR_PORT', 8080))

# Redis 配置
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))

# 添加Channel Layer配置（使用您现有的Redis）
CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels_redis.core.RedisChannelLayer',
        'CONFIG': {
            "hosts": [(REDIS_HOST, REDIS_PORT)],
        },
    },
}

# WebRTC特定配置
WEBRTC_CONFIG = {
    'ice_servers': [
        {'urls': 'stun:stun.l.google.com:19302'}
    ],
    'signal_timeout': 300,  # 5分钟
}

# 在您现有的代码基础上添加WebRTC相关的键
WEBRTC_REDIS_KEYS = {
    # 权限相关
    'permission_request': 'perm:req:{}',
    'access_token': 'access:token:{}',

    # WebRTC信令
    'manager_peer': 'webrtc:peer:{}',
    'signal_room': 'webrtc:room:{}',
}

# 缓存配置
CACHES = {
    'default': {
        'BACKEND': 'django_redis.cache.RedisCache',
        'LOCATION': f'redis://{REDIS_HOST}:{REDIS_PORT}/1',
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        }
    }
}

# Session 配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'

# 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'logs', 'django.log'),
            'formatter': 'verbose',
        },
        'console': {
            'level': 'DEBUG' if DEBUG else 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
        'apps.login.api': {
            'handlers': ['file', 'console'],
            'level': 'DEBUG' if DEBUG else 'INFO',
            'propagate': False,
        },
    },
}

# 文件上传配置
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB

# 安全设置（生产环境）
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    X_FRAME_OPTIONS = 'DENY'


def ensure_directories():
    """确保所有必需的目录存在"""
    directories = [
        os.path.join(BASE_DIR, 'logs'),
        MEDIA_ROOT,
        STATIC_ROOT,
        FACE_IMAGES_ROOT,
        ENTERPRISE_ARCHIVES_ROOT,
        os.path.join(MEDIA_ROOT, 'temp'),  # OCR 临时文件目录
    ]

    for directory in directories:
        os.makedirs(directory, exist_ok=True)

    # 创建 .gitkeep 文件以保持目录结构
    for directory in directories:
        gitkeep_path = os.path.join(directory, '.gitkeep')
        if not os.path.exists(gitkeep_path):
            with open(gitkeep_path, 'w', encoding='utf-8') as f:
                f.write('# This file keeps the directory in git\n')


# 初始化目录
ensure_directories()