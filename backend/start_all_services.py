#!/usr/bin/env python
"""
启动所有必需的服务
"""
import subprocess
import time
import os
import sys
import signal
import atexit
import requests
import platform
from pathlib import Path
from dotenv import load_dotenv

# 1. 在脚本最开始加载 .env
load_dotenv()

# 2. 从环境变量获取端口，如果获取不到则使用默认值
DJANGO_PORT = int(os.getenv('PYTHON_APP_PORT', 8000)) 
REDIS_PORT = int(os.getenv('REDIS_PORT', 6379))
JANUS_PORT = int(os.getenv('JANUS_PORT', 5001))
JAVA_OCR_PORT=int(os.getenv('JAVA_OCR_PORT', 8080))
PYTHON_OCR=int(os.getenv('PYTHON_OCR',5000))

# 服务进程列表
processes = []


def cleanup():
    """清理所有子进程"""
    print("\n正在关闭所有服务...")
    for process in processes:
        if process.poll() is None:  # 进程仍在运行
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    print("所有服务已关闭")


# 注册清理函数
atexit.register(cleanup)
signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))


def check_port(port, service_name="服务"):
    """检查端口是否被占用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', port))
    sock.close()
    if result == 0:
        print(f"端口 {port} 已被占用，{service_name}可能已在运行")
        return True
    return False


def start_redis():
    """启动Redis服务器"""
    print("启动Redis服务...")

    # 检查端口
    if check_port(REDIS_PORT, "Redis"):
        print("Redis已在运行")
        return None

    # 根据操作系统选择Redis路径
    if platform.system() == "Windows":
        redis_path = Path(__file__).parent / "Redis-x64-5.0.14.1" / "redis-server.exe"
        if not redis_path.exists():
            print(f"Redis未找到: {redis_path}")
            print("请确保Redis-x64-5.0.14.1文件夹位于backend目录下")
            return None

        # 启动Redis
        process = subprocess.Popen(
            [str(redis_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

        time.sleep(2)  # 等待Redis启动

        # 检查是否成功启动
        if process.poll() is None and check_port(REDIS_PORT):
            print("Redis启动成功")
            return process
        else:
            print("Redis启动失败")
            return None


def start_java_ocr():
    """启动Java OCR服务"""
    print("启动Java OCR服务...")

    # 检查端口
    if check_port(JAVA_OCR_PORT, "Java OCR"):
        try:
            response = requests.get(f"http://localhost:{JAVA_OCR_PORT}/actuator/health", timeout=2)
            if response.status_code == 200:
                print("Java OCR服务已在运行")
                return None
        except:
            pass
        # 端口占用但服务不健康，尝试释放端口
        print(f"⚠️  端口 {JAVA_OCR_PORT} 被占用但服务无响应，尝试释放端口...")
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
                for line in result.stdout.splitlines():
                    if f":{JAVA_OCR_PORT}" in line and "LISTENING" in line:
                        parts = line.split()
                        pid = parts[-1]
                        subprocess.run(["taskkill", "/F", "/PID", pid], capture_output=True)
                        print(f"已终止占用端口的进程 PID={pid}")
                        break
            time.sleep(2)
        except Exception as e:
            print(f"释放端口失败: {e}，继续尝试启动...")

    # 获取当前脚本目录
    current_dir = Path(__file__).parent

    # 查找JAR文件
    jar_path = current_dir / "lib" / "ocr-application.jar"

    if not jar_path.exists():
        print(f"❌ JAR文件未找到: {jar_path}")
        print("请确认 backend/lib/ocr-application.jar 文件存在")
        return None

    print(f"找到JAR文件: {jar_path}")

    # 检查Java是否安装
    try:
        result = subprocess.run(["java", "-version"], capture_output=True, text=True)
        print(f"Java检查通过")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Java未安装，请先安装Java Runtime Environment")
        return None

    working_dir = current_dir
    cmd = ["java", "-jar", str(jar_path.absolute())]
    print(f"启动命令: {' '.join(cmd)}")
    print(f"工作目录: {working_dir}")

    try:
        process = subprocess.Popen(
            cmd,
            cwd=str(working_dir),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # 合并 stderr，方便看启动错误
            encoding='utf-8',
            errors='replace'
        )
    except Exception as e:
        print(f"启动Java进程失败: {e}")
        return None

    # 实时打印 Java 启动日志，方便诊断问题
    import threading
    def _print_java_log():
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[Java OCR] {line.rstrip()}")
    log_thread = threading.Thread(target=_print_java_log, name="Thread-JavaOCR-log", daemon=True)
    log_thread.start()

    # Spring Boot 通常需要 15-60 秒启动，等待最多 60 秒
    print("等待Java OCR服务启动（最多60秒）...")
    for i in range(60):
        time.sleep(1)

        if process.poll() is not None:
            print(f"❌ Java进程意外退出，退出码: {process.returncode}")
            print("请查看上方 [Java OCR] 日志确认错误原因")
            return None

        try:
            response = requests.get(f"http://localhost:{JAVA_OCR_PORT}/actuator/health", timeout=1)
            if response.status_code == 200:
                print(f"✅ Java OCR服务启动成功（用时约{i+1}秒）")
                return process
        except requests.exceptions.RequestException:
            pass

        if (i + 1) % 10 == 0:
            print(f"等待中... ({i + 1}/60秒)")

    print("❌ Java OCR服务启动超时（60秒内未就绪）")
    print("请查看上方 [Java OCR] 日志确认错误原因")
    process.terminate()
    return None


def start_janus():
    """启动Janus查询服务"""
    print("启动Janus查询服务...")

    janus_port = JANUS_PORT

    if check_port(janus_port, "Janus"):
        print("Janus服务已在运行")
        return None

    current_dir = Path(__file__).parent
    janus_service_path = current_dir / "janus_query_service.py"
    if not janus_service_path.exists():
        print(f"Janus服务文件未找到: {janus_service_path}")
        return None

    print("启动Janus查询服务...")
    try:
        process = subprocess.Popen(
            [sys.executable, "-u", str(janus_service_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(current_dir),
            env={**os.environ, "PYTHONUNBUFFERED": "1"},
            encoding='utf-8',
            errors='replace'
        )

        print("等待Janus服务启动...")
        for i in range(30):
            time.sleep(1)

            if process.poll() is not None:
                stdout, stderr = process.communicate()
                print(f"Janus进程意外退出，退出码: {process.returncode}")
                if stderr:
                    print(f"错误输出: {stderr}")
                return None

            try:
                response = requests.get(f"http://localhost:{janus_port}/api/query", timeout=1)
                if response.status_code in [200, 400, 404, 405]:
                    print("Janus服务启动成功")
                    return process
            except requests.exceptions.RequestException:
                if check_port(janus_port):
                    print("Janus服务启动成功（端口已绑定）")
                    return process

            if i % 5 == 0:
                print(f"等待中... ({i + 1}/30秒)")

        print("Janus服务启动超时")
        process.terminate()
        return None

    except Exception as e:
        print(f"启动Janus服务失败: {e}")
        return None


def start_python_face_recognition():
    """启动Python人脸识别服务"""
    print("启动Python人脸识别服务...")

    if check_port(PYTHON_OCR, "Python人脸识别"):
        print("Python人脸识别服务已在运行")
        return None

    app_path = Path(__file__).parent / "face_service" / "app.py"
    if not app_path.exists():
        app_path = Path(__file__).parent / "app.py"

    if not app_path.exists():
        print(f"人脸识别服务未找到: {app_path}")
        return None

    process = subprocess.Popen(
        [sys.executable, "-u", str(app_path)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(app_path.parent),
        env={**os.environ, "PYTHONUNBUFFERED": "1"}
    )

    print("等待Python人脸识别服务启动...")
    for i in range(10):
        time.sleep(1)
        try:
            response = requests.get(f"http://localhost:{PYTHON_OCR}/api/registered_users", timeout=1)
            if response.status_code == 200:
                print("Python人脸识别服务启动成功")
                return process
        except:
            continue

    print("Python人脸识别服务启动超时")
    process.terminate()
    return None


def start_celery():
    """启动Celery Worker"""
    print("\n" + "=" * 50)
    print("启动Celery Worker...")
    print("=" * 50)

    if not check_port(REDIS_PORT, "Redis"):
        print("❌ 错误：Redis未运行，Celery无法启动")
        return None

    print("✓ Redis已运行，开始启动Celery...")

    # 实时显示输出
    process = subprocess.Popen(
        [sys.executable, "-m", "celery", "-A", "core", "worker", "-l", "info", "--pool=eventlet", "--concurrency=2", "--purge"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        cwd=str(Path(__file__).parent)
    )

    # 实时显示Celery输出
    def print_celery_output():
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[Celery] {line.strip()}")

    import threading
    output_thread = threading.Thread(target=print_celery_output)
    output_thread.daemon = True
    output_thread.start()

    # ✅ 等待更长时间,确保启动成功
    time.sleep(5)

    if process.poll() is None:
        print("\n✅ Celery Worker启动成功")
        print("=" * 50 + "\n")
        return process
    else:
        print("\n❌ Celery Worker启动失败")
        print("=" * 50 + "\n")
        return None


def start_django():
    """启动Django服务器 (使用 daphne 支持 WebSocket)"""
    print("\n" + "=" * 50)
    print("启动Django服务 (支持WebSocket)...")
    print("=" * 50)

    if check_port(DJANGO_PORT, "Django"):
        print("Django已在运行，跳过启动")
        return None

    # 检查 daphne 是否已安装
    try:
        import daphne
        print("✓ daphne 已安装")
    except ImportError:
        print("\n❌ 错误：daphne 未安装")
        print("正在安装 daphne...")
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "daphne==4.0.0"],
                check=True,
                capture_output=True
            )
            print("✓ daphne 安装成功")
        except subprocess.CalledProcessError as e:
            print(f"❌ daphne 安装失败: {e}")
            print("请手动运行: pip install daphne")
            return None

    # 使用 daphne 而不是 runserver
    backend_dir = Path(__file__).parent

    # 启动命令：daphne -b 0.0.0.0 -p 8000 core.asgi:application
    process = subprocess.Popen(
        [
            sys.executable, "-m", "daphne",
            "-b", "0.0.0.0",
            "-p", str(DJANGO_PORT),
            "core.asgi:application"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        encoding='utf-8',
        errors='replace',
        bufsize=1,
        cwd=str(backend_dir)
    )

    # 实时显示Django输出
    def print_output():
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[Django] {line.strip()}")

    import threading
    output_thread = threading.Thread(target=print_output, name="Thread-Django-output")
    output_thread.daemon = True
    output_thread.start()

    print("等待Django服务启动...")
    max_wait = 30
    started = False
    for i in range(max_wait):
        time.sleep(1)
        if process.poll() is not None:
            print(f"\n❌ Django进程意外退出，退出码: {process.returncode}")
            print("=" * 50 + "\n")
            return None
        if check_port(DJANGO_PORT):
            started = True
            break
        if (i + 1) % 5 == 0:
            print(f"  Django仍在启动中...已等待 {i + 1} 秒")

    if started:
        print(f"\n✅ Django服务启动成功 (支持WebSocket)")
        print(f"   HTTP:      http://localhost:{DJANGO_PORT}")
        print(f"   WebSocket: ws://localhost:{DJANGO_PORT}/ws/")
        print("=" * 50 + "\n")
        return process
    else:
        print(f"\n⚠️ Django服务在 {max_wait} 秒内未就绪，但进程仍在运行，继续等待...")
        print(f"   进程PID: {process.pid}")
        print("=" * 50 + "\n")
        return process


def main():
    """主函数"""
    print("厨房检测系统启动中...")
    print("=" * 50)

    # 启动Redis
    redis_process = start_redis()
    if redis_process:
        processes.append(redis_process)
    time.sleep(1)

    # 启动Java OCR服务
    java_process = start_java_ocr()
    if java_process:
        processes.append(java_process)
    time.sleep(1)

    # 启动Janus查询服务
    janus_process = start_janus()
    if janus_process:
        processes.append(janus_process)
    else:
        print("⚠️  警告: Janus未启动，AI查询功能将无法使用!")
    time.sleep(1)

    # 启动Python人脸识别服务
    python_process = start_python_face_recognition()
    if python_process:
        processes.append(python_process)
    time.sleep(1)

    # ✅ 启动Celery (在Django之前)
    celery_process = start_celery()
    if celery_process:
        processes.append(celery_process)
    else:
        print("⚠️  警告: Celery未启动,检测功能将无法使用!")

    time.sleep(2)

    # ⚠️ 启动Django (使用 daphne)
    django_process = start_django()
    if django_process:
        processes.append(django_process)
    else:
        print("⚠️  警告: Django未启动,Web界面将无法访问!")

    print("\n" + "=" * 50)
    print("✅ 所有服务启动完成!")
    print("=" * 50)
    print("\n服务列表:")
    print(f"  - Redis:            运行中 (端口 {REDIS_PORT})")
    print(f"  - Java OCR:         http://localhost:{JAVA_OCR_PORT}")
    print(f"  - Janus查询:        http://localhost:{JANUS_PORT}")
    print(f"  - Python人脸识别:   http://localhost:{PYTHON_OCR}")
    print(f"  - Celery Worker:    运行中")
    print(f"  - Django HTTP:      http://localhost:{DJANGO_PORT}")
    print(f"  - Django WebSocket: ws://localhost:{DJANGO_PORT}/ws/")
    print(f"  - Django 管理后台:  http://localhost:{DJANGO_PORT}/admin")
    print("\n按 Ctrl+C 停止所有服务")
    print("=" * 50 + "\n")

    # 监控循环
    try:
        while True:
            time.sleep(10)

            # 检查进程状态
            service_names = ["Redis", "Java OCR", "Janus", "Python人脸识别", "Celery", "Django (daphne)"]
            for i, process in enumerate(processes):
                if process and process.poll() is not None:
                    print(f"\n⚠️  {service_names[i]} 已停止，退出码: {process.returncode}")

    except KeyboardInterrupt:
        print("\n收到停止信号...")


if __name__ == "__main__":
    main()