import jwt
import logging
from datetime import datetime, timedelta
from functools import wraps
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)


def create_access_token(payload: dict, expires_hours: int = None) -> str:
    if expires_hours is None:
        expires_hours = getattr(settings, 'JWT_EXPIRATION_HOURS', 24)

    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

    to_encode = payload.copy()
    to_encode['exp'] = datetime.utcnow() + timedelta(hours=expires_hours)
    to_encode['iat'] = datetime.utcnow()

    return jwt.encode(to_encode, secret, algorithm=algorithm)


def decode_access_token(token: str) -> dict:
    secret = getattr(settings, 'JWT_SECRET_KEY', settings.SECRET_KEY)
    algorithm = getattr(settings, 'JWT_ALGORITHM', 'HS256')

    return jwt.decode(token, secret, algorithms=[algorithm])


def login_required_jwt(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')

        if not auth_header.startswith('Bearer '):
            return JsonResponse(
                {'success': False, 'message': '未提供认证令牌'},
                status=401
            )

        token = auth_header.split(' ', 1)[1]
        try:
            payload = decode_access_token(token)
            request.jwt_user = payload
        except jwt.ExpiredSignatureError:
            return JsonResponse(
                {'success': False, 'message': '令牌已过期，请重新登录'},
                status=401
            )
        except jwt.InvalidTokenError:
            return JsonResponse(
                {'success': False, 'message': '无效的认证令牌'},
                status=401
            )

        return view_func(request, *args, **kwargs)
    return wrapper


def role_required(*allowed_roles):
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            jwt_user = getattr(request, 'jwt_user', None)
            if not jwt_user:
                return JsonResponse(
                    {'success': False, 'message': '未经认证'},
                    status=401
                )
            user_type = jwt_user.get('user_type', '')
            if user_type not in allowed_roles:
                return JsonResponse(
                    {'success': False, 'message': '权限不足，需要角色: ' + ', '.join(allowed_roles)},
                    status=403
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator