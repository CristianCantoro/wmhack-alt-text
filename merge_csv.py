#!/usr/bin/env python3

import argparse
import csv
from pathlib import Path


def merge_tsv_files(input_files, output_file):
    if not input_files:
        raise ValueError("No input files provided")

    header = None

    with output_file.open("w", newline="", encoding="utf-8") as out_f:
        writer = None

        for input_file in input_files:
            with input_file.open("r", newline="", encoding="utf-8") as in_f:
                reader = csv.reader(in_f, delimiter="\t")

                try:
                    current_header = next(reader)
                except StopIteration:
                    # Skip empty files
                    continue

                if header is None:
                    header = current_header
                    writer = csv.writer(out_f, delimiter="\t")
                    writer.writerow(header)
                elif current_header != header:
                    raise ValueError(
                        f"Header mismatch in {input_file}:\n"
                        f"Expected: {header}\n"
                        f"Found:    {current_header}"
                    )

                for row in reader:
                    writer.writerow(row)


def main():
    parser = argparse.ArgumentParser(
        description="Merge TSV files with headers into a single TSV file."
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        type=Path,
        help="Output TSV file",
    )
    parser.add_argument(
        "input_files",
        nargs="+",
        type=Path,
        help="Input TSV files to merge",
    )

    args = parser.parse_args()

    merge_tsv_files(args.input_files, args.output)


if __name__ == "__main__":
    main()