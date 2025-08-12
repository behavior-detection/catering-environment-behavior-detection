# run_processor.py - 定时运行处理脚本

import time
from .identity_recognition.identity_recognition import process_all_uploads

if __name__ == "__main__":
    print("身份证识别处理器已启动，按Ctrl+C停止...")
    try:
        while True:
            process_all_uploads()
            time.sleep(5)  # 每5秒检查一次新上传
    except KeyboardInterrupt:
        print("处理器已停止")