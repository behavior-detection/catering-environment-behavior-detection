# apps/login/face_recognition/admin.py
from django.contrib import admin
from face_recognition.models import FaceRecognitionLog  # 可以直接导入

@admin.register(FaceRecognitionLog)
class FaceRecognitionLogAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'is_real_person', 'status', 'created_at']
    list_filter = ['is_real_person', 'status', 'created_at']
    search_fields = ['user_name']
    readonly_fields = ['created_at']