from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.db import transaction
from django.core.mail import send_mail
from django.conf import settings
import json
import redis
import random
import re
from .models import Visitor, Manager, Admin, Verification, SecurityProblem

# Redis 客户端
redis_client = redis.Redis(
    host=settings.REDIS_HOST,
    port=settings.REDIS_PORT,
    decode_responses=True
)


@csrf_exempt
@require_http_methods(["POST"])
def visitor_login(request):
    """访客登录"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        if not username or not password:
            return JsonResponse({'success': False, 'message': '用户名和密码不能为空'}, status=400)

        visitor = Visitor.objects.filter(name=username, password=password).first()

        if visitor:
            return JsonResponse({'success': True, 'message': '登录成功'})
        else:
            return JsonResponse({'success': False, 'message': '用户名或密码错误'}, status=401)
    except Exception as e:
        return JsonResponse({'success': False, 'message': f'服务器错误: {str(e)}'}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def manager_login(request):
    """经理登录"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        manager = Manager.objects.filter(name=username, password=password).first()

        if manager:
            return JsonResponse({'success': True, 'message': '登录成功'})
        else:
            return JsonResponse({'success': False, 'message': '用户名或密码错误'}, status=401)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def admin_login(request):
    """管理员登录"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')

        admin = Admin.objects.filter(name=username, password=password).first()

        if admin:
            return JsonResponse({'success': True, 'message': '登录成功'})
        else:
            return JsonResponse({'success': False, 'message': '用户名或密码错误'}, status=401)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def visitor_register(request):
    """访客注册"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')

        # 验证参数
        if not all([username, email, password]):
            return JsonResponse({'success': False, 'message': '所有字段都是必填的'}, status=400)

        # 验证用户名长度
        if len(username) < 3 or len(username) > 20:
            return JsonResponse({'success': False, 'message': '用户名长度应在3-20个字符之间'}, status=400)

        # 验证密码格式
        password_regex = r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]).{8,16}$'
        if not re.match(password_regex, password):
            return JsonResponse({'success': False, 'message': '密码格式不符合要求'}, status=400)

        # 验证邮箱格式
        email_regex = r'^[^\s@]+@[^\s@]+\.[^\s@]+$'
        if not re.match(email_regex, email):
            return JsonResponse({'success': False, 'message': '邮箱格式不正确'}, status=400)

        # 检查用户名是否存在
        if Visitor.objects.filter(name=username).exists():
            return JsonResponse({'success': False, 'message': '用户名已存在'}, status=400)

        # 检查邮箱是否存在
        if Verification.objects.filter(email=email).exists():
            return JsonResponse({'success': False, 'message': '邮箱已被使用'}, status=400)

        # 使用事务保证数据一致性
        with transaction.atomic():
            # 创建访客
            visitor = Visitor.objects.create(
                name=username,
                password=password
            )

            # 创建验证记录
            verification = Verification.objects.create(
                name=username,
                email=email
            )

        return JsonResponse({'success': True, 'message': '注册成功'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


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

        # 存储到Redis（5分钟过期）
        redis_client.setex(f'verify_code:{email}', 300, code)

        # 发送邮件
        html_message = f"""
        <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif;">
            <div style="background-color: #667eea; padding: 30px; text-align: center;">
                <h1 style="color: white; margin: 0;">厨房检测系统</h1>
            </div>
            <div style="background-color: #f9f9f9; padding: 40px;">
                <h2 style="color: #333; text-align: center;">邮箱验证码</h2>
                <p style="color: #666; text-align: center; font-size: 16px;">
                    您正在进行邮箱验证，请使用以下验证码：
                </p>
                <div style="background-color: white; border: 2px solid #667eea; border-radius: 8px; padding: 20px; margin: 20px 0; text-align: center;">
                    <span style="font-size: 36px; font-weight: bold; color: #667eea; letter-spacing: 5px;">{code}</span>
                </div>
                <p style="color: #999; text-align: center; font-size: 14px;">
                    验证码有效期为5分钟，请尽快使用。<br>
                    如果这不是您的操作，请忽略此邮件。
                </p>
            </div>
        </div>
        """

        send_mail(
            subject='【厨房检测系统】邮箱验证码',
            message=f'您的验证码是：{code}',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            html_message=html_message,
            fail_silently=False,
        )

        return JsonResponse({'success': True, 'message': '验证码已发送'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_code(request):
    """验证邮箱验证码"""
    try:
        data = json.loads(request.body)
        email = data.get('email')
        code = data.get('code')

        stored_code = redis_client.get(f'verify_code:{email}')

        if not stored_code:
            return JsonResponse({'success': False, 'message': '验证码已过期'}, status=400)

        if stored_code == str(code):
            redis_client.delete(f'verify_code:{email}')
            return JsonResponse({'success': True, 'message': '验证成功'})
        else:
            return JsonResponse({'success': False, 'message': '验证码错误'}, status=400)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def get_security_questions(request):
    """获取密保问题"""
    username = request.GET.get('username')

    if not username:
        return JsonResponse({'success': False, 'message': '用户名不能为空'}, status=400)

    try:
        security = SecurityProblem.objects.filter(name=username).first()
        if security:
            questions = []
            if security.problem1:
                questions.append(security.problem1)
            if security.problem2:
                questions.append(security.problem2)
            return JsonResponse({'success': True, 'questions': questions})
        else:
            return JsonResponse({'success': False, 'message': '未找到密保问题'}, status=404)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def verify_security_answers(request):
    """验证密保答案"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        answers = data.get('answers')

        if not username or not answers:
            return JsonResponse({'success': False, 'message': '参数不完整'}, status=400)

        security = SecurityProblem.objects.filter(name=username).first()
        if not security:
            return JsonResponse({'success': False, 'message': '未找到密保信息'}, status=404)

        correct_answers = []
        if security.answer1:
            correct_answers.append(security.answer1)
        if security.answer2:
            correct_answers.append(security.answer2)

        if len(answers) == len(correct_answers) and all(a == b for a, b in zip(answers, correct_answers)):
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'message': '答案错误'})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def reset_password(request):
    """重置密码"""
    try:
        data = json.loads(request.body)
        username = data.get('username')
        user_type = data.get('userType')
        new_password = data.get('newPassword')

        if not all([username, user_type, new_password]):
            return JsonResponse({'success': False, 'message': '参数不完整'}, status=400)

        # 验证密码格式
        password_regex = r'^(?=.*[a-zA-Z])(?=.*\d)(?=.*[!@#$%^&*()_+\-=\[\]{};\':"\\|,.<>\/?]).{8,16}$'
        if not re.match(password_regex, new_password):
            return JsonResponse({'success': False, 'message': '密码格式不符合要求'}, status=400)

        # 根据用户类型更新密码
        if user_type == 'visitor':
            updated = Visitor.objects.filter(name=username).update(password=new_password)
        elif user_type == 'manager':
            updated = Manager.objects.filter(name=username).update(password=new_password)
        elif user_type == 'admin':
            updated = Admin.objects.filter(name=username).update(password=new_password)
        else:
            return JsonResponse({'success': False, 'message': '无效的用户类型'}, status=400)

        if updated:
            return JsonResponse({'success': True, 'message': '密码修改成功'})
        else:
            return JsonResponse({'success': False, 'message': '用户不存在'}, status=404)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def check_username(request):
    """检查用户名是否存在"""
    try:
        data = json.loads(request.body)
        username = data.get('username')

        if not username:
            return JsonResponse({'success': False, 'message': '用户名不能为空'}, status=400)

        exists = (
                Visitor.objects.filter(name=username).exists() or
                Verification.objects.filter(name=username).exists()
        )

        return JsonResponse({'success': True, 'exists': exists})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)