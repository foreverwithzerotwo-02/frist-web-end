from django.http import JsonResponse
from .models import Course, Chapter, ChapterImage, CourseCategory, CourseFavorite
from django.views.decorators.csrf import csrf_exempt
from django.db.models import F
import os
import json
import traceback

#  引入创建完整 url 路径
from utils.media import get_full_media_url, extract_image_urls_from_tiptap_json


# 获取全部课程分类
@csrf_exempt
def get_course_category_list(request):
    # 获取全部课程分类
    all_data = list(CourseCategory.objects.values())

    return JsonResponse({'message': '获取成功', 'data': all_data}, status=200)


# 获取分类下的全部课程
@csrf_exempt
# id：课程分类的id
def get_courses_by_category(request):
    if request.method != "POST":
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body)
        category_id = data.get("id")  # 分类 id

        if not category_id:
            return JsonResponse({"error": "请提供分类 id"}, status=400)

        # 获取分类
        try:
            category = CourseCategory.objects.get(id=category_id)
        except CourseCategory.DoesNotExist:
            return JsonResponse({"error": "分类不存在"}, status=404)

        # 获取课程（默认按 order 排序，因为 Meta 里写了 ordering = ["order"]）
        courses = category.courses.all().values()

        # 返回图片完整的url路径
        for data in courses:
            if data['cover_image']:
                data['cover_image'] = get_full_media_url(request, data['cover_image'])

        return JsonResponse({
            "category": {
                "id": category.id,
                "name": category.name,
                "description": category.description,
            },
            "courses": list(courses)
        }, status=200)

    except Exception as err:
        return JsonResponse({"error": f"获取课程失败：{str(err)}"}, status=500)


# 新增课程分类
@csrf_exempt
def add_course_category(request):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    data = json.loads(request.body)
    name = data.get('name')  # 分类名称
    description = data.get('description')  # 分类简介

    try:
        CourseCategory.objects.create(name=name, description=description)

        return JsonResponse({'message': '添加课程分类成功'}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'添加课程分类失败：{str(err)}'}, status=500)


# 修改课程分类数据
@csrf_exempt
def update_course_category_value(request):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    data = json.loads(request.body)
    category_id = data.get('id')
    name = data.get('name')
    description = data.get('description')

    print(name, category_id, description)

    try:
        category = CourseCategory.objects.get(id=category_id)

        if name:
            category.name = name

        if description:
            category.description = description

        category.save()
        return JsonResponse({'message': '修改成功'}, status=200)

    except Course.DoesNotExist:
        return JsonResponse({'error': '分类不存在'}, status=404)
    except Exception as err:
        return JsonResponse({'error': f'修改失败：{str(err)}'}, status=500)


# 修改课程分类排序
@csrf_exempt
def update_course_category_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body)
        orders = data.get("orders", [])

        if not isinstance(orders, list) or not orders:
            return JsonResponse({"error": "请传入非空的 orders 数组"}, status=400)

        # 批量更新
        for item in orders:
            category_id = item.get("id")
            new_order = item.get("order")
            if category_id and new_order is not None:
                CourseCategory.objects.filter(id=category_id).update(order=new_order)

        return JsonResponse({"message": "排序更新成功"}, status=200)

    except Exception as err:
        return JsonResponse({"error": f"排序更新失败：{str(err)}"}, status=500)


# 删除课程分类
@csrf_exempt
def delete_course_category_value(request, category_id):
    if request.method != 'DELETE':
        return JsonResponse({'error': '只支持 DELETE 请求'}, status=405)
    if category_id is None:
        return JsonResponse({'error': '没有获取到需要删除的分类 ID'}, status=505)

    try:
        category = CourseCategory.objects.get(id=category_id)
        category.delete()
        return JsonResponse({'message': '删除成功'}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'删除失败：{str(err)}'}, status=500)


# 获取全部课程数据
def get_course_list(request):
    # 获取课程表全部数据
    all_data = list(Course.objects.values())

    for data in all_data:
        # 处理封面图片完整 URL
        if data['cover_image']:
            data['cover_image'] = get_full_media_url(request, data['cover_image'])

        # 判断是否收藏
        is_favorited = False
        if request.user.is_authenticated:  # 登录才判断
            is_favorited = CourseFavorite.objects.filter(
                user=request.user,
                course_id=data['id']
            ).exists()
        data['is_favorited'] = is_favorited

    return JsonResponse(all_data, safe=False)


