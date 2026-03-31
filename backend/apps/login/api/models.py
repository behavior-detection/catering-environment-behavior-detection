from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Visitor(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')  # 添加 primary_key=True
    password = models.CharField(max_length=255, db_column='Password')

    class Meta:
        db_table = 'visitor'
        managed = False

    def set_password(self, raw_password):
        self.password = raw_password  # 注意：实际应用应该加密

    def check_password(self, raw_password):
        return self.password == raw_password


class Manager(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')
    rep = models.CharField(max_length=255, null=True, db_column='Rep')
    eid = models.CharField(max_length=50, null=True, db_column='EID')

    class Meta:
        db_table = 'manager'
        managed = False


class Admin(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')

    class Meta:
        db_table = 'admin'
        managed = False


class Verification(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    email = models.EmailField(max_length=100, unique=True, db_column='Email')

    class Meta:
        db_table = 'verification'
        managed = False


class Enterprise(models.Model):
    eid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)

    class Meta:
        db_table = 'Enterprise'
        managed = False

class SecurityProblem(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    answer1 = models.CharField(max_length=255, db_column='Answer1')  # 您的出生城市是？
    answer2 = models.CharField(max_length=255, db_column='Answer2')  # 您最喜欢的颜色是？

    class Meta:
        db_table = 'security_problem'
        managed = False