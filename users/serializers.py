from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import User
import random


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ("username", "nickname", "avatar", "bio", "password", "password2", "email")
        extra_kwargs = {
            "email": {"required": True},
            "nickname": {"required": False},
            "avatar": {"required": False, "allow_null": True},
            "bio": {"required": False, "allow_blank": True},
        }

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError({"password": "两次输入的密码不一致"})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password2")  # 移除 password2
        user = User.objects.create_user(**validated_data)  # 自动加密密码
        # 自动生成昵称（例：用户_<随机4位数>）
        if not user.nickname:
            user.nickname = f"用户_{random.randint(1000, 9999)}"
            user.save()
        return user


# 用户头像
class AvatarUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["avatar"]
