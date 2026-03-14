from django.core.management.base import BaseCommand
import subprocess
import sys
import os
from pathlib import Path


class Command(BaseCommand):
    help = '启动所有服务（Redis、Java OCR、Python人脸识别、Django）'

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-django',
            action='store_true',
            help='不启动Django服务（仅启动外部服务）',
        )

    def handle(self, *args, **options):
        # 找到项目根目录（manage.py所在目录）
        current_file = Path(__file__).resolve()
        # 从 apps/monitor/management/commands/runall.py 回到项目根目录
        project_root = current_file.parent.parent.parent.parent.parent

        # 启动脚本路径
        script_path = project_root / 'start_all_services.py'

        if not script_path.exists():
            self.stdout.write(self.style.ERROR(f'启动脚本不存在: {script_path}'))
            self.stdout.write(self.style.WARNING('请确保 start_all_services.py 位于项目根目录'))
            return

        self.stdout.write(self.style.SUCCESS('开始启动所有服务...'))

        # 构建命令
        cmd = [sys.executable, str(script_path)]
        if options['no_django']:
            cmd.append('--no-django')

        # 运行启动脚本
        try:
            subprocess.run(cmd)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\n服务已停止'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'启动失败: {e}'))