#!/bin/bash

# Usage function
usage() {
    echo "Usage: $0 <input_gpx_file> <output_gpx_file> [prefix]"
    echo "Example: $0 mytrack.gpx output.gpx myprefix"
    echo "Note: If no prefix is provided, it will default to the input filename without extension."
    exit 1
}

# Check if at least two arguments are provided
if [ "$#" -lt 2 ]; then
    usage
fi

# Assign arguments to variables
INPUT_GPX="$1"
OUTPUT_GPX="$2"
PREFIX="${3:-$(basename "$INPUT_GPX" .gpx)}"  # Default prefix to input filename if not provided

# Validate if the input GPX file exists
if [ ! -f "$INPUT_GPX" ]; then
    echo "Error: Input file '$INPUT_GPX' not found!"
    exit 1
fi

# Logging
echo "Running Trailmark with the following parameters:"
echo "  - Input GPX: $INPUT_GPX"
echo "  - Output GPX: $OUTPUT_GPX"
echo "  - Prefix: $PREFIX"

# Execute the Docker command
docker run --rm -v "$(pwd)":/app -w /app trailmark "$INPUT_GPX" "$OUTPUT_GPX" "$PREFIX"

# Check exit status
if [ $? -eq 0 ]; then
    echo "Success: Trailmark executed successfully!"
else
    echo "Error: Something went wrong with the execution!"
    exit 1
fi
