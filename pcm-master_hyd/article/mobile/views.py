# Create your views here.
from article.mobile.serializers import ArticleSerializer
from article.models import Article
from tools.viewset import ModelViewSet


class ArticleView(ModelViewSet):
    http_method_names = ["get"]
    queryset = Article.objects.order_by("-id")
    serializer_class = ArticleSerializer
