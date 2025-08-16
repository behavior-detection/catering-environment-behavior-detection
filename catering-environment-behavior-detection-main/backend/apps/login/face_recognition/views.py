import json
import requests
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def verify_face(request):
    """人脸验证"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    try:
        data = json.loads(request.body)

        # 调用Python人脸识别服务
        python_url = f'http://localhost:{settings.PYTHON_APP_PORT}'
        response = requests.post(
            f'{python_url}/api/verify_face',
            json=data,
            timeout=30
        )

        return JsonResponse(response.json())

    except requests.exceptions.ConnectionError:
        return JsonResponse({
            'success': False,
            'error': '人脸识别服务未启动',
            'results': []
        }, status=503)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


def get_registered_users(request):
    """获取注册用户列表"""
    try:
        python_url = f'http://localhost:{settings.PYTHON_APP_PORT}'
        response = requests.get(f'{python_url}/api/registered_users')
        return JsonResponse(response.json())
    except:
        return JsonResponse({
            'success': False,
            'error': '人脸识别服务不可用',
            'users': []
        }, status=503)


@csrf_exempt
def reload_database(request):
    """重新加载人脸数据库"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    try:
        python_url = f'http://localhost:{settings.PYTHON_APP_PORT}'
        response = requests.post(f'{python_url}/api/reload_database')
        return JsonResponse(response.json())
    except:
        return JsonResponse({
            'success': False,
            'error': '人脸识别服务不可用'
        }, status=503)