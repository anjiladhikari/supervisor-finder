from __future__ import annotations

from functools import lru_cache

from pydantic import Field, field_validator, model_validator

from research_finder.models import StrictModel


class UniversityDirectoryError(ValueError):
    """University directory could not serve a country."""


class UniversityRecord(StrictModel):
    """One verified university directory entry."""

    name: str = Field(
        min_length=2,
        max_length=200,
    )
    aliases: list[str] = Field(
        default_factory=list,
    )
    country_code: str = Field(
        pattern=r"^[A-Z]{2}$",
    )
    state_codes: list[str] = Field(
        min_length=1,
    )
    official_domain: str = Field(
        min_length=4,
        max_length=255,
    )

    @field_validator("official_domain", mode="before")
    @classmethod
    def normalise_domain(
        cls,
        value: object,
    ) -> object:
        """Normalise the official root domain."""

        if not isinstance(value, str):
            return value

        domain = value.strip().casefold()
        domain = domain.removeprefix("www.")

        if "://" in domain or "/" in domain:
            raise ValueError("official_domain must not contain a scheme or path.")

        return domain

    @field_validator("state_codes", mode="before")
    @classmethod
    def normalise_state_codes(
        cls,
        value: object,
    ) -> object:
        """Normalise and deduplicate state codes."""

        if not isinstance(value, list):
            return value

        return list(
            dict.fromkeys(
                item.strip().upper() for item in value if isinstance(item, str) and item.strip()
            )
        )

    @model_validator(mode="after")
    def validate_state_country(
        self,
    ) -> UniversityRecord:
        """Ensure all states belong to the country."""

        expected_prefix = f"{self.country_code}-"

        if any(not state_code.startswith(expected_prefix) for state_code in self.state_codes):
            raise ValueError("University state codes must belong to country_code.")

        return self


# Format:
# name | domain | state codes | aliases
_AUSTRALIAN_UNIVERSITY_DATA = """
Adelaide University|adelaideuni.edu.au|AU-SA|Adelaide Uni
Australian Catholic University|acu.edu.au|AU-ACT,AU-NSW,AU-QLD,AU-VIC|ACU
Australian University of Theology|aut.edu.au|AU-NSW|AUT
Australian National University|anu.edu.au|AU-ACT|ANU;The Australian National University
Avondale University|avondale.edu.au|AU-NSW|Avondale
Bond University|bond.edu.au|AU-QLD|Bond
Charles Darwin University|cdu.edu.au|AU-NSW,AU-NT|CDU
Charles Sturt University|csu.edu.au|AU-ACT,AU-NSW|CSU
CQUniversity Australia|cqu.edu.au|AU-NSW,AU-QLD,AU-SA,AU-VIC,AU-WA|CQUniversity;CQU;Central Queensland University
Curtin University|curtin.edu.au|AU-WA|Curtin
Deakin University|deakin.edu.au|AU-VIC|Deakin
Edith Cowan University|ecu.edu.au|AU-WA|ECU
Federation University Australia|federation.edu.au|AU-VIC|Federation University;FedUni
Flinders University|flinders.edu.au|AU-NT,AU-SA|Flinders
Griffith University|griffith.edu.au|AU-QLD|Griffith
James Cook University|jcu.edu.au|AU-QLD|JCU
La Trobe University|latrobe.edu.au|AU-NSW,AU-VIC|La Trobe
Macquarie University|mq.edu.au|AU-NSW|Macquarie;MQ
Monash University|monash.edu|AU-VIC|Monash
Murdoch University|murdoch.edu.au|AU-WA|Murdoch
Queensland University of Technology|qut.edu.au|AU-QLD|QUT
RMIT University|rmit.edu.au|AU-VIC|RMIT
Southern Cross University|scu.edu.au|AU-NSW,AU-QLD|Southern Cross;SCU
Swinburne University of Technology|swinburne.edu.au|AU-VIC|Swinburne
Torrens University Australia|torrens.edu.au|AU-NSW,AU-QLD,AU-SA,AU-VIC|Torrens University
University of Canberra|canberra.edu.au|AU-ACT|UC
University of Divinity|divinity.edu.au|AU-VIC|Divinity
University of Melbourne|unimelb.edu.au|AU-VIC|The University of Melbourne;UniMelb
University of New England|une.edu.au|AU-NSW|UNE
UNSW Sydney|unsw.edu.au|AU-ACT,AU-NSW|UNSW;University of New South Wales
University of Newcastle|newcastle.edu.au|AU-NSW|The University of Newcastle;UON
University of Notre Dame Australia|notredame.edu.au|AU-NSW,AU-WA|Notre Dame;UNDA
University of Queensland|uq.edu.au|AU-QLD|The University of Queensland;UQ
University of Southern Queensland|unisq.edu.au|AU-QLD|UniSQ;USQ
University of Sydney|sydney.edu.au|AU-NSW|The University of Sydney;USYD
University of Tasmania|utas.edu.au|AU-NSW,AU-TAS|UTAS
University of Technology Sydney|uts.edu.au|AU-NSW|UTS
University of the Sunshine Coast|unisc.edu.au|AU-QLD|UniSC;USC
University of Western Australia|uwa.edu.au|AU-WA|The University of Western Australia;UWA
University of Wollongong|uow.edu.au|AU-NSW|UOW
Victoria University|vu.edu.au|AU-NSW,AU-QLD,AU-VIC|VU
Western Sydney University|westernsydney.edu.au|AU-NSW|WSU
""".strip()


@lru_cache
def load_australian_universities() -> tuple[UniversityRecord, ...]:
    """Load the verified Australian university directory."""

    universities: list[UniversityRecord] = []

    for line in _AUSTRALIAN_UNIVERSITY_DATA.splitlines():
        name, domain, state_text, alias_text = (part.strip() for part in line.split("|"))

        universities.append(
            UniversityRecord(
                name=name,
                aliases=[alias.strip() for alias in alias_text.split(";") if alias.strip()],
                country_code="AU",
                state_codes=[code.strip() for code in state_text.split(",")],
                official_domain=domain,
            )
        )

    if len(universities) != 42:
        raise RuntimeError("Australian university directory must contain 42 universities.")

    return tuple(universities)


def supports_country(country_code: str) -> bool:
    """Return whether a university directory exists."""

    return country_code.strip().upper() == "AU"


def get_universities(
    country_code: str,
    state_code: str | None = None,
) -> tuple[UniversityRecord, ...]:
    """Return universities for a country and optional state."""

    normalised_country = country_code.strip().upper()

    if normalised_country != "AU":
        raise UniversityDirectoryError(f"No university directory exists for {normalised_country}.")

    universities = load_australian_universities()

    if state_code is None:
        return universities

    normalised_state = state_code.strip().upper()

    return tuple(
        university for university in universities if normalised_state in university.state_codes
    )
