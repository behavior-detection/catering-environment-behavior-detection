from django.db import models


class Visitor(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    password = models.CharField(max_length=255, db_column='Password')

    class Meta:
        db_table = 'visitor'
        managed = False


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


class SecurityProblem(models.Model):
    name = models.CharField(max_length=50, primary_key=True, db_column='Name')
    problem1 = models.CharField(max_length=255, null=True, db_column='Problem1')
    answer1 = models.CharField(max_length=255, null=True, db_column='Answer1')
    problem2 = models.CharField(max_length=255, null=True, db_column='Problem2')
    answer2 = models.CharField(max_length=255, null=True, db_column='Answer2')

    class Meta:
        db_table = 'Security_Problem'
        managed = False


class Enterprise(models.Model):
    eid = models.CharField(max_length=50, primary_key=True, db_column='EID')
    name = models.CharField(max_length=100, db_column='Name')

    class Meta:
        db_table = 'Enterprise'
        managed = False