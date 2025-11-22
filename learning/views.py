from django.http import JsonResponse
from .models import Course, Chapter, CourseFavorite, CourseRating, CourseViewHistory
from .serializers import CourseFavoriteSerializer, CourseViewHistorySerializer, CourseSerializer
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticatedOrReadOnly
from django.db.models import F, ExpressionWrapper, FloatField
from django.db.models.functions import Log, Exp, Cast

#  引入创建完整 url 路径
from utils.media import get_full_media_url


# 指定获取的课程
@api_view(["GET"])
def get_courses(request):
    """
    获取指定课程信息（支持多个）
    - ?ids=1,2,3
    - 如果不传 ids，返回所有课程
    """
    ids = request.query_params.get("ids")

    if ids:
        try:
            ids = [int(i) for i in ids.split(",") if i.strip().isdigit()]
        except ValueError:
            return Response({"error": "ids 参数格式错误"}, status=status.HTTP_400_BAD_REQUEST)

        courses = Course.objects.filter(id__in=ids)
        if not courses.exists():
            return Response({"error": "未找到课程"}, status=status.HTTP_404_NOT_FOUND)
    else:
        courses = Course.objects.all().order_by("-created_at")

    serializer = CourseSerializer(courses, many=True, context={"request": request})
    return Response(serializer.data, status=status.HTTP_200_OK)


