#!/usr/bin/env python3
"""Aggregate community contributions into paper-ready tables.

Usage:
    python scripts/aggregate_contributions.py [--dir community_results] [--format latex|csv|json]

Reads all contribution JSON files from the specified directory, aggregates
them by model and method, and outputs summary tables suitable for inclusion
in the paper.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from obliteratus.community import (
    aggregate_results,
    generate_latex_table,
    load_contributions,
)


def main():
    parser = argparse.ArgumentParser(
        description="Aggregate community contributions into paper tables."
    )
    parser.add_argument(
        "--dir",
        default="community_results",
        help="Directory containing contribution JSON files (default: community_results)",
    )
    parser.add_argument(
        "--format",
        choices=["latex", "csv", "json", "summary"],
        default="summary",
        help="Output format (default: summary)",
    )
    parser.add_argument(
        "--metric",
        default="refusal_rate",
        help="Metric to display in tables (default: refusal_rate)",
    )
    parser.add_argument(
        "--methods",
        nargs="*",
        help="Methods to include (default: all)",
    )
    parser.add_argument(
        "--min-runs",
        type=int,
        default=1,
        help="Minimum runs per (model, method) to include (default: 1)",
    )
    args = parser.parse_args()

    # Load all contributions
    records = load_contributions(args.dir)
    if not records:
        print(f"No contributions found in {args.dir}/", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(records)} contribution(s) from {args.dir}/", file=sys.stderr)

    # Aggregate
    aggregated = aggregate_results(records)

    # Filter by minimum runs
    if args.min_runs > 1:
        for model in list(aggregated.keys()):
            for method in list(aggregated[model].keys()):
                if aggregated[model][method]["n_runs"] < args.min_runs:
                    del aggregated[model][method]
            if not aggregated[model]:
                del aggregated[model]

    if not aggregated:
        print("No results meet the minimum run threshold.", file=sys.stderr)
        sys.exit(1)

    # Output
    if args.format == "summary":
        _print_summary(aggregated, args.metric)
    elif args.format == "latex":
        print(generate_latex_table(aggregated, methods=args.methods, metric=args.metric))
    elif args.format == "json":
        print(json.dumps(aggregated, indent=2))
    elif args.format == "csv":
        _print_csv(aggregated, args.metric)


def _print_summary(aggregated: dict, metric: str):
    """Print a human-readable summary of aggregated results."""
    total_runs = sum(
        data["n_runs"]
        for model_data in aggregated.values()
        for data in model_data.values()
    )
    n_models = len(aggregated)
    n_methods = len(set(
        method
        for model_data in aggregated.values()
        for method in model_data
    ))

    print(f"\n{'=' * 70}")
    print("Community Contribution Summary")
    print(f"{'=' * 70}")
    print(f"  Total runs:    {total_runs}")
    print(f"  Models:        {n_models}")
    print(f"  Methods:       {n_methods}")
    print()

    for model in sorted(aggregated.keys()):
        model_data = aggregated[model]
        short = model.split("/")[-1] if "/" in model else model
        print(f"  {short}:")
        for method in sorted(model_data.keys()):
            data = model_data[method]
            n = data["n_runs"]
            if metric in data:
                stats = data[metric]
                mean = stats["mean"]
                std = stats["std"]
                if std > 0 and n > 1:
                    print(f"    {method:20s}  {metric}={mean:.2f} ± {std:.2f}  (n={n})")
                else:
                    print(f"    {method:20s}  {metric}={mean:.2f}  (n={n})")
            else:
                print(f"    {method:20s}  (no {metric} data, n={n})")
        print()

    print(f"{'=' * 70}")
    print(f"To generate LaTeX: python {sys.argv[0]} --format latex")
    print(f"To generate CSV:   python {sys.argv[0]} --format csv")


def _print_csv(aggregated: dict, metric: str):
    """Print results as CSV."""
    print("model,method,n_runs,mean,std,min,max")
    for model in sorted(aggregated.keys()):
        for method in sorted(aggregated[model].keys()):
            data = aggregated[model][method]
            n = data["n_runs"]
            if metric in data:
                stats = data[metric]
                print(
                    f"{model},{method},{n},"
                    f"{stats['mean']:.4f},{stats['std']:.4f},"
                    f"{stats['min']:.4f},{stats['max']:.4f}"
                )


if __name__ == "__main__":
    main()
