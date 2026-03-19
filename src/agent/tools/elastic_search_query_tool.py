import json
from typing import Any, Dict, List, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class ElasticsearchQueryInput(BaseModel):
    """Input schema for Elasticsearch Query Tool."""

    user_query: str = Field(..., description="The search query from the user")
    index_name: str = Field(
        ..., description="The Elasticsearch index name to search in"
    )


class ElasticsearchQueryTool(BaseTool):
    """Enhanced tool for searching Elasticsearch with multi_match queries, field boosting, and fuzzy matching."""

    name: str = "Elasticsearch Query Tool"
    description: str = (
        "Search Elasticsearch using enhanced multi_match queries with field boosting and fuzzy matching. "
        "Searches across content and document_path fields with content prioritized. "
        "Returns detailed results including document_path for proper citations. "
        "Requires ELASTICSEARCH_URL and ELASTICSEARCH_API_KEY environment variables."
    )
    args_schema: Type[BaseModel] = ElasticsearchQueryInput

    def _run(self, user_query: str, index_name: str) -> str:
        """
        Search Elasticsearch using enhanced multi_match query with boosting and fuzzy matching.

        Args:
            user_query: The search query from the user
            index_name: The Elasticsearch index name to search in

        Returns:
            JSON string with enhanced search results including document_path for citations
        """
        try:
            # Get environment variables
            import os

            elasticsearch_url = os.getenv("ELASTICSEARCH_URL")
            elasticsearch_api_key = os.getenv("ELASTICSEARCH_API_KEY")

            if not elasticsearch_url:
                return json.dumps(
                    {
                        "success": False,
                        "error": "ELASTICSEARCH_URL environment variable is not set",
                    }
                )

            if not elasticsearch_api_key:
                return json.dumps(
                    {
                        "success": False,
                        "error": "ELASTICSEARCH_API_KEY environment variable is not set",
                    }
                )

            # Ensure URL ends with /
            if not elasticsearch_url.endswith("/"):
                elasticsearch_url += "/"

            # Build search URL
            search_url = f"{elasticsearch_url}{index_name}/_search"

            # Prepare headers with API key authentication
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"ApiKey {elasticsearch_api_key}",
            }

            # Build enhanced search query with multi_match, boosting, and fuzzy matching
            search_body = {
                "query": {
                    "bool": {
                        "should": [
                            # Primary multi_match query with cross_fields for better relevance
                            {
                                "multi_match": {
                                    "query": user_query,
                                    "fields": [
                                        "content^3",  # Boost content field higher
                                        "document_path^1",  # Lower boost for document_path
                                    ],
                                    "type": "cross_fields",
                                    "operator": "and",
                                    "minimum_should_match": "75%",
                                }
                            },
                            # Fuzzy matching for better recall with lower boost
                            {
                                "multi_match": {
                                    "query": user_query,
                                    "fields": [
                                        "content^2",  # Slightly lower boost for fuzzy
                                        "document_path^0.5",
                                    ],
                                    "fuzziness": "AUTO",
                                    "type": "best_fields",
                                    "minimum_should_match": "50%",
                                }
                            },
                            # Handle empty content gracefully with document_path only query
                            {
                                "bool": {
                                    "must": [
                                        {
                                            "bool": {
                                                "should": [
                                                    {"term": {"content": ""}},
                                                    {
                                                        "bool": {
                                                            "must_not": {
                                                                "exists": {
                                                                    "field": "content"
                                                                }
                                                            }
                                                        }
                                                    },
                                                ]
                                            }
                                        },
                                        {
                                            "match": {
                                                "document_path": {
                                                    "query": user_query,
                                                    "boost": 0.8,
                                                }
                                            }
                                        },
                                    ]
                                }
                            },
                        ],
                        "minimum_should_match": 1,
                    }
                },
                "size": 10,  # Return up to 10 results
                "_source": {
                    "includes": [
                        "document_path",
                        "content",
                        "timestamp",
                    ]  # Only return relevant fields
                },
                "sort": [
                    {"_score": {"order": "desc"}},  # Sort by relevance score first
                    {
                        "timestamp": {"order": "desc"}
                    },  # Then by timestamp for tie-breaking
                ],
                "highlight": {
                    "fields": {
                        "content": {"fragment_size": 150, "number_of_fragments": 2},
                        "document_path": {},
                    },
                    "pre_tags": ["<mark>"],
                    "post_tags": ["</mark>"],
                },
            }

            # Make the search request
            response = requests.post(
                search_url, headers=headers, json=search_body, timeout=30
            )

            # Check if request was successful
            if response.status_code == 200:
                search_results = response.json()

                # Extract relevant information
                hits = search_results.get("hits", {})
                total_hits = hits.get("total", {})

                # Handle different Elasticsearch versions
                if isinstance(total_hits, dict):
                    total_count = total_hits.get("value", 0)
                else:
                    total_count = total_hits

                # Process results with enhanced formatting
                results = []
                for hit in hits.get("hits", []):
                    source = hit.get("_source", {})
                    highlight = hit.get("highlight", {})

                    # Handle empty content gracefully
                    content = source.get("content", "")
                    if not content or content.strip() == "":
                        content = "[No content available]"

                    result = {
                        "id": hit.get("_id"),
                        "score": hit.get("_score"),
                        "document_path": source.get("document_path", "Unknown"),
                        "content": content,
                        "timestamp": source.get("timestamp", "Unknown"),
                        "content_preview": (
                            content[:200] + "..." if len(content) > 200 else content
                        ),
                        "highlighted_content": highlight.get("content", []),
                        "highlighted_document_path": highlight.get("document_path", []),
                    }
                    results.append(result)

                # Create summary statistics
                has_content_results = sum(
                    1 for r in results if r["content"] != "[No content available]"
                )

                return json.dumps(
                    {
                        "success": True,
                        "query": user_query,
                        "index": index_name,
                        "total_hits": total_count,
                        "returned_results": len(results),
                        "results_with_content": has_content_results,
                        "results_without_content": len(results) - has_content_results,
                        "results": results,
                        "search_strategy": "multi_match with content boosting and fuzzy fallback",
                    },
                    indent=2,
                )

            else:
                # Handle HTTP errors
                error_message = f"HTTP {response.status_code}: {response.text}"
                return json.dumps(
                    {
                        "success": False,
                        "error": f"Elasticsearch request failed: {error_message}",
                    }
                )

        except requests.exceptions.Timeout:
            return json.dumps(
                {"success": False, "error": "Request timed out after 30 seconds"}
            )
        except requests.exceptions.ConnectionError:
            return json.dumps(
                {
                    "success": False,
                    "error": "Could not connect to Elasticsearch cluster",
                }
            )
        except requests.exceptions.RequestException as e:
            return json.dumps({"success": False, "error": f"Request error: {str(e)}"})
        except json.JSONDecodeError as e:
            return json.dumps(
                {
                    "success": False,
                    "error": f"Invalid JSON response from Elasticsearch: {str(e)}",
                }
            )
        except Exception as e:
            return json.dumps(
                {"success": False, "error": f"Unexpected error: {str(e)}"}
            )
