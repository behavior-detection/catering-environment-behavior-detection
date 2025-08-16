import os
import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from authentication.models import Enterprise


@csrf_exempt
def ocr_idcard(request):
    """身份证OCR识别"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    if 'idCard' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['idCard']

        # 检查Java服务是否可用
        java_url = f'http://localhost:{settings.JAVA_OCR_PORT}'
        try:
            health_check = requests.get(f'{java_url}/actuator/health', timeout=1)
            if health_check.status_code != 200:
                raise Exception('Java服务不可用')
        except:
            # Java服务不可用，返回模拟数据
            return JsonResponse({
                'success': True,
                'data': {
                    'name': '测试用户',
                    'idNumber': '110101199001011234',
                    'sex': '男',
                    'nation': '汉',
                    'birth': '1990-01-01',
                    'address': '北京市朝阳区测试街道'
                },
                'message': '注意：OCR服务未启动，使用模拟数据'
            })

        # 保存临时文件
        temp_path = default_storage.save(f'temp/{file.name}', ContentFile(file.read()))
        temp_file_path = os.path.join(settings.MEDIA_ROOT, temp_path)

        try:
            # 调用Java OCR服务
            with open(temp_file_path, 'rb') as f:
                files = {'idCard': (file.name, f, file.content_type)}
                response = requests.post(
                    f'{java_url}/api/ocr/idcard-front',
                    files=files,
                    timeout=30
                )

            if response.status_code == 200:
                return JsonResponse(response.json())
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'OCR识别失败'
                }, status=response.status_code)

        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def check_enterprise(request):
    """检查企业是否注册"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    try:
        data = json.loads(request.body)
        enterprise_name = data.get('enterpriseName')

        if not enterprise_name:
            return JsonResponse({'success': False, 'message': '企业名称不能为空'}, status=400)

        exists = Enterprise.objects.filter(name=enterprise_name).exists()

        return JsonResponse({
            'success': True,
            'exists': exists
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


def system_health(request):
    """系统健康检查"""
    try:
        # 检查数据库
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            db_status = 'connected'
    except:
        db_status = 'disconnected'

    # 检查其他服务
    services_status = {
        'python': check_service_health(f'http://localhost:{settings.PYTHON_APP_PORT}/api/registered_users'),
        'java_ocr': check_service_health(f'http://localhost:{settings.JAVA_OCR_PORT}/actuator/health'),
        'redis': check_redis_health()
    }

    return JsonResponse({
        'database': db_status,
        'services': services_status,
        'timestamp': datetime.now().isoformat()
    })


def check_service_health(url):
    """检查服务健康状态"""
    try:
        response = requests.get(url, timeout=2)
        return 'running' if response.status_code == 200 else 'error'
    except:
        return 'stopped'


def check_redis_health():
    """检查Redis健康状态"""
    try:
        import redis
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT
        )
        redis_client.ping()
        return 'running'
    except:
        return 'stopped'


@csrf_exempt
def save_employee_verification(request):
    """保存员工验证文件到人脸识别服务目录"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    if 'idCard' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['idCard']
        user_name = request.POST.get('userName')
        enterprise_name = request.POST.get('enterpriseName')

        if not user_name or not enterprise_name:
            return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)

        # 生成文件名
        file_extension = os.path.splitext(file.name)[1]
        sanitized_user_name = ''.join(c for c in user_name if c.isalnum() or c in '._-')
        sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')
        file_name = f'{sanitized_user_name}-{sanitized_enterprise_name}{file_extension}'

        # 保存到 MEDIA_ROOT (即 face_service/Registration_Images)
        file_path = os.path.join(settings.MEDIA_ROOT, file_name)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'message': '身份验证信息已保存',
            'data': {
                'fileName': file_name,
                'userName': user_name,
                'enterpriseName': enterprise_name
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def save_license_file(request):
    """保存营业执照文件到企业档案目录"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    if 'license' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['license']
        company_name = request.POST.get('companyName')
        credit_code = request.POST.get('creditCode', '')

        if not company_name:
            return JsonResponse({'success': False, 'message': '缺少企业名称'}, status=400)

        # 生成文件名和文件夹名
        file_extension = os.path.splitext(file.name)[1]
        sanitized_company_name = ''.join(c for c in company_name if c.isalnum() or c in '._-')
        sanitized_credit_code = ''.join(c for c in credit_code if c.isalnum() or c in '._-')

        folder_name = f'{sanitized_company_name}-{sanitized_credit_code}'
        file_name = f'营业执照-{sanitized_company_name}-{sanitized_credit_code}{file_extension}'

        # 创建企业档案目录
        enterprise_dir = os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, folder_name)
        os.makedirs(enterprise_dir, exist_ok=True)

        # 保存文件
        file_path = os.path.join(enterprise_dir, file_name)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'message': '营业执照文件已保存',
            'data': {
                'fileName': file_name,
                'companyName': company_name,
                'creditCode': credit_code,
                'folderName': folder_name
            }
        })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)