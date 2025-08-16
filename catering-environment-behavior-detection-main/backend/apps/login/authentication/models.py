from django.db import models


class Visitor(models.Model):
    name = models.CharField(max_length=50, unique=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'visitor'
        managed = False  # 因为表已存在


class Manager(models.Model):
    name = models.CharField(max_length=50, unique=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'manager'
        managed = False


class Admin(models.Model):
    name = models.CharField(max_length=50, unique=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'admin'
        managed = False


class Verification(models.Model):
    name = models.CharField(max_length=50, unique=True, db_column='Name')
    email = models.EmailField(max_length=100, unique=True, db_column='Email')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'verification'
        managed = False


class SecurityProblem(models.Model):
    name = models.CharField(max_length=50, unique=True, db_column='Name')
    problem1 = models.CharField(max_length=255, null=True, db_column='Problem1')
    answer1 = models.CharField(max_length=255, null=True, db_column='Answer1')
    problem2 = models.CharField(max_length=255, null=True, db_column='Problem2')
    answer2 = models.CharField(max_length=255, null=True, db_column='Answer2')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'security_problem'
        managed = False


class Enterprise(models.Model):
    eid = models.CharField(max_length=50, unique=True, db_column='EID')
    name = models.CharField(max_length=100, db_column='Name')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'Enterprise'
        managed = False