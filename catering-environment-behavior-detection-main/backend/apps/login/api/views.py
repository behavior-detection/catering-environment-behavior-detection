import os
import json
import requests
from datetime import datetime
from django.http import JsonResponse
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from .models import Enterprise, Verification, Visitor, Manager, Admin, SecurityProblem
from django.views.decorators.http import require_http_methods
import hashlib
from django.core.mail import send_mail
import redis
import json
import logging
import random
from django.http import FileResponse

# 配置日志
logger = logging.getLogger(__name__)

@csrf_exempt
def ocr_idcard(request):
    """身份证 OCR 识别"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

    if 'idCard' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['idCard']

        # 检查文件格式
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'message': '不支持的文件格式，请上传 JPG、PNG 或 WEBP 格式的图片'
            }, status=400)

        # 检查文件大小
        if file.size > 10 * 1024 * 1024:  # 10MB
            return JsonResponse({
                'success': False,
                'message': '图片文件过大，请上传小于10MB的图片'
            }, status=400)

        # 检查 Java 服务是否可用
        java_url = f'http://localhost:{settings.JAVA_OCR_PORT}'
        try:
            health_check = requests.get(f'{java_url}/actuator/health', timeout=2)
            if health_check.status_code != 200:
                raise Exception('OCR服务不可用')
        except:
            return JsonResponse({
                'success': False,
                'message': 'OCR服务暂时不可用，请稍后再试'
            }, status=503)

        # 保存临时文件
        temp_path = default_storage.save(f'temp/{file.name}', ContentFile(file.read()))
        temp_file_path = os.path.join(settings.MEDIA_ROOT, temp_path)

        try:
            # 调用 Java OCR 服务
            with open(temp_file_path, 'rb') as f:
                files = {'idCard': (file.name, f, file.content_type)}
                response = requests.post(
                    f'{java_url}/api/ocr/idcard-front',
                    files=files,
                    timeout=45  # 增加超时时间
                )

            if response.status_code == 200:
                result = response.json()
                # 检查识别结果是否完整
                if result.get('success') and result.get('data'):
                    data = result['data']
                    if not data.get('name') or not data.get('idNumber'):
                        return JsonResponse({
                            'success': False,
                            'message': '身份证识别不完整，请确保上传的图片清晰且包含完整的身份证正面'
                        }, status=400)
                    return JsonResponse(result)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '身份证识别失败，请确保图片清晰并重新上传'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'message': '身份证识别失败，请检查图片质量并重新上传'
                }, status=400)

        except requests.exceptions.ReadTimeout:
            return JsonResponse({
                'success': False,
                'message': 'OCR识别超时，可能是图片过大或质量问题，请尝试上传更清晰的图片'
            }, status=408)
        except Exception as e:
            print(f"OCR识别异常: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': '身份证识别出现异常，请重新上传'
            }, status=500)
        finally:
            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

    except Exception as e:
        print(f"处理请求异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '处理请求时出现错误，请重试'
        }, status=500)


@csrf_exempt
def check_enterprise(request):
    """检查企业是否注册"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

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
    """检查 Redis 健康状态"""
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
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

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

        # 保存到 MEDIA_ROOT（即 face_service/Registration_Images）
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
        return JsonResponse({'success': False, 'message': '只支持 POST 请求'}, status=405)

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


