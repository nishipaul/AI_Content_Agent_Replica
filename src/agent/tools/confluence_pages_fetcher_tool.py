import json
from typing import Any, Dict, Type

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth


class ConfluencePagesFetcherInput(BaseModel):
    """Input schema for ConfluencePagesFetcher Tool."""

    confluence_domain: str = Field(
        ..., description="The Confluence domain (e.g., 'mycompany.atlassian.net')"
    )
    space_id: str = Field(
        ..., description="The ID of the Confluence space to fetch pages from"
    )
    email: str = Field(..., description="Email address for Confluence authentication")
    api_token: str = Field(..., description="API token for Confluence authentication")


class ConfluencePagesFetcher(BaseTool):
    """Tool for fetching all pages from a Confluence space using API v2."""

    name: str = "confluence_pages_fetcher"
    description: str = (
        "Fetches all pages from a specified Confluence space using the Confluence API v2. "
        "Requires confluence_domain, space_id, email, and api_token parameters. "
        "Returns JSON response containing page information including titles, IDs, and metadata."
    )
    args_schema: Type[BaseModel] = ConfluencePagesFetcherInput

    def _run(
        self, confluence_domain: str, space_id: str, email: str, api_token: str
    ) -> str:
        """
        Fetch all pages from a Confluence space.

        Args:
            confluence_domain: The Confluence domain
            space_id: The space ID to fetch pages from
            email: Email for authentication
            api_token: API token for authentication

        Returns:
            JSON string containing the pages data or error message
        """
        try:
            # Construct the API URL
            url = f"https://{confluence_domain}/wiki/api/v2/spaces/{space_id}/pages"

            # Set up authentication
            auth = HTTPBasicAuth(email, api_token)

            # Set headers
            headers = {"Accept": "application/json", "Content-Type": "application/json"}

            # Make the API request
            response = requests.get(url, headers=headers, auth=auth, timeout=30)

            # Check if the request was successful
            if response.status_code == 200:
                # Return the JSON response
                return json.dumps(response.json(), indent=2)

            elif response.status_code == 401:
                return json.dumps(
                    {
                        "error": "Authentication failed. Please check your email and API token.",
                        "status_code": 401,
                    },
                    indent=2,
                )

            elif response.status_code == 403:
                return json.dumps(
                    {
                        "error": "Access forbidden. You may not have permission to access this space.",
                        "status_code": 403,
                    },
                    indent=2,
                )

            elif response.status_code == 404:
                return json.dumps(
                    {
                        "error": f"Space with ID '{space_id}' not found or does not exist.",
                        "status_code": 404,
                    },
                    indent=2,
                )

            else:
                # Handle other HTTP errors
                try:
                    error_response = response.json()
                    return json.dumps(
                        {
                            "error": f"API request failed with status {response.status_code}",
                            "details": error_response,
                            "status_code": response.status_code,
                        },
                        indent=2,
                    )
                except json.JSONDecodeError:
                    return json.dumps(
                        {
                            "error": f"API request failed with status {response.status_code}",
                            "details": response.text,
                            "status_code": response.status_code,
                        },
                        indent=2,
                    )

        except requests.exceptions.Timeout:
            return json.dumps(
                {
                    "error": "Request timed out. The Confluence server may be slow to respond.",
                    "status_code": "timeout",
                },
                indent=2,
            )

        except requests.exceptions.ConnectionError:
            return json.dumps(
                {
                    "error": f"Failed to connect to {confluence_domain}. Please check the domain name.",
                    "status_code": "connection_error",
                },
                indent=2,
            )

        except requests.exceptions.RequestException as e:
            return json.dumps(
                {"error": f"Request failed: {str(e)}", "status_code": "request_error"},
                indent=2,
            )

        except Exception as e:
            return json.dumps(
                {
                    "error": f"Unexpected error occurred: {str(e)}",
                    "status_code": "unexpected_error",
                },
                indent=2,
            )
