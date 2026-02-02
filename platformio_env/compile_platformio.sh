#!/bin/bash
# compile_platformio.sh

# Check if the required environment variables are set
if [ -z "$ZIP_FILE" ] || [ -z "$OUTPUT_PATH" ] || [ -z "$BOARD" ]; then
    echo "ERROR: Missing required environment variables ZIP_FILE, OUTPUT_PATH, or BOARD."
    exit 1
fi

# Save ZIP file to tmp before cleaning workspace
cp "$ZIP_FILE" /tmp/source.zip

# Clean workspace
rm -rf /workspace/*

# Copy template to workspace
cp -r /template/* /workspace/

# Unzip the source code to src directory
unzip -o /tmp/source.zip -d /workspace/src/

# Remove macOS metadata if exists
if [ -e /workspace/src/__MACOSX ]; then
    rm -r /workspace/src/__MACOSX
fi

# Clean up tmp file
rm /tmp/source.zip

# Compile the source code
cd /workspace
platformio run -e "$BOARD"

# Check if compilation was successful
if [ $? -eq 0 ]; then
    BUILD_DIR="/workspace/.pio/build/$BOARD"
    OUTPUT_DIR="/tmp/output_$$"
    mkdir -p "$OUTPUT_DIR"

    # Copy firmware.bin (required)
    cp "$BUILD_DIR/firmware.bin" "$OUTPUT_DIR/"

    # Copy bootloader.bin if exists
    if [ -f "$BUILD_DIR/bootloader.bin" ]; then
        cp "$BUILD_DIR/bootloader.bin" "$OUTPUT_DIR/"
    fi

    # Copy partitions.bin if exists
    if [ -f "$BUILD_DIR/partitions.bin" ]; then
        cp "$BUILD_DIR/partitions.bin" "$OUTPUT_DIR/"
    fi

    # Create ZIP archive with all binary files
    cd "$OUTPUT_DIR"
    zip -j "$OUTPUT_PATH" *.bin

    # Clean up
    rm -rf "$OUTPUT_DIR"

    echo "Compilation finished successfully."
else
    echo "Compilation failed."
    exit 1
fi
