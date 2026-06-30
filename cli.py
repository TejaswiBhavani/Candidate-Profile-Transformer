#!/usr/bin/env python3
"""
CLI for the Eightfold candidate-profile pipeline.

Usage:
    python cli.py --sources recruiter.csv resume.pdf [linkedin.json ...] \\
                   [--config configs/public_profile.json] \\
                   [--out outputs/result.json] \\
                   [--show-canonical]

With no --config, emits the default output schema. With --config, emits
whatever shape that config's `fields` list describes, validated against
a schema built from that config.

Exit codes: 0 = success, 1 = pipeline produced validation/projection
errors (e.g. on_missing="error" hit a missing required field), 2 = bad
CLI usage (e.g. file not found is NOT this — that's handled gracefully
inside the pipeline as a per-source warning, not a CLI error).
"""

import argparse
import json
import sys

from eightfold.pipeline import run


def main():
    parser = argparse.ArgumentParser(description="Eightfold candidate-profile pipeline")
    parser.add_argument("--sources", nargs="+", required=True,
                         help="Input source files (.csv, .json, .pdf), in priority order")
    parser.add_argument("--config", default=None,
                         help="Path to a runtime projection config JSON. Omit for the default schema.")
    parser.add_argument("--out", default=None,
                         help="Write JSON output here instead of stdout")
    parser.add_argument("--show-canonical", action="store_true",
                         help="Also print the internal canonical profile (with full provenance) to stderr")
    args = parser.parse_args()

    config = None
    if args.config:
        with open(args.config, encoding="utf-8") as f:
            config = json.load(f)

    result = run(args.sources, config=config)

    for w in result.warnings:
        print(f"[warn] {w}", file=sys.stderr)

    if args.show_canonical:
        print("---- canonical profile ----", file=sys.stderr)
        print(json.dumps(result.canonical, indent=2, default=str), file=sys.stderr)

    if not result.ok:
        for e in result.validation_errors:
            print(f"[error] {e}", file=sys.stderr)
        sys.exit(1)

    out_json = json.dumps(result.output, indent=2, ensure_ascii=False)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            f.write(out_json + "\n")
        print(f"Wrote {args.out}", file=sys.stderr)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
