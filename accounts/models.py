import uuid

from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        if not extra_fields.get("is_staff"):
            raise ValueError("Superuser must have is_staff=True.")
        if not extra_fields.get("is_superuser"):
            raise ValueError("Superuser must have is_superuser=True.")
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return self.email


class AllowedEmail(models.Model):
    email = models.EmailField(unique=True)
    note = models.CharField(max_length=200, blank=True, help_text="Optional label, e.g. person's name")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["email"]

    def __str__(self):
        return self.email


def is_email_allowed(email: str) -> bool:
    return AllowedEmail.objects.filter(email__iexact=email.strip()).exists()


class WaitlistEntry(models.Model):
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return self.email
