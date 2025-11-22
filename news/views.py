
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from .models import News
from .serializers import NewsSerializer


# 获取资讯
@api_view(["GET"])
def news_list(request):
    qs = News.objects.order_by('-published')

    # 优先处理 limit 参数
    limit = request.GET.get("limit")
    if limit:
        try:
            limit = int(limit)
        except ValueError:
            limit = 10  # 默认值
        serializer = NewsSerializer(qs[:limit], many=True)
        return Response(serializer.data)

    # 分页处理
    paginator = PageNumberPagination()
    try:
        paginator.page_size = int(request.GET.get("pagesize", 20))  # 默认每页20条
    except ValueError:
        paginator.page_size = 20

    result_page = paginator.paginate_queryset(qs, request)
    serializer = NewsSerializer(result_page, many=True)
    return paginator.get_paginated_response(serializer.data)