# 课程收藏
class CourseFavoriteViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """获取当前用户收藏的全部课程"""
        favorites = CourseFavorite.objects.filter(user=request.user).select_related("course")
        serializer = CourseFavoriteSerializer(favorites, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def create(self, request, course_id=None):
        """用户收藏课程"""
        course = get_object_or_404(Course, id=course_id)
        favorite, created = CourseFavorite.objects.get_or_create(user=request.user, course=course)
        if created:
            return Response({"message": "课程已收藏"}, status=status.HTTP_201_CREATED)
        return Response({"message": "你已经收藏过了"}, status=status.HTTP_200_OK)

    def destroy(self, request, course_id=None):
        """用户取消收藏"""
        course = get_object_or_404(Course, id=course_id)
        favorite = CourseFavorite.objects.filter(user=request.user, course=course)
        if favorite.exists():
            favorite.delete()
            return Response({"message": "取消收藏成功"}, status=status.HTTP_204_NO_CONTENT)
        return Response({"message": "你还没有收藏该课程"}, status=status.HTTP_400_BAD_REQUEST)


# 获取最受欢迎课程
@api_view(["GET"])
def popular_courses(request):
    """
    获取最受欢迎课程（带分类名称）
    - 可传参数 limit=5 指定获取数量
    """
    limit = request.query_params.get("limit", 5)
    try:
        limit = int(limit)
    except ValueError:
        return Response({"error": "limit 参数必须是整数"}, status=status.HTTP_400_BAD_REQUEST)

    # 计算受欢迎度得分
    queryset = Course.objects.annotate(
        rating_weight=ExpressionWrapper(
            1 - Exp(-Cast(F("rating_count"), FloatField()) / 50.0),
            output_field=FloatField()
        ),
        popularity=ExpressionWrapper(
            (F("rating") * F("rating_weight") * 0.6) +
            (Log(F("rating_count") + 1, 10) * 0.2) +
            (Log(F("total_views") + 1, 10) * 0.2),
            output_field=FloatField()
        )
    ).order_by("-popularity", "-created_at")[:limit]

    # 手动构造返回数据
    data = []
    for course in queryset:
        data.append({
            "id": course.id,
            "title": course.title,
            "description": course.description,
            "cover_image": request.build_absolute_uri(course.cover_image.url) if course.cover_image else None,
            "rating": float(course.rating),
            "rating_count": course.rating_count,
            "total_views": course.total_views,
            "created_at": course.created_at,
            "updated_at": course.updated_at,
            "category_name": course.category.name if course.category else None,
        })

    return Response(data, status=status.HTTP_200_OK)


# 根据课程ID获取已发布的全部章节
@api_view(['GET'])
@permission_classes([IsAuthenticatedOrReadOnly])
@csrf_exempt
def get_published_chapters(request, course_id):
    try:
        # 获取课程
        course = Course.objects.values().get(id=course_id)
        # 返回图片完整的url路径
        course['cover_image'] = get_full_media_url(request, course['cover_image'])

        # 是否收藏
        is_favorited = False
        if request.user.is_authenticated:
            from .models import CourseFavorite
            is_favorited = CourseFavorite.objects.filter(
                user=request.user,
                course_id=course_id
            ).exists()
        course['is_favorited'] = is_favorited

        # 获取已发布章节
        chapters = list(
            Chapter.objects.filter(
                course_id=int(course_id),
                is_published=True
            ).order_by('order', 'id').values()
        )

        return JsonResponse({'course': course, 'chapters': chapters}, status=200)

    except Course.DoesNotExist:
        return JsonResponse({'error': '课程不存在'}, status=404)
    except Exception as err:
        return JsonResponse({'error': f'获取章节失败：{str(err)}'}, status=500)


# 给课程评分（支持修改评分）
@api_view(["POST"])
@permission_classes([IsAuthenticated])  # 必须登录才能评分
def rate_course(request, course_id):
    user = request.user
    score = request.data.get("score")

    if score is None:
        return Response({"error": "必须提供评分"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        score = float(score)
    except ValueError:
        return Response({"error": "评分必须是数字"}, status=status.HTTP_400_BAD_REQUEST)

    if score < 0 or score > 5:
        return Response({"error": "评分必须在 0-5 之间"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response({"error": "课程不存在"}, status=status.HTTP_404_NOT_FOUND)

    # 查找是否已有评分
    rating, created = CourseRating.objects.update_or_create(
        user=user,
        course=course,
        defaults={"score": round(score, 1)}  # 固定一位小数
    )

    # 重新计算课程的平均分和人数
    all_ratings = course.ratings.all()
    course.rating_count = all_ratings.count()
    course.rating = round(sum(r.score for r in all_ratings) / course.rating_count, 1)
    course.save()

    return Response({
        "message": "评分成功" if created else "评分已更新",
        "course_id": course.id,
        "rating": float(course.rating),
        "rating_count": course.rating_count
    })


# 记录课程浏览
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def record_course_view(request, course_id):
    user = request.user
    try:
        course = Course.objects.get(pk=course_id)
    except Course.DoesNotExist:
        return Response({"error": "课程不存在"}, status=status.HTTP_404_NOT_FOUND)

    # 更新课程总浏览量
    course.total_views += 1
    course.save()

    # 更新/新增用户的浏览记录
    history, created = CourseViewHistory.objects.get_or_create(
        user=user,
        course=course,
        defaults={"view_count": 1}
    )
    if not created:
        history.view_count += 1
        history.save()

    return Response({
        "message": "浏览已记录",
        "course_id": course.id,
        "total_views": course.total_views,
        "user_view_count": history.view_count,
        "last_viewed_at": history.last_viewed_at
    })


# 获取浏览历史
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_view_history(request):
    user = request.user

    # 获取前端传的 limit 参数，默认 20，最大 100
    limit = request.query_params.get("limit", 20)
    try:
        limit = int(limit)
    except ValueError:
        limit = 20
    limit = min(limit, 100)

    # 查询用户浏览历史（按时间倒序）
    histories = (
        CourseViewHistory.objects.filter(user=user)
        .select_related("course")
        .order_by("-last_viewed_at")[:limit]
    )

    serializer = CourseViewHistorySerializer(
        histories, many=True, context={"request": request}
    )

    return Response({
        "count": len(serializer.data),
        "results": serializer.data
    })


# 删除单条浏览历史
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_view_history(request, history_id):
    user = request.user
    try:
        history = CourseViewHistory.objects.get(id=history_id, user=user)
        history.delete()
        return Response({"message": "浏览记录已删除"})
    except CourseViewHistory.DoesNotExist:
        return Response({"error": "记录不存在"}, status=status.HTTP_404_NOT_FOUND)


# 清空所有浏览历史
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def clear_view_history(request):
    user = request.user
    deleted_count, _ = CourseViewHistory.objects.filter(user=user).delete()
    return Response({"message": f"已清空 {deleted_count} 条浏览记录"})
