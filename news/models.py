from django.db import models


# 存放资讯
class News(models.Model):
    title = models.CharField(max_length=255)
    link = models.URLField(unique=True)  # 用 link 去重
    source = models.CharField(max_length=50)
    summary = models.TextField(blank=True, null=True)
    published = models.DateTimeField(null=True, blank=True)
    image_url = models.URLField(max_length=500, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-published', '-created_at']

    def __str__(self):
        return self.title
