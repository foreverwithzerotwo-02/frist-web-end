from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly
from django.shortcuts import get_object_or_404
from .models import ForumPost, ForumCategory, ForumPostImage, ForumFavorite, ForumLike, ForumComment
from .serializers import ForumPostSerializer, CommentSerializer
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q


# 分页配置
class PostPagination(PageNumberPagination):
    page_size = 10  # 默认每页 10 条
    page_size_query_param = "page_size"
    max_page_size = 50


# 获取帖子列表
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def list_posts(request):
    """
    帖子列表（带作者信息、is_liked、is_favorited）
    支持 ?category=xxx & ?page= & ?page_size=
    """
    queryset = ForumPost.objects.filter(is_draft=False).order_by("-is_pinned", "-created_at")

    category_id = request.query_params.get("category")
    if category_id:
        queryset = queryset.filter(category_id=category_id)

    # 为避免 N+1 查询：预取关联 author, category
    queryset = queryset.select_related("author", "category")

    paginator = PostPagination()
    page = paginator.paginate_queryset(queryset, request)  # page 是 list of ForumPost

    # 获取当前页的 post id 列表
    post_ids = [p.id for p in page]

    # 如果用户已登录，批量查询该用户在这些帖子上的 like / favorite
    user = request.user if request.user and request.user.is_authenticated else None
    liked_post_ids = set()
    favorited_post_ids = set()
    if user:
        liked_post_ids = set(
            ForumLike.objects.filter(user=user, post_id__in=post_ids).values_list("post_id", flat=True)
        )
        favorited_post_ids = set(
            ForumFavorite.objects.filter(user=user, post_id__in=post_ids).values_list("post_id", flat=True)
        )

    results = []
    for post in page:
        author = post.author
        # 安全取作者字段（避免 author 没有某字段导致异常）
        avatar_url = None
        if getattr(author, "avatar", None):
            try:
                avatar_url = request.build_absolute_uri(author.avatar.url)
            except Exception:
                avatar_url = None

        author_data = {
            "id": getattr(author, "id", None),
            "username": getattr(author, "username", None),
            "nickname": getattr(author, "nickname", None),
            "avatar": avatar_url,
            "bio": getattr(author, "bio", None),
        }

        # 可选：帖子图片缩略（只取第一张）或全部图片 url
        images = []
        if hasattr(post, "images"):  # related_name = "images"
            for img in post.images.all():
                try:
                    images.append(request.build_absolute_uri(img.image.url))
                except Exception:
                    pass

        item = {
            "id": post.id,
            "title": post.title,
            "excerpt": (post.content[:200] + "...") if post.content and len(post.content) > 200 else post.content,
            "content": post.content,  # 列表中可以只返回 excerpt，视前端需求调整
            "category_id": post.category.id if post.category else None,
            "category_name": post.category.name if post.category else None,
            "is_draft": post.is_draft,
            "view_count": post.view_count,
            "like_count": post.like_count,
            "favorite_count": post.favorite_count,
            "is_pinned": post.is_pinned,
            "created_at": post.created_at,
            "updated_at": post.updated_at,
            "author": author_data,
            "images": images,
            "is_liked": (post.id in liked_post_ids) if user else False,
            "is_favorited": (post.id in favorited_post_ids) if user else False,
        }
        results.append(item)

    # paginator.get_paginated_response 能接收我们构造的 results 列表
    return paginator.get_paginated_response(results)


