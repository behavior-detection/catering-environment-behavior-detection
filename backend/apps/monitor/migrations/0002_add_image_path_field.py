# apps/monitor/migrations/0002_add_image_path_field.py
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('monitor', '0001_initial'),
    ]

    operations = [
        # 添加image_path字段到violations_records表
        migrations.AddField(
            model_name='violationrecord',
            name='image_path',
            field=models.CharField(max_length=500, blank=True, null=True, verbose_name='图像路径'),
        ),

        # 确保数据库表名正确
        migrations.AlterModelTable(
            name='violationrecord',
            table='violations_records',
        ),
    ]