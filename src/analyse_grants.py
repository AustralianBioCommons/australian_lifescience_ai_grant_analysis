#!/usr/bin/env python3
"""Classify 2022-2025 ARC/NHMRC/MRFF grants and produce the headline analysis."""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import PercentFormatter

from grants import classify_grants, load_grants

START_YEAR = 2022
END_YEAR = 2025
SOURCES = ["NHMRC", "MRFF", "ARC"]


def _summarise(data: pd.DataFrame, by: list[str]) -> pd.DataFrame:
    mls = data[data["molecular_life_science"]].copy()
    mls["ai_funding"] = mls["funding"].where(mls["ai"], 0)
    result = mls.groupby(by, as_index=False).agg(
        molecular_life_science_grants=("grant_id", "size"),
        ai_molecular_life_science_grants=("ai", "sum"),
        molecular_life_science_funding=("funding", "sum"),
        ai_molecular_life_science_funding=("ai_funding", "sum"),
    )
    result["ai_share_of_molecular_life_science_grants"] = (
        result["ai_molecular_life_science_grants"] / result["molecular_life_science_grants"]
    )
    return result


def summary_table(data: pd.DataFrame) -> pd.DataFrame:
    """One table containing annual plot data and pooled 2022-2025 results."""
    annual = _summarise(data, ["source", "year"])
    annual["period"] = annual["year"].astype(str)
    annual = annual.drop(columns="year")

    all_annual = _summarise(data.assign(source="All funders"), ["source", "year"])
    all_annual["period"] = all_annual["year"].astype(str)
    all_annual = all_annual.drop(columns="year")

    pooled = _summarise(data, ["source"])
    pooled["period"] = f"{START_YEAR}-{END_YEAR} pooled"

    all_pooled = _summarise(data.assign(source="All funders"), ["source"])
    all_pooled["period"] = f"{START_YEAR}-{END_YEAR} pooled"

    columns = [
        "source",
        "period",
        "molecular_life_science_grants",
        "ai_molecular_life_science_grants",
        "ai_share_of_molecular_life_science_grants",
        "ai_molecular_life_science_funding",
        "molecular_life_science_funding",
    ]
    return pd.concat([annual, all_annual, pooled, all_pooled], ignore_index=True)[columns]


def plot_ai_share(summary: pd.DataFrame, path: Path) -> None:
    annual = summary[
        summary["source"].isin(SOURCES) & summary["period"].str.fullmatch(r"\d{4}")
    ].copy()
    annual["year"] = annual["period"].astype(int)

    colors = {"NHMRC": "#e91e8f", "MRFF": "#67c5b8", "ARC": "#1f77b4"}
    label_offsets = {
        ("NHMRC", 2022): (0, 12), ("NHMRC", 2023): (0, 12),
        ("NHMRC", 2024): (0, 12), ("NHMRC", 2025): (0, -22),
        ("MRFF", 2022): (0, 12), ("MRFF", 2023): (0, 12),
        ("MRFF", 2024): (-32, -28), ("MRFF", 2025): (0, 12),
        ("ARC", 2022): (0, -22), ("ARC", 2023): (0, 12),
        ("ARC", 2024): (32, 12), ("ARC", 2025): (0, 12),
    }

    plt.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 17,
        "axes.labelsize": 18, "xtick.labelsize": 18, "ytick.labelsize": 16,
    })
    fig, ax = plt.subplots(figsize=(13.5, 7.5))

    for source in SOURCES:
        d = annual[annual["source"] == source].sort_values("year")
        ax.plot(
            d["year"], d["ai_share_of_molecular_life_science_grants"],
            marker="o", markersize=10, linewidth=3.5,
            color=colors[source], label=source,
        )
        for row in d.itertuples(index=False):
            dx, dy = label_offsets[(source, row.year)]
            ax.annotate(
                f"{int(row.ai_molecular_life_science_grants):,}",
                (row.year, row.ai_share_of_molecular_life_science_grants),
                xytext=(dx, dy), textcoords="offset points", ha="center",
                va="bottom" if dy >= 0 else "top", fontsize=15.5,
                fontweight="semibold", color=colors[source],
            )

    ax.set_xlabel("Year")
    ax.set_ylabel("% of molecular life-science\ngrants")
    ax.set_xticks(range(START_YEAR, END_YEAR + 1))
    ax.set_ylim(0, 0.08)
    ax.set_yticks([0, 0.02, 0.04, 0.06, 0.08])
    ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
    ax.grid(axis="y", alpha=0.22, linewidth=1.0)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines["left"].set_linewidth(1.1)
    ax.spines["bottom"].set_linewidth(1.1)
    ax.tick_params(axis="y", width=1.0)
    ax.tick_params(axis="x", width=1.0, pad=8)
    legend = ax.legend(
        frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.17),
        ncol=3, handlelength=2.8, columnspacing=1.8,
    )
    for line in legend.get_lines():
        line.set_linewidth(4)
    fig.subplots_adjust(top=0.96, bottom=0.26, left=0.12, right=0.98)
    fig.savefig(path, dpi=300, bbox_inches="tight")
    plt.close(fig)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arc", type=Path, required=True)
    parser.add_argument("--nhmrc", type=Path, required=True)
    parser.add_argument("--mrff", type=Path, required=True)
    parser.add_argument("--outdir", type=Path, required=True)
    args = parser.parse_args()
    args.outdir.mkdir(parents=True, exist_ok=True)

    grants = classify_grants(load_grants(args.arc, args.nhmrc, args.mrff, START_YEAR, END_YEAR))
    summary = summary_table(grants)

    grants.to_csv(args.outdir / "grants_classified.csv", index=False)
    summary.to_csv(args.outdir / "grant_ai_summary.csv", index=False)
    plot_ai_share(summary, args.outdir / "grant_ai_proportion.png")

    print(summary.to_string(index=False))


if __name__ == "__main__":
    main()
