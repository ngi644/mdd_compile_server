#!/bin/bash
# compile_codal.sh

# Check if the required environment variables are set
if [ -z "$ZIP_FILE" ] || [ -z "$OUTPUT_PATH" ]; then
    echo "ERROR: Missing required environment variables ZIP_FILE or OUTPUT_PATH."
    exit 1
fi

# Remove existing source files to avoid conflicts
rm -f ./source/main.cpp
rm -f ./source/Main.cpp

# Unzip the source code
unzip -o "$ZIP_FILE" -d ./source

if [ -e ./source/__MACOSX ]; then
    rm -r ./source/__MACOSX
fi

# Clean previous build artifacts (keep library cache, only rebuild user code)
rm -f MICROBIT.hex MICROBIT.bin

# Remove only user source object files to force recompilation
rm -rf build/source/
rm -rf build/CMakeFiles/MICROBIT.dir/

# Touch source files to ensure they are seen as modified
find ./source -name "*.cpp" -exec touch {} \;
find ./source -name "*.h" -exec touch {} \;

# Compile the source code
ninja
cp MICROBIT.hex $OUTPUT_PATH

# remove compiled files
rm MICROBIT.hex
rm MICROBIT.bin

echo "Compilation finished."
