from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),

    # 注册用户相关
    path('users/', include('users.urls')),

    # 注册 learning 和 后台 learning 学习的路由
    path('learning/', include('learning.admin_urls')),
    path('learning/', include('learning.urls')),

    # 注册 论坛 路由
    path('forum/', include('forum.admin_urls')),
    path('forum/', include('forum.urls')),

    # 资讯
    path("news/", include("news.urls")),
]

# 处理图片保存本地
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
