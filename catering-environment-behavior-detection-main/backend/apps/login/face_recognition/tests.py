from django.test import TestCase
from django.urls import reverse
import json


class FaceRecognitionTestCase(TestCase):
    """人脸识别功能测试"""

    def test_get_registered_users(self):
        """测试获取注册用户列表"""
        response = self.client.get(reverse('get_registered_users'))
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertIn('success', data)

    def test_verify_face_without_data(self):
        """测试人脸验证接口 - 无数据"""
        response = self.client.post(
            reverse('verify_face'),
            data={},
            content_type='application/json'
        )
        # 应该返回错误或503（服务不可用）
        self.assertIn(response.status_code, [400, 503])