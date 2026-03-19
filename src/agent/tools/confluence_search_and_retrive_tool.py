import json
import re
from typing import Any, Dict, List, Optional, Type, cast

import requests
from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from requests.auth import HTTPBasicAuth


class ConfluenceSearchRequest(BaseModel):
    """Input schema for Confluence Search and Retrieve Tool."""

    query: str = Field(
        ..., description="Search query or keywords to find in Confluence"
    )
    space_key: Optional[str] = Field(
        None, description="Specific Confluence space key to search within (optional)"
    )
    content_type: Optional[str] = Field(
        "page",
        description="Type of content to search for (page, blogpost, comment, attachment)",
    )
    max_results: Optional[int] = Field(
        10, description="Maximum number of results to return (1-100)"
    )


class ConfluenceSearchAndRetrieveTool(BaseTool):
    """Tool for searching and retrieving content from Confluence using fuzzy text search with debugging."""

    name: str = "confluence_search_and_retrieve"
    description: str = (
        "Search for and retrieve content from Confluence using flexible fuzzy text search queries with comprehensive debugging. "
        "Uses fuzzy matching as primary strategy to find relevant content even with partial matches, includes extensive debugging "
        "information to track search behavior and multiple fallback strategies for comprehensive results."
    )
    args_schema: Type[BaseModel] = ConfluenceSearchRequest

    def _run(
        self,
        query: str,
        space_key: Optional[str] = None,
        content_type: str = "page",
        max_results: int = 10,
    ) -> str:
        """Execute Confluence search and retrieve content with debugging."""
        try:
            # Get environment variables
            domain = self.get_env("CONFLUENCE_DOMAIN")
            email = self.get_env("CONFLUENCE_EMAIL")
            api_key = self.get_env("CONFLUENCE_API_KEY")

            if not all([domain, email, api_key]):
                return json.dumps(
                    {
                        "error": "Missing required environment variables: CONFLUENCE_DOMAIN, CONFLUENCE_EMAIL, or CONFLUENCE_API_KEY",
                        "results": [],
                    }
                )

            domain = cast(str, domain)
            email = cast(str, email)
            api_key = cast(str, api_key)

            # Validate max_results
            max_results = max(1, min(max_results, 100))

            # Add debugging information
            debug_info: Dict[str, Any] = {
                "original_query": query,
                "space_key": space_key,
                "content_type": content_type,
                "search_strategies_attempted": [],
            }

            # Try search strategies in order of specificity (most specific first)
            # Strategy 1: Exact phrase match (most specific)
            search_results = None
            try:
                exact_cql = self._build_cql_query(
                    query, space_key, content_type, "exact"
                )
                debug_info["search_strategies_attempted"].append(
                    f"exact (with space): {exact_cql}"
                )
                exact_results = self._execute_search(
                    domain, email, api_key, exact_cql, max_results
                )
                if exact_results.get("results"):
                    # Filter by space and relevance
                    filtered = self._filter_relevant_results(
                        exact_results, query, space_key
                    )
                    if filtered.get("results"):
                        search_results = filtered
                        debug_info["exact_success"] = True
                        debug_info["primary_cql"] = exact_cql
            except Exception as e:
                debug_info["exact_error"] = str(e)

            # Strategy 2: All words must match (AND logic) - more specific than OR
            if not search_results or not search_results.get("results"):
                try:
                    all_words_cql = self._build_cql_query(
                        query, space_key, content_type, "all_words"
                    )
                    debug_info["search_strategies_attempted"].append(
                        f"all_words (with space): {all_words_cql}"
                    )
                    all_words_results = self._execute_search(
                        domain, email, api_key, all_words_cql, max_results
                    )
                    if all_words_results.get("results"):
                        # Filter by space and relevance
                        filtered = self._filter_relevant_results(
                            all_words_results, query, space_key
                        )
                        if filtered.get("results"):
                            search_results = filtered
                            debug_info["all_words_success"] = True
                            debug_info["primary_cql"] = all_words_cql
                except Exception as e:
                    debug_info["all_words_error"] = str(e)

            # Strategy 3: Fuzzy search (OR logic) - less specific but broader
            # Only use if previous strategies didn't find results
            if not search_results or not search_results.get("results"):
                try:
                    fuzzy_cql = self._build_cql_query(
                        query, space_key, content_type, "fuzzy"
                    )
                    debug_info["search_strategies_attempted"].append(
                        f"fuzzy (with space): {fuzzy_cql}"
                    )
                    fuzzy_results = self._execute_search(
                        domain, email, api_key, fuzzy_cql, max_results
                    )
                    # Filter fuzzy results to ensure they're relevant (not just matching on one common word)
                    if fuzzy_results.get("results"):
                        filtered_results = self._filter_relevant_results(
                            fuzzy_results, query, space_key
                        )
                        if filtered_results.get("results"):
                            search_results = filtered_results
                            debug_info["fuzzy_success"] = True
                            debug_info["primary_cql"] = fuzzy_cql
                        else:
                            debug_info["fuzzy_results_filtered"] = (
                                "Results filtered out as not relevant"
                            )
                except Exception as e:
                    debug_info["fuzzy_error"] = str(e)

            # Strategy 4: Try fallback search strategies (individual words, wildcard)
            if not search_results or not search_results.get("results"):
                fallback_results = self._try_fallback_searches_with_debug(
                    domain,
                    email,
                    api_key,
                    query,
                    space_key,
                    content_type,
                    max_results,
                    debug_info,
                )
                if fallback_results:
                    search_results = fallback_results

            # If still no results, try broader searches
            # BUT: If space_key was specified, don't search without space restriction
            # Instead, only try alternative content types within the same space
            if not search_results or not search_results.get("results"):
                debug_info["attempting_broad_search"] = True
                # Only try searching without space restriction if space_key was NOT specified
                # If space_key IS specified, we should respect it and not return results from other spaces
                if not space_key:
                    broad_cql = self._build_cql_query(
                        query, None, content_type, "fuzzy"
                    )
                    try:
                        broad_results = self._execute_search(
                            domain, email, api_key, broad_cql, max_results
                        )
                        if broad_results.get("results"):
                            search_results = broad_results
                            debug_info["broad_search_success"] = True
                    except Exception as e:
                        debug_info["broad_search_error"] = str(e)
                else:
                    debug_info["space_specified_no_fallback"] = (
                        f"Space '{space_key}' specified - not falling back to no-space search to avoid wrong-space results"
                    )

                # Try searching all content types
                if not search_results or not search_results.get("results"):
                    for content_type_option in ["page", "blogpost", "comment"]:
                        if content_type_option != content_type:
                            try:
                                alt_cql = self._build_cql_query(
                                    query, space_key, content_type_option, "fuzzy"
                                )
                                alt_results = self._execute_search(
                                    domain, email, api_key, alt_cql, max_results
                                )
                                if alt_results.get("results"):
                                    search_results = alt_results
                                    debug_info[
                                        f"{content_type_option}_search_success"
                                    ] = True
                                    break
                            except Exception:
                                continue

            # Process and enhance results
            if search_results:
                enhanced_results = self._process_search_results(
                    domain, email, api_key, search_results
                )
                enhanced_results["debug_info"] = debug_info
                return json.dumps(enhanced_results, indent=2)
            else:
                return json.dumps(
                    {
                        "error": "No results found despite multiple search strategies",
                        "debug_info": debug_info,
                        "results": [],
                    }
                )

        except Exception as e:
            return json.dumps(
                {
                    "error": f"Search failed: {str(e)}",
                    "debug_info": debug_info if "debug_info" in locals() else {},
                    "results": [],
                }
            )

    def _filter_relevant_results(
        self, search_data: Dict[str, Any], query: str, space_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Filter results to ensure they match multiple meaningful words and are from the correct space."""
        results = search_data.get("results", [])
        if not results:
            return search_data

        # Extract meaningful words from query (same logic as in _build_text_search_clause)
        query_clean = (
            query.strip()
            .replace("?", "")
            .replace("!", "")
            .replace("(", "")
            .replace(")", "")
        )
        words = query_clean.split()
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "what",
            "are",
            "is",
            "was",
            "were",
            "followed",
        }
        # Include acronyms (2+ chars, all caps) and words longer than 2 chars
        meaningful_words = []
        for w in words:
            w_lower = w.lower()
            # Include if: acronym (2+ chars, all caps) OR (length > 2 and not a stop word)
            if (len(w) >= 2 and w.isupper()) or (
                len(w) > 2 and w_lower not in stop_words
            ):
                meaningful_words.append(w_lower)

        # Identify key terms (important words that should strongly indicate relevance)
        # These are typically acronyms, technical terms, or domain-specific words
        key_terms = []
        for word in words:
            word_lower = word.lower()
            # Key terms:
            # 1. Acronyms (all caps, 2+ chars) like "ML", "AI", "API"
            # 2. Technical terms (not stop words, 3+ chars) that aren't very common
            if len(word) >= 2 and word.isupper():
                key_terms.append(word_lower)  # Acronyms are always key terms
            elif word_lower not in stop_words and len(word) > 3:
                if word_lower not in {
                    "workflow",
                    "workflows",
                    "setup",
                    "guide",
                    "local",
                    "simpplr",
                    "contracts",
                }:
                    key_terms.append(word_lower)

        # Common words that appear in many pages (company names, common terms)
        very_common_words = {
            "simpplr",
            "workflow",
            "workflows",
            "setup",
            "guide",
            "local",
            "frontend",
            "backend",
            "followed",
        }

        filtered_results = []
        space_filtered_count = 0
        relevance_filtered_count = 0
        space_debug_info = []

        for result in results:
            # Filter by space if specified
            if space_key:
                result_space = result.get("space", {}).get("key", "")
                space_name = result.get("space", {}).get("name", "")
                result_id = result.get("id", "unknown")

                # Debug: log space info
                space_debug_info.append(
                    {
                        "result_id": result_id,
                        "result_space": result_space,
                        "space_name": space_name,
                        "requested_space": space_key,
                    }
                )

                # Check if space matches (exact match or if space_key is a prefix)
                if result_space:
                    # Exact match
                    if result_space == space_key:
                        pass  # Space matches, continue
                    # Check if space_key is a prefix (for personal spaces like ~userid)
                    elif space_key.startswith("~") and result_space.startswith(
                        space_key
                    ):
                        pass  # Space matches, continue
                    # Check if result_space starts with space_key (for cases where space_key is a prefix)
                    elif result_space.startswith(space_key):
                        pass  # Space matches, continue
                    else:
                        space_filtered_count += 1
                        continue  # Skip results from wrong space
                elif not result_space:
                    # If space info is missing, log it but don't filter (might be API issue)
                    space_debug_info[-1]["warning"] = "Space info missing from result"

            # Check title and content for matches
            title = (result.get("title", "") or "").lower()
            body = result.get("body", {}).get("storage", {}).get("value", "") or ""
            body_text = re.sub(r"<[^>]+>", " ", body).lower()
            combined_text = f"{title} {body_text}"

            # Count how many meaningful words match
            title_matches = 0
            content_matches = 0
            key_term_matches = 0

            for word in meaningful_words:
                if word in title:
                    title_matches += 1
                if word in combined_text:
                    content_matches += 1

            # Check for key term matches (these are more important)
            for key_term in key_terms:
                if key_term in title:
                    key_term_matches += 1
                    break  # At least one key term in title is a strong signal

            # Scoring: prioritize title matches and key terms
            # Require either:
            # 1. At least 2 meaningful words in title (strong relevance)
            # 2. At least 1 key term in title AND 1 meaningful word anywhere
            # 3. At least 3 meaningful words total (title + content), with at least 1 in title
            # 4. At least 2 meaningful words total, but neither can be very common words

            total_matches = max(title_matches, content_matches)

            is_relevant = False
            if title_matches >= 2:
                is_relevant = True  # Strong: multiple words in title
            elif key_term_matches >= 1 and (title_matches >= 1 or content_matches >= 1):
                is_relevant = True  # Strong: key term in title + other matches
            elif title_matches >= 1 and total_matches >= 3:
                is_relevant = True  # Good: word in title + multiple total matches
            elif total_matches >= 2:
                # Check if matches are on very common words only
                matched_words = [w for w in meaningful_words if w in combined_text]
                non_common_matches = [
                    w for w in matched_words if w not in very_common_words
                ]
                if len(non_common_matches) >= 1:
                    is_relevant = True  # At least one non-common word matches

            if is_relevant:
                filtered_results.append(result)
            else:
                relevance_filtered_count += 1

        # Add debug info about filtering
        filter_debug = {
            "original_results_count": len(results),
            "space_filtered_count": space_filtered_count,
            "relevance_filtered_count": relevance_filtered_count,
            "final_results_count": len(filtered_results),
            "space_debug": (
                space_debug_info[:5] if len(space_debug_info) > 5 else space_debug_info
            ),  # Limit to first 5 for brevity
        }

        return {
            **search_data,
            "results": filtered_results,
            "size": len(filtered_results),
            "filter_debug": filter_debug,
        }

    def _build_cql_query(
        self,
        query: str,
        space_key: Optional[str],
        content_type: str,
        search_strategy: str = "fuzzy",
    ) -> str:
        """Build CQL query with different search strategies (exact, all_words, fuzzy, etc.)."""
        cql_parts = []

        # Content type filter
        if content_type and content_type != "all":
            cql_parts.append(f'type="{content_type}"')

        # Space filter
        if space_key:
            escaped_space_key = space_key.replace('"', '\\\\"')
            cql_parts.append(f'space="{escaped_space_key}"')

        # Enhanced text search based on strategy
        if query:
            query = query.strip()
            if query:
                text_clause = self._build_text_search_clause(query, search_strategy)
                if text_clause:
                    cql_parts.append(text_clause)

        return " AND ".join(cql_parts) if cql_parts else f'type="{content_type}"'

    def _build_text_search_clause(self, query: str, strategy: str) -> str:
        """Build text search clause with different strategies using valid CQL syntax."""
        # Clean and prepare query - remove special characters that break CQL
        query = query.strip()
        if not query:
            return ""

        # Remove or escape special characters that can break CQL parsing
        # Remove question marks, exclamation marks, and other problematic chars
        query = (
            query.replace("?", "").replace("!", "").replace("(", "").replace(")", "")
        )
        query = query.strip()

        if not query:
            return ""

        # Check if query has multiple words
        words = query.split()
        # Filter out common stop words, but include acronyms (2+ chars, all caps)
        stop_words = {
            "the",
            "a",
            "an",
            "and",
            "or",
            "but",
            "in",
            "on",
            "at",
            "to",
            "for",
            "of",
            "with",
            "by",
            "what",
            "are",
            "is",
            "was",
            "were",
        }
        meaningful_words = []
        for w in words:
            # Include if: acronym (2+ chars, all caps) OR (length > 2 and not a stop word)
            if (len(w) >= 2 and w.isupper()) or (
                len(w) > 2 and w.lower() not in stop_words
            ):
                meaningful_words.append(w)

        # If we filtered out all words, use original words but skip very short ones (except acronyms)
        if not meaningful_words:
            meaningful_words = [
                w for w in words if len(w) >= 2 and (w.isupper() or len(w) > 2)
            ]

        # If still no words, use all words
        if not meaningful_words:
            meaningful_words = words

        is_multi_word = len(meaningful_words) > 1

        def escape_cql_string(s: str) -> str:
            """Properly escape string for CQL."""
            # Escape quotes
            s = s.replace('"', '\\"')
            # Remove any remaining problematic characters
            return s

        if strategy == "exact":
            # Strategy 1: Exact phrase search
            escaped_query = escape_cql_string(query)
            return f'text="{escaped_query}"'

        elif strategy == "all_words":
            # Strategy 2: All words must match (AND logic) - more specific
            if is_multi_word:
                word_clauses = []
                for word in meaningful_words:
                    escaped_word = escape_cql_string(word)
                    word_clauses.append(f'text ~ "{escaped_word}"')
                if word_clauses:
                    return f'({" AND ".join(word_clauses)})'
            else:
                escaped_query = escape_cql_string(query)
                return f'text ~ "{escaped_query}"'

        elif strategy == "fuzzy":
            # Strategy 3: Fuzzy matching - use text ~ operator (valid CQL syntax) with OR logic
            escaped_query = escape_cql_string(query)
            if is_multi_word:
                # For multi-word, try fuzzy match for whole phrase and individual words
                word_clauses = []
                for word in meaningful_words:
                    escaped_word = escape_cql_string(word)
                    word_clauses.append(f'text ~ "{escaped_word}"')

                if word_clauses:
                    fuzzy_clause = f'text ~ "{escaped_query}"'
                    word_clause = f'({" OR ".join(word_clauses)})'
                    return f"({fuzzy_clause} OR {word_clause})"
                else:
                    return f'text ~ "{escaped_query}"'
            else:
                # Single word: use fuzzy search
                return f'text ~ "{escaped_query}"'

        elif strategy == "individual_words":
            # Strategy 3: Individual word search with OR logic
            if is_multi_word:
                word_clauses = []
                for word in meaningful_words:
                    escaped_word = escape_cql_string(word)
                    word_clauses.append(f'text ~ "{escaped_word}"')
                if word_clauses:
                    return f'({" OR ".join(word_clauses)})'
            else:
                escaped_query = escape_cql_string(query)
                return f'text ~ "{escaped_query}"'

        elif strategy == "wildcard":
            # Strategy 4: Wildcard search for partial matches
            if is_multi_word:
                word_clauses = []
                for word in meaningful_words:
                    escaped_word = escape_cql_string(word)
                    word_clauses.append(f'text ~ "{escaped_word}*"')
                if word_clauses:
                    return f'({" OR ".join(word_clauses)})'
            else:
                escaped_query = escape_cql_string(query)
                return f'text ~ "{escaped_query}*"'

        # Default fallback - fuzzy text search
        escaped_query = escape_cql_string(query)
        return f'text ~ "{escaped_query}"'

    def _execute_search(
        self, domain: str, email: str, api_key: str, cql: str, limit: int
    ) -> Dict[str, Any]:
        """Execute CQL search against Confluence."""
        # Normalize domain: remove protocol, ensure /wiki suffix for Confluence Cloud
        domain = domain.replace("https://", "").replace("http://", "").rstrip("/")

        # For Confluence Cloud, base URL should include /wiki
        # Check if /wiki is already present
        if not domain.endswith("/wiki"):
            # Check if it's an atlassian.net domain (Confluence Cloud)
            if "atlassian.net" in domain:
                base_url = f"https://{domain}/wiki"
            else:
                # For on-premise or other setups, use as-is
                base_url = f"https://{domain}"
        else:
            base_url = f"https://{domain}"

        search_url = f"{base_url}/rest/api/content/search"

        params: Dict[str, str | int] = {
            "cql": cql,
            "limit": limit,
            "start": 0,
            "expand": "body.storage,space,version,ancestors",
        }

        auth = HTTPBasicAuth(email, api_key)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        response = requests.get(
            search_url, params=params, auth=auth, headers=headers, timeout=30
        )

        # Check for HTTP errors
        if response.status_code != 200:
            error_msg = f"Confluence API returned status {response.status_code}"
            try:
                error_detail = response.json()
                error_msg += f": {error_detail}"
            except Exception:
                error_msg += f": {response.text}"
            raise requests.exceptions.HTTPError(error_msg)

        return cast(Dict[str, Any], response.json())

    def _try_fallback_searches_with_debug(
        self,
        domain: str,
        email: str,
        api_key: str,
        query: str,
        space_key: Optional[str],
        content_type: str,
        limit: int,
        debug_info: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Try multiple sophisticated search strategies starting with fuzzy search."""
        search_strategies = [
            ("exact", "Exact phrase matching"),
            ("individual_words", "Individual word search"),
            ("wildcard", "Wildcard partial matching"),
        ]

        for strategy, description in search_strategies:
            try:
                # Try with space restriction if space_key is specified
                if space_key:
                    cql_query = self._build_cql_query(
                        query, space_key, content_type, strategy
                    )
                    debug_info["search_strategies_attempted"].append(
                        f"{strategy} (with space): {cql_query}"
                    )
                    results = self._execute_search(
                        domain, email, api_key, cql_query, limit
                    )
                    if results.get("results"):
                        debug_info[f"{strategy}_success"] = True
                        return results
                else:
                    # Only try without space restriction if space_key was NOT specified
                    cql_query = self._build_cql_query(
                        query, None, content_type, strategy
                    )
                    debug_info["search_strategies_attempted"].append(
                        f"{strategy} (no space): {cql_query}"
                    )
                    results = self._execute_search(
                        domain, email, api_key, cql_query, limit
                    )
                    if results.get("results"):
                        debug_info[f"{strategy}_no_space_success"] = True
                        return results

            except Exception as e:
                debug_info[f"{strategy}_error"] = str(e)
                continue

        return None

    def _try_fallback_searches(
        self,
        domain: str,
        email: str,
        api_key: str,
        query: str,
        space_key: Optional[str],
        content_type: str,
        limit: int,
    ) -> Optional[Dict[str, Any]]:
        """Legacy method for backward compatibility."""
        debug_info: Dict[str, Any] = {"search_strategies_attempted": []}
        return self._try_fallback_searches_with_debug(
            domain, email, api_key, query, space_key, content_type, limit, debug_info
        )

    def _process_search_results(
        self, domain: str, email: str, api_key: str, search_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process and enhance search results with additional details."""
        results = search_data.get("results", [])
        # Normalize domain: remove protocol, ensure /wiki suffix for Confluence Cloud
        normalized_domain = (
            domain.replace("https://", "").replace("http://", "").rstrip("/")
        )

        # For Confluence Cloud, base URL should include /wiki
        if not normalized_domain.endswith("/wiki"):
            # Check if it's an atlassian.net domain (Confluence Cloud)
            if "atlassian.net" in normalized_domain:
                base_url = f"https://{normalized_domain}/wiki"
            else:
                # For on-premise or other setups, use as-is
                base_url = f"https://{normalized_domain}"
        else:
            base_url = f"https://{normalized_domain}"

        processed_results = []

        for result in results:
            try:
                processed_result = {
                    "id": result.get("id"),
                    "title": result.get("title", ""),
                    "type": result.get("type", ""),
                    "status": result.get("status", ""),
                    "space": {
                        "key": result.get("space", {}).get("key", ""),
                        "name": result.get("space", {}).get("name", ""),
                    },
                    "url": f"{base_url}{result.get('_links', {}).get('webui', '')}",
                    "created": result.get("version", {}).get("when", ""),
                    "updated": result.get("version", {}).get("when", ""),
                    "version": result.get("version", {}).get("number", 1),
                }

                # Add content preview if available
                body = result.get("body", {}).get("storage", {})
                if body and body.get("value"):
                    content = body.get("value", "")
                    # Clean HTML and extract text preview
                    text_content = re.sub(r"<[^>]+>", " ", content)
                    text_content = re.sub(r"\s+", " ", text_content).strip()
                    processed_result["content_preview"] = (
                        text_content[:500] + "..."
                        if len(text_content) > 500
                        else text_content
                    )
                    processed_result["content_length"] = len(content)

                # Add ancestors (breadcrumb path)
                ancestors = result.get("ancestors", [])
                if ancestors:
                    processed_result["path"] = " > ".join(
                        [ancestor.get("title", "") for ancestor in ancestors]
                    )

                processed_results.append(processed_result)

            except Exception as e:
                # If processing individual result fails, include basic info
                processed_results.append(
                    {
                        "id": result.get("id"),
                        "title": result.get("title", ""),
                        "error": f"Failed to process result: {str(e)}",
                    }
                )

        result_dict = {
            "query_info": {
                "total_results": search_data.get("size", 0),
                "returned_results": len(processed_results),
                "search_successful": True,
            },
            "results": processed_results,
        }

        # Preserve filter_debug if it exists
        if "filter_debug" in search_data:
            result_dict["filter_debug"] = search_data["filter_debug"]

        return result_dict

    def get_env(self, var_name: str) -> Optional[str]:
        """Get environment variable value."""
        import os

        return os.getenv(var_name)
