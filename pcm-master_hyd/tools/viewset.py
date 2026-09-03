# _*_coding:utf-8_*_
# __author: guo
import re

from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework import status
from django.http import Http404
from tools.resp import get_response


class CreateModelMixin(object):
    """
    Create a model instance.
    """

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
        except Exception as e:
            if "unique" in e.args[0]["non_field_errors"][0]:
                fields = re.search(r"The fields (.*?) must", e.args[0]["non_field_errors"][0]).group(1).split(",")
                fields = [_f.strip() for _f in fields]
                query = {_f: request.data[_f] for _f in fields}
                self.queryset.model.objects.filter(**query).update(deleted=0)
                instance = self.queryset.model.objects.filter(**query).first()
                serializer = self.get_serializer(instance, data=request.data, partial=False)
                serializer.is_valid(raise_exception=True)
                self.perform_update(serializer)

        return get_response(serializer.data, msg="创建成功")

    def perform_create(self, serializer):
        serializer.save()


class RetrieveModelMixin(object):
    """
    Retrieve a model instance.
    """

    def retrieve(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return get_response(serializer.data, msg="数据获取成功")
        except Http404 as e:
            return get_response({}, msg="数据获取成功")


class ListModelMixin:
    """
    List a queryset.
    """

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return get_response(serializer.data, msg="数据获取成功")


class UpdateModelMixin(object):
    """
    Update a model instance.
    """

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            # If 'prefetch_related' has been applied to a queryset, we need to
            # forcibly invalidate the prefetch cache on the instance.
            instance._prefetched_objects_cache = {}

        return get_response(serializer.data, msg="编辑成功")

    def perform_update(self, serializer):
        serializer.save()

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)


class DestroyModelMixin(object):
    """
    Destroy a model instance.
    """

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return get_response(msg="删除成功")

    def perform_destroy(self, instance):
        self.queryset.filter(id=instance.id).delete()


from rest_framework.viewsets import GenericViewSet


class BaseDispatch:

    def dispatch(self, request, *args, **kwargs):
        """
        `.dispatch()` is pretty much the same as Django's regular dispatch,
        but with extra hooks for startup, finalize, and exception handling.
        """
        self.args = args
        self.kwargs = kwargs
        request = self.initialize_request(request, *args, **kwargs)

        self.request = request
        self.headers = self.default_response_headers  # deprecate?

        try:
            self.initial(request, *args, **kwargs)

            # Get the appropriate handler method
            if request.method.lower() in self.http_method_names:
                handler = getattr(self, request.method.lower(),
                                  self.http_method_not_allowed)
            else:
                handler = self.http_method_not_allowed

            response = handler(request, *args, **kwargs)

        except Exception as exc:
            response = self.handle_exception(exc)

        self.response = self.finalize_response(request, response, *args, **kwargs)
        return self.response


class ModelViewSet(CreateModelMixin,
                   RetrieveModelMixin,
                   UpdateModelMixin,
                   DestroyModelMixin,
                   ListModelMixin,
                   BaseDispatch,
                   GenericViewSet):
    """
    A viewset that provides default `create()`, `retrieve()`, `update()`,
    `partial_update()`, `destroy()` and `list()` actions.
    """
    pass


class ReadOnlyModelViewSet(RetrieveModelMixin,
                           ListModelMixin,
                           BaseDispatch,
                           GenericViewSet):
    """
    A viewset that provides default `list()` and `retrieve()` actions.
    """
    pass


class DestroyViewSet(DestroyModelMixin, BaseDispatch, GenericViewSet):
    pass


class CreateViewSet(CreateModelMixin, BaseDispatch, GenericViewSet):
    pass


class ListViewSet(ListModelMixin, BaseDispatch, GenericViewSet):
    pass


class UpdateViewSet(UpdateModelMixin, BaseDispatch, GenericViewSet):
    pass


class RetrieveViewSet(RetrieveModelMixin, BaseDispatch, GenericViewSet):
    pass
