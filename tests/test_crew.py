"""
Crew model tests: Insight, SurveySummaryWithComments validation and structure.
No real LLM or Crew execution.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agent.crew import Insight, SurveySummaryWithComments


@pytest.mark.unit
def test_insight_valid() -> None:
    """Insight accepts content and 1–5 comment_ids."""
    i = Insight(content="Summary insight text.", comment_ids=["c1"])
    assert i.content == "Summary insight text."
    assert i.comment_ids == ["c1"]

    i2 = Insight(content="Another.", comment_ids=["a", "b", "c", "d", "e"])
    assert len(i2.comment_ids) == 5


@pytest.mark.unit
def test_insight_requires_at_least_one_comment_id() -> None:
    """Insight raises ValidationError when comment_ids is empty."""
    with pytest.raises(ValidationError):
        Insight(content="Text", comment_ids=[])


@pytest.mark.unit
def test_insight_max_five_comment_ids() -> None:
    """Insight raises ValidationError when more than 5 comment_ids."""
    with pytest.raises(ValidationError):
        Insight(content="Text", comment_ids=["c1", "c2", "c3", "c4", "c5", "c6"])


@pytest.mark.unit
def test_survey_summary_with_comments_valid() -> None:
    """SurveySummaryWithComments accepts summary, insights, recommendations."""
    data = SurveySummaryWithComments(
        summary="Overall summary.",
        insights=[Insight(content="Insight one.", comment_ids=["c1"])],
        recommendations=["Recommendation 1", "Recommendation 2"],
    )
    assert data.summary == "Overall summary."
    assert len(data.insights) == 1
    assert data.insights[0].content == "Insight one."
    assert data.recommendations == ["Recommendation 1", "Recommendation 2"]


@pytest.mark.unit
def test_survey_summary_with_comments_minimal() -> None:
    """SurveySummaryWithComments allows single insight and single recommendation."""
    data = SurveySummaryWithComments(
        summary="S",
        insights=[Insight(content="I", comment_ids=["c1"])],
        recommendations=["R"],
    )
    assert data.summary == "S"
    assert len(data.insights) == 1
    assert len(data.recommendations) == 1


@pytest.mark.unit
def test_survey_summary_with_comments_missing_required_raises() -> None:
    """SurveySummaryWithComments raises when required fields missing."""
    with pytest.raises(ValidationError):
        SurveySummaryWithComments(
            insights=[Insight(content="I", comment_ids=["c1"])],
            recommendations=["R"],
        )
