#!/usr/bin/env bash
set -euo pipefail
IFS=$'\n\t'

DEFAULT_OUTPUT_DIR='output/'
DEFAULT_PROC_DIR='proc/'

usage() {
  cat <<EOF
Usage: $(basename "$0") -o OUTPUT_DIR -p PROC_DIR INPUT_LIST

Options:
  -o, --output OUTPUT_DIR    Directory where output CSV files will be written
  							 [default: ${DEFAULT_OUTPUT_DIR}]
  -p, --proc-dir PROC_DIR    Processing directory [default: ${DEFAULT_PROC_DIR}]
  -h, --help                 Show this help message
EOF
}

output_dir="${DEFAULT_OUTPUT_DIR}"
proc_dir="${DEFAULT_PROC_DIR}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    -o|--output)
      output_dir="${2:-}"
      output_dir="$(realpath ${output_dir})"
      shift 2
      ;;
    -p|--proc-dir)
      proc_dir="${2:-}"
      proc_dir="$(realpath ${proc_dir})"
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

if [[ $# -ne 1 ]]; then
  echo "Error: missing INPUT_LIST" >&2
  usage >&2
  exit 1
fi

input_list="$1"

if [[ -z "${output_dir}" ]]; then
  echo "Error: -o/--output is required" >&2
  usage >&2
  exit 1
fi

if [[ -z "${proc_dir}" ]]; then
  echo "Error: -p/--proc-dir is required" >&2
  usage >&2
  exit 1
fi

mkdir -p "${output_dir}"
mkdir -p "${proc_dir}"

scriptdir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# source "${scriptdir}/venv/alt_text/bin/activate"

# parallel \
#   --sshloginfile "${scriptdir}/machines.txt" \
#   --progress \
#   --results "${proc_dir}/$(date +"%Y-%m-%dT%H:%M:%S")" \
#     -- "${scriptdir}/extract_image_alt_text.py" \
#        -o "${output_dir}/{/.}_alt_text.csv" \
#        -p "${proc_dir}" \
#        "{}" :::: "${input_list}"
parallel \
  --sshloginfile "${scriptdir}/machines.txt" \
  -j8 \
  --progress \
  --results "${proc_dir}/$(date +"%Y-%m-%dT%H:%M:%S")" \
    -- "${scriptdir}/extract_image_alt_text.py" \
       -o "${output_dir}/{/.}_alt_text.csv" \
       "{}" :::: "${input_list}"

exit 0

