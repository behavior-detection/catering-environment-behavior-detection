import json
import redis
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from datetime import datetime
import hashlib


class WebRTCFileShareConsumer(AsyncWebsocketConsumer):
    """WebRTC P2P文件共享信令服务器"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.user_id = None  # visitor_name 或 manager_name
        self.user_type = None  # 'manager' 或 'visitor'
        self.eid = None
        self.redis_client = redis.StrictRedis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=int(getattr(settings, 'REDIS_PORT', 6379)),
            db=0,
            decode_responses=True
        )

    async def connect(self):
        """WebSocket连接建立"""
        await self.accept()

        # 等待用户发送认证信息
        print(f"WebSocket连接已建立，等待认证")

    async def disconnect(self, close_code):
        """用户断开连接"""
        if self.user_id:
            # 从在线列表移除
            await self.set_user_offline()

            # 通知房间内其他用户
            if self.eid:
                await self.channel_layer.group_send(
                    f'eid_{self.eid}',
                    {
                        'type': 'user_offline',
                        'user_id': self.user_id,
                        'user_type': self.user_type
                    }
                )

                # 离开EID组
                await self.channel_layer.group_discard(
                    f'eid_{self.eid}',
                    self.channel_name
                )

    async def receive(self, text_data):
        """接收并处理消息"""
        try:
            data = json.loads(text_data)
            message_type = data.get('type')

            # 路由到不同的处理函数
            handlers = {
                'auth': self.handle_auth,
                'request_file_access': self.handle_file_access_request,
                'approve_file_access': self.handle_approve_file_access,
                'offer': self.handle_offer,
                'answer': self.handle_answer,
                'ice-candidate': self.handle_ice_candidate,
                'file_chunk': self.handle_file_chunk,
                'request_online_users': self.handle_request_online_users,
            }

            handler = handlers.get(message_type)
            if handler:
                await handler(data)
            else:
                await self.send_error(f'未知消息类型: {message_type}')

        except json.JSONDecodeError:
            await self.send_error('无效的JSON格式')
        except Exception as e:
            await self.send_error(f'处理消息失败: {str(e)}')

    async def handle_auth(self, data):
        """处理用户认证"""
        self.user_id = data.get('user_id')  # visitor_name 或 manager_name
        self.user_type = data.get('user_type')  # 'manager' 或 'visitor'
        self.eid = data.get('eid')
        access_token = data.get('access_token')  # visitor需要提供

        # 验证权限
        is_valid = await self.verify_access(access_token)

        if not is_valid:
            await self.send_error('认证失败，权限不足')
            await self.close()
            return

        # 加入EID组
        await self.channel_layer.group_add(
            f'eid_{self.eid}',
            self.channel_name
        )

        # 设置在线状态
        await self.set_user_online()

        # 发送认证成功消息
        await self.send(text_data=json.dumps({
            'type': 'auth_success',
            'user_id': self.user_id,
            'user_type': self.user_type,
            'eid': self.eid
        }))

        # 广播用户上线
        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'user_online',
                'user_id': self.user_id,
                'user_type': self.user_type
            }
        )

    async def handle_request_online_users(self, data):
        """获取在线用户列表"""
        online_users = await self.get_online_users()

        await self.send(text_data=json.dumps({
            'type': 'online_users',
            'users': online_users
        }))

    async def handle_file_access_request(self, data):
        """Visitor请求访问Manager的文件"""
        target_manager = data.get('target_manager')
        warehouse_id = data.get('warehouse_id')
        file_path = data.get('file_path')

        # 检查Manager是否在线
        is_online = await self.check_user_online(target_manager, 'manager')

        if not is_online:
            await self.send_error(f'用户 {target_manager} 不在线')
            return

        # 转发请求给Manager
        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'file_access_request',
                'from_user': self.user_id,
                'from_type': self.user_type,
                'target_manager': target_manager,
                'warehouse_id': warehouse_id,
                'file_path': file_path
            }
        )

    async def handle_approve_file_access(self, data):
        """Manager批准文件访问"""
        visitor_id = data.get('visitor_id')
        approved = data.get('approved', False)

        # 转发批准消息给Visitor
        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'file_access_response',
                'manager_id': self.user_id,
                'visitor_id': visitor_id,
                'approved': approved
            }
        )

    async def handle_offer(self, data):
        """转发WebRTC Offer"""
        target_user = data.get('target_user')

        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'webrtc_offer',
                'from_user': self.user_id,
                'target_user': target_user,
                'offer': data['offer']
            }
        )

    async def handle_answer(self, data):
        """转发WebRTC Answer"""
        target_user = data.get('target_user')

        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'webrtc_answer',
                'from_user': self.user_id,
                'target_user': target_user,
                'answer': data['answer']
            }
        )

    async def handle_ice_candidate(self, data):
        """转发ICE候选"""
        target_user = data.get('target_user')

        await self.channel_layer.group_send(
            f'eid_{self.eid}',
            {
                'type': 'webrtc_ice',
                'from_user': self.user_id,
                'target_user': target_user,
                'candidate': data['candidate']
            }
        )

    async def handle_file_chunk(self, data):
        """处理文件分块传输（可选，用于监控）"""
        # 可以在这里记录传输进度
        pass

    # ========== 组消息处理器 ==========

    async def user_online(self, event):
        """广播用户上线"""
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'user_online',
                'user_id': event['user_id'],
                'user_type': event['user_type']
            }))

    async def user_offline(self, event):
        """广播用户下线"""
        if event['user_id'] != self.user_id:
            await self.send(text_data=json.dumps({
                'type': 'user_offline',
                'user_id': event['user_id'],
                'user_type': event['user_type']
            }))

    async def file_access_request(self, event):
        """转发文件访问请求"""
        # 只发送给目标Manager
        if self.user_id == event['target_manager'] and self.user_type == 'manager':
            await self.send(text_data=json.dumps({
                'type': 'file_access_request',
                'from_user': event['from_user'],
                'warehouse_id': event['warehouse_id'],
                'file_path': event['file_path']
            }))

    async def file_access_response(self, event):
        """转发文件访问响应"""
        # 只发送给目标Visitor
        if self.user_id == event['visitor_id'] and self.user_type == 'visitor':
            await self.send(text_data=json.dumps({
                'type': 'file_access_response',
                'manager_id': event['manager_id'],
                'approved': event['approved']
            }))

    async def webrtc_offer(self, event):
        """转发WebRTC Offer"""
        if self.user_id == event['target_user']:
            await self.send(text_data=json.dumps({
                'type': 'offer',
                'from_user': event['from_user'],
                'offer': event['offer']
            }))

    async def webrtc_answer(self, event):
        """转发WebRTC Answer"""
        if self.user_id == event['target_user']:
            await self.send(text_data=json.dumps({
                'type': 'answer',
                'from_user': event['from_user'],
                'answer': event['answer']
            }))

    async def webrtc_ice(self, event):
        """转发ICE候选"""
        if self.user_id == event['target_user']:
            await self.send(text_data=json.dumps({
                'type': 'ice-candidate',
                'from_user': event['from_user'],
                'candidate': event['candidate']
            }))

    # ========== 辅助方法 ==========

    @database_sync_to_async
    def verify_access(self, access_token):
        """验证访问权限"""
        if self.user_type == 'manager':
            # Manager直接验证是否属于该EID
            from apps.login.api.models import Manager
            return Manager.objects.filter(
                name=self.user_id,
                eid=self.eid
            ).exists()

        elif self.user_type == 'visitor':
            # Visitor需要验证access_token
            if not access_token:
                return False

            token_key = f'access:token:{access_token}'
            token_data = self.redis_client.get(token_key)

            if not token_data:
                return False

            token_info = json.loads(token_data)
            return (token_info.get('visitor_name') == self.user_id and
                    token_info.get('eid') == self.eid)

        return False

    @database_sync_to_async
    def set_user_online(self):
        """设置用户在线状态"""
        online_key = f'online:{self.eid}:{self.user_type}:{self.user_id}'
        self.redis_client.setex(online_key, 3600, json.dumps({
            'user_id': self.user_id,
            'user_type': self.user_type,
            'eid': self.eid,
            'channel_name': self.channel_name,
            'online_at': datetime.now().isoformat()
        }))

    @database_sync_to_async
    def set_user_offline(self):
        """设置用户离线"""
        online_key = f'online:{self.eid}:{self.user_type}:{self.user_id}'
        self.redis_client.delete(online_key)

    @database_sync_to_async
    def check_user_online(self, user_id, user_type):
        """检查用户是否在线"""
        online_key = f'online:{self.eid}:{user_type}:{user_id}'
        return self.redis_client.exists(online_key)

    @database_sync_to_async
    def get_online_users(self):
        """获取在线用户列表"""
        online_users = []

        # 扫描该EID下的所有在线用户
        pattern = f'online:{self.eid}:*'
        for key in self.redis_client.scan_iter(match=pattern):
            user_data = self.redis_client.get(key)
            if user_data:
                online_users.append(json.loads(user_data))

        return online_users

    async def send_error(self, message):
        """发送错误消息"""
        await self.send(text_data=json.dumps({
            'type': 'error',
            'message': message
        }))