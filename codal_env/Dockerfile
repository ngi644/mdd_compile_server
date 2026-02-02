# codal_env/Dockerfile
FROM debian:bookworm-slim as builder

ENV TZ=Asia/Tokyo
ENV DEBIAN_FRONTEND=noninteractive

# Update packages and install required tools
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    ninja-build \
    srecord \
    zip \
    unzip \
    ca-certificates \
    wget \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install ARM GCC toolchain manually (detect architecture)
RUN ARCH=$(uname -m) && \
    if [ "$ARCH" = "x86_64" ]; then \
        TOOLCHAIN_URL="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-x86_64-arm-none-eabi.tar.xz"; \
    elif [ "$ARCH" = "aarch64" ]; then \
        TOOLCHAIN_URL="https://developer.arm.com/-/media/Files/downloads/gnu/13.2.rel1/binrel/arm-gnu-toolchain-13.2.rel1-aarch64-arm-none-eabi.tar.xz"; \
    else \
        echo "Unsupported architecture: $ARCH"; exit 1; \
    fi && \
    wget -q "$TOOLCHAIN_URL" -O /tmp/gcc-arm.tar.xz && \
    mkdir -p /opt/gcc-arm && \
    tar -xf /tmp/gcc-arm.tar.xz -C /opt/gcc-arm --strip-components=1 && \
    rm /tmp/gcc-arm.tar.xz

ENV PATH="/opt/gcc-arm/bin:${PATH}"

# Clone the microbit-v2-samples repository
RUN git clone --recursive https://github.com/lancaster-university/microbit-v2-samples.git

# Setup the build environment
WORKDIR /microbit-v2-samples

# Add a build script to compile the source code
COPY compile_codal.sh /microbit-v2-samples/

# Pre compile
RUN mkdir -p build && \
    cmake . -GNinja && \
    ninja

RUN rm MICROBIT.hex && rm MICROBIT.bin

# Set the entrypoint to the build script
ENTRYPOINT ["/bin/bash", "-c", "tail -f /dev/null"]
