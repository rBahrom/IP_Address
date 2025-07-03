from django.urls import path
from . import views
from .views import archive_view, download_archive, UserListView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', views.home_view, name='home'),
    path('users/', UserListView.as_view(), name='userlist'),
    path('archive/', archive_view, name='archive'),
    path('download/<str:filename>/', download_archive, name='download_archive'),
    path('check_ips/', views.check_ips, name='check_ips'),
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
]
# Media fayllarini ko'rsatish uchun
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
