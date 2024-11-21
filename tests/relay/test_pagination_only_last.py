import sys

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from strawberry.relay import to_base64

from tests import utils
from tests.projects.faker import MilestoneFactory, ProjectFactory


@pytest.mark.django_db(transaction=True)
def test_pagination_only_last(gql_client: utils.GraphQLTestClient):
    # Pagination query that only uses the `last` argument
    query = """
      query testPaginationOnlyLast($last: Int!) {
        milestoneConn(last: $last) {
          edges {
            node {
              id
            }
          }
        }
      }
    """

    # Create a project with some milestones
    project = ProjectFactory()
    milestones = MilestoneFactory.create_batch(10, project=project)

    # Run the pagination query
    # Capture the SQL queries that are executed
    with CaptureQueriesContext(connection) as ctx:
        result = gql_client.query(query, {"last": 3})

    # We expect the last 3 milestones to be returned
    assert not result.errors
    assert result.data == {
        "milestoneConn": {
            "edges": [
                {"node": {"id": to_base64("MilestoneType", milestone.id)}}
                for milestone in milestones[-3:]
            ]
        }
    }

    # We don't expect *every* record to be fetched from the database behind the scenes!
    # At the moment, this does a query like:
    #
    # SELECT "projects_milestone"."name",
    #     "projects_milestone"."id",
    #     "projects_milestone"."due_date",
    #     "projects_milestone"."project_id"
    # FROM "projects_milestone" LIMIT 9223372036854775807  <- This is ``sys.maxsize``
    #
    # This means that all records are fetched from the database, and then the last 3 are
    # filtered out in Python. If you have a large number of records, this can be very
    # inefficient.
    if not gql_client.is_async:
        # Note: It seems ``CaptureQueriesContext`` doesn't work properly in an async
        # context so we just ignore it here
        assert len(ctx.captured_queries) == 1
        assert f"LIMIT {sys.maxsize}" not in ctx.captured_queries[0]["sql"]
