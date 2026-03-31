from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/video/(?P<source_id>\w+)/$', consumers.VideoStreamConsumer.as_asgi()),
    re_path(r'ws/violations/(?P<source_id>\w+)/$', consumers.ViolationConsumer.as_asgi()),
    re_path(r'ws/violations/$', consumers.ViolationConsumer.as_asgi()),
]