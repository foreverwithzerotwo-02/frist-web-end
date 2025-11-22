from django.apps import AppConfig
from django.db.models.signals import post_migrate


class UsersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'

    def ready(self):
        # ✅ 在 ready() 方法内注册信号（此时模型已加载）
        from django.dispatch import receiver
        from .models import Role, Permission

        @receiver(post_migrate)
        def create_default_roles_permissions(sender, **kwargs):
            # 确保只在当前 app 执行（防止其它 app 重复触发）
            if sender.name != self.name:
                return

            # 定义所有权限
            permissions_data = [
                ("管理用户", "can_manage_users"),
                ("审核帖子", "can_approve_posts"),
                ("审核课程", "can_approve_courses"),
                ("管理课程", "can_manage_courses"),
                ("管理论坛", "can_manage_forum"),
                ("访问后台页面", "can_view_backend"),
            ]

            for name, code in permissions_data:
                Permission.objects.get_or_create(name=name, code=code)

            # 定义角色与权限关系
            roles_permissions = {
                "管理员": [
                    "can_manage_users",
                    "can_approve_posts",
                    "can_approve_courses",
                    "can_manage_courses",
                    "can_manage_forum",
                    "can_view_backend",
                ],
                "审核员": ["can_approve_posts", "can_approve_courses", "can_view_backend"],
                "讲师": ["can_manage_courses", "can_view_backend"],
                "普通用户": [],
            }

            for role_name, permission_codes in roles_permissions.items():
                role, _ = Role.objects.get_or_create(name=role_name)
                role.permissions.set(Permission.objects.filter(code__in=permission_codes))
