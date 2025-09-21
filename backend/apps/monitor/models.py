# apps/monitor/models.py
from django.db import models
from django.contrib.auth.models import User
import json
from datetime import datetime


class ViolationRecord(models.Model):
    """违规记录模型"""
    CAMERA_CHOICES = [
        ('cam_11', 'CAM_11'),
        ('cam_28', 'CAM_28'),
        ('cam_34', 'CAM_34'),
        ('D11', 'D11'),
        ('D28', 'D28'),
        ('D34', 'D34'),
    ]

    camera_id = models.CharField(max_length=50, choices=CAMERA_CHOICES, verbose_name="摄像头ID")
    detection_timestamp = models.DateTimeField(verbose_name="检测时间")
    violation_data = models.JSONField(verbose_name="违规数据")
    image_path = models.CharField(max_length=500, blank=True, null=True, verbose_name="图片路径")
    total_violations = models.IntegerField(default=0, verbose_name="总违规次数")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'violations_records'
        verbose_name = "违规记录"
        verbose_name_plural = "违规记录"
        ordering = ['-detection_timestamp']
        indexes = [
            models.Index(fields=['camera_id', 'detection_timestamp']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.camera_id} - {self.detection_timestamp} - {self.total_violations}次违规"

    @property
    def formatted_violations(self):
        """格式化违规数据显示"""
        if isinstance(self.violation_data, dict):
            violations = self.violation_data.get('violations', {})
            return violations
        return {}

    @classmethod
    def get_violations_by_time_range(cls, hours=24):
        """根据时间范围获取违规数据"""
        from django.utils import timezone
        from datetime import timedelta

        if hours == 0:  # 查询所有数据
            return cls.objects.all()

        time_threshold = timezone.now() - timedelta(hours=hours)
        return cls.objects.filter(detection_timestamp__gte=time_threshold)


class AIAnalysisReport(models.Model):
    """AI分析报告模型"""
    ANALYSIS_TYPE_CHOICES = [
        ('janus_model', 'Janus模型'),
        ('rule_engine', '规则引擎'),
        ('multimodal_simulation', '多模态模拟'),
        ('comprehensive', '综合分析'),
        ('quick', '快速分析'),
        ('risk_focused', '风险关注'),
        ('compliance', '合规分析'),
        ('error', '错误分析'),
    ]

    RISK_LEVEL_CHOICES = [
        ('无风险', '无风险'),
        ('低风险', '低风险'),
        ('中风险', '中风险'),
        ('高风险', '高风险'),
        ('未知', '未知'),
    ]

    analysis_id = models.CharField(max_length=100, unique=True, verbose_name="分析ID")
    violation_record = models.ForeignKey(
        ViolationRecord,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="关联违规记录"
    )
    analysis_type = models.CharField(
        max_length=50,
        choices=ANALYSIS_TYPE_CHOICES,
        default='rule_engine',
        verbose_name="分析类型"
    )
    risk_level = models.CharField(
        max_length=20,
        choices=RISK_LEVEL_CHOICES,
        default='低风险',
        verbose_name="风险等级"
    )
    analysis_result = models.JSONField(verbose_name="分析结果")
    summary = models.TextField(blank=True, verbose_name="摘要")
    recommendations = models.JSONField(default=list, verbose_name="建议")
    compliance_score = models.IntegerField(default=0, verbose_name="合规分数")
    confidence_score = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.80,
        verbose_name="置信度分数"
    )
    processing_time = models.DateTimeField(default=datetime.now, verbose_name="处理时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'ai_analysis_reports'
        verbose_name = "AI分析报告"
        verbose_name_plural = "AI分析报告"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['analysis_id']),
            models.Index(fields=['risk_level']),
            models.Index(fields=['created_at']),
        ]

    def __str__(self):
        return f"{self.analysis_id} - {self.analysis_type} - {self.risk_level}"


class AIQueryHistory(models.Model):
    """AI查询历史记录"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="用户")
    query = models.TextField(verbose_name="查询内容")
    time_range_hours = models.IntegerField(default=24, verbose_name="时间范围(小时)")
    query_all_data = models.BooleanField(default=False, verbose_name="查询所有数据")
    response_data = models.JSONField(verbose_name="响应数据")
    success = models.BooleanField(default=True, verbose_name="是否成功")
    error_message = models.TextField(blank=True, verbose_name="错误信息")
    processing_time = models.FloatField(default=0.0, verbose_name="处理时间(秒)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'ai_query_history'
        verbose_name = "AI查询历史"
        verbose_name_plural = "AI查询历史"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.query[:50]}... - {self.created_at}"


class ChatConversation(models.Model):
    """聊天对话模型 - 可选，如果完全使用Redis可以不用这个"""
    conversation_id = models.CharField(max_length=100, unique=True, verbose_name="对话ID")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, verbose_name="用户")
    title = models.CharField(max_length=200, default="新对话", verbose_name="对话标题")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    is_active = models.BooleanField(default=True, verbose_name="是否活跃")

    class Meta:
        db_table = 'chat_conversations'
        verbose_name = "聊天对话"
        verbose_name_plural = "聊天对话"
        ordering = ['-updated_at']

    def __str__(self):
        return f"{self.conversation_id} - {self.title}"


class ChatMessage(models.Model):
    """聊天消息模型 - 可选，主要用Redis存储"""
    MESSAGE_TYPE_CHOICES = [
        ('user', '用户消息'),
        ('ai', 'AI回复'),
        ('system', '系统消息'),
    ]

    conversation = models.ForeignKey(ChatConversation, on_delete=models.CASCADE, verbose_name="对话")
    message_id = models.CharField(max_length=100, verbose_name="消息ID")
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, verbose_name="消息类型")
    content = models.TextField(verbose_name="消息内容")
    metadata = models.JSONField(default=dict, blank=True, verbose_name="元数据")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = 'chat_messages'
        verbose_name = "聊天消息"
        verbose_name_plural = "聊天消息"
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['message_id']),
        ]

    def __str__(self):
        return f"{self.message_type} - {self.content[:50]}..."


class SystemConfig(models.Model):
    """系统配置模型"""
    key = models.CharField(max_length=100, unique=True, verbose_name="配置键")
    value = models.TextField(verbose_name="配置值")
    description = models.TextField(blank=True, verbose_name="描述")
    is_active = models.BooleanField(default=True, verbose_name="是否激活")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = 'system_config'
        verbose_name = "系统配置"
        verbose_name_plural = "系统配置"

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"

    @classmethod
    def get_config(cls, key, default=None):
        """获取配置值"""
        try:
            config = cls.objects.get(key=key, is_active=True)
            return config.value
        except cls.DoesNotExist:
            return default

    @classmethod
    def set_config(cls, key, value, description=""):
        """设置配置值"""
        config, created = cls.objects.get_or_create(
            key=key,
            defaults={'value': value, 'description': description}
        )
        if not created:
            config.value = value
            config.description = description
            config.save()
        return config
