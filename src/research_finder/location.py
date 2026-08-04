from dataclasses import dataclass

import pycountry


class LocationLookupError(ValueError):
    """Country or state input could not be resolved."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


@dataclass(frozen=True)
class ResolvedLocation:
    """Canonical country and optional state information."""

    country: str
    country_code: str
    state: str | None
    state_code: str | None


def resolve_country(value: object) -> tuple[str, str]:
    """Resolve a country name or ISO code."""

    if not isinstance(value, str) or not value.strip():
        raise LocationLookupError(
            "country",
            "Country must be a non-empty string.",
        )

    try:
        country = pycountry.countries.lookup(value.strip())
    except LookupError as error:
        raise LocationLookupError(
            "country",
            f"Unsupported country: {value.strip()!r}.",
        ) from error

    return country.name, country.alpha_2


def resolve_state(
    country_code: str,
    value: object,
) -> tuple[str | None, str | None]:
    """Resolve an optional state name, abbreviation or ISO code."""

    if value is None:
        return None, None

    if not isinstance(value, str):
        raise LocationLookupError(
            "state",
            "State must be a string.",
        )

    cleaned_value = " ".join(value.split())

    if not cleaned_value:
        return None, None

    upper_value = cleaned_value.upper()

    if "-" in upper_value:
        subdivision = pycountry.subdivisions.get(
            code=upper_value
        )
    else:
        subdivision = pycountry.subdivisions.get(
            code=f"{country_code}-{upper_value}"
        )

    if subdivision is None:
        subdivisions = pycountry.subdivisions.get(
            country_code=country_code
        )

        subdivision = next(
            (
                candidate
                for candidate in subdivisions
                if candidate.name.casefold()
                == cleaned_value.casefold()
            ),
            None,
        )

    if (
        subdivision is None
        or subdivision.country_code != country_code
    ):
        raise LocationLookupError(
            "state",
            (
                f"Unknown state {cleaned_value!r} "
                f"for country {country_code}."
            ),
        )

    return subdivision.name, subdivision.code


def resolve_location(
    country: object,
    state: object = None,
) -> ResolvedLocation:
    """Resolve canonical country and optional state values."""

    country_name, country_code = resolve_country(country)
    state_name, state_code = resolve_state(
        country_code,
        state,
    )

    return ResolvedLocation(
        country=country_name,
        country_code=country_code,
        state=state_name,
        state_code=state_code,
    )