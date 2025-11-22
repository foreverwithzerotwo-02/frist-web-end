from django.db import models
from django.conf import settings
import random

User = settings.AUTH_USER_MODEL  # 用于兼容自定义用户表


# 分类
class ForumCategory(models.Model):
    name = models.CharField(max_length=100, unique=True, verbose_name="分类名")
    description = models.TextField(blank=True, null=True, verbose_name="分类描述")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


# 帖子
class ForumPost(models.Model):
    category = models.ForeignKey(
        ForumCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posts",
        verbose_name="所属分类"
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="forum_posts",
        verbose_name="作者"
    )
    title = models.CharField(max_length=200, blank=True, null=True, verbose_name="标题")
    content = models.TextField(blank=True, null=True, verbose_name="内容")
    is_draft = models.BooleanField(default=False, verbose_name="是否为草稿")
    view_count = models.PositiveIntegerField(default=0, verbose_name="浏览次数")
    like_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    favorite_count = models.PositiveIntegerField(default=0, verbose_name="收藏数")
    is_pinned = models.BooleanField(default=False, verbose_name="是否置顶")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    # 初始数据
    def save(self, *args, **kwargs):
        if self.pk is None:
            # 生成随机评分和人数
            self.view_count = random.randint(700, 5000)
            self.favorite_count = random.randint(50, 200)
            self.like_count = random.randint(200, 700)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title


# 帖子插图
class ForumPostImage(models.Model):
    post = models.ForeignKey(
        "ForumPost",
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="所属帖子"
    )
    image = models.ImageField(
        upload_to="forum/post_images/%Y/%m/",
        verbose_name="帖子图片"
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")

    def __str__(self):
        return f"图片 - {self.post.title}"


# 点赞表
class ForumLike(models.Model):
    post = models.ForeignKey(
        ForumPost,
        on_delete=models.CASCADE,
        related_name="likes",
        verbose_name="帖子"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="forum_likes",
        verbose_name="点赞用户"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} 👍 {self.post}"


# 收藏表
class ForumFavorite(models.Model):
    post = models.ForeignKey(
        ForumPost,
        on_delete=models.CASCADE,
        related_name="favorites",
        verbose_name="帖子"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="forum_favorites",
        verbose_name="收藏用户"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("post", "user")

    def __str__(self):
        return f"{self.user} ⭐ {self.post}"


# 评论表
class ForumComment(models.Model):
    post = models.ForeignKey(
        "ForumPost",
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="所属帖子"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="comments",
        verbose_name="评论用户"
    )
    content = models.TextField(verbose_name="评论内容")
    parent = models.ForeignKey(
        "self",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="replies",
        verbose_name="父评论"
    )
    like_count = models.PositiveIntegerField(default=0, verbose_name="点赞数")
    is_deleted = models.BooleanField(default=False, verbose_name="是否删除")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"评论 by {self.user} on {self.post}"
