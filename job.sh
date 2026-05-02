#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

usage() {
  cat <<EOF
Usage: $(basename "$0") -o OUTPUT_DIR INPUT_LIST

Options:
  -h, --help                 Show this help message
EOF
}

output_file=

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      output_file="${2:-}"
      output_file="$(realpath ${output_file})"
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

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

source "${scriptdir}/venv/alt_text/bin/activate"

"${scriptdir}/extract_image_alt_text.py" \
  -o ${output_file} \
  "${input_file}"

exit 0