# 新增课程表数据
@csrf_exempt
def add_course_value(request):
    title = request.POST.get('title')
    description = request.POST.get('description')
    category = request.POST.get('category_id')
    cover_image = request.FILES.get('cover_image')

    try:
        Course.objects.create(title=title, description=description, category_id=category, cover_image=cover_image)

        return JsonResponse({'message': '添加成功'}, status=200)

    except Exception as err:
        return JsonResponse({'error': f'添加失败：{str(err)}'}, status=500)


# 修改课程表数据
@csrf_exempt
def update_course_value(request):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    course_id = request.POST.get('id')
    title = request.POST.get('title')
    description = request.POST.get('description')
    category = request.POST.get('category_id')
    new_cover_image = request.FILES.get('cover_image')

    try:
        course = Course.objects.get(id=course_id)

        if new_cover_image:
            # 如果原来有图片，删除旧的文件
            if course.cover_image:
                old_path = course.cover_image.path
                if os.path.isfile(old_path):
                    os.remove(old_path)

            course.cover_image = new_cover_image

        if category:
            course.category_id = category

        if title:
            course.title = title

        course.description = description

        course.save()
        return JsonResponse({'message': '修改成功'}, status=200)

    except Course.DoesNotExist:
        return JsonResponse({'error': '课程不存在'}, status=404)
    except Exception as err:
        return JsonResponse({'error': f'修改失败：{str(err)}'}, status=500)


# 修改课程排序
@csrf_exempt
def update_course_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body)
        orders = data.get("orders", [])

        if not isinstance(orders, list) or not orders:
            return JsonResponse({"error": "请传入非空的 orders 数组"}, status=400)

        # 批量更新
        for item in orders:
            course_id = item.get("id")
            new_order = item.get("order")
            if course_id and new_order is not None:
                Course.objects.filter(id=course_id).update(order=new_order)

        return JsonResponse({"message": "排序更新成功"}, status=200)

    except Exception as err:
        return JsonResponse({"error": f"排序更新失败：{str(err)}"}, status=500)


# 删除课程
@csrf_exempt
def delete_course_value(request, id):
    if request.method != 'DELETE':
        return JsonResponse({'error': '只支持 DELETE 请求'}, status=405)
    if id is None:
        return JsonResponse({'error': '没有获取到需要删除的课程 ID'}, status=505)

    try:
        course = Course.objects.get(id=id)
        course.delete()
        return JsonResponse({'message': '删除成功'}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'删除失败：{str(err)}'}, status=500)


# 新增课程章节
@csrf_exempt
def add_chapter(request):
    if request.method != 'POST':
        return JsonResponse({'error': '只支持 POST 请求'}, status=405)

    data = json.loads(request.body)
    print(data)
    course_id = data.get('course_id')  # 关联的课程 id
    title = data.get('title')  # 章节名称
    content = data.get('content')  # 章节富文本内容
    is_published = data.get('is_published')  # 是否为正式发布

    try:
        new_chapter = Chapter.objects.create(course_id=course_id, title=title, content=content,
                                             is_published=is_published)

        return JsonResponse({'message': '添加章节成功', 'data': {'id': new_chapter.id}}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'新增章节失败：{str(err)}'}, status=500)


# 获取全部章节
@csrf_exempt
def get_chapter_list(request, course_id):
    if request.method != 'GET':
        return JsonResponse({'error': '只支持 GET 请求'}, status=405)

    try:
        course = Course.objects.get(id=course_id)
        chapters = list(course.chapters.values())

        for chapter in chapters:
            # 保存课程名称
            chapter['course_title'] = course.title

        return JsonResponse({'message': '获取全部章节成功', 'all_chapters': chapters}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'获取全部章节失败：{str(err)}'}, status=500)


