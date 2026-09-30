"""Load ARC, NHMRC and MRFF grants into one schema and classify them."""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from search_terms import (
    AI_ACRONYMS,
    AI_FOR_TERMS,
    AI_NEURAL_NETWORK_TERMS,
    AI_TEXT_TERMS,
    MLS_FOR_TERMS,
    MLS_GENETICS_TERMS,
    MLS_TEXT_TERMS,
)


def _clean(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _normalise(*values: object) -> str:
    """Match the normalisation used by the original classifier."""
    text = " | ".join(_clean(v) for v in values if _clean(v))
    text = re.sub(r"[^a-z0-9+_-]+", " ", text.lower())
    text = re.sub(r"\s+", " ", text).strip()
    return f" {text} "


def _has_term(text: str, terms: tuple[str, ...]) -> bool:
    return any(f" {term} " in text for term in terms)


def _has_substring(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


AI_ACRONYM_RE = re.compile(rf"\b(?:{'|'.join(map(re.escape, AI_ACRONYMS))})\b")


def load_arc(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path, low_memory=False)
    x = x[~x["grant-status"].fillna("").eq("Declined")].copy()
    return pd.DataFrame({
        "source": "ARC",
        "grant_id": x["code"].fillna(""),
        "year": pd.to_numeric(x["funding-commencement-year"], errors="coerce").astype("Int64"),
        "scheme": x["scheme-name"].fillna(""),
        "institution": x["current-admin-organisation"].fillna(x["announcement-admin-organisation"]).fillna(""),
        "funding": pd.to_numeric(x["announced-funding-amount"], errors="coerce"),
        "title": x["grant-summary"].fillna("").str.split(". ", n=1, regex=False).str[0],
        "summary": x["grant-summary"].fillna(""),
        "keywords": "",
        "for_text": x["primary-field-of-research"].fillna(""),
        "broad_area": "",
    })


def load_nhmrc(path: Path) -> pd.DataFrame:
    x = pd.read_csv(path, low_memory=False)
    x = x[x["analysis_include"].astype(str).str.lower().eq("true")].copy()
    return pd.DataFrame({
        "source": "NHMRC",
        "grant_id": x["award_record_id"].fillna(""),
        "year": pd.to_numeric(x["source_year"], errors="coerce").astype("Int64"),
        "scheme": x["funding_scheme"].fillna(""),
        "institution": x["administering_institution"].fillna(""),
        "funding": pd.to_numeric(x["total_amount_awarded"], errors="coerce"),
        "title": x["title"].fillna(""),
        "summary": x["description"].fillna(""),
        "keywords": x["research_keywords"].fillna("") + " | " + x["health_keywords"].fillna(""),
        "for_text": x["fields_of_research"].fillna("") + " | " + x["for_category"].fillna(""),
        "broad_area": x["broad_research_area"].fillna(""),
    })


def load_mrff(path: Path) -> pd.DataFrame:
    x = pd.read_excel(path, sheet_name="Grants List")
    x = x[x["Project Name"].notna()].copy()
    return pd.DataFrame({
        "source": "MRFF",
        "grant_id": x["Grant ID"].fillna(""),
        "year": pd.to_datetime(x["Contract Start Date"], errors="coerce").dt.year.astype("Int64"),
        "scheme": x["Grant Opportunity"].fillna(""),
        "institution": x["Organisation"].fillna(""),
        "funding": pd.to_numeric(x["Total Grant Value"], errors="coerce"),
        "title": x["Project Name"].fillna(""),
        "summary": x["Project Summary"].fillna(""),
        "keywords": "",
        "for_text": x["Field(s) of Research\n(DIVISION / Group / Field)"].fillna(""),
        "broad_area": x["Broad Research Area"].fillna(""),
    })


def load_grants(arc: Path, nhmrc: Path, mrff: Path, start_year: int = 2022, end_year: int = 2025) -> pd.DataFrame:
    grants = pd.concat([load_arc(arc), load_nhmrc(nhmrc), load_mrff(mrff)], ignore_index=True)
    return (
        grants[grants["year"].between(start_year, end_year, inclusive="both")]
        .sort_values(["source", "year", "grant_id"])
        .reset_index(drop=True)
    )


def _classify_row(row: pd.Series) -> tuple[bool, bool]:
    raw = " | ".join(_clean(v) for v in (row.title, row.summary, row.keywords) if _clean(v))
    text = _normalise(row.title, row.summary, row.keywords)
    for_text = _normalise(row.for_text)
    domain = _normalise(row.for_text, row.broad_area)

    ai_explicit = _has_term(text, AI_TEXT_TERMS)
    ai_acronym = bool(AI_ACRONYM_RE.search(raw))
    ai_for = _has_substring(for_text, AI_FOR_TERMS)

    # Preserve the original biological-neural-network ambiguity rule.
    neural_only = (
        _has_term(text, AI_NEURAL_NETWORK_TERMS)
        and not _has_term(text, tuple(t for t in AI_TEXT_TERMS if t not in AI_NEURAL_NETWORK_TERMS))
        and not ai_acronym
    )
    if neural_only and _has_substring(domain, ("neuroscience", "neurosciences", "central nervous system")):
        if not any(x in text for x in ("machine learning", "deep learning", "algorithm", "classifier", "computational", "artificial intelligence")):
            ai_explicit = False

    ai = ai_for or ai_explicit or ai_acronym

    mls_terms = MLS_TEXT_TERMS
    if " genetic algorithm " in text or " genetic algorithms " in text:
        mls_terms = tuple(t for t in MLS_TEXT_TERMS if t not in MLS_GENETICS_TERMS)
    mls = _has_substring(domain, MLS_FOR_TERMS) or _has_term(text, mls_terms)

    return ai, mls


def classify_grants(grants: pd.DataFrame) -> pd.DataFrame:
    """Add only the booleans used by the final analysis."""
    out = grants.copy()
    flags = out.apply(_classify_row, axis=1, result_type="expand")
    flags.columns = ["ai", "molecular_life_science"]
    out[["ai", "molecular_life_science"]] = flags
    out["ai_mls"] = out["ai"] & out["molecular_life_science"]
    return out
