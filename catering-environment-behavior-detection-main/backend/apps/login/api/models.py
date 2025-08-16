from django.db import models
from django.contrib.auth.hashers import make_password, check_password


class Visitor(models.Model):
    name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visitor'

    def set_password(self, raw_password):
        self.password = raw_password  # 注意：实际应用应该加密

    def check_password(self, raw_password):
        return self.password == raw_password


class Manager(models.Model):
    name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manager'


class Admin(models.Model):
    name = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin'


class Verification(models.Model):
    name = models.CharField(max_length=50, unique=True)
    email = models.EmailField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification'


class SecurityProblem(models.Model):
    name = models.CharField(max_length=50, unique=True)
    problem1 = models.CharField(max_length=255, null=True)
    answer1 = models.CharField(max_length=255, null=True)
    problem2 = models.CharField(max_length=255, null=True)
    answer2 = models.CharField(max_length=255, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_problem'


class Enterprise(models.Model):
    eid = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Enterprise'