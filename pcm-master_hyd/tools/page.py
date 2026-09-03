# _*_coding:utf-8_*_
# __author: guo
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination


class CustomPaginationSerializer(LimitOffsetPagination):

    def paginate_queryset(self, queryset, request, view=None):
        self.limit = self.get_limit(request)
        if self.limit is None:
            return None

        self.offset = self.get_offset(request)
        self.request = request

        if getattr(self.request, "end", None):
            self.count = self.limit
            return queryset[self.offset:self.offset + self.limit]
        else:
            self.count = self.get_count(queryset)

            if self.count > self.limit and self.template is not None:
                self.display_page_controls = True

            if self.count == 0 or self.offset > self.count:
                return []
            return queryset[self.offset:self.offset + self.limit]

    def get_paginated_response(self, data):
        return Response({
            "code": 200,
            "msg": "数据获取成功",
            "data": {
                "count": self.count,
                "previous": self.get_previous_link(),
                "next": self.get_next_link(),
                "results": data
            }
        })
