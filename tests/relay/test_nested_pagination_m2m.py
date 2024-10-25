import pytest

from strawberry_django.optimizer import DjangoOptimizerExtension
from tests import utils
from tests.projects.faker import IssueFactory, TagFactory


@pytest.mark.django_db(transaction=True)
def test_nested_pagination_m2m(gql_client: utils.GraphQLTestClient):
    # Create 2 tags and 3 issues
    tags = [TagFactory(name=f"Tag {i + 1}") for i in range(2)]
    issues = [IssueFactory(name=f"Issue {i + 1}") for i in range(3)]

    # Assign issues 1 and 2 to the 1st tag
    # Assign issues 2 and 3 to the 2nd tag
    # This means that both tags share the 2nd issue
    tags[0].issues.set(issues[:2])
    tags[1].issues.set(issues[1:])

    # Query the tags with their issues
    # We expect only 2 database queries if the optimizer is enabled, otherwise 3 (N+1)
    with utils.assert_num_queries(2 if DjangoOptimizerExtension.enabled.get() else 3):
        result = gql_client.query(
            """
            query {
              tagConn {
                edges {
                  node {
                    name
                    issues {
                      edges {
                        node {
                          name
                        }
                      }
                    }
                  }
                }
              }
            }
            """
        )

    # Check the results
    assert not result.errors
    assert result.data == {
        "tagConn": {
            "edges": [
                {
                    "node": {
                        "name": "Tag 1",
                        "issues": {
                            "edges": [
                                {"node": {"name": "Issue 1"}},
                                {"node": {"name": "Issue 2"}},
                            ]
                        },
                    }
                },
                {
                    "node": {
                        "name": "Tag 2",
                        "issues": {
                            "edges": [
                                {"node": {"name": "Issue 2"}},
                                {"node": {"name": "Issue 3"}},
                            ]
                        },
                    }
                },
            ]
        }
    }
