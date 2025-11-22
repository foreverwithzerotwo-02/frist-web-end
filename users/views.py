from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import RegisterSerializer, AvatarUpdateSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from users.models import User, Role, Permission
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db.models import Q

User_model = get_user_model()


@api_view(["GET"])
def list_users(request):
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))

    # 添加搜索关键字
    keyword = request.GET.get("search", "").strip()

    # 过滤用户
    users = User.objects.all().order_by("id")
    if keyword:
        users = users.filter(
            Q(username__icontains=keyword) |
            Q(nickname__icontains=keyword) |
            Q(email__icontains=keyword)
        )

    paginator = Paginator(users, page_size)
    page_obj = paginator.get_page(page)

    data = []
    for user in page_obj.object_list:
        data.append({
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
            "role_name": [role.name for role in user.roles.all()],
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        })

    return Response({
        "count": paginator.count,
        "page": page,
        "page_size": page_size,
        "num_pages": paginator.num_pages,
        "results": data
    })


@api_view(["GET"])
def list_roles(request):
    """
    获取全部角色及其对应权限
    - 可选参数：keyword（按角色名或权限名模糊搜索）
    """
    keyword = request.query_params.get("keyword", "").strip()

    # 查询
    roles = Role.objects.prefetch_related("permissions").all()
    if keyword:
        roles = roles.filter(
            Q(name__icontains=keyword) |
            Q(permissions__name__icontains=keyword) |
            Q(permissions__code__icontains=keyword)
        ).distinct()

    # 构造返回数据
    data = []
    for role in roles:
        data.append({
            "id": role.id,
            "name": role.name,
            "permissions": [
                {
                    "id": p.id,
                    "name": p.name,
                    "code": p.code
                } for p in role.permissions.all()
            ],
        })

    return Response(data)


@api_view(["PUT"])
def update_role(request, role_id):
    """
    编辑角色（修改名称与权限）
    请求参数：
    - name: 角色名称
    - permission_ids: 权限ID列表
    """
    try:
        role = Role.objects.get(id=role_id)
    except Role.DoesNotExist:
        return Response({"error": "角色不存在"}, status=status.HTTP_404_NOT_FOUND)

    name = request.data.get("name")
    permission_codes = request.data.get("permissions", [])

    # 修改角色名称
    if name:
        role.name = name

    # 修改权限（传入权限ID列表）
    if isinstance(permission_codes, list):
        permissions = Permission.objects.filter(code__in=permission_codes)
        role.permissions.set(permissions)

    role.save()

    # 返回更新后的信息
    data = {
        "id": role.id,
        "name": role.name,
        "permissions": list(role.permissions.values("id", "name", "code")),
    }

    return Response(data, status=status.HTTP_200_OK)


@api_view(["DELETE"])
def delete_role(request, role_id):
    """
    删除角色（通过 role_id）
    - 保护：
      * 如果 role.code == "admin" 则拒绝删除（防误删）
      * 如果仍有用户绑定该角色，返回提示（并返回绑定用户数量），前端可提示先解除用户绑定
    """
    role = get_object_or_404(Role, id=role_id)

    # 防止误删关键角色（通过 code 判断更稳）
    if getattr(role, "code", None) == "admin":
        return Response({"error": "管理员角色不能被删除"}, status=status.HTTP_400_BAD_REQUEST)

    # 检查是否有用户仍然关联此角色（适用于 user.roles ManyToMany 或 user.role FK）
    # 支持两种情况：User.roles (m2m) 或 User.role (fk)
    user_count = 0
    if hasattr(User, "roles"):
        user_count = role.users.count()  # related_name="users" 的前提
    elif hasattr(User, "role"):
        user_count = User.objects.filter(role=role).count()

    if user_count > 0:
        return Response({
            "error": "该角色仍有用户绑定，无法删除",
            "bound_user_count": user_count,
            "detail": "请先将这些用户的角色修改为其他角色或移除角色后再删除"
        }, status=status.HTTP_400_BAD_REQUEST)

    role_name = role.name
    role.delete()
    return Response({"message": f"角色 '{role_name}'（id={role_id}）已删除"}, status=status.HTTP_200_OK)


