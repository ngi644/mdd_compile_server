# platformio_env/Dockerfile
FROM python:3.9-slim

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Install required packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    unzip \
    && apt-get autoremove -y \
    && apt-get clean -y \
    && rm -rf /var/lib/apt/lists/*

# Install PlatformIO CLI
RUN pip install --no-cache-dir platformio

# Install ESP32 platform
RUN platformio platform install espressif32

# Install M5Unified library globally
RUN platformio pkg install -g --library "m5stack/M5Unified"

# Copy template project
COPY template/ /template/
COPY compile_platformio.sh /compile_platformio.sh
RUN chmod +x /compile_platformio.sh

# Pre-compile to cache dependencies (using atoms3 as reference)
WORKDIR /pre_build
RUN cp -r /template/* /pre_build/ && \
    echo '#include <M5Unified.h>\nvoid setup() { M5.begin(); }\nvoid loop() { M5.update(); }' > /pre_build/src/main.cpp && \
    platformio run -e m5stack-atoms3 || true && \
    rm -rf /pre_build

WORKDIR /workspace

# Set the entrypoint to keep container running
ENTRYPOINT ["/bin/bash", "-c", "tail -f /dev/null"]
