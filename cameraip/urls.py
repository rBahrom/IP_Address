from django.urls import path
from django.urls import include
from django.contrib import admin
from accounts import views
from .views import camera_ips

urlpatterns = [
    path('camera_ips/', camera_ips, name='camera_ips'),
    path('camera/', views.camera_view, name='camera'),
]
