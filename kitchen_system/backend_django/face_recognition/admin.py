from django.contrib import admin
from .models import FaceRecognitionLog


@admin.register(FaceRecognitionLog)
class FaceRecognitionLogAdmin(admin.ModelAdmin):
    list_display = ['user_name', 'is_real_person', 'status', 'created_at']
    list_filter = ['is_real_person', 'status', 'created_at']
    search_fields = ['user_name']
    readonly_fields = ['created_at']