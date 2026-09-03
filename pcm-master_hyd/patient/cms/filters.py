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
    name = filters.CharFilter(method="filter_name")
    date = filters.CharFilter(method="filter_date")
    sex = filters.CharFilter(field_name="sex")
    age = filters.CharFilter(field_name="age")
    q_type = filters.CharFilter(field_name="q_type")
    company = filters.CharFilter(method="filter_company")
    department = filters.CharFilter(method="filter_department")

    def filter_name(self, queryset, name, value):
        return queryset.filter(name__icontains=value)

    def filter_company(self, queryset, name, value):
        return queryset.filter(company__icontains=value)

    def filter_department(self, queryset, name, value):
        return queryset.filter(department__icontains=value)

    def filter_date(self, queryset, name, value):
        min_date, max_date = value.split("~")
        min_date = f"{min_date} 00:00:00"
        max_date = f"{max_date} 23:59:59"
        queryset = queryset.filter(date__gt=min_date, date__lt=max_date)
        return queryset

    class Meta:
        model = Patient
        fields = ()
