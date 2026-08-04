import pytest

from research_finder.location import (
    LocationLookupError,
    resolve_location,
)
from research_finder.models import SearchRequest
from research_finder.nodes import (
    find_universities,
    validate_input,
)
from research_finder.university_directory import (
    UniversityRecord,
    get_universities,
)


def test_resolves_australian_state_abbreviation() -> None:
    location = resolve_location(
        "Australia",
        "vic",
    )

    assert location.country == "Australia"
    assert location.country_code == "AU"
    assert location.state == "Victoria"
    assert location.state_code == "AU-VIC"


def test_state_is_optional() -> None:
    location = resolve_location(
        "Australia",
        None,
    )

    assert location.state is None
    assert location.state_code is None


def test_invalid_state_is_rejected() -> None:
    with pytest.raises(
        LocationLookupError,
        match="Unknown state",
    ):
        resolve_location(
            "Australia",
            "California",
        )


def test_unsupported_country_is_rejected() -> None:
    result = validate_input(
        {
            "raw_request": {
                "country": "United States",
                "state": "California",
                "research_topic": (
                    "Reinforcement learning"
                ),
            }
        }
    )

    assert result["request"] is None

    assert any(
        "not supported yet" in error
        for error in result["errors"]
    )


def test_australia_has_42_universities() -> None:
    universities = get_universities("AU")

    assert len(universities) == 42


def test_victoria_has_12_universities() -> None:
    universities = get_universities(
        country_code="AU",
        state_code="AU-VIC",
    )

    assert len(universities) == 12

    assert all(
        "AU-VIC" in university.state_codes
        for university in universities
    )


def test_university_node_uses_state() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state="Victoria",
        state_code="AU-VIC",
        research_topic="Artificial intelligence",
    )

    result = find_universities(
        {"request": request}
    )

    candidates = result[
        "candidate_universities"
    ]

    assert len(candidates) == 12

    assert all(
        isinstance(
            university,
            UniversityRecord,
        )
        for university in candidates
    )

    assert result["execution_log"] == [
        (
            "University directory selected "
            "12 candidates for Victoria, Australia."
        )
    ]


def test_university_node_without_state_returns_all() -> None:
    request = SearchRequest(
        country="Australia",
        country_code="AU",
        state=None,
        state_code=None,
        research_topic="Artificial intelligence",
    )

    result = find_universities(
        {"request": request}
    )

    assert len(
        result["candidate_universities"]
    ) == 42

    assert result["execution_log"] == [
        (
            "University directory selected "
            "42 candidates for Australia."
        )
    ]