# 获取用户帖子
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_user_posts(request):
    """
    获取当前用户的帖子
    - 支持分页 ?page=1&page_size=10
    - 支持数量限制 ?limit=5
    """
    queryset = (
        ForumPost.objects.filter(author=request.user, is_draft=False)
        .annotate(
            reply_count=Count("comments", filter=Q(comments__is_deleted=False))
        )
        .order_by("-created_at")
    )

    # 如果传了 limit，就不分页，直接取前 N 条
    limit = request.query_params.get("limit")
    if limit:
        try:
            limit = int(limit)
            queryset = queryset[:limit]
        except ValueError:
            return Response({"error": "limit 参数必须是整数"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = ForumPostSerializer(queryset, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    # 否则走分页
    paginator = PostPagination()
    page = paginator.paginate_queryset(queryset, request)
    serializer = ForumPostSerializer(page, many=True, context={"request": request})
    return paginator.get_paginated_response(serializer.data)


# 获取单帖详情
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def get_post_detail(request, post_id):
    """
    单帖详情（带作者信息、图片、is_liked、is_favorited）
    """
    post = get_object_or_404(ForumPost, id=post_id)

    # 增加浏览量
    post.view_count = post.view_count + 1
    post.save(update_fields=["view_count"])

    author = post.author
    avatar_url = None
    if getattr(author, "avatar", None):
        try:
            avatar_url = request.build_absolute_uri(author.avatar.url)
        except Exception:
            avatar_url = None

    author_data = {
        "id": getattr(author, "id", None),
        "username": getattr(author, "username", None),
        "nickname": getattr(author, "nickname", None),
        "avatar": avatar_url,
        "bio": getattr(author, "bio", None),
    }

    # 图片列表
    images = []
    if hasattr(post, "images"):
        for img in post.images.all():
            try:
                images.append(request.build_absolute_uri(img.image.url))
            except Exception:
                pass

    user = request.user if request.user and request.user.is_authenticated else None
    is_liked = False
    is_favorited = False
    if user:
        is_liked = ForumLike.objects.filter(user=user, post=post).exists()
        is_favorited = ForumFavorite.objects.filter(user=user, post=post).exists()

    data = {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "category_id": post.category.id if post.category else None,
        "category_name": post.category.name if post.category else None,
        "is_draft": post.is_draft,
        "view_count": post.view_count,
        "like_count": post.like_count,
        "favorite_count": post.favorite_count,
        "is_pinned": post.is_pinned,
        "created_at": post.created_at,
        "updated_at": post.updated_at,
        "author": author_data,
        "images": images,
        "is_liked": is_liked,
        "is_favorited": is_favorited,
    }
    return Response(data)


# 创建帖子
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_post(request):
    print(request.data)
    title = request.data.get("title")
    content = request.data.get("content")
    category_id = request.data.get("category")
    is_draft = request.data.get("is_draft", False)

    category = None
    if category_id:
        category = get_object_or_404(ForumCategory, id=category_id)

    post = ForumPost.objects.create(
        title=title,
        content=content,
        category=category,
        is_draft=is_draft,
        author=request.user,
    )

    serializer = ForumPostSerializer(post)
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# 获取用户草稿列表
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def list_drafts(request):
    drafts = ForumPost.objects.filter(author=request.user, is_draft=True).order_by("-updated_at")
    serializer = ForumPostSerializer(drafts, many=True)
    return Response(serializer.data)


# 删除帖子
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_post(request, pk):
    post = get_object_or_404(ForumPost, pk=pk, author=request.user)
    post.delete()
    return Response({"message": "帖子已删除"}, status=status.HTTP_204_NO_CONTENT)


# 上传帖子插图
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # 必须登录
def upload_post_image(request, post_id):
    """
    上传帖子图片
    """
    try:
        post = ForumPost.objects.get(id=post_id, author=request.user)
    except ForumPost.DoesNotExist:
        return Response({"error": "帖子不存在或无权限"}, status=status.HTTP_404_NOT_FOUND)

    if "image" not in request.FILES:
        return Response({"error": "请上传图片"}, status=status.HTTP_400_BAD_REQUEST)

    image = request.FILES["image"]
    post_image = ForumPostImage.objects.create(post=post, image=image)

    return Response({
        "message": "图片上传成功",
        "image_url": request.build_absolute_uri(post_image.image.url)
    }, status=status.HTTP_201_CREATED)


# 修改帖子
@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_post(request, post_id):
    """
    修改帖子
    - 可以修改标题、内容、分类、是否草稿
    - 如果草稿要发布，必须保证标题和内容不为空
    """
    post = get_object_or_404(ForumPost, id=post_id, author=request.user)

    title = request.data.get("title", post.title)
    content = request.data.get("content", post.content)
    category_id = request.data.get("category", post.category.id if post.category else None)
    is_draft = request.data.get("is_draft", post.is_draft)

    # 如果用户要发布帖子，校验标题和内容
    if not is_draft and (not title or not content):
        return Response(
            {"error": "发布帖子时，标题和内容不能为空"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # 分类更新
    category = None
    if category_id:
        category = get_object_or_404(ForumCategory, id=category_id)

    # 更新字段
    post.title = title
    post.content = content
    post.category = category
    post.is_draft = is_draft
    post.save()

    serializer = ForumPostSerializer(post, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 点赞/取消点赞
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_like_post(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    user = request.user

    like, created = ForumLike.objects.get_or_create(user=user, post=post)
    if not created:
        # 已经点赞过 -> 取消点赞
        like.delete()
        post.like_count = post.likes.count()
        post.save(update_fields=["like_count"])
        return Response({"message": "取消点赞成功", "like_count": post.like_count})

    # 新点赞
    post.like_count = post.likes.count()
    post.save(update_fields=["like_count"])
    return Response({"message": "点赞成功", "like_count": post.like_count})


# 收藏/取消收藏
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def toggle_favorite_post(request, post_id):
    post = get_object_or_404(ForumPost, id=post_id)
    user = request.user

    favorite, created = ForumFavorite.objects.get_or_create(user=user, post=post)
    if not created:
        # 已经收藏过 -> 取消收藏
        favorite.delete()
        post.favorite_count = post.favorites.count()
        post.save(update_fields=["favorite_count"])
        return Response({"message": "取消收藏成功", "favorite_count": post.favorite_count})

    # 新收藏
    post.favorite_count = post.favorites.count()
    post.save(update_fields=["favorite_count"])
    return Response({"message": "收藏成功", "favorite_count": post.favorite_count})


# ✅ 创建评论
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_comment(request, post_id):
    """
    给帖子添加评论或回复
    """
    post = get_object_or_404(ForumPost, id=post_id, is_draft=False)
    parent_id = request.data.get("parent")
    content = request.data.get("content")

    if not content:
        return Response({"error": "评论内容不能为空"}, status=status.HTTP_400_BAD_REQUEST)

    parent = None
    if parent_id:
        parent = get_object_or_404(ForumComment, id=parent_id, post=post)

    comment = ForumComment.objects.create(
        post=post, user=request.user, content=content, parent=parent
    )

    serializer = CommentSerializer(comment, context={"request": request})
    return Response(serializer.data, status=status.HTTP_201_CREATED)


# ✅ 获取评论列表
@api_view(["GET"])
@permission_classes([IsAuthenticatedOrReadOnly])
def list_comments(request, post_id):
    """
    获取帖子下的所有评论（仅顶级评论，子评论在 replies 里）
    """
    post = get_object_or_404(ForumPost, id=post_id, is_draft=False)
    comments = ForumComment.objects.filter(post=post, parent=None).order_by("-created_at")

    serializer = CommentSerializer(comments, many=True, context={"request": request})
    return Response(serializer.data)


# ✅ 删除评论（软删除）
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_comment(request, comment_id):
    """
    用户删除自己的评论 → 软删除
    """
    comment = get_object_or_404(ForumComment, id=comment_id)

    if comment.author != request.user:
        return Response({"error": "没有权限删除该评论"}, status=status.HTTP_403_FORBIDDEN)

    comment.is_deleted = True
    comment.content = "[该评论已被删除]"
    comment.save()

    return Response({"message": "评论已删除"}, status=status.HTTP_200_OK)
