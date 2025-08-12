# identity_recognition.py - 优化版识别处理（不保存原图）

import cv2
import pytesseract
import re
import os
import numpy as np
from pytesseract import Output
from ..config import UPLOAD_FOLDER, OUTPUT_FOLDER

# 初始化人脸检测器
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
custom_config = r'--oem 3 --psm 6 -l chi_sim'


def validate_id_number(id_number):
    """验证中国身份证号码的校验码"""
    if len(id_number) != 18:
        return False
    factors = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    checksum_map = {0: '1', 1: '0', 2: 'X', 3: '9', 4: '8', 5: '7', 6: '6', 7: '5', 8: '4', 9: '3', 10: '2'}
    total = sum(int(id_number[i]) * factors[i] for i in range(17))
    return id_number[-1].upper() == checksum_map[total % 11]


def is_valid_id_card(text):
    """检查关键字段和身份证号码"""
    required_fields = ["姓名", "性别", "民族", "出生", "住址", "公民身份号码"]
    for field in required_fields:
        if field not in text:
            return False

    id_number_match = re.search(r'公民身份号码[:：]?\s*([\dX]{18})', text)
    if not id_number_match or not validate_id_number(id_number_match.group(1)):
        return False
    return True


def validate_id_card(image):
    """综合验证身份证有效性"""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    # 检查人脸
    faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5)
    if len(faces) != 1:
        return False, "未检测到人脸或有多张人脸"

    # 检查身份证文本
    text = pytesseract.image_to_string(gray_image, config=custom_config)
    if not is_valid_id_card(text):
        return False, "关键字段缺失或身份证号无效"

    return True, "验证通过"


def extract_name_and_face(image, upload_id, output_dir=None):
    """提取姓名和头像"""
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    processed_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
    _, processed_image = cv2.threshold(processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    # 提取姓名
    text = pytesseract.image_to_string(processed_image, config=custom_config)
    name_match = re.search(r'姓名[:：]?\s*([\u4e00-\u9fa5A-Za-z\s]+)', text)
    name = name_match.group(1).strip() if name_match else "Unknown"

    # 提取头像
    faces = face_cascade.detectMultiScale(gray_image, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    if len(faces) == 0:
        return None, "未检测到人脸"

    x, y, w, h = faces[0]
    padding = 20
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(w + 2 * padding, image.shape[1] - x)
    h = min(h + 2 * padding, image.shape[0] - y)
    face_image = image[y:y + h, x:x + w]

    # 保存人脸图像到指定目录
    target_output_dir = output_dir if output_dir else OUTPUT_FOLDER
    os.makedirs(target_output_dir, exist_ok=True)

    output_filename = f"{upload_id}_{name}.jpg"
    output_path = os.path.join(target_output_dir, output_filename)
    cv2.imwrite(output_path, face_image)

    return name, output_path


def process_uploaded_file(filepath, upload_id=None, output_dir=None):
    """直接处理指定的文件路径，处理完后删除原图"""
    try:
        # 如果没有提供upload_id，从文件名中提取或生成
        if upload_id is None:
            filename = os.path.basename(filepath)
            if '_' in filename:
                upload_id = filename.split('_')[0]
            else:
                upload_id = os.path.splitext(filename)[0]

        # 检查文件是否存在
        if not os.path.exists(filepath):
            return {'status': 'error', 'message': f'文件不存在: {filepath}'}

        image = cv2.imread(filepath)
        if image is None:
            return {'status': 'error', 'message': '无法加载图像'}

        # 验证身份证
        is_valid, message = validate_id_card(image)
        if not is_valid:
            # 验证失败，删除原图
            try:
                os.remove(filepath)
            except OSError:
                pass
            return {'status': 'error', 'message': f'身份证验证失败: {message}'}

        # 提取信息 - 传入自定义输出目录
        name, face_path = extract_name_and_face(image, upload_id, output_dir)
        if not name:
            # 提取失败，删除原图
            try:
                os.remove(filepath)
            except OSError:
                pass
            return {'status': 'error', 'message': face_path}

        # 处理成功，删除原图
        try:
            os.remove(filepath)
        except OSError as e:
            # 即使删除失败也不影响主要流程
            print(f"警告：无法删除原图 {filepath}: {e}")

        return {
            'status': 'success',
            'upload_id': upload_id,
            'name': name,
            'face_path': face_path
        }
    except Exception as e:
        # 发生异常时也尝试删除原图
        try:
            if os.path.exists(filepath):
                os.remove(filepath)
        except OSError:
            pass
        return {'status': 'error', 'message': str(e)}


def process_single_upload(filename, output_dir=None):
    """处理单个上传文件（从UPLOAD_FOLDER）"""
    filepath = os.path.join(UPLOAD_FOLDER, filename)

    # 提取upload_id
    upload_id = filename.split('_')[0] if '_' in filename else os.path.splitext(filename)[0]

    return process_uploaded_file(filepath, upload_id, output_dir)


def process_file_immediately(file_path, output_dir=None):
    """立即处理指定路径的文件"""
    return process_uploaded_file(file_path, None, output_dir)


if __name__ == "__main__":
    # 示例用法
    import sys

    if len(sys.argv) > 1:
        # 直接处理指定文件
        file_path = sys.argv[1]

        custom_output_dir = "../../../fontend/identity_collection/faces"

        result = process_file_immediately(file_path, custom_output_dir)
        print(f"处理结果: {result}")
    else:
        print("请提供要处理的文件路径")
        print("用法: python identity_recognition.py /path/to/image.jpg")