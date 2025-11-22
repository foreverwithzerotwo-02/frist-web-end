from django.urls import path
from .views import delete_role, create_permission,delete_permission, edit_permission, update_role, create_role, get_all_permissions, update_user_roles, list_roles, list_users, RegisterView, get_user_info, change_password_view, update_user_info, update_avatar, assign_role_to_user, assign_permission_to_user
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('list_users/', list_users, name='list_users'),  # 获取全部或搜索用户
    path("roles/", list_roles, name="list_roles"),  # 获取全部角色以及角色权限
    path("roles/create/", create_role, name="create_role"),  # 新增角色
    path("roles/<int:role_id>/edit/", update_role, name="update_role"),  # 编辑角色
    path("roles/<int:role_id>/delete/", delete_role, name="delete_role_by_id"),  # 删除角色
    path("permissions/", get_all_permissions, name="get_all_permissions"),  # 获取全部权限信息
    path("permissions/create/", create_permission),  # 新增权限
    path("permissions/<int:permission_id>/edit/", edit_permission),  # 修改权限
    path("permissions/<int:permission_id>/delete/", delete_permission),  # 删除权限
    path("<int:user_id>/update_roles/", update_user_roles, name="update_user_roles"),  # 修改用户角色
    path('register/', RegisterView.as_view(), name='register'),  # 注册
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),  # 登录
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),  # 获取短时 token
    path('change_password_view/', change_password_view, name='change_password_view'),  # 修改密码
    path("get_user_info/", get_user_info, name="get_user_info"),  # 获取用户信息
    path("update_avatar/", update_avatar, name="update_avatar"),  # 修改用户头像
    path("update_user_info/", update_user_info, name="update_user_info"),  # 修改用户信息
    path("assign-role/", assign_role_to_user, name="assign-role"),  # 给用户设置身份
    path("assign-permission/", assign_permission_to_user, name="assign-permission"),  #给用户设置权限
]
