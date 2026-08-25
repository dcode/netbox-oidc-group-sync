"""A minimal stand-in for NetBox's real `users` app, used only in tests.

Mirrors the parts of NetBox 4.x's actual `users.models.Group`/`users.models.User`
shape that `netbox_oidc_group_sync.pipeline.sync_groups` depends on: `Group` is
a standalone model (NOT `django.contrib.auth.models.Group`), and `User.groups`
is a `ManyToManyField` pointing at it. Getting this wrong in the real package
is exactly the bug this test app exists to catch.
"""

from typing import ClassVar

from django.contrib.auth.base_user import AbstractBaseUser
from django.contrib.auth.models import PermissionsMixin
from django.db import models


class Group(models.Model):
    name = models.CharField(max_length=150, unique=True)

    class Meta:
        app_label = "users"

    def __str__(self) -> str:
        return self.name


class User(AbstractBaseUser, PermissionsMixin):
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        to="users.Group",
        blank=True,
        related_name="users",
        related_query_name="user",
    )

    USERNAME_FIELD = "username"
    REQUIRED_FIELDS: ClassVar[list[str]] = []

    class Meta:
        app_label = "users"
