#!/bin/bash
# compile_platformio.sh

# Check if the required environment variables are set
if [ -z "$ZIP_FILE" ] || [ -z "$OUTPUT_PATH" ] || [ -z "$BOARD" ]; then
    echo "ERROR: Missing required environment variables ZIP_FILE, OUTPUT_PATH, or BOARD."
    exit 1
fi

# Clean workspace
rm -rf /workspace/*

# Copy template to workspace
cp -r /template/* /workspace/

# Unzip the source code to src directory
unzip -o "$ZIP_FILE" -d /workspace/src/

# Remove macOS metadata if exists
if [ -e /workspace/src/__MACOSX ]; then
    rm -r /workspace/src/__MACOSX
fi

# Compile the source code
cd /workspace
platformio run -e "$BOARD"

# Check if compilation was successful
if [ $? -eq 0 ]; then
    # Copy the output binary
    cp /workspace/.pio/build/$BOARD/firmware.bin "$OUTPUT_PATH"
    echo "Compilation finished successfully."
else
    echo "Compilation failed."
    exit 1
fi
