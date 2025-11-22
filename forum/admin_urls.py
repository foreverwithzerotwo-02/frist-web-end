from . import admin_views
from django.urls import path

urlpatterns = [
    # 获取全部论坛分类
    path("admin/categories/", admin_views.list_categories, name="list_categories"),
    # 新增论坛分类
    path("admin/categories/create/", admin_views.create_category, name="create_category"),
    # 更新论坛分类
    path("admin/categories/<int:pk>/update/", admin_views.update_category, name="update_category"),
    # 删除论坛分类
    path("admin/categories/<int:pk>/delete/", admin_views.delete_category, name="delete_category"),
]