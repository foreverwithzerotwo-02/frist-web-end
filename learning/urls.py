from . import views
from django.urls import path

# 获取全部收藏
course_favorite_list = views.CourseFavoriteViewSet.as_view({
    'get': 'list'
})

# 收藏、取消收藏（需要 course_id）
course_favorite = views.CourseFavoriteViewSet.as_view({
    'post': 'create',     # 收藏
    'delete': 'destroy',  # 取消收藏
})

urlpatterns = [
    # 获取指定课程
    path("courses/", views.get_courses, name="get_courses"),
    # 获取全部收藏课程
    path("courses/favorite/", course_favorite_list, name="course_favorite_list"),
    # 获取最受欢迎课程
    path("courses/popular/", views.popular_courses, name="popular_courses"),
    # 收藏/取消收藏
    path("courses/<int:course_id>/favorite/", course_favorite, name="course_favorite"),
    # 根据课程id获取全部章节
    path('get_published_chapters/<int:course_id>/', views.get_published_chapters, name='get_published_chapters'),
    # 给课程评分
    path("courses/<int:course_id>/rate/", views.rate_course, name="rate_course"),
    # 记录课程浏览
    path("courses/<int:course_id>/view/", views.record_course_view, name="record_course_view"),
    # 获取用户最近浏览记录
    path("users/view-history/", views.get_view_history, name="get_view_history"),
    # 删除单条浏览记录
    path("course/history/<int:history_id>/", views.delete_view_history, name="delete_view_history"),
    # 清空浏览记录
    path("course/history/clear/", views.clear_view_history, name="clear_view_history"),
]
