from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from .models import ForumCategory


# 创建分类
@api_view(["POST"])
def create_category(request):
    name = request.data.get("name")
    description = request.data.get("description", "")

    if not name:
        return Response({"error": "分类名不能为空"}, status=status.HTTP_400_BAD_REQUEST)

    # 避免重复
    if ForumCategory.objects.filter(name=name).exists():
        return Response({"error": "该分类已存在"}, status=status.HTTP_400_BAD_REQUEST)

    category = ForumCategory.objects.create(name=name, description=description)
    return Response({
        "message": "分类创建成功",
        "id": category.id,
        "name": category.name,
        "description": category.description,
        "created_at": category.created_at
    }, status=status.HTTP_201_CREATED)


# 获取所有分类
@api_view(["GET"])
def list_categories(request):
    categories = ForumCategory.objects.all().order_by("id")
    data = [
        {
            "id": c.id,
            "name": c.name,
            "description": c.description,
            "created_at": c.created_at
        }
        for c in categories
    ]
    return Response(data)


# 修改分类
@api_view(["PUT", "PATCH"])
def update_category(request, pk):
    try:
        category = ForumCategory.objects.get(pk=pk)
    except ForumCategory.DoesNotExist:
        return Response({"error": "分类不存在"}, status=status.HTTP_404_NOT_FOUND)

    name = request.data.get("name")
    description = request.data.get("description")

    if name:
        # 避免重名（排除当前分类）
        if ForumCategory.objects.filter(name=name).exclude(pk=pk).exists():
            return Response({"error": "该分类名已存在"}, status=status.HTTP_400_BAD_REQUEST)
        category.name = name

    if description is not None:
        category.description = description

    category.save()

    return Response({
        "message": "分类修改成功",
        "id": category.id,
        "name": category.name,
        "description": category.description
    })


# 删除分类
@api_view(["DELETE"])
def delete_category(request, pk):
    try:
        category = ForumCategory.objects.get(pk=pk)
    except ForumCategory.DoesNotExist:
        return Response({"error": "分类不存在"}, status=status.HTTP_404_NOT_FOUND)

    category.delete()
    return Response({"message": "分类删除成功"}, status=status.HTTP_200_OK)
