# 处理数据表删除本地图片
import os
from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import Course


@receiver(post_delete, sender=Course)
def delete_course_image(sender, instance, **kwargs):
    # 有图片，并且本地也有则删除
    if instance.cover_image and os.path.isfile(instance.cover_image.path):
        os.remove(instance.cover_image.path)
