"""Repeatable synthetic-only UAT dataset for laboratory work 11.

All input records are generated from the repository's local mock examples.
No clinical records, names, identifiers or secrets are read or written.
"""

from __future__ import annotations

import argparse
import csv
import io
import random
from pathlib import Path

from integration import EXTERNAL_COLUMNS, MAX_ROWS
from mock_medical_service import RECORDS

DEFAULT_INVALID_ROWS = (10, 20, 30, 40, 50)


def generate_csv(*, seed: int = 11011, rows: int = 50,
                 invalid_rows: tuple[int, ...] = DEFAULT_INVALID_ROWS) -> bytes:
    """Return UTF-8 CSV; row numbers are 1-based excluding the header."""
    if not 1 <= rows <= MAX_ROWS:
        raise ValueError(f"rows must be between 1 and {MAX_ROWS}")
    if any(not 1 <= index <= rows for index in invalid_rows):
        raise ValueError("invalid_rows must reference existing data rows")

    rng = random.Random(seed)
    sample_records = tuple(RECORDS.values())
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=EXTERNAL_COLUMNS,
                            lineterminator="\n", extrasaction="raise")
    writer.writeheader()
    invalid_set = set(invalid_rows)
    for row_number in range(1, rows + 1):
        record = dict(sample_records[rng.randrange(len(sample_records))])
        if row_number in invalid_set:
            record["age_years"] = "not-a-number"
        writer.writerow(record)
    return output.getvalue().encode("utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic CardioPrognoz UAT CSV")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=11011)
    parser.add_argument("--rows", type=int, default=50)
    parser.add_argument("--invalid-rows", default="10,20,30,40,50",
                        help="1-based comma-separated row numbers")
    args = parser.parse_args()
    invalid_rows = tuple(int(part) for part in args.invalid_rows.split(",") if part.strip())
    data = generate_csv(seed=args.seed, rows=args.rows, invalid_rows=invalid_rows)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)
    print(f"Generated {args.rows} synthetic rows in {args.output}; invalid rows: {invalid_rows}")


if __name__ == "__main__":
    main()
