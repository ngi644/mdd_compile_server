#!/bin/bash
# compile_codal.sh

# Check if the required environment variables are set
if [ -z "$ZIP_FILE" ] || [ -z "$OUTPUT_PATH" ]; then
    echo "ERROR: Missing required environment variables ZIP_FILE or OUTPUT_PATH."
    exit 1
fi

# Unzip the source code
unzip -o "$ZIP_FILE" -d ./source

if [ -e ./source/__MACOSX ]; then
    rm -r ./source/__MACOSX
fi

# Create a temporary build directory
mkdir -p build

# Compile the source code
cmake . -GNinja
ninja
cp MICROBIT.hex $OUTPUT_PATH

# remove compiled files
rm MICROBIT.hex
rm MICROBIT.bin

echo "Compilation finished."