@csrf_exempt
@require_http_methods(["POST"])
def verify_user_email(request):
    """验证邮箱是否与用户名匹配"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')

        if not username or not email:
            return JsonResponse({'success': False, 'message': '用户名和邮箱不能为空'}, status=400)

        # 使用 exists() 而不是 first()，避免查询 id 字段
        exists = Verification.objects.filter(name=username, email=email).exists()

        if exists:
            return JsonResponse({'success': True, 'message': '邮箱验证通过'})
        else:
            return JsonResponse({'success': False, 'message': '邮箱与用户名不匹配'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_manager_username(request):
    """检查管理员用户名是否存在"""
    try:
        data = json.loads(request.body)
        username = data.get('username')

        if not username:
            return JsonResponse({'success': False, 'message': '用户名不能为空'}, status=400)

        # 检查用户名是否在 Manager 表中存在
        exists = Manager.objects.filter(name=username).exists()

        return JsonResponse({'success': True, 'exists': exists})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_visitor_username(request):
    """检查访客用户名是否存在"""
    try:
        data = json.loads(request.body)
        username = data.get('username')

        if not username:
            return JsonResponse({'success': False, 'message': '用户名不能为空'}, status=400)

        # 检查用户名是否在 Visitor 表中存在
        exists = Visitor.objects.filter(name=username).exists()

        return JsonResponse({'success': True, 'exists': exists})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_employee_verification_data(request):
    """保存员工验证数据"""
    try:
        data = json.loads(request.body)
        enterprise_name = data.get('enterprise_name')
        employee_name = data.get('employee_name')
        id_number = data.get('id_number')
        verification_status = data.get('verification_status', 'pending')

        if not all([enterprise_name, employee_name, id_number]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 检查企业是否存在
        enterprise = Enterprise.objects.filter(name=enterprise_name).first()
        if not enterprise:
            return JsonResponse({
                'success': False,
                'message': '企业不存在'
            }, status=404)

        # 这里您需要创建一个新的模型来保存员工验证信息
        # 或者临时保存到 session/缓存中
        # 示例：使用 Django 缓存
        from django.core.cache import cache
        verification_id = f"emp_verify_{employee_name}_{id_number}"

        cache.set(verification_id, {
            'enterprise_name': enterprise_name,
            'employee_name': employee_name,
            'id_number': id_number,
            'verification_status': verification_status,
        }, 3600)  # 缓存 1 小时

        return JsonResponse({
            'success': True,
            'message': '员工验证信息已保存',
            'verification_id': verification_id
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的 JSON 格式'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)


@csrf_exempt
def ocr_business_license(request):
    """营业执照OCR识别"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    if 'license' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['license']

        # 检查文件格式
        allowed_types = ['image/jpeg', 'image/jpg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            return JsonResponse({
                'success': False,
                'message': '不支持的文件格式，请上传 JPG、PNG 或 WEBP 格式的图片'
            }, status=400)

        # 检查文件大小
        if file.size > 10 * 1024 * 1024:  # 10MB
            return JsonResponse({
                'success': False,
                'message': '图片文件过大，请上传小于10MB的图片'
            }, status=400)

        # 尝试调用Java OCR服务
        java_url = f'http://localhost:{settings.JAVA_OCR_PORT}/api/ocr/business-license'

        try:
            # 检查服务健康状态
            health_check = requests.get(
                f'http://localhost:{settings.JAVA_OCR_PORT}/actuator/health',
                timeout=2
            )
            if health_check.status_code != 200:
                raise Exception('OCR服务不可用')

            # 保存临时文件
            temp_path = default_storage.save(f'temp/{file.name}', ContentFile(file.read()))
            temp_file_path = os.path.join(settings.MEDIA_ROOT, temp_path)

            # 调用Java服务
            with open(temp_file_path, 'rb') as f:
                files = {'license': (file.name, f, file.content_type)}
                response = requests.post(java_url, files=files, timeout=45)

            # 清理临时文件
            if os.path.exists(temp_file_path):
                os.remove(temp_file_path)

            if response.status_code == 200:
                result = response.json()
                # 检查识别结果
                if result.get('success') and result.get('data'):
                    data = result['data']
                    # 验证必要字段
                    if not data.get('name') or not data.get('eid'):
                        return JsonResponse({
                            'success': False,
                            'message': '营业执照识别不完整，请确保上传的图片清晰且包含完整的营业执照'
                        }, status=400)
                    return JsonResponse(result)
                else:
                    return JsonResponse({
                        'success': False,
                        'message': '营业执照识别失败，请确保图片清晰并重新上传'
                    }, status=400)
            else:
                return JsonResponse({
                    'success': False,
                    'message': '营业执照识别失败，请检查图片质量并重新上传'
                }, status=400)

        except requests.exceptions.ReadTimeout:
            return JsonResponse({
                'success': False,
                'message': 'OCR识别超时，可能是图片过大或质量问题，请尝试上传更清晰的图片'
            }, status=408)
        except Exception as e:
            print(f"OCR服务调用失败: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'OCR服务暂时不可用，请稍后再试'
            }, status=503)

    except Exception as e:
        print(f"处理营业执照识别请求异常: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '处理请求时出现错误，请重试'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_code(request):
    """验证邮箱验证码 - API版本"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        code = data.get('code')

        from django.core.cache import cache
        stored_code = cache.get(f'verification_code:{email}')

        if not stored_code:
            return JsonResponse({'success': False, 'message': '验证码已过期'}, status=400)

        if stored_code == str(code):
            cache.delete(f'verification_code:{email}')
            return JsonResponse({'success': True, 'message': '验证成功'})
        else:
            return JsonResponse({'success': False, 'message': '验证码错误'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_username(request):
    """检查用户名是否存在 - API版本"""
    try:
        data = json.loads(request.body)
        username = data.get('username')

        if not username:
            return JsonResponse({'success': False, 'message': '用户名不能为空'}, status=400)

        exists = Visitor.objects.filter(name=username).exists()
        return JsonResponse({'success': True, 'exists': exists})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def visitor_register(request):
    """访客注册 - API版本"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        if not all([username, email, password]):
            return JsonResponse({'success': False, 'message': '所有字段都是必填的'}, status=400)

        # 检查用户名是否存在
        if Visitor.objects.filter(name=username).exists():
            return JsonResponse({'success': False, 'message': '用户名已存在'}, status=400)

        # 创建访客 - 使用明文密码
        visitor = Visitor.objects.create(
            name=username,
            password=password  # 明文密码
        )

        # 创建验证记录
        Verification.objects.create(
            name=username,
            email=email
        )

        return JsonResponse({'success': True, 'message': '注册成功'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def user_register(request):
    """用户注册 """
    try:
        data = json.loads(request.body)
        # 处理完整的用户注册逻辑
        return visitor_register(request)  # 临时重用访客注册逻辑

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reset_password_email(request):
    """通过邮箱重置密码"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        verification_code = data.get('verification_code')
        new_password = data.get('new_password')

        if not all([email, verification_code, new_password]):
            return JsonResponse({'success': False, 'message': '参数不完整'}, status=400)

        # 验证验证码
        from django.core.cache import cache
        stored_code = cache.get(f'verification_code:{email}')

        if not stored_code or stored_code != verification_code:
            return JsonResponse({'success': False, 'message': '验证码错误或已过期'}, status=400)

        # 根据邮箱找到用户并更新密码
        verification = Verification.objects.filter(email=email).first()
        if not verification:
            return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)

        # 更新密码（使用明文密码）
        updated = False
        for model in [Visitor, Manager, Admin]:
            if model.objects.filter(name=verification.name).update(password=new_password):
                updated = True
                break

        if updated:
            cache.delete(f'verification_code:{email}')
            return JsonResponse({'success': True, 'message': '密码重置成功'})
        else:
            return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def create_enterprise_archive(request):
    """创建企业档案"""
    try:
        data = json.loads(request.body)
        company_name = data.get('companyName')
        eid = data.get('unifiedSocialCreditCode')

        if not company_name:
            return JsonResponse({'success': False, 'message': '企业名称不能为空'}, status=400)

        # 创建或更新企业记录
        enterprise, created = Enterprise.objects.get_or_create(
            name=company_name,
            defaults={'eid': eid or ''}
        )

        return JsonResponse({
            'success': True,
            'message': '企业档案创建成功',
            'data': {
                'id': enterprise.id,
                'name': enterprise.name,
                'eid': enterprise.eid
            }
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_legal_representative_id(request):
    """保存法定代表人身份证"""
    if 'idCard' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    try:
        file = request.FILES['idCard']
        user_name = request.POST.get('userName')
        enterprise_name = request.POST.get('enterpriseName')
        id_number = request.POST.get('idNumber', '')
        credit_code = request.POST.get('creditCode', '')

        if not user_name or not enterprise_name:
            return JsonResponse({'success': False, 'message': '缺少必要参数'}, status=400)

        # 生成文件名
        file_extension = os.path.splitext(file.name)[1]
        sanitized_user_name = ''.join(c for c in user_name if c.isalnum() or c in '._-')
        sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')
        sanitized_credit_code = ''.join(c for c in credit_code if c.isalnum() or c in '._-')

        # 创建文件名：法定代表人身份证-用户名-企业名-信用代码
        file_name = f'法定代表人身份证-{sanitized_user_name}-{sanitized_enterprise_name}-{sanitized_credit_code}{file_extension}'

        # 创建企业档案目录
        folder_name = f'{sanitized_enterprise_name}-{sanitized_credit_code}'
        enterprise_dir = os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, folder_name)
        os.makedirs(enterprise_dir, exist_ok=True)

        # 保存文件到企业档案目录
        file_path = os.path.join(enterprise_dir, file_name)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 同时保存到人脸识别目录（用于后续验证）
        face_recognition_file_name = f'{sanitized_user_name}-{sanitized_enterprise_name}{file_extension}'
        face_recognition_path = os.path.join(settings.MEDIA_ROOT, face_recognition_file_name)

        with open(face_recognition_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        return JsonResponse({
            'success': True,
            'message': '法定代表人身份证已保存',
            'data': {
                'fileName': file_name,
                'userName': user_name,
                'enterpriseName': enterprise_name,
                'idNumber': id_number,
                'creditCode': credit_code,
                'folderName': folder_name,
                'faceRecognitionFile': face_recognition_file_name
            }
        })

    except Exception as e:
        print(f"保存法定代表人身份证失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '保存失败: ' + str(e)
        }, status=500)

# 修复Redis客户端初始化
def get_redis_client():
    """获取Redis客户端，如果连接失败返回None"""
    try:
        from django.conf import settings

        client = redis.Redis(
            host=getattr(settings, 'REDIS_HOST', 'localhost'),
            port=getattr(settings, 'REDIS_PORT', 6379),
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )

        # 测试连接
        client.ping()
        return client

    except AttributeError as e:
        logger.error(f"Redis配置缺失: {str(e)}")
        return None
    except redis.ConnectionError as e:
        logger.error(f"Redis连接失败: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Redis客户端创建失败: {str(e)}")
        return None


# 在需要使用Redis的地方使用这个函数
redis_client = get_redis_client()


@csrf_exempt
@require_http_methods(["POST"])
def send_verification_code(request):
    """发送邮箱验证码"""
    try:
        data = json.loads(request.body)
        email = data.get('email')

        if not email:
            return JsonResponse({'success': False, 'message': '邮箱不能为空'}, status=400)

        # 生成6位验证码
        code = str(random.randint(100000, 999999))

        # 如果Redis可用，使用Redis存储
        if redis_client:
            redis_client.setex(f'verify_code:{email}', 300, code)
        else:
            # 如果Redis不可用，使用Django的缓存
            from django.core.cache import cache
            cache.set(f'verification_code:{email}', code, 300)

        # 发送邮件
        try:
            send_mail(
                '验证码',
                f'您的验证码是：{code}，5分钟内有效。',
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return JsonResponse({'success': True, 'message': '验证码已发送'})
        except Exception as e:
            print(f"Email send error: {str(e)}")
            return JsonResponse({'success': False, 'message': '邮件发送失败，请检查邮件配置'}, status=500)

    except Exception as e:
        print(f"send_verification_code error: {str(e)}")
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_manager_registration_cache(request):
    """保存管理员注册数据到缓存，等待审核"""
    try:
        data = json.loads(request.body)

        # 验证必要字段
        required_fields = [
            'companyName', 'legalRepresentative', 'unifiedSocialCreditCode',
            'username', 'email', 'password', 'idNumber'
        ]

        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'message': f'缺少必要字段: {", ".join(missing_fields)}'
            }, status=400)

        # 检查用户名是否已存在（包括缓存中的）
        username = data.get('username')

        # 检查数据库中是否已存在
        if Manager.objects.filter(name=username).exists():
            return JsonResponse({
                'success': False,
                'message': '用户名已存在'
            }, status=400)

        # 检查缓存中是否已存在
        redis_client = get_redis_client()
        if redis_client:
            existing_cache_keys = redis_client.keys(f'manager_registration:*:{username}')
            if existing_cache_keys:
                return JsonResponse({
                    'success': False,
                    'message': '该用户名的注册申请已在审核中'
                }, status=400)

        # 检查企业是否已经注册
        company_name = data.get('companyName')
        credit_code = data.get('unifiedSocialCreditCode')

        if Enterprise.objects.filter(name=company_name).exists():
            return JsonResponse({
                'success': False,
                'message': '该企业已经注册'
            }, status=400)

        if credit_code and Enterprise.objects.filter(eid=credit_code).exists():
            return JsonResponse({
                'success': False,
                'message': '该统一社会信用代码已被注册'
            }, status=400)

        # 生成唯一的注册ID
        registration_id = hashlib.md5(f"{username}_{company_name}_{datetime.now().isoformat()}".encode()).hexdigest()[
                          :16]

        # 准备缓存数据
        cache_data = {
            # 基本信息
            'registrationId': registration_id,
            'registrationType': 'manager',
            'approvalStatus': 'pending_approval',
            'submissionTime': datetime.now().isoformat(),

            # 企业信息
            'companyName': data.get('companyName'),
            'legalRepresentative': data.get('legalRepresentative'),
            'unifiedSocialCreditCode': data.get('unifiedSocialCreditCode'),
            'registeredCapital': data.get('registeredCapital', ''),
            'establishmentDate': data.get('establishmentDate', ''),

            # 用户信息
            'username': username,
            'email': data.get('email'),
            'password': data.get('password'),  # 使用明文密码
            'idNumber': data.get('idNumber'),
            'address': data.get('address', ''),

            # 验证状态
            'licenseVerified': data.get('licenseVerified', False),
            'idVerified': data.get('idVerified', False),
            'emailVerified': data.get('emailVerified', False),

            # 文件信息
            'savedFiles': data.get('savedFiles', {}),

            # 审核信息
            'reviewComments': '',
            'reviewedBy': '',
            'reviewedAt': ''
        }

        # 保存到缓存
        cache_key = f'manager_registration:{registration_id}:{username}'

        if redis_client:
            # 使用Redis保存，设置7天过期时间
            print(f"保存注册信息到Redis，key: {cache_key}")
            redis_client.setex(cache_key, 7 * 24 * 3600, json.dumps(cache_data, ensure_ascii=False))

            # 同时维护一个待审核列表
            print("添加到待审核列表")
            redis_client.lpush('pending_manager_registrations', cache_key)

            # 广播到所有管理员账号
            print("准备广播到管理员...")
            broadcast_result = broadcast_to_admins(cache_data, redis_client)
            print(f"广播结果: {broadcast_result}")

            if not broadcast_result:
                print("WARNING: 广播到管理员失败，但注册信息已保存")
                # 即使广播失败，注册信息已经保存，可以继续

            storage_type = 'redis'
        else:
            # 如果Redis不可用，使用Django缓存
            print("WARNING: Redis不可用，使用Django缓存")
            from django.core.cache import cache
            cache.set(cache_key, cache_data, 7 * 24 * 3600)  # 7天过期
            storage_type = 'django_cache'

        return JsonResponse({
            'success': True,
            'message': '注册申请已提交，等待管理员审核',
            'data': {
                'registrationId': registration_id,
                'storageType': storage_type,
                'estimatedReviewTime': '1-3个工作日',
                'submissionTime': cache_data['submissionTime']
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        print(f"保存管理员注册缓存失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': '保存注册信息失败，请重试'
        }, status=500)


def broadcast_to_admins(registration_data, redis_client=None):
    """改进版的广播函数，使用动态文件命名"""
    try:
        if not redis_client:
            redis_client = get_redis_client()
            if not redis_client:
                return False

        admin_usernames = list(Admin.objects.values_list('name', flat=True))
        if not admin_usernames:
            return False

        # 处理文件信息，提取实际的文件列表
        saved_files = registration_data.get('savedFiles', {})
        file_list = []

        for filename, filepath in saved_files.items():
            # 确保使用相对路径
            if filepath.startswith('/'):
                filepath = filepath.lstrip('/')

            file_info = {
                'filename': filename,
                'path': filepath,
                'type': 'license' if '营业执照' in filename else 'idCard',
                'registration_type': 'enterprise'  # 添加注册类型
            }
            file_list.append(file_info)

        # 创建广播消息
        broadcast_message = {
            'type': 'registration_request',
            'id': registration_data['registrationId'],
            'timestamp': registration_data['submissionTime'],
            'data': {
                'companyName': registration_data['companyName'],
                'legalRepresentative': registration_data['legalRepresentative'],
                'username': registration_data['username'],
                'email': registration_data['email'],
                'unifiedSocialCreditCode': registration_data['unifiedSocialCreditCode'],
                'submissionTime': registration_data['submissionTime'],
                'approvalStatus': registration_data['approvalStatus'],
                # 使用文件列表而不是固定字段
                'files': file_list,
                'licenseVerified': registration_data.get('licenseVerified', False),
                'idVerified': registration_data.get('idVerified', False)
            },
            'message': f'新的企业注册申请：{registration_data["companyName"]}'
        }

        # 广播到所有管理员
        success_count = 0
        for admin_username in admin_usernames:
            try:
                notification_key = f'admin_notifications:{admin_username}'
                redis_client.lpush(notification_key, json.dumps(broadcast_message, ensure_ascii=False))
                redis_client.expire(notification_key, 30 * 24 * 3600)
                success_count += 1
            except Exception as e:
                print(f"ERROR: 推送到 {admin_username} 失败: {str(e)}")

        return success_count > 0

    except Exception as e:
        print(f"ERROR: 广播到管理员失败: {str(e)}")
        return False


@csrf_exempt
@require_http_methods(["POST"])
def approve_manager_registration(request):
    """审核通过管理员注册申请"""
    try:
        data = json.loads(request.body)
        registration_id = data.get('registrationId')
        approval_decision = data.get('decision')  # 'approve' 或 'reject'
        review_comments = data.get('reviewComments', '')
        reviewed_by = data.get('reviewedBy', 'admin')

        if not registration_id or not approval_decision:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 查找注册申请
        cache_keys = redis_client.keys(f'manager_registration:{registration_id}:*')
        if not cache_keys:
            return JsonResponse({
                'success': False,
                'message': '未找到该注册申请'
            }, status=404)

        cache_key = cache_keys[0]
        cache_data = redis_client.get(cache_key)

        if not cache_data:
            return JsonResponse({
                'success': False,
                'message': '注册申请已过期'
            }, status=404)

        registration_data = json.loads(cache_data)

        if approval_decision == 'approve':
            # 审核通过，写入数据库
            try:
                # 创建企业记录
                enterprise, created = Enterprise.objects.get_or_create(
                    name=registration_data['companyName'],
                    defaults={'eid': registration_data['unifiedSocialCreditCode']}
                )

                # 创建管理员记录，rep字段默认设置为'yes'
                manager = Manager.objects.create(
                    name=registration_data['username'],
                    password=registration_data['password'],  # 使用明文密码
                    rep='yes',  # 默认设置为yes，因为是企业首位注册用户
                    eid=registration_data['unifiedSocialCreditCode']
                )

                # 创建验证记录
                Verification.objects.create(
                    name=registration_data['username'],
                    email=registration_data['email']
                )

                result_message = '注册申请已通过，用户账户已创建'

            except Exception as e:
                print(f"创建用户账户失败: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': '创建用户账户失败'
                }, status=500)

        else:  # reject
            result_message = '注册申请已拒绝'

        # 更新审核状态
        registration_data.update({
            'approvalStatus': 'approved' if approval_decision == 'approve' else 'rejected',
            'reviewComments': review_comments,
            'reviewedBy': reviewed_by,
            'reviewedAt': datetime.now().isoformat()
        })

        # 保存审核结果到历史记录（可选）
        history_key = f'manager_registration_history:{registration_id}'
        redis_client.setex(history_key, 30 * 24 * 3600, json.dumps(registration_data, ensure_ascii=False))

        # 从待审核列表中移除
        redis_client.lrem('pending_manager_registrations', 0, cache_key)

        # 删除原始缓存
        redis_client.delete(cache_key)

        # 更新所有管理员的通知状态
        update_admin_notifications(registration_data, approval_decision, review_comments)

        return JsonResponse({
            'success': True,
            'message': result_message,
            'data': {
                'registrationId': registration_id,
                'decision': approval_decision,
                'reviewedAt': registration_data['reviewedAt']
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        print(f"审核注册申请失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '审核操作失败'
        }, status=500)


def update_admin_notifications(registration_data, decision, comments):
    """更新管理员通知状态"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return False

        admin_usernames = list(Admin.objects.values_list('name', flat=True))

        # 创建审核结果通知 - 使用相同的registrationId确保能正确匹配
        result_message = {
            'type': 'registration_result',
            'id': registration_data['registrationId'],  # 使用相同的ID
            'timestamp': datetime.now().isoformat(),
            'data': {
                'companyName': registration_data['companyName'],
                'decision': decision,
                'reviewComments': comments,
                'reviewedBy': registration_data.get('reviewedBy', 'admin'),
                'username': registration_data.get('username'),  # 添加用户名信息
                'email': registration_data.get('email'),  # 添加邮箱信息
                'unifiedSocialCreditCode': registration_data.get('unifiedSocialCreditCode')  # 添加信用代码
            },
            'message': f'企业注册申请已{decision == "approve" and "通过" or "拒绝"}：{registration_data["companyName"]}'
        }

        # 广播结果到所有管理员
        success_count = 0
        for admin_username in admin_usernames:
            try:
                notification_key = f'admin_notifications:{admin_username}'

                # 先获取现有通知列表
                existing_notifications = redis_client.lrange(notification_key, 0, -1) or []

                # 过滤掉相同ID的待审核通知，避免重复显示
                filtered_notifications = []
                for notification_raw in existing_notifications:
                    try:
                        notification = json.loads(notification_raw)
                        # 如果不是相同ID的registration_request，则保留
                        if not (notification.get('type') == 'registration_request' and
                                notification.get('id') == registration_data['registrationId']):
                            filtered_notifications.append(notification_raw)
                    except:
                        # 保留无法解析的通知
                        filtered_notifications.append(notification_raw)

                # 重新设置通知列表（先删除再重建）
                redis_client.delete(notification_key)

                # 添加结果通知到列表头部
                redis_client.lpush(notification_key, json.dumps(result_message, ensure_ascii=False))

                # 添加其他通知
                if filtered_notifications:
                    redis_client.lpush(notification_key, *filtered_notifications)

                # 设置过期时间
                redis_client.expire(notification_key, 30 * 24 * 3600)

                success_count += 1
                print(f"成功更新管理员 {admin_username} 的通知")

            except Exception as e:
                print(f"更新管理员 {admin_username} 通知失败: {str(e)}")

        print(f"通知更新完成: 成功更新 {success_count}/{len(admin_usernames)} 个管理员账号")
        return success_count > 0

    except Exception as e:
        print(f"更新管理员通知失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@csrf_exempt
@require_http_methods(["GET"])
def get_pending_manager_registrations(request):
    """获取待审核的管理员注册申请列表（管理员专用）"""
    try:
        redis_client = get_redis_client()
        pending_registrations = []

        if redis_client:
            try:
                # 从 Redis 获取待审核列表
                cache_keys = redis_client.lrange("pending_manager_registrations", 0, -1) or []

                for cache_key in cache_keys:
                    try:
                        # redis-py 支持 bytes 形式的 key
                        cache_data = redis_client.get(cache_key)

                        if cache_data:
                            registration_data = _loads_json_safely(cache_data)

                            if registration_data:
                                # 只返回必要信息，不包含密码等敏感字段
                                pending_registrations.append({
                                    "registrationId": registration_data.get("registrationId"),
                                    "companyName": registration_data.get("companyName"),
                                    "legalRepresentative": registration_data.get("legalRepresentative"),
                                    "username": registration_data.get("username"),
                                    "email": registration_data.get("email"),
                                    "submissionTime": registration_data.get("submissionTime"),
                                    "approvalStatus": registration_data.get("approvalStatus"),
                                    "licenseVerified": registration_data.get("licenseVerified", False),
                                    "idVerified": registration_data.get("idVerified", False),
                                    "emailVerified": registration_data.get("emailVerified", False),
                                })
                        else:
                            # 如果缓存数据已过期或不存在，从待审核列表中移除该 key
                            redis_client.lrem("pending_manager_registrations", 0, cache_key)

                    except Exception as e:
                        # 单条数据处理异常不影响整体
                        logger.error(f"处理缓存数据失败: {str(e)}")
                        continue

            except Exception as redis_error:
                logger.error(f"Redis操作失败: {str(redis_error)}")
                # Redis失败时返回空列表

        return JsonResponse({
            "success": True,
            "data": {
                "pendingRegistrations": pending_registrations,
                "totalCount": len(pending_registrations),
            }
        })

    except Exception as e:
        logger.error(f"获取待审核注册列表失败: {str(e)}", exc_info=True)
        return JsonResponse({
            "success": False,
            "message": f"获取待审核列表失败: {str(e)}"
        }, status=500)

def _loads_json_safely(data):
    """安全地加载JSON数据"""
    try:
        if isinstance(data, (bytes, str)):
            return json.loads(data)
        return data
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return None

# 修复get_admin_notifications函数，增加更详细的错误处理
@csrf_exempt
@require_http_methods(["GET"])
def get_admin_notifications(request):
    """获取管理员通知（用于账号管理页面）"""
    try:
        # 从URL参数或session中获取管理员用户名
        admin_name = request.GET.get('admin_name')

        if not admin_name:
            # 尝试从session获取
            admin_info = request.session.get('adminInfo')
            if admin_info:
                admin_name = admin_info.get('username')

        if not admin_name:
            logger.warning("未指定管理员用户名")
            return JsonResponse({
                'success': False,
                'message': '未指定管理员用户名'
            }, status=400)

        # 验证管理员是否存在
        try:
            admin_exists = Admin.objects.filter(name=admin_name).exists()
            if not admin_exists:
                logger.warning(f"管理员账号不存在: {admin_name}")
                return JsonResponse({
                    'success': False,
                    'message': '管理员账号不存在'
                }, status=404)
        except Exception as db_error:
            logger.error(f"数据库查询失败: {str(db_error)}")
            return JsonResponse({
                'success': False,
                'message': '数据库连接失败'
            }, status=500)

        # 获取Redis客户端
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis服务不可用，返回空通知列表")
            return JsonResponse({
                'success': True,
                'data': {
                    'notifications': [],
                    'totalCount': 0,
                    'adminName': admin_name,
                    'note': 'Redis服务不可用'
                }
            })

        # 获取该管理员的通知
        notification_key = f'admin_notifications:{admin_name}'
        try:
            notifications_raw = redis_client.lrange(notification_key, 0, -1) or []
        except Exception as redis_error:
            logger.error(f"Redis查询失败: {str(redis_error)}")
            return JsonResponse({
                'success': True,
                'data': {
                    'notifications': [],
                    'totalCount': 0,
                    'adminName': admin_name,
                    'note': 'Redis查询失败'
                }
            })

        notifications = []
        for notification_raw in notifications_raw:
            try:
                notification = _loads_json_safely(notification_raw)
                if notification:
                    notifications.append(notification)
            except Exception as parse_error:
                logger.error(f"通知解析失败: {str(parse_error)}")
                continue

        logger.info(f"成功获取 {len(notifications)} 个通知，用户: {admin_name}")
        return JsonResponse({
            'success': True,
            'data': {
                'notifications': notifications,
                'totalCount': len(notifications),
                'adminName': admin_name
            }
        })

    except Exception as e:
        logger.error(f"获取管理员通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取通知失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_admin_notifications(request):
    """清理管理员的所有通知（管理员专用）"""
    try:
        data = json.loads(request.body)
        admin_name = data.get('admin_name')

        if not admin_name:
            return JsonResponse({
                'success': False,
                'message': '缺少管理员用户名'
            }, status=400)

        # 验证管理员是否存在
        if not Admin.objects.filter(name=admin_name).exists():
            return JsonResponse({
                'success': False,
                'message': '管理员账号不存在'
            }, status=404)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 清理该管理员的通知
        notification_key = f'admin_notifications:{admin_name}'
        deleted_count = redis_client.delete(notification_key)

        # 同时清理待审核列表中的过期项
        pending_keys = redis_client.lrange("pending_manager_registrations", 0, -1) or []
        cleaned_pending = 0

        for cache_key in pending_keys:
            # 检查对应的缓存是否还存在
            cache_data = redis_client.get(cache_key)
            if not cache_data:
                # 如果缓存不存在，从待审核列表中移除
                redis_client.lrem("pending_manager_registrations", 0, cache_key)
                cleaned_pending += 1

        return JsonResponse({
            'success': True,
            'message': f'清理完成',
            'data': {
                'cleared_notifications': bool(deleted_count),
                'cleaned_pending_items': cleaned_pending
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"清理管理员通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'清理失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_specific_notification(request):
    """删除特定通知"""
    try:
        data = json.loads(request.body)
        admin_name = data.get('admin_name')
        notification_id = data.get('notification_id')

        if not admin_name or not notification_id:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 获取该管理员的所有通知
        notification_key = f'admin_notifications:{admin_name}'
        notifications_raw = redis_client.lrange(notification_key, 0, -1) or []

        # 过滤掉指定ID的通知
        filtered_notifications = []
        removed_count = 0

        for notification_raw in notifications_raw:
            try:
                notification = json.loads(notification_raw)
                if notification.get('id') != notification_id:
                    filtered_notifications.append(notification_raw)
                else:
                    removed_count += 1
            except:
                # 保留无法解析的通知
                filtered_notifications.append(notification_raw)

        # 重新设置通知列表
        if removed_count > 0:
            redis_client.delete(notification_key)
            if filtered_notifications:
                redis_client.lpush(notification_key, *filtered_notifications)
                redis_client.expire(notification_key, 30 * 24 * 3600)  # 重新设置过期时间

        return JsonResponse({
            'success': True,
            'message': f'已删除 {removed_count} 个通知',
            'data': {
                'removed_count': removed_count
            }
        })

    except Exception as e:
        logger.error(f"删除特定通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def save_employee_registration_cache(request):
    """保存员工注册数据到缓存，等待广播给企业管理员"""
    try:
        data = json.loads(request.body)

        # 验证必要字段
        required_fields = [
            'enterpriseName', 'employeeName', 'idNumber',
            'username', 'email', 'password'
        ]

        missing_fields = [field for field in required_fields if not data.get(field)]
        if missing_fields:
            return JsonResponse({
                'success': False,
                'message': f'缺少必要字段: {", ".join(missing_fields)}'
            }, status=400)

        # 检查企业是否存在并获取EID
        enterprise_name = data.get('enterpriseName')
        enterprise = Enterprise.objects.filter(name=enterprise_name).first()

        if not enterprise:
            return JsonResponse({
                'success': False,
                'message': '企业不存在，请确认企业名称是否正确'
            }, status=400)

        enterprise_eid = enterprise.eid

        # 检查用户名是否已存在
        username = data.get('username')
        if Visitor.objects.filter(name=username).exists() or Manager.objects.filter(name=username).exists():
            return JsonResponse({
                'success': False,
                'message': '用户名已存在'
            }, status=400)

        # 生成唯一的注册ID
        registration_id = hashlib.md5(
            f"{username}_{enterprise_name}_{datetime.now().isoformat()}".encode()).hexdigest()[:16]

        # 🔧 修复：确保员工注册文件信息正确处理
        employee_name = data.get('employeeName')

        # 如果没有传入savedFiles，尝试构建默认的文件信息
        saved_files = data.get('savedFiles', {})

        # 如果前端传入了文件路径信息但格式不对，尝试修正
        if not saved_files and data.get('idCardPath'):
            # 构建标准的员工身份证文件信息
            sanitized_employee_name = ''.join(c for c in employee_name if c.isalnum() or c in '._-')
            sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')

            id_filename = f"{sanitized_employee_name}-{sanitized_enterprise_name}-身份证.jpg"
            saved_files[id_filename] = data.get('idCardPath')
            print(f"构建员工文件信息: {id_filename} -> {data.get('idCardPath')}")

        # 准备缓存数据
        cache_data = {
            # 基本信息
            'registrationId': registration_id,
            'registrationType': 'employee',
            'approvalStatus': 'pending_approval',
            'submissionTime': datetime.now().isoformat(),

            # 企业信息
            'enterpriseName': enterprise_name,
            'enterpriseEid': enterprise_eid,

            # 员工信息
            'employeeName': employee_name,
            'idNumber': data.get('idNumber'),
            'username': username,
            'email': data.get('email'),
            'password': data.get('password'),  # 使用明文密码

            # 验证状态
            'idVerified': data.get('idVerified', True),  # 已通过身份证验证
            'emailVerified': data.get('emailVerified', True),  # 已通过邮箱验证

            # 🔧 修复：确保文件信息正确保存
            'savedFiles': saved_files,

            # 审核信息
            'reviewComments': '',
            'reviewedBy': '',
            'reviewedAt': ''
        }

        print(f"员工注册缓存数据:")
        print(f"  注册ID: {registration_id}")
        print(f"  员工姓名: {employee_name}")
        print(f"  企业名称: {enterprise_name}")
        print(f"  文件信息: {saved_files}")

        # 保存到缓存
        cache_key = f'employee_registration:{registration_id}:{username}'

        redis_client = get_redis_client()
        if redis_client:
            # 使用Redis保存
            print(f"保存员工注册信息到Redis，key: {cache_key}")
            redis_client.setex(cache_key, 7 * 24 * 3600, json.dumps(cache_data, ensure_ascii=False))

            # 维护待审核列表
            redis_client.lpush('pending_employee_registrations', cache_key)

            # 广播给符合条件的企业管理员
            broadcast_result = broadcast_to_enterprise_managers(cache_data, enterprise_eid, redis_client)
            print(f"广播结果: {broadcast_result}")

            storage_type = 'redis'
        else:
            # 如果Redis不可用，使用Django缓存
            from django.core.cache import cache
            cache.set(cache_key, cache_data, 7 * 24 * 3600)
            storage_type = 'django_cache'

        return JsonResponse({
            'success': True,
            'message': '员工注册申请已提交，等待企业管理员审核',
            'data': {
                'registrationId': registration_id,
                'storageType': storage_type,
                'estimatedReviewTime': '1-3个工作日',
                'submissionTime': cache_data['submissionTime']
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        print(f"保存员工注册缓存失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({
            'success': False,
            'message': '保存注册信息失败，请重试'
        }, status=500)


# 🔧 同时修复broadcast_to_enterprise_managers函数，确保文件信息正确处理
def broadcast_to_enterprise_managers(employee_data, enterprise_eid, redis_client=None):
    """🔧 修复：改进版的广播函数，正确处理文件信息"""
    try:
        if not redis_client:
            redis_client = get_redis_client()
            if not redis_client:
                return False

        qualified_managers = list(Manager.objects.filter(
            rep='yes',
            eid=enterprise_eid
        ).values_list('name', flat=True))

        if not qualified_managers:
            print("没有找到符合条件的企业管理员")
            return False

        # 🔧 修复：正确处理文件信息
        saved_files = employee_data.get('savedFiles', {})
        file_list = []

        print(f"员工注册广播 - 处理文件信息，savedFiles: {saved_files}")

        # 处理保存的文件信息
        for filename, filepath in saved_files.items():
            # 确保使用相对路径
            if filepath.startswith('/'):
                filepath = filepath.lstrip('/')

            file_info = {
                'filename': filename,
                'path': filepath,
                'type': 'idCard',  # 员工注册主要是身份证
                'registration_type': 'employee'  # 添加注册类型
            }
            file_list.append(file_info)
            print(f"添加文件到广播列表: {file_info}")

        # 如果没有文件信息，尝试构建默认的文件信息
        if not file_list:
            print("WARNING: 没有找到文件信息，尝试构建默认文件信息")
            # 构建默认的员工身份证文件信息
            employee_name = employee_data.get('employeeName', '')
            enterprise_name = employee_data.get('enterpriseName', '')

            if employee_name and enterprise_name:
                sanitized_employee_name = ''.join(c for c in employee_name if c.isalnum() or c in '._-')
                sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')

                # 假设的文件路径
                default_filename = f"{sanitized_employee_name}-{sanitized_enterprise_name}-身份证.jpg"
                default_path = f"{sanitized_employee_name}-{sanitized_enterprise_name}/{sanitized_employee_name}-身份证.jpg"

                file_info = {
                    'filename': default_filename,
                    'path': default_path,
                    'type': 'idCard',
                    'registration_type': 'employee'
                }
                file_list.append(file_info)
                print(f"构建默认文件信息: {file_info}")

        # 创建广播消息
        broadcast_message = {
            'type': 'employee_registration_request',
            'id': employee_data['registrationId'],
            'timestamp': employee_data['submissionTime'],
            'data': {
                'employeeName': employee_data['employeeName'],
                'username': employee_data['username'],
                'email': employee_data['email'],
                'enterpriseName': employee_data['enterpriseName'],
                'enterpriseEid': employee_data['enterpriseEid'],
                'submissionTime': employee_data['submissionTime'],
                'approvalStatus': employee_data['approvalStatus'],
                # 🔧 修复：使用处理后的文件列表
                'files': file_list,
                'idVerified': employee_data.get('idVerified', False)
            },
            'message': f'新的员工注册申请：{employee_data["employeeName"]}申请加入{employee_data["enterpriseName"]}'
        }

        print(f"员工注册广播消息: {broadcast_message}")

        # 广播到企业管理员
        success_count = 0
        for manager_name in qualified_managers:
            try:
                notification_key = f'manager_notifications:{manager_name}'
                redis_client.lpush(notification_key, json.dumps(broadcast_message, ensure_ascii=False))
                redis_client.expire(notification_key, 30 * 24 * 3600)
                success_count += 1
                print(f"成功广播到管理员: {manager_name}")
            except Exception as e:
                print(f"ERROR: 推送到 {manager_name} 失败: {str(e)}")

        print(f"员工注册广播完成，成功推送到 {success_count}/{len(qualified_managers)} 个管理员")
        return success_count > 0

    except Exception as e:
        print(f"ERROR: 广播到企业管理员失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def handle_employee_registration_files(employee_name, enterprise_name, uploaded_files):
    """🔧 新增：处理员工注册文件的辅助函数"""
    saved_files = {}

    # 员工注册主要是身份证文件
    if 'idCard' in uploaded_files:
        # 文件命名：员工姓名-企业名-身份证.jpg
        sanitized_employee_name = ''.join(c for c in employee_name if c.isalnum() or c in '._-')
        sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')

        id_filename = f"{sanitized_employee_name}-{sanitized_enterprise_name}-身份证.jpg"
        saved_files[id_filename] = uploaded_files['idCard']['path']

    return saved_files


@csrf_exempt
@require_http_methods(["POST"])
def approve_employee_registration(request):
    """企业管理员审核员工注册申请"""
    try:
        data = json.loads(request.body)
        registration_id = data.get('registrationId')
        approval_decision = data.get('decision')  # 'approve' 或 'reject'
        review_comments = data.get('reviewComments', '')
        reviewed_by = data.get('reviewedBy', 'manager')

        if not registration_id or not approval_decision:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 查找注册申请
        cache_keys = redis_client.keys(f'employee_registration:{registration_id}:*')
        if not cache_keys:
            return JsonResponse({
                'success': False,
                'message': '未找到该注册申请'
            }, status=404)

        cache_key = cache_keys[0]
        cache_data = redis_client.get(cache_key)

        if not cache_data:
            return JsonResponse({
                'success': False,
                'message': '注册申请已过期'
            }, status=404)

        registration_data = json.loads(cache_data)

        if approval_decision == 'approve':
            # 审核通过，创建员工账户 - 修改为写入Manager表
            try:
                # 创建Manager记录，rep='no'（区别于企业注册的'yes'）
                manager = Manager.objects.create(
                    name=registration_data['username'],
                    password=registration_data['password'],  # 使用明文密码
                    rep='no',  # 员工注册默认设置为no
                    eid=registration_data['enterpriseEid']  # 关联企业EID
                )

                # 创建验证记录
                Verification.objects.create(
                    name=registration_data['username'],
                    email=registration_data['email']
                )

                result_message = '员工注册申请已通过，员工账户已创建'

            except Exception as e:
                print(f"创建员工账户失败: {str(e)}")
                return JsonResponse({
                    'success': False,
                    'message': '创建员工账户失败'
                }, status=500)
        else:
            result_message = '员工注册申请已拒绝'

        # 更新审核状态
        registration_data.update({
            'approvalStatus': 'approved' if approval_decision == 'approve' else 'rejected',
            'reviewComments': review_comments,
            'reviewedBy': reviewed_by,
            'reviewedAt': datetime.now().isoformat()
        })

        # 保存审核结果到历史记录
        history_key = f'employee_registration_history:{registration_id}'
        redis_client.setex(history_key, 30 * 24 * 3600, json.dumps(registration_data, ensure_ascii=False))

        # 从待审核列表中移除
        redis_client.lrem('pending_employee_registrations', 0, cache_key)

        # 删除原始缓存
        redis_client.delete(cache_key)

        # 更新企业管理员的通知状态
        update_manager_notifications(registration_data, approval_decision, review_comments)

        return JsonResponse({
            'success': True,
            'message': result_message,
            'data': {
                'registrationId': registration_id,
                'decision': approval_decision,
                'reviewedAt': registration_data['reviewedAt']
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        print(f"审核员工注册申请失败: {str(e)}")
        return JsonResponse({
            'success': False,
            'message': '审核操作失败'
        }, status=500)


def update_manager_notifications(registration_data, decision, comments):
    """更新企业管理员通知状态"""
    try:
        redis_client = get_redis_client()
        if not redis_client:
            return False

        # 获取符合条件的企业管理员
        enterprise_eid = registration_data['enterpriseEid']
        qualified_managers = list(Manager.objects.filter(
            rep='yes',
            eid=enterprise_eid
        ).values_list('name', flat=True))

        # 创建审核结果通知
        result_message = {
            'type': 'employee_registration_result',
            'id': registration_data['registrationId'],
            'timestamp': datetime.now().isoformat(),
            'data': {
                'employeeName': registration_data['employeeName'],
                'username': registration_data['username'],
                'enterpriseName': registration_data['enterpriseName'],
                'decision': decision,
                'reviewComments': comments,
                'reviewedBy': registration_data.get('reviewedBy', 'manager')
            },
            'message': f'员工注册申请已{decision == "approve" and "通过" or "拒绝"}：{registration_data["employeeName"]}'
        }

        # 广播结果到所有符合条件的企业管理员
        success_count = 0
        for manager_name in qualified_managers:
            try:
                notification_key = f'manager_notifications:{manager_name}'

                # 获取现有通知列表
                existing_notifications = redis_client.lrange(notification_key, 0, -1) or []

                # 过滤掉相同ID的待审核通知
                filtered_notifications = []
                for notification_raw in existing_notifications:
                    try:
                        notification = json.loads(notification_raw)
                        if not (notification.get('type') == 'employee_registration_request' and
                                notification.get('id') == registration_data['registrationId']):
                            filtered_notifications.append(notification_raw)
                    except:
                        filtered_notifications.append(notification_raw)

                # 重新设置通知列表
                redis_client.delete(notification_key)

                # 添加结果通知到列表头部
                redis_client.lpush(notification_key, json.dumps(result_message, ensure_ascii=False))

                # 添加其他通知
                if filtered_notifications:
                    redis_client.lpush(notification_key, *filtered_notifications)

                # 设置过期时间
                redis_client.expire(notification_key, 30 * 24 * 3600)

                success_count += 1
                print(f"成功更新企业管理员 {manager_name} 的通知")

            except Exception as e:
                print(f"更新企业管理员 {manager_name} 通知失败: {str(e)}")

        print(f"通知更新完成: 成功更新 {success_count}/{len(qualified_managers)} 个企业管理员账号")
        return success_count > 0

    except Exception as e:
        print(f"更新企业管理员通知失败: {str(e)}")
        return False


@csrf_exempt
@require_http_methods(["GET"])
def get_manager_notifications(request):
    """获取企业管理员的员工注册通知"""
    try:
        # 从URL参数获取管理员用户名
        manager_name = request.GET.get('manager_name')

        if not manager_name:
            return JsonResponse({
                'success': False,
                'message': '未指定管理员用户名'
            }, status=400)

        # 验证管理员是否存在且有权限
        try:
            manager = Manager.objects.filter(name=manager_name, rep='yes').first()
            if not manager:
                return JsonResponse({
                    'success': False,
                    'message': '管理员账号不存在或无权限'
                }, status=404)
        except Exception as db_error:
            logger.error(f"数据库查询失败: {str(db_error)}")
            return JsonResponse({
                'success': False,
                'message': '数据库连接失败'
            }, status=500)

        # 获取Redis客户端
        redis_client = get_redis_client()
        if not redis_client:
            logger.warning("Redis服务不可用，返回空通知列表")
            return JsonResponse({
                'success': True,
                'data': {
                    'notifications': [],
                    'totalCount': 0,
                    'managerName': manager_name,
                    'note': 'Redis服务不可用'
                }
            })

        # 获取该管理员的员工注册通知
        notification_key = f'manager_notifications:{manager_name}'
        try:
            notifications_raw = redis_client.lrange(notification_key, 0, -1) or []
        except Exception as redis_error:
            logger.error(f"Redis查询失败: {str(redis_error)}")
            return JsonResponse({
                'success': True,
                'data': {
                    'notifications': [],
                    'totalCount': 0,
                    'managerName': manager_name,
                    'note': 'Redis查询失败'
                }
            })

        notifications = []
        for notification_raw in notifications_raw:
            try:
                notification = _loads_json_safely(notification_raw)
                if notification:
                    notifications.append(notification)
            except Exception as parse_error:
                logger.error(f"通知解析失败: {str(parse_error)}")
                continue

        logger.info(f"成功获取 {len(notifications)} 个员工注册通知，管理员: {manager_name}")
        return JsonResponse({
            'success': True,
            'data': {
                'notifications': notifications,
                'totalCount': len(notifications),
                'managerName': manager_name
            }
        })

    except Exception as e:
        logger.error(f"获取管理员通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'获取通知失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_manager_notifications(request):
    """清理企业管理员的所有员工注册通知"""
    try:
        data = json.loads(request.body)
        manager_name = data.get('manager_name')

        if not manager_name:
            return JsonResponse({
                'success': False,
                'message': '缺少管理员用户名'
            }, status=400)

        # 验证管理员是否存在且有权限
        manager = Manager.objects.filter(name=manager_name, rep='yes').first()
        if not manager:
            return JsonResponse({
                'success': False,
                'message': '管理员账号不存在或无权限'
            }, status=404)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 清理该管理员的通知
        notification_key = f'manager_notifications:{manager_name}'
        deleted_count = redis_client.delete(notification_key)

        # 同时清理待审核列表中的过期项
        pending_keys = redis_client.lrange("pending_employee_registrations", 0, -1) or []
        cleaned_pending = 0

        for cache_key in pending_keys:
            # 检查对应的缓存是否还存在
            cache_data = redis_client.get(cache_key)
            if not cache_data:
                # 如果缓存不存在，从待审核列表中移除
                redis_client.lrem("pending_employee_registrations", 0, cache_key)
                cleaned_pending += 1

        return JsonResponse({
            'success': True,
            'message': f'清理完成',
            'data': {
                'cleared_notifications': bool(deleted_count),
                'cleaned_pending_items': cleaned_pending
            }
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"清理管理员通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'清理失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def clear_specific_manager_notification(request):
    """删除企业管理员的特定员工注册通知"""
    try:
        data = json.loads(request.body)
        manager_name = data.get('manager_name')
        notification_id = data.get('notification_id')

        if not manager_name or not notification_id:
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 验证管理员权限
        manager = Manager.objects.filter(name=manager_name, rep='yes').first()
        if not manager:
            return JsonResponse({
                'success': False,
                'message': '管理员账号不存在或无权限'
            }, status=404)

        redis_client = get_redis_client()
        if not redis_client:
            return JsonResponse({
                'success': False,
                'message': 'Redis服务不可用'
            }, status=503)

        # 获取该管理员的所有通知
        notification_key = f'manager_notifications:{manager_name}'
        notifications_raw = redis_client.lrange(notification_key, 0, -1) or []

        # 过滤掉指定ID的通知
        filtered_notifications = []
        removed_count = 0

        for notification_raw in notifications_raw:
            try:
                notification = json.loads(notification_raw)
                if notification.get('id') != notification_id:
                    filtered_notifications.append(notification_raw)
                else:
                    removed_count += 1
            except:
                # 保留无法解析的通知
                filtered_notifications.append(notification_raw)

        # 重新设置通知列表
        if removed_count > 0:
            redis_client.delete(notification_key)
            if filtered_notifications:
                redis_client.lpush(notification_key, *filtered_notifications)
                redis_client.expire(notification_key, 30 * 24 * 3600)  # 重新设置过期时间

        return JsonResponse({
            'success': True,
            'message': f'已删除 {removed_count} 个通知',
            'data': {
                'removed_count': removed_count
            }
        })

    except Exception as e:
        logger.error(f"删除特定管理员通知失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': f'删除失败: {str(e)}'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def change_password(request):
    """更改用户密码"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        user_type = data.get('userType')
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')

        if not all([username, user_type, old_password, new_password]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 根据用户类型选择对应的模型
        user_model = None
        if user_type == 'visitor':
            user_model = Visitor
        elif user_type == 'manager':
            user_model = Manager
        elif user_type == 'admin':
            user_model = Admin
        else:
            return JsonResponse({
                'success': False,
                'message': '无效的用户类型'
            }, status=400)

        # 查找用户
        try:
            user = user_model.objects.get(name=username)
        except user_model.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '用户不存在'
            }, status=404)

        # 验证旧密码（明文比较）
        if user.password != old_password:
            return JsonResponse({
                'success': False,
                'message': '当前密码错误'
            }, status=400)

        # 更新密码（明文存储）
        user.password = new_password
        user.save()

        return JsonResponse({
            'success': True,
            'message': '密码更新成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"更改密码失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '更改密码失败，请稍后重试'
        }, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def check_security_status(request):
    """检查用户是否已设置密保问题"""
    try:
        username = request.GET.get('username')

        if not username:
            return JsonResponse({
                'success': False,
                'message': '缺少用户名参数'
            }, status=400)

        # 检查用户是否在security_problem表中存在
        try:
            security_record = SecurityProblem.objects.get(name=username)
            return JsonResponse({
                'success': True,
                'hasSecurityQuestions': True,
                'questions': {
                    'question1': '您的出生城市是？',
                    'question2': '您最喜欢的颜色是？'
                }
            })
        except SecurityProblem.DoesNotExist:
            return JsonResponse({
                'success': True,
                'hasSecurityQuestions': False
            })

    except Exception as e:
        logger.error(f"检查密保状态失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '检查密保状态失败'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def set_security_questions(request):
    """设置密保问题"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        answer1 = data.get('answer1')
        answer2 = data.get('answer2')

        if not all([username, answer1, answer2]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 检查用户是否已设置密保
        if SecurityProblem.objects.filter(name=username).exists():
            return JsonResponse({
                'success': False,
                'message': '您已设置密保问题，请使用重置功能'
            }, status=400)

        # 创建密保记录
        SecurityProblem.objects.create(
            name=username,
            answer1=answer1,
            answer2=answer2
        )

        return JsonResponse({
            'success': True,
            'message': '密保问题设置成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"设置密保问题失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '设置密保问题失败，请稍后重试'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_security_answers(request):
    """验证密保答案"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        answer1 = data.get('answer1')
        answer2 = data.get('answer2')

        if not all([username, answer1, answer2]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 获取用户的密保记录
        try:
            security_record = SecurityProblem.objects.get(name=username)
        except SecurityProblem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '未找到密保设置'
            }, status=404)

        # 验证答案（区分大小写）
        if security_record.answer1 == answer1 and security_record.answer2 == answer2:
            return JsonResponse({
                'success': True,
                'message': '验证成功'
            })
        else:
            return JsonResponse({
                'success': False,
                'message': '密保答案错误，请检查后重试'
            }, status=400)

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"验证密保答案失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '验证失败，请稍后重试'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reset_security_questions(request):
    """重置密保问题"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        old_answer1 = data.get('oldAnswer1')
        old_answer2 = data.get('oldAnswer2')
        new_answer1 = data.get('newAnswer1')
        new_answer2 = data.get('newAnswer2')

        if not all([username, old_answer1, old_answer2, new_answer1, new_answer2]):
            return JsonResponse({
                'success': False,
                'message': '缺少必要参数'
            }, status=400)

        # 获取用户的密保记录
        try:
            security_record = SecurityProblem.objects.get(name=username)
        except SecurityProblem.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': '未找到密保设置'
            }, status=404)

        # 验证旧答案
        if security_record.answer1 != old_answer1 or security_record.answer2 != old_answer2:
            return JsonResponse({
                'success': False,
                'message': '原密保答案错误'
            }, status=400)

        # 更新答案
        security_record.answer1 = new_answer1
        security_record.answer2 = new_answer2
        security_record.save()

        return JsonResponse({
            'success': True,
            'message': '密保问题重置成功'
        })

    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'message': '无效的JSON格式'
        }, status=400)
    except Exception as e:
        logger.error(f"重置密保问题失败: {str(e)}", exc_info=True)
        return JsonResponse({
            'success': False,
            'message': '重置密保问题失败，请稍后重试'
        }, status=500)


def handle_enterprise_registration_files(ocr_data, uploaded_files):

    saved_files = {}

    # 从OCR数据中获取信息
    company_name = ocr_data.get('companyName', '')
    credit_code = ocr_data.get('unifiedSocialCreditCode', '')
    legal_rep_name = ocr_data.get('legalRepresentative', '')

    # 营业执照文件命名：企业名称-营业执照.jpg
    if 'license' in uploaded_files:
        license_filename = f"{company_name}-营业执照.jpg"
        saved_files[license_filename] = uploaded_files['license']['path']

    # 身份证文件命名：企业名称-法人姓名-身份证.jpg
    if 'idCard' in uploaded_files:
        id_filename = f"{company_name}-{legal_rep_name}-身份证.jpg"
        saved_files[id_filename] = uploaded_files['idCard']['path']

    return saved_files

def handle_employee_registration_files(employee_name, enterprise_name, uploaded_files):
    """处理员工注册文件，返回保存后的文件信息"""
    saved_files = {}

    if 'idCard' in uploaded_files:
        # 文件命名和路径处理
        sanitized_employee_name = ''.join(c for c in employee_name if c.isalnum() or c in '._-')
        sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')

        # 创建员工文件夹：员工姓名-企业名
        folder_name = f"{sanitized_employee_name}-{sanitized_enterprise_name}"
        id_filename = f"{sanitized_employee_name}-身份证.jpg"

        # ✅ 使用正确的路径：相对于 EMPLOYEE_ARCHIVES_ROOT
        relative_path = os.path.join(folder_name, id_filename)
        saved_files[id_filename] = relative_path

    return saved_files


@csrf_exempt
@require_http_methods(["GET"])
def download_registration_file(request):
    """下载注册相关文件（强制下载）"""
    try:
        file_path = request.GET.get('file_path')
        file_name = request.GET.get('file_name')
        user_type = request.GET.get('user_type')
        username = request.GET.get('username')
        registration_type = request.GET.get('registration_type', 'enterprise')  # 默认为企业

        if not all([file_path, file_name, user_type, username]):
            return JsonResponse({'success': False, 'message': '参数不完整'}, status=400)

        # 验证用户权限
        if user_type == 'admin':
            if not Admin.objects.filter(name=username).exists():
                return JsonResponse({'success': False, 'message': '无权限访问'}, status=403)
        elif user_type == 'manager':
            if not Manager.objects.filter(name=username, rep='yes').exists():
                return JsonResponse({'success': False, 'message': '无权限访问'}, status=403)
        else:
            return JsonResponse({'success': False, 'message': '无效的用户类型'}, status=400)

        # 构建完整的文件路径
        full_path = build_file_path(file_path, file_name, registration_type)

        # 调试输出
        print(f"下载文件调试信息:")
        print(f"  原始路径: {file_path}")
        print(f"  文件名: {file_name}")
        print(f"  完整路径: {full_path}")
        print(f"  文件存在: {os.path.exists(full_path)}")

        # 检查文件是否存在
        if not os.path.exists(full_path):
            # 尝试其他可能的路径
            possible_paths = [
                os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, file_path),
                os.path.join(settings.MEDIA_ROOT, file_path),
                file_path  # 原始路径
            ]

            for test_path in possible_paths:
                print(f"  尝试路径: {test_path}")
                if os.path.exists(test_path):
                    full_path = test_path
                    break
            else:
                return JsonResponse({'success': False, 'message': f'文件不存在: {file_path}'}, status=404)

        # 返回文件（强制下载）
        response = FileResponse(
            open(full_path, 'rb'),
            as_attachment=True,  # 强制下载
            filename=file_name
        )

        # 添加必要的头信息
        response['Content-Disposition'] = f'attachment; filename="{file_name}"'
        return response

    except Exception as e:
        logger.error(f"下载文件失败: {str(e)}")
        return JsonResponse({'success': False, 'message': f'下载失败: {str(e)}'}, status=500)


# 在 views.py 中找到 preview_registration_file 函数，替换为以下版本

@csrf_exempt
@require_http_methods(["GET"])
def preview_registration_file(request):
    """预览注册相关文件（在浏览器中显示）"""
    try:
        file_path = request.GET.get('file_path')
        file_name = request.GET.get('file_name')
        user_type = request.GET.get('user_type')
        username = request.GET.get('username')
        registration_type = request.GET.get('registration_type', 'enterprise')

        # 修改调试信息，移除特殊字符
        print("=== Preview File Debug Info ===")
        print("Request parameters:")
        print(f"  file_path: {file_path}")
        print(f"  file_name: {file_name}")
        print(f"  user_type: {user_type}")
        print(f"  username: {username}")
        print(f"  registration_type: {registration_type}")

        if not all([file_path, file_name, user_type, username]):
            missing_params = [k for k, v in {'file_path': file_path, 'file_name': file_name, 'user_type': user_type,
                                             'username': username}.items() if not v]
            print(f"Missing parameters: {missing_params}")
            return JsonResponse({'success': False, 'message': '参数不完整'}, status=400)

        # 权限验证
        if user_type == 'admin':
            if not Admin.objects.filter(name=username).exists():
                print(f"Admin permission denied: {username}")
                return JsonResponse({'success': False, 'message': '无权限访问'}, status=403)
        elif user_type == 'manager':
            if not Manager.objects.filter(name=username, rep='yes').exists():
                print(f"Manager permission denied: {username}")
                return JsonResponse({'success': False, 'message': '无权限访问'}, status=403)
        else:
            print(f"Invalid user type: {user_type}")
            return JsonResponse({'success': False, 'message': '无效的用户类型'}, status=400)

        # 构建文件路径
        full_path = build_file_path(file_path, file_name, registration_type)
        print(f"Full path built: {full_path}")

        # 检查文件是否存在
        if not os.path.exists(full_path):
            print("File not found, trying alternative paths...")

            # 尝试其他可能的路径
            possible_paths = [
                os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, file_path),
                os.path.join(settings.MEDIA_ROOT, file_path),
                file_path,
                os.path.join(settings.BASE_DIR, file_path)
            ]

            for i, test_path in enumerate(possible_paths):
                print(f"  Trying path {i + 1}: {test_path}")
                print(f"  Path exists: {os.path.exists(test_path)}")
                if os.path.exists(test_path):
                    full_path = test_path
                    print(f"  [OK] Found file at: {test_path}")
                    break
            else:
                print("File not found in any path")
                # 列出目录内容帮助调试
                try:
                    parent_dir = os.path.dirname(os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, file_path))
                    if os.path.exists(parent_dir):
                        files_in_dir = os.listdir(parent_dir)
                        print(f"Parent directory contents ({parent_dir}): {files_in_dir}")
                except Exception as e:
                    print(f"Cannot list parent directory: {e}")

                return JsonResponse({'success': False, 'message': f'文件不存在: {file_path}'}, status=404)

        # 检查文件大小
        try:
            file_size = os.path.getsize(full_path)
            print(f"File size: {file_size} bytes")
            if file_size == 0:
                print("WARNING: File size is 0")
        except Exception as e:
            print(f"Failed to get file size: {e}")

        # 检查是否为图片文件
        if not is_image_file(file_name):
            print(f"File is not an image: {file_name}")
            return JsonResponse({'success': False, 'message': '只支持预览图片文件'}, status=400)

        # 获取文件的MIME类型
        import mimetypes
        content_type, encoding = mimetypes.guess_type(full_path)
        print(f"Detected MIME type: {content_type}")
        print(f"Encoding: {encoding}")

        if not content_type:
            # 根据文件扩展名手动设置
            ext = os.path.splitext(file_name)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.bmp': 'image/bmp',
                '.webp': 'image/webp'
            }
            content_type = mime_types.get(ext, 'application/octet-stream')
            print(f"Manually set MIME type: {content_type}")

        # 尝试读取文件头部检查文件完整性
        try:
            with open(full_path, 'rb') as f:
                header = f.read(10)
                print(f"File header (first 10 bytes): {header.hex()}")
        except Exception as e:
            print(f"Failed to read file header: {e}")

        # 返回文件
        try:
            # 使用二进制模式打开文件
            with open(full_path, 'rb') as f:
                file_data = f.read()

            # 创建HttpResponse而不是FileResponse，避免编码问题
            from django.http import HttpResponse
            response = HttpResponse(file_data, content_type=content_type)

            # 添加必要的HTTP头
            response['Content-Disposition'] = f'inline; filename="{file_name}"'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'

            print("[OK] Successfully created file response")
            print(f"Response headers: Content-Type={content_type}")
            print(f"Response headers: Content-Disposition=inline; filename=\"{file_name}\"")

            return response

        except Exception as e:
            print(f"Failed to create response: {e}")
            return JsonResponse({'success': False, 'message': f'创建响应失败: {str(e)}'}, status=500)

    except Exception as e:
        print(f"Preview file exception: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': f'预览失败: {str(e)}'}, status=500)


def build_file_path(file_path, file_name, registration_type=None):
    """构建完整的文件路径，使用 settings.py 中正确的路径配置"""
    # 去掉前导斜杠
    if file_path.startswith('/'):
        file_path = file_path.lstrip('/')

    # 如果路径已经包含目录信息，直接使用
    if 'enterprise_archives' in file_path:
        file_path = file_path.replace('enterprise_archives/', '')
        return os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, file_path)

    if 'employee_archives' in file_path:
        file_path = file_path.replace('employee_archives/', '')
        return os.path.join(settings.EMPLOYEE_ARCHIVES_ROOT, file_path)

    # 根据文件名和注册类型判断路径
    if registration_type == 'employee' or '员工' in file_name:
        # ❌ 原来的代码：使用 MEDIA_ROOT
        # ✅ 修正：应该优先使用 EMPLOYEE_ARCHIVES_ROOT
        return os.path.join(settings.EMPLOYEE_ARCHIVES_ROOT, file_path)
    elif '营业执照' in file_name or '法人身份证' in file_name or '法定代表人' in file_name:
        return os.path.join(settings.ENTERPRISE_ARCHIVES_ROOT, file_path)
    else:
        # 默认情况（如人脸识别文件）使用MEDIA_ROOT
        return os.path.join(settings.MEDIA_ROOT, file_path)


def is_image_file(filename):
    """检查是否为图片文件"""
    if not filename:
        return False
    image_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    extension = filename.lower()
    for ext in image_extensions:
        if extension.endswith(ext):
            return True
    return False


@csrf_exempt
def save_registration_file(request):
    """统一的文件保存方法"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': '只支持POST请求'}, status=405)

    file_type = request.POST.get('file_type')  # 'license', 'idCard', 'employee_idCard'
    registration_type = request.POST.get('registration_type')  # 'enterprise' 或 'employee'

    if not file_type or not registration_type:
        return JsonResponse({'success': False, 'message': '缺少文件类型或注册类型参数'}, status=400)

    # 检查文件
    if 'file' not in request.FILES:
        return JsonResponse({'success': False, 'message': '未上传文件'}, status=400)

    uploaded_file = request.FILES['file']

    # 准备保存路径
    if registration_type == 'enterprise':
        company_name = request.POST.get('company_name')
        credit_code = request.POST.get('credit_code', '')
        legal_rep_name = request.POST.get('legal_rep_name', '')

        if not company_name:
            return JsonResponse({'success': False, 'message': '缺少企业名称'}, status=400)

        # 清理文件名中的特殊字符
        sanitized_company_name = ''.join(c for c in company_name if c.isalnum() or c in '._-')
        sanitized_credit_code = ''.join(c for c in credit_code if c.isalnum() or c in '._-')

        # 创建企业文件夹
        folder_name = f"{sanitized_company_name}-{sanitized_credit_code}"
        base_dir = settings.ENTERPRISE_ARCHIVES_ROOT

    elif registration_type == 'employee':
        employee_name = request.POST.get('employee_name')
        enterprise_name = request.POST.get('enterprise_name')

        if not employee_name or not enterprise_name:
            return JsonResponse({'success': False, 'message': '缺少员工或企业名称'}, status=400)

        # 清理文件名中的特殊字符
        sanitized_employee_name = ''.join(c for c in employee_name if c.isalnum() or c in '._-')
        sanitized_enterprise_name = ''.join(c for c in enterprise_name if c.isalnum() or c in '._-')

        # 创建员工文件夹
        folder_name = f"{sanitized_employee_name}-{sanitized_enterprise_name}"
        base_dir = settings.EMPLOYEE_ARCHIVES_ROOT if hasattr(settings,
                                                              'EMPLOYEE_ARCHIVES_ROOT') else settings.MEDIA_ROOT

    else:
        return JsonResponse({'success': False, 'message': '无效的注册类型'}, status=400)

    # 创建目录
    full_dir_path = os.path.join(base_dir, folder_name)
    os.makedirs(full_dir_path, exist_ok=True)

    # 生成文件名
    file_extension = os.path.splitext(uploaded_file.name)[1]
    if file_type == 'license':
        filename = f"营业执照{file_extension}"
    elif file_type == 'idCard':
        if registration_type == 'enterprise':
            filename = f"法人身份证{file_extension}"
        else:
            filename = f"员工身份证{file_extension}"
    else:
        filename = uploaded_file.name

    # 完整文件路径
    file_path = os.path.join(full_dir_path, filename)

    # 保存文件
    with open(file_path, 'wb+') as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    # 返回相对路径用于存储在缓存中
    relative_path = os.path.join(folder_name, filename)

    return JsonResponse({
        'success': True,
        'message': '文件保存成功',
        'data': {
            'file_path': relative_path,
            'file_type': file_type,
            'folder_name': folder_name,
            'registration_type': registration_type
        }
    })