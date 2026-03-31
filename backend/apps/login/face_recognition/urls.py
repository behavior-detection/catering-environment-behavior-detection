from django.urls import path
from . import views

urlpatterns = [
    path('api/verify_face', views.verify_face, name='verify_face'),
    path('api/registered_users', views.get_registered_users, name='get_registered_users'),
    path('api/reload_database', views.reload_database, name='reload_database'),
]