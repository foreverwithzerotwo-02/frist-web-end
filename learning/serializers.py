from rest_framework import serializers
from .models import CourseFavorite, Course, CourseViewHistory


class CourseSerializer(serializers.ModelSerializer):
    cover_image = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = "__all__"

    def get_cover_image(self, obj):
        request = self.context.get("request")
        if obj.cover_image and request:
            return request.build_absolute_uri(obj.cover_image.url)
        return None


class CourseFavoriteSerializer(serializers.ModelSerializer):
    course = CourseSerializer()

    class Meta:
        model = CourseFavorite
        fields = ["id", "course", "created_at"]


class CourseViewHistorySerializer(serializers.ModelSerializer):
    course = CourseSerializer(read_only=True)  # 嵌套课程信息

    class Meta:
        model = CourseViewHistory
        fields = "__all__"
