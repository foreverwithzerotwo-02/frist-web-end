from django.contrib.auth.models import AbstractUser
from django.db import models


# 权限表
class Permission(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="权限名称")
    code = models.CharField(max_length=50, unique=True, verbose_name="权限代码")

    def __str__(self):
        return f"{self.name} ({self.code})"


# 角色表
class Role(models.Model):
    name = models.CharField(max_length=50, unique=True, verbose_name="角色名称")
    permissions = models.ManyToManyField(Permission, blank=True, related_name="roles", verbose_name="拥有的权限")

    def __str__(self):
        return self.name


# 用户表
class User(AbstractUser):
    nickname = models.CharField(max_length=50, blank=True, verbose_name="昵称")
    avatar = models.ImageField(upload_to="users/avatars/",
                               default="users/avatars/default.png", blank=True, null=True, verbose_name="头像")
    bio = models.TextField(blank=True, null=True, verbose_name="个人签名")
    points = models.PositiveIntegerField(default=10, verbose_name="积分")
    is_teacher = models.BooleanField(default=False, verbose_name="是否讲师")
    # 🔹 用户的角色
    roles = models.ManyToManyField(Role, blank=True, related_name="users", verbose_name="所属角色")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="注册时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="最后活跃时间")

    def __str__(self):
        return self.nickname or self.username
