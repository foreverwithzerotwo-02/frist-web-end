from django.urls import path
from . import admin_views

urlpatterns = [
    # 课程分类管理
    path('admin/get_course_category_list/', admin_views.get_course_category_list, name='get_course_category_list'),
    path('admin/add_course_category/', admin_views.add_course_category, name='add_course_category'),
    path('admin/update_course_category_value/', admin_views.update_course_category_value,
         name='update_course_category_value'),
    path('admin/update_course_category_order/', admin_views.update_course_category_order,
         name='update_course_category_order'),
    path('admin/delete_course_category_value/<int:category_id>/', admin_views.delete_course_category_value,
         name='delete_course_category_value'),

    # 课程管理
    path('admin/get_course_list/', admin_views.get_course_list, name='get_course_list'),
    path('admin/get_courses_by_category/', admin_views.get_courses_by_category, name='get_courses_by_category'),
    path('admin/add_course_value/', admin_views.add_course_value, name='add_course_value'),
    path('admin/update_course_value/', admin_views.update_course_value, name='update_course_value'),
    path('admin/update_course_order/', admin_views.update_course_order, name='update_course_order'),
    path('admin/delete_course_value/<int:id>/', admin_views.delete_course_value, name='delete_course_value'),

    # 章节管理
    path('admin/add_chapter/', admin_views.add_chapter, name='add_chapter'),
    path('admin/get_chapter_list/<int:course_id>/', admin_views.get_chapter_list, name='get_chapter_list'),
    path('admin/get_chapters_by_course/', admin_views.get_chapters_by_course, name='get_chapters_by_course'),
    path('admin/delete_chapter/', admin_views.delete_chapter, name='delete_chapter'),
    path('admin/update_chapter/', admin_views.update_chapter, name='update_chapter'),
    path('admin/update_chapter_order/', admin_views.update_chapter_order, name='update_chapter_order'),
    path('admin/upload_chapter_image/', admin_views.upload_chapter_image, name='upload_chapter_image'),
]
