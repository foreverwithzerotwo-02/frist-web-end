from django.conf import settings


# 返回完整 url 访问路径
def get_full_media_url(request, path: str) -> str:
    if not path:
        return ""
    return request.build_absolute_uri(settings.MEDIA_URL + path)


# 找到返回全部富文本 json 格式中的图片url
def extract_image_urls_from_tiptap_json(node):
    urls = []

    if isinstance(node, dict):
        if node.get("type") == "image":
            attrs = node.get("attrs", {})
            src = attrs.get("src")
            if src:
                urls.append(src)

        # 递归查找 content 子节点
        if "content" in node:
            for child in node["content"]:
                urls.extend(extract_image_urls_from_tiptap_json(child))

    elif isinstance(node, list):
        for item in node:
            urls.extend(extract_image_urls_from_tiptap_json(item))

    return urls
