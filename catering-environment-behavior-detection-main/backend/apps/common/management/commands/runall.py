from django.core.management.base import BaseCommand
import subprocess
import time
import sys
import os


class Command(BaseCommand):
    help = '启动所有服务（Redis、Java OCR、Django）'

    def handle(self, *args, **options):
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

        # 使用之前的启动脚本
        script_path = os.path.join(base_dir, 'start_all_services.py')
        subprocess.run([sys.executable, script_path])