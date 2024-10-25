import pytest
from django.db import connection
from django.db.models import Prefetch
from django.test.utils import CaptureQueriesContext

from strawberry_django.pagination import apply_window_pagination
from tests.projects.faker import IssueFactory, TagFactory
from tests.projects.models import Issue, Tag


@pytest.mark.django_db(transaction=True)
def test_apply_window_pagination_queries():
    # Create 2 tags and 3 issues
    tags = [TagFactory(name=f"Tag {i + 1}") for i in range(2)]
    issues = [IssueFactory(name=f"Issue {i + 1}") for i in range(3)]

    # Assign issues 1 and 2 to the 1st tag
    # Assign issues 2 and 3 to the 2nd tag
    # This means that both tags share the 2nd issue
    tags[0].issues.set(issues[:2])
    tags[1].issues.set(issues[1:])

    # Strawberry-Django pagination
    with CaptureQueriesContext(connection) as ctx:
        queryset = Tag.objects.only("name").prefetch_related(
            Prefetch(
                "issues",
                queryset=apply_window_pagination(
                    queryset=Issue.objects.only("name"),
                    related_field_id="tags",
                    offset=0,
                    limit=2,
                ),
                to_attr="issues_paginated"
            ),
        )
        # Trigger and capture the queries
        list(queryset)
        strawberry_django_queries = [q["sql"] for q in ctx.captured_queries]

    # Django inbuilt pagination
    with CaptureQueriesContext(connection) as ctx:
        queryset = Tag.objects.only("name").prefetch_related(
            Prefetch(
                "issues",
                queryset=Issue.objects.only("name")[:2],
                to_attr="issues_paginated"
            )
        )
        # Trigger and capture the queries
        list(queryset)
        django_queries = [q["sql"] for q in ctx.captured_queries]

    # Compare the queries
    assert strawberry_django_queries == django_queries
