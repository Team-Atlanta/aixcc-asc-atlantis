#!/bin/bash

# Initialize variables
CP_HARNESS_NAME=""
CP_INPUT_BLOB=""

# Parse command-line options
while getopts "h:i:" opt; do
  case $opt in
    h) CP_HARNESS_NAME="$OPTARG"
    ;;
    i) CP_INPUT_BLOB="$OPTARG"
    ;;
    \?) echo "Invalid option -$OPTARG" >&2
    ;;
  esac
done

# Check if both options are provided
if [ -z "$CP_HARNESS_NAME" ] || [ -z "$CP_INPUT_BLOB" ]; then
  echo "Usage: $0 -h <harness_name> -i <input_blob>"
  exit 1
fi

# Your original script logic
cd /out
./$CP_HARNESS_NAME -runs=1 -timeout=30 ./pov_validation/$CP_INPUT_BLOB 

exit 0