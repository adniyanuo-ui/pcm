# _*_coding:utf-8_*_
# __author: guo
from django.db.models import Q, QuerySet, Subquery, OuterRef
from django_filters import rest_framework as filters

from patient.models import Patient
from question.models import Question
import cn2an


class Search:
    search_fields = []
    search = filters.CharFilter(method="filter_search")

    no_search_fields = []
    noSearch = filters.CharFilter(method="filter_no_search")

    def filter_search(self, queryset, name, value):
        values = value.split(" ")
        q2 = Q()
        q2.connector = "AND"
        for value in values:
            q1 = Q()
            q1.connector = "OR"
            for field in self.search_fields:
                q1.children.append([f"{field}__icontains", value])
            q2.children.append(q1)

        queryset = queryset.filter(q2)
        return queryset

    def filter_no_search(self, queryset, name, value):
        values = value.split(" ")
        q2 = Q()
        q2.connector = "AND"
        for value in values:
            q1 = Q()
            q1.connector = "OR"
            for field in self.search_fields:
                q1.children.append([f"{field}__icontains", value])
            q2.children.append(q1)

        queryset = queryset.exclude(q2)
        return queryset


class PatientFilter(Search, filters.FilterSet):
    name = filters.CharFilter(field_name="name")
    phone = filters.CharFilter(field_name="phone")

    class Meta:
        model = Patient
        fields = ()
