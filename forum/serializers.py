from rest_framework import serializers
from .models import ForumPost, ForumLike, ForumFavorite, ForumComment


class ForumPostSerializer(serializers.ModelSerializer):
    author_nickname = serializers.CharField(source="author.nickname", read_only=True)
    author_avatar = serializers.SerializerMethodField()
    reply_count = serializers.IntegerField(read_only=True)  # 评论数

    class Meta:
        model = ForumPost
        fields = "__all__"
        read_only_fields = [
            "author",
            "view_count",
            "like_count",
            "favorite_count",
            "created_at",
            "updated_at",
        ]

    def get_author_avatar(self, obj):
        request = self.context.get("request")
        if obj.author.avatar and hasattr(obj.author.avatar, "url"):
            if request:
                return request.build_absolute_uri(obj.author.avatar.url)
            return obj.author.avatar.url  # fallback，至少有个相对路径
        return None


class CommentSerializer(serializers.ModelSerializer):
    user_info = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()

    class Meta:
        model = ForumComment
        fields = [
            "id", "post", "user", "user_info", "content",
            "parent", "is_deleted", "created_at", "updated_at", "replies"
        ]
        read_only_fields = ["user", "created_at", "updated_at"]

    def get_user_info(self, obj):
        return {
            "id": obj.user.id,
            "username": obj.user.username,
            "nickname": obj.user.nickname,
            "avatar": (
                self.context["request"].build_absolute_uri(obj.user.avatar.url)
                if obj.user.avatar else None
            ),
        }

    def get_replies(self, obj):
        replies = obj.replies.filter(is_deleted=False).order_by("created_at")
        return CommentSerializer(replies, many=True, context=self.context).data

