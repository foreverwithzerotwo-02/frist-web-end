from django.db import models
from django.db.models import Max, F
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
import random
from decimal import Decimal

# 课程相关图片存放路径
BASIC_COURSE_IMG_URL = 'courses/'


# 课程分类
class CourseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名称")
    description = models.TextField(blank=True, null=True, verbose_name="分类描述")
    order = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    # 初始化排序
    def save(self, *args, **kwargs):
        if self.pk is None:
            max_order = CourseCategory.objects.aggregate(max_order=Max("order"))["max_order"]
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

    # 删除重置排序
    def delete(self, *args, **kwargs):
        current_order = self.order
        super().delete(*args, **kwargs)
        # 删除后，把后面的记录 order 往前移一位
        CourseCategory.objects.filter(order__gt=current_order).update(order=F("order") - 1)

    class Meta:
        ordering = ["order"]  # 默认按照 order 排序


# 全部课程
class Course(models.Model):
    title = models.CharField(max_length=200, verbose_name="课程标题")
    description = models.TextField(blank=True, null=True, verbose_name="课程简介")
    cover_image = models.ImageField(upload_to=BASIC_COURSE_IMG_URL + 'course_covers', verbose_name="封面图片链接")
    order = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL,
                                 null=True,
                                 blank=True,
                                 related_name="courses",
                                 verbose_name="课程分类")
    # ⭐ 平均评分，固定一位小数
    rating = models.DecimalField(
        max_digits=2,      # 总位数（整数+小数）
        decimal_places=1,  # 一位小数
        default=5,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        verbose_name="平均评分"
    )
    rating_count = models.PositiveIntegerField(default=35, verbose_name="评分人数")

    total_views = models.PositiveIntegerField(default=1, verbose_name="总浏览量")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    def __str__(self):
        return self.title

    # 初始化排序
    def save(self, *args, **kwargs):
        if self.pk is None:
            # 生成随机评分和人数
            self.rating = Decimal(str(round(random.uniform(4.0, 5.0), 1)))
            self.rating_count = random.randint(50, 400)
            self.total_views = random.randint(100, 700)

            # 初始化排序
            max_order = Course.objects.aggregate(max_order=Max("order"))["max_order"]
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

    # 删除重置排序
    def delete(self, *args, **kwargs):
        current_order = self.order
        super().delete(*args, **kwargs)
        # 删除后，把后面的记录 order 往前移一位
        Course.objects.filter(order__gt=current_order).update(order=F("order") - 1)

    class Meta:
        ordering = ["order"]  # 默认按照 order 排序


# 用户课程浏览记录
class CourseViewHistory(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        related_name="view_history",
        verbose_name="用户"
    )
    course = models.ForeignKey(
        "Course",
        on_delete=models.CASCADE,
        related_name="viewed_by",
        verbose_name="课程"
    )
    last_viewed_at = models.DateTimeField(auto_now=True, verbose_name="最近浏览时间")
    view_count = models.PositiveIntegerField(default=1, verbose_name="该用户浏览次数")

    class Meta:
        verbose_name = "课程浏览历史"
        verbose_name_plural = "课程浏览历史"
        unique_together = ("user", "course")  # 一个用户对同一课程只保留一条记录
        ordering = ["-last_viewed_at"]  # 默认按时间倒序

    def __str__(self):
        return f"{self.user.username} 浏览了 {self.course.title}"


# 用户对课程的评分表
class CourseRating(models.Model):
    user = models.ForeignKey(
        "users.User",
        on_delete=models.CASCADE,
        verbose_name="用户"
    )
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="ratings",
        verbose_name="课程"
    )
    score = models.DecimalField(
        max_digits=2,
        decimal_places=1,  # 保留一位小数
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name="评分 (1~5)"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="评分时间")

    class Meta:
        unique_together = ("user", "course")  # 一个用户只能给一个课程打一次分

    def __str__(self):
        return f"{self.user.username} -> {self.course.title}: {self.score}"


# 用户收藏课程
class CourseFavorite(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="favorites", verbose_name="用户")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="favorited_by", verbose_name="课程")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="收藏时间")

    class Meta:
        unique_together = ("user", "course")  # 防止重复收藏


# 用户学习进度
class CourseProgress(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="progresses", verbose_name="用户")
    course = models.ForeignKey("Course", on_delete=models.CASCADE, related_name="progresses", verbose_name="课程")
    chapter = models.ForeignKey("Chapter", on_delete=models.CASCADE, related_name="progresses", verbose_name="章节")
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")
    completed_at = models.DateTimeField(blank=True, null=True, verbose_name="完成时间")

    class Meta:
        unique_together = ("user", "chapter")  # 一个用户一章只能有一条进度记录


# 全部章节
class Chapter(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name="chapters")
    title = models.CharField(max_length=200, verbose_name="章节标题", default="未命名章节", blank=True, null=True)
    content = models.TextField(verbose_name="章节富文本内容", blank=True, null=True)
    order = models.PositiveIntegerField(null=True, blank=True, db_index=True)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.course.title} 的全部章节"

    # 初始化排序
    def save(self, *args, **kwargs):
        if self.pk is None:
            max_order = Chapter.objects.filter(course_id=self.course_id).aggregate(max_order=Max("order"))["max_order"]
            self.order = (max_order or 0) + 1
        super().save(*args, **kwargs)

    # 删除重置排序
    def delete(self, *args, **kwargs):
        current_order = self.order
        course_id = self.course_id
        super().delete(*args, **kwargs)
        # 删除后，把后面的记录 order 往前移一位
        Chapter.objects.filter(course_id=course_id, order__gt=current_order).update(order=F("order") - 1)

    class Meta:
        ordering = ["order"]  # 默认按照 order 排序


# 章节富文本插图
class ChapterImage(models.Model):
    chapter = models.ForeignKey(Chapter, on_delete=models.CASCADE,
                                related_name='images',
                                verbose_name='所属章节')
    image = models.ImageField(upload_to=BASIC_COURSE_IMG_URL + 'chapter_images', verbose_name="章节插图")
    is_used = models.BooleanField(default=False)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.chapter.title} 的图片 - {self.image.name}"
