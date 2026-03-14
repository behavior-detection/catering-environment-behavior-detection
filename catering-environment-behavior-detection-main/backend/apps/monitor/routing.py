from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    # 原有的WebRTC信令路由（可以保留或移除）
    # re_path(r'ws/webrtc/(?P<room_id>\w+)/$', consumers.WebRTCSignalingConsumer.as_asgi()),

    # 新的文件共享WebRTC路由
    re_path(r'ws/file-share/$', consumers.WebRTCFileShareConsumer.as_asgi()),
]