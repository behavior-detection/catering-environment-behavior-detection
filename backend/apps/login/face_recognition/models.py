from django.db import models


# 人脸识别相关的模型
# 如果需要记录人脸识别日志等，可以在这里定义模型
class FaceRecognitionLog(models.Model):
    """人脸识别日志"""
    user_name = models.CharField('用户名', max_length=100, null=True, blank=True)
    is_real_person = models.BooleanField('是否真人', default=False)
    status = models.CharField('状态', max_length=20)
    created_at = models.DateTimeField('识别时间', auto_now_add=True)

    class Meta:
        db_table = 'face_recognition_log'
        verbose_name = '人脸识别日志'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']