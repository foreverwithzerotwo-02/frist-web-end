from django.urls import path
from . import views

urlpatterns = [
    # 获取帖子
    path("posts/", views.list_posts, name="list_posts"),
    # 获取对应用户的全部帖子
    path("posts/user/", views.list_user_posts, name="list_user_posts"),
    # 获取单帖详细信息
    path("posts/<int:post_id>/", views.get_post_detail, name="post_detail"),
    # 创建帖子
    path("posts/create/", views.create_post, name="create_post"),
    # 获取帖子草稿
    path("posts/drafts/", views.list_drafts, name="list_drafts"),
    # 删除帖子
    path("posts/delete/<int:pk>/", views.delete_post, name="delete_post"),
    # 上传帖子插图
    path("posts/<int:post_id>/upload_image/", views.upload_post_image, name="upload_post_image"),
    # 更新帖子
    path("posts/<int:post_id>/update/", views.update_post, name="update_post"),
    # 点赞帖子
    path("posts/<int:post_id>/like/", views.toggle_like_post, name="toggle_like_post"),
    # 收藏帖子
    path("posts/<int:post_id>/favorite/", views.toggle_favorite_post, name="toggle_favorite_post"),
    # 获取帖子对应评论
    path("posts/<int:post_id>/comments/", views.list_comments, name="list_comments"),
    # 创建评论
    path("posts/<int:post_id>/comments/create/", views.create_comment, name="create_comment"),
    # 软删除评论
    path("comments/<int:comment_id>/delete/", views.delete_comment, name="delete_comment"),
]
