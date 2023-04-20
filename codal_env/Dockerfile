# codal_env/Dockerfile
FROM ubuntu:18.04 as builder

ENV TZ=Asia/Tokyo
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

RUN apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      software-properties-common && \
    add-apt-repository -y ppa:team-gcc-arm-embedded/ppa && \
    apt-get update -qq && \
    apt-get install -y --no-install-recommends \
      git make cmake python3 \
      gcc-arm-embedded && \
    apt-get autoremove -y && \
    apt-get clean -y && \
    rm -rf /var/lib/apt/lists/*

# Update packages and install required tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3 \
    ninja-build \
    srecord \
    zip

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

