#!/usr/bin/env python3
"""
G25 Averager

Input formats supported:
1) CSV-like lines:
   SampleName,0.123,0.456,... (25 numbers)
2) Optional whitespace around commas is fine.
3) Blank lines and lines starting with # are ignored.

Modes:
- simple: average all samples equally
- grouped: average by group prefix (text before first ':', or before first '_' if no ':'),
          then average group means equally (prevents sample-count imbalance)
"""

from __future__ import annotations

import sys
import math
from pathlib import Path
from typing import Dict, List, Tuple


DIMS = 25  # G25 has 25 dimensions


def parse_g25_line(line: str) -> Tuple[str, List[float]]:
    parts = [p.strip() for p in line.split(",")]
    if len(parts) != DIMS + 1:
        raise ValueError(f"Expected {DIMS+1} comma-separated fields, got {len(parts)}")
    name = parts[0]
    try:
        vec = [float(x) for x in parts[1:]]
    except ValueError as e:
        raise ValueError(f"Failed to parse floats for sample '{name}': {e}") from e
    return name, vec


def mean(vectors: List[List[float]]) -> List[float]:
    if not vectors:
        raise ValueError("No vectors to average.")
    out = [0.0] * DIMS
    for v in vectors:
        if len(v) != DIMS:
            raise ValueError(f"Vector has {len(v)} dims, expected {DIMS}")
        for i in range(DIMS):
            out[i] += v[i]
    n = float(len(vectors))
    return [x / n for x in out]


def is_finite_vec(vec: List[float]) -> bool:
    return all(math.isfinite(x) for x in vec)


def infer_group(sample_name: str) -> str:
    """
    Heuristic grouping:
    - If name contains ':', group is part before ':'
      e.g. 'German_Hamburg:GSM1031510' -> 'German_Hamburg'
    - Else if contains '_', group is part before last '_'? (safer: before first '_')
      e.g. 'Ukrainian_Lviv' -> 'Ukrainian'
    - Else group is the full name
    """
    if ":" in sample_name:
        return sample_name.split(":", 1)[0].strip()
    if "_" in sample_name:
        return sample_name.split("_", 1)[0].strip()
    return sample_name.strip()


def load_vectors(path: Path) -> List[Tuple[str, List[float]]]:
    samples: List[Tuple[str, List[float]]] = []
    for idx, raw in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        # allow tab-separated from some exports by converting first tab to comma name+coords?
        # but safest: require comma-separated.
        try:
            name, vec = parse_g25_line(line)
        except ValueError as e:
            raise ValueError(f"{path}:{idx}: {e}\nLine: {raw}") from e

        if not is_finite_vec(vec):
            raise ValueError(f"{path}:{idx}: Non-finite value in vector for '{name}'")
        samples.append((name, vec))
    if not samples:
        raise ValueError("No valid samples found in file.")
    return samples


def average_simple(samples: List[Tuple[str, List[float]]]) -> List[float]:
    return mean([vec for _, vec in samples])


def average_grouped(samples: List[Tuple[str, List[float]]]) -> Tuple[List[float], Dict[str, int]]:
    groups: Dict[str, List[List[float]]] = {}
    for name, vec in samples:
        g = infer_group(name)
        groups.setdefault(g, []).append(vec)

    group_means: List[List[float]] = []
    counts: Dict[str, int] = {}
    for g, vecs in sorted(groups.items()):
        counts[g] = len(vecs)
        group_means.append(mean(vecs))

    # Equal weight per group
    return mean(group_means), counts


def format_g25(name: str, vec: List[float]) -> str:
    # match typical g25 formatting: name then 25 floats
    nums = ",".join(f"{x:.6f}" for x in vec)
    return f"{name},{nums}"


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python g25_average.py <input.txt> [--mode simple|grouped] [--out output.txt]", file=sys.stderr)
        return 2

    in_path = Path(sys.argv[1])
    mode = "simple"
    out_path: Path | None = None

    # tiny arg parser
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--mode":
            i += 1
            if i >= len(sys.argv):
                print("Missing value for --mode", file=sys.stderr)
                return 2
            mode = sys.argv[i].strip().lower()
            if mode not in ("simple", "grouped"):
                print("Mode must be 'simple' or 'grouped'", file=sys.stderr)
                return 2
        elif arg == "--out":
            i += 1
            if i >= len(sys.argv):
                print("Missing value for --out", file=sys.stderr)
                return 2
            out_path = Path(sys.argv[i])
        else:
            print(f"Unknown arg: {arg}", file=sys.stderr)
            return 2
        i += 1

    samples = load_vectors(in_path)

    out_name = input("Enter output sample name: ").strip()
    if not out_name:
        print("Output name cannot be empty.", file=sys.stderr)
        return 2

    if mode == "simple":
        avg = average_simple(samples)
        report = f"Averaged {len(samples)} samples (simple)."
    else:
        avg, counts = average_grouped(samples)
        report_lines = [f"Averaged {len(samples)} samples using grouped mode (equal weight per group).", "Group counts:"]
        for g, c in sorted(counts.items()):
            report_lines.append(f"  - {g}: {c}")
        report = "\n".join(report_lines)

    line = format_g25(out_name, avg)
    print("\n" + report)
    print("\nResult:")
    print(line)

    if out_path is None:
        out_path = in_path.with_suffix(in_path.suffix + ".avg.txt")
    out_path.write_text(line + "\n", encoding="utf-8")
    print(f"\nSaved to: {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