# 获取课程下的全部章节
@csrf_exempt
def get_chapters_by_course(request):
    if request.method != "POST":
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body)
        course_id = data.get("id")  # 课程 id

        if not course_id:
            return JsonResponse({"error": "请提供课程 id"}, status=400)

        # 获取课程
        try:
            course = Course.objects.values().get(id=course_id)
            # 返回图片完整的url路径
            course['cover_image'] = get_full_media_url(request, course['cover_image'])
        except Course.DoesNotExist:
            return JsonResponse({"error": "课程不存在"}, status=404)

        # 获取课程下的章节（默认按 order 排序）
        chapters = list(Chapter.objects.filter(course_id=course_id).values())

        return JsonResponse({
            "course": course,       # 课程的全部字段
            "chapters": chapters    # 当前课程下的全部章节
        }, status=200)

    except Exception as err:
        return JsonResponse({"error": f"获取章节失败：{str(err)}"}, status=500)


# 删除章节
@csrf_exempt
def delete_chapter(request):
    if request.method != 'POST':
        return JsonResponse({'error': '该请求只允许 POST 请求方式'}, status=405)

    try:
        # 获取要删除的章节
        data = json.loads(request.body)
        ids = data.get('ids', [])

        if not isinstance(ids, list) or not ids:
            return JsonResponse({'error': '请传入非空的 ID 数组'}, status=400)

        # 删除
        chapters_to_delete = Chapter.objects.filter(id__in=ids)
        for chapter in chapters_to_delete:
            Chapter.objects.filter(course_id=chapter.course_id, order__gt=chapter.order).update(order=F("order") - 1)

        chapters_to_delete.delete()

        return JsonResponse({'message': '删除章节成功'}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'删除章节失败：{str(err)}'}, status=500)


# 更新章节内容
@csrf_exempt
def update_chapter(request):
    if request.method != 'POST':
        return JsonResponse({'error': '该请求只允许 POST 请求方式'}, status=405)

    # 获取更新内容
    data = json.loads(request.body)
    chapter_id = data.get('chapter_id')
    course_id = data.get('course_id')
    title = data.get('title')
    content = data.get('content')
    is_published = data.get('is_published')

    if not chapter_id:
        return JsonResponse({'error': '未查到章节 ID', 'message': '请传入需要修改的章节 ID'}, status=400)

    try:
        # 获取修改章节
        chapter = Chapter.objects.get(id=chapter_id)
        if course_id:
            chapter.course_id = course_id
        if title:
            chapter.title = title
        if content:
            chapter.content = content
        if is_published:
            chapter.is_published = is_published
        chapter.save()

        image_urls = extract_image_urls_from_tiptap_json(json.loads(content))
        ChapterImage.objects.filter(chapter_id=chapter_id).update(is_used=False)
        for url in image_urls:
            if 'chapter_images/' in url:
                path = url.split('/media/')[-1]
                ChapterImage.objects.filter(image=path).update(is_used=True)
        # 删除掉没用的图片
        ChapterImage.objects.filter(is_used=False).delete()

        return JsonResponse({'message': '更新章节成功'}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'更新章节失败：{str(err)}'}, status=500)


# 修改章节排序
@csrf_exempt
def update_chapter_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "只支持 POST 请求"}, status=405)

    try:
        data = json.loads(request.body)
        orders = data.get("orders", [])

        if not isinstance(orders, list) or not orders:
            return JsonResponse({"error": "请传入非空的 orders 数组"}, status=400)

        # 批量更新
        for item in orders:
            chapter_id = item.get("id")
            new_order = item.get("order")
            if chapter_id and new_order is not None:
                Chapter.objects.filter(id=chapter_id).update(order=new_order)

        return JsonResponse({"message": "排序更新成功"}, status=200)

    except Exception as err:
        return JsonResponse({"error": f"排序更新失败：{str(err)}"}, status=500)


# 上传章节插图
@csrf_exempt
def upload_chapter_image(request):
    if request.method != 'POST':
        return JsonResponse({'error': '该请求只允许 POST 请求方式'}, status=405)

    img = request.FILES.get('image')
    chapter_id = request.POST.get('chapter_id')

    if not img:
        return JsonResponse({'error': '没有图片', 'message': '请传入图片'}, status=400)
    if not chapter_id:
        return JsonResponse({'error': '没有章节 ID', 'message': '请传入章节 ID '}, status=400)

    try:
        chapter_image = ChapterImage.objects.create(chapter_id=chapter_id, image=img, is_used=False)
        image = get_full_media_url(request, str(chapter_image.image))
        return JsonResponse({'message': '图片上传成功', 'image_url': image}, status=200)
    except Exception as err:
        return JsonResponse({'error': f'图片上传失败：{str(err)}'}, status=500)