@api_view(['POST'])
def create_role(request):
    """
    创建新角色并可选绑定权限
    """
    try:
        name = request.data.get("name")
        permission_codes = request.data.get("permissions", [])  # 接收权限 code 列表

        if not name:
            return Response({"error": "角色名称不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        # 检查角色是否已存在
        if Role.objects.filter(name=name).exists():
            return Response({"error": "该角色已存在"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建角色
        role = Role.objects.create(name=name)

        # 如果有权限则绑定
        if permission_codes:
            permissions = Permission.objects.filter(code__in=permission_codes)
            role.permissions.set(permissions)

        # 返回结果
        data = {
            "id": role.id,
            "name": role.name,
            "permissions": list(role.permissions.values("id", "name", "code")),
        }

        return Response({"message": "角色创建成功", "role": data}, status=status.HTTP_201_CREATED)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(["GET"])
def get_all_permissions(request):
    """
    获取全部权限（可搜索）
    搜索字段：name, code
    """
    try:
        search = request.query_params.get("search", "").strip()

        permissions = Permission.objects.all()

        # 如果有搜索内容，进行过滤
        if search:
            permissions = permissions.filter(
                Q(name__icontains=search) |
                Q(code__icontains=search)
            )

        permissions = permissions.values("id", "name", "code")

        return Response(list(permissions), status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class RegisterView(APIView):
    """
    用户注册接口
    """

    def post(self, request):  # type: ignore
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            print(serializer.errors)  # 打印错误信息
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "注册成功", "user_id": user.id})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
def create_permission(request):
    """
    新增权限
    参数：
        name: 权限名称（中文/展示名）
        code: 权限唯一标识（英文，唯一）
    """
    name = request.data.get("name")
    code = request.data.get("code")

    if not name or not code:
        return Response({"error": "name 和 code 不能为空"}, status=400)

    # code 是否已存在
    if Permission.objects.filter(code=code).exists():
        return Response({"error": "code 已存在"}, status=400)

    permission = Permission.objects.create(name=name, code=code)

    return Response({
        "id": permission.id,
        "name": permission.name,
        "code": permission.code
    }, status=201)


@api_view(["PUT"])
def edit_permission(request, permission_id):
    """
    编辑权限
    参数：
        name: 新的权限名称
        code: 新的权限 code（唯一）
    """
    try:
        permission = Permission.objects.get(id=permission_id)
    except Permission.DoesNotExist:
        return Response({"error": "权限不存在"}, status=404)

    name = request.data.get("name")
    code = request.data.get("code")

    if not name or not code:
        return Response({"error": "name 和 code 不能为空"}, status=400)

    # 检查 code 是否重复（排除当前权限）
    if Permission.objects.filter(code=code).exclude(id=permission_id).exists():
        return Response({"error": "code 已存在"}, status=400)

    permission.name = name
    permission.code = code
    permission.save()

    return Response({
        "id": permission.id,
        "name": permission.name,
        "code": permission.code
    }, status=200)


@api_view(["DELETE"])
def delete_permission(request, permission_id):
    """
    删除权限
    """
    try:
        permission = Permission.objects.get(id=permission_id)
    except Permission.DoesNotExist:
        return Response({"error": "权限不存在"}, status=404)

    permission.delete()

    return Response({"message": "权限删除成功"}, status=200)


@api_view(["POST"])
# @permission_classes([IsAuthenticated])  # 你可以换成管理员权限
def update_user_roles(request, user_id):
    """
    修改用户角色（支持单个或多个角色）
    请求体示例：
    {
        "role_ids": [1, 2]
    }
    """
    # 检查请求参数
    role_ids = request.data.get("role_ids", [])
    if not isinstance(role_ids, list):
        return Response({"error": "role_ids 必须是列表"}, status=status.HTTP_400_BAD_REQUEST)

    # 找到目标用户
    user = get_object_or_404(User, id=user_id)

    # 找到指定角色
    roles = Role.objects.filter(id__in=role_ids)
    if not roles.exists():
        return Response({"error": "未找到有效角色"}, status=status.HTTP_400_BAD_REQUEST)

    # 更新角色
    user.roles.set(roles)
    user.save()

    # 构造返回数据
    data = {
        "user_id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "roles": [
            {"id": role.id, "name": role.name} for role in roles
        ]
    }

    return Response({"message": "用户角色更新成功", "data": data}, status=status.HTTP_200_OK)


# 修改密码
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # 必须登录才能获取
def change_password_view(request):
    user = request.user
    old_password = request.data.get("old_password")
    new_password = request.data.get("new_password")

    if not old_password or not new_password:
        return Response({"error": "旧密码和新密码都不能为空"}, status=status.HTTP_400_BAD_REQUEST)

    # 验证旧密码
    if not user.check_password(old_password):
        return Response({"error": "旧密码错误"}, status=status.HTTP_400_BAD_REQUEST)

    # 设置新密码
    user.set_password(new_password)
    user.save()
    return Response({"message": "密码修改成功"})


# 获取用户信息
@api_view(["GET"])
@permission_classes([IsAuthenticated])  # 必须登录才能获取
def get_user_info(request):
    user: User = request.user  # 当前登录的用户
    data = {
        "id": user.id,
        "username": user.username,
        "nickname": user.nickname,
        "email": user.email,
        "avatar": request.build_absolute_uri(user.avatar.url) if user.avatar else None,
        "bio": user.bio,
        "points": user.points,
        "is_teacher": user.is_teacher,
        "created_at": user.created_at,
        "updated_at": user.updated_at,
    }
    return Response(data)


# 修改用户头像
@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_avatar(request):
    """
    修改用户头像
    - 请求体: multipart/form-data, 字段名为 avatar
    """
    user = request.user
    serializer = AvatarUpdateSerializer(user, data=request.data, partial=True, context={"request": request})

    if serializer.is_valid():
        serializer.save()
        # 返回完整 URL
        avatar_url = (
            request.build_absolute_uri(user.avatar.url)
            if user.avatar and hasattr(user.avatar, "url")
            else None
        )
        return Response({"avatar": avatar_url}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_user_info(request):
    """
    修改用户基本信息
    """
    user = request.user
    username = request.data.get("username")
    nickname = request.data.get("nickname")
    bio = request.data.get("bio")

    if username:
        # ⚠️ 用户名唯一性检查
        from django.contrib.auth import get_user_model
        user_model = get_user_model()
        if user_model.objects.exclude(id=user.id).filter(username=username).exists():
            return Response({"error": "用户名已被占用"}, status=status.HTTP_400_BAD_REQUEST)
        user.username = username

    if nickname is not None:
        user.nickname = nickname

    if bio is not None:
        user.bio = bio

    user.save()

    return Response({
        "message": "资料更新成功",
        "user": {
            "id": user.id,
            "username": user.username,
            "nickname": user.nickname,
            "bio": user.bio,
        }
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
def assign_role_to_user(request):
    """
    给用户分配角色
    参数:
        - user_id: 用户ID
        - role_id: 角色ID
    """
    user_id = request.data.get("user_id")
    role_id = request.data.get("role_id")

    if not user_id or not role_id:
        return Response({"error": "缺少参数 user_id 或 role_id"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, id=user_id)
    role = get_object_or_404(Role, id=role_id)

    user.role = role
    user.save()

    return Response({
        "message": f"已成功将用户 {user.username} 设置为角色 {role.name}",
        "user_id": user.id,
        "role": role.name,
    }, status=status.HTTP_200_OK)


@api_view(["POST"])
def assign_permission_to_user(request):
    """
    给用户单独添加权限（不依赖角色）
    参数:
        - user_id: 用户ID
        - permission_codes: 权限代码列表 (如 ["can_approve_posts", "can_manage_courses"])
    """
    user_id = request.data.get("user_id")
    permission_codes = request.data.get("permission_codes", [])

    if not user_id or not isinstance(permission_codes, list):
        return Response({"error": "参数错误，请提供 user_id 和 权限代码列表"}, status=status.HTTP_400_BAD_REQUEST)

    user = get_object_or_404(User, id=user_id)
    permissions = Permission.objects.filter(code__in=permission_codes)

    if not permissions.exists():
        return Response({"error": "无效的权限代码"}, status=status.HTTP_400_BAD_REQUEST)

    # 为用户单独绑定权限（可以存在一个 m2m 表，比如 user_permissions）
    # 若未定义，可直接记录在 role 权限中返回时合并展示
    user_permissions_field = getattr(user, "permissions", None)
    if user_permissions_field is not None:
        user.permissions.add(*permissions)
    else:
        return Response({"error": "用户模型未定义单独权限字段"}, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "message": f"已成功为用户 {user.username} 添加权限",
        "permissions": [p.code for p in permissions],
    }, status=status.HTTP_200_OK)