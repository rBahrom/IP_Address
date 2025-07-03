from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    # email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True, null=True)
    address = models.CharField(max_length=100, blank=True, null=True)
    bio = models.TextField(blank=True)  # Qo'shimcha maydon
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True)  # Rasm maydoni

    def __str__(self):
        return self.username

    class Meta:
        ordering = ['username']
