#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<EOF
Usage: $(basename "$0") -o OUTPUT_FILE INPUT_FILE

Options:
  -o, --output OUTPUT_FILE   Output CSV file
  -h, --help                 Show this help message
EOF
}

output_file=
input_file=

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      if [[ $# -lt 2 || "${2:-}" == -* ]]; then
        echo "Error: -o/--output requires an argument" >&2
        usage >&2
        exit 1
      fi
      output_file="$(realpath "$2")"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    --)
      shift
      break
      ;;
    -*)
      echo "Error: unknown option: $1" >&2
      usage >&2
      exit 1
      ;;
    *)
      break
      ;;
  esac
done

if [[ $# -gt 0 ]]; then
  input_file="$1"
  shift
fi

if [[ $# -gt 0 ]]; then
  echo "Error: too many arguments" >&2
  usage >&2
  exit 1
fi

if [[ -z "${input_file}" ]]; then
  echo "Error: INPUT_FILE is required" >&2
  usage >&2
  exit 1
fi

if [[ -z "${output_file}" ]]; then
  echo "Error: -o/--output is required" >&2
  usage >&2
  exit 1
fi

input_file="$(realpath "$input_file")"

scriptdir="$(cd "$(dirname "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"

source "${scriptdir}/venv/alt_text/bin/activate"

set -x

"${scriptdir}/extract_image_alt_text.py" \
  -o "$output_file" \
  "$input_file"

exit 0