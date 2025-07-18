import cv2
import pytesseract
import re
import os
import numpy as np
import json
import sys
from pytesseract import Output

# 初始化配置
custom_config = r'--oem 3 --psm 6 -l chi_sim'


def validate_id_number(id_number):
    """验证统一社会信用代码的校验码"""
    if len(id_number) != 18:
        return False
    factors = [1, 3, 9, 27, 19, 26, 16, 17, 20, 29, 25, 13, 8, 24, 10, 30, 28]
    chars = "0123456789ABCDEFGHJKLMNPQRTUWXY"
    checksum = 0

    for i in range(17):
        char = id_number[i]
        value = chars.index(char) if char in chars else -1
        if value == -1:
            return False
        checksum += value * factors[i]

    check_code = 31 - (checksum % 31)
    check_code = 0 if check_code == 31 else check_code
    return chars[check_code] == id_number[-1]


def is_valid_business_license(text):
    """检查营业执照关键字段"""
    required_fields = ["营业执照", "统一社会信用代码", "名称", "类型", "住址", "法定代表人",
                       "注册资本", "成立日期", "经营范围", "登记机关"]
    found_fields = sum(1 for field in required_fields if field in text)
    return found_fields >= 5  # 至少匹配5个关键字段


def extract_business_info(text):
    """从文本中提取企业名称和统一社会信用代码"""
    # 提取统一社会信用代码
    eid_match = re.search(r'统一社会信用代码[:：]?\s*([0-9A-Z]{18})', text)
    eid = eid_match.group(1) if eid_match else None

    # 提取企业名称
    name_match = re.search(r'名称[:：]?\s*([^\n]+)', text)
    name = name_match.group(1).strip() if name_match else None

    # 清理名称中的特殊字符和多余空格
    if name:
        name = re.sub(r'[^\w\u4e00-\u9fa5]', '', name)

    return eid, name


def process_image(image_path):
    """处理图像并返回结果"""
    try:
        image = cv2.imread(image_path)
        if image is None:
            return {"status": "error", "message": "无法加载图像"}

        # 预处理图像
        gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        processed_image = cv2.GaussianBlur(gray_image, (5, 5), 0)
        _, processed_image = cv2.threshold(processed_image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        # OCR识别文本
        text = pytesseract.image_to_string(processed_image, config=custom_config)

        # 验证营业执照
        if not is_valid_business_license(text):
            return {"status": "error", "message": "营业执照关键字段缺失"}

        # 提取信息
        eid, name = extract_business_info(text)
        if not eid or not name:
            return {"status": "error", "message": "无法提取统一社会信用代码或企业名称"}

        if not validate_id_number(eid):
            return {"status": "error", "message": "统一社会信用代码无效"}

        return {
            "status": "success",
            "eid": eid,
            "name": name,
            "text": text  # 可选：返回识别的完整文本用于调试
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


if __name__ == "__main__":
    # 从命令行参数获取图片路径
    if len(sys.argv) < 2:
        print(json.dumps({"status": "error", "message": "请提供图片路径"}))
        sys.exit(1)

    image_path = sys.argv[1]
    result = process_image(image_path)
    print(json.dumps(result))