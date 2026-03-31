"""
ASGI config for backend project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

# 设置环境变量
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

# 初始化 Django ASGI 应用（这会加载所有 Django 设置）
from django.core.asgi import get_asgi_application
django_asgi_app = get_asgi_application()

# Django 初始化完成后导入 Channels
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# 导入 WebSocket 路由
try:
    from detection.routing import websocket_urlpatterns as detection_ws
except ImportError as e:
    print(f"Warning: Could not import detection.routing: {e}")
    detection_ws = []

try:
    from apps.monitor.routing import websocket_urlpatterns as monitor_ws
except ImportError as e:
    print(f"Warning: Could not import apps.monitor.routing: {e}")
    monitor_ws = []

# 合并所有 WebSocket 路由
all_websocket_patterns = detection_ws + monitor_ws

# 配置 ASGI 应用
application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AuthMiddlewareStack(
        URLRouter(all_websocket_patterns)
    ),
})