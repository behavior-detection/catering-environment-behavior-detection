import pymysql
pymysql.install_as_MySQLdb()

import subprocess
import time
import requests
import redis
from django.conf import settings


def check_services():
    """检查必要的服务是否运行"""
    # 检查Redis
    try:
        r = redis.Redis(host='localhost', port=6379)
        r.ping()
        print("✓ Redis服务正常")
    except:
        print("✗ Redis服务未启动！请运行Redis-x64-5.0.14.1/redis-server.exe")

    # 检查Java OCR服务
    try:
        response = requests.get(f'http://localhost:8080/health', timeout=2)
        print("✓ Java OCR服务正常")
    except:
        print("✗ Java OCR服务未启动！")


# 在开发环境下检查
import os

if os.getenv('DJANGO_SETTINGS_MODULE') == 'core.settings':
    check_services()