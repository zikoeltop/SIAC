from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class Roles(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        USER = 'USER', 'User'
    role = models.CharField(max_length=10, choices=Roles.choices, default=Roles.USER)

    @property
    def is_admin_role(self):
        return self.is_superuser or self.role == self.Roles.ADMIN
