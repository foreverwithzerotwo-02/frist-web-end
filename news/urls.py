from django.urls import path
from .views import news_list

urlpatterns = [
    # 获取新闻资讯
    path("", news_list, name="news_list"),
]
