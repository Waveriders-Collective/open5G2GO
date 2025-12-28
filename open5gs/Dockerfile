# Open5GS 4G EPC Dockerfile
# Provides all 4G core network functions (HSS, MME, SGWC, SGWU, SMF, UPF)

FROM ubuntu:22.04

LABEL maintainer="Waveriders Collective <info@waveriders.io>"
LABEL description="Open5GS 4G EPC for Open5G2GO private network deployment"

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=UTC

# Install dependencies and Open5GS
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    software-properties-common \
    gnupg \
    ca-certificates \
    curl \
    openssl \
    iproute2 \
    iptables \
    iputils-ping \
    net-tools \
    && add-apt-repository ppa:open5gs/latest \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    open5gs \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create directories
RUN mkdir -p /var/log/open5gs /etc/open5gs /etc/freeDiameter

# Copy and run certificate generation script
COPY generate-certs.sh /generate-certs.sh
RUN chmod +x /generate-certs.sh && /generate-certs.sh

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Expose ports (informational)
# S1AP: 36412/sctp - eNodeB connection
# GTP-U: 2152/udp - User data
# GTP-C: 2123/udp - Control plane
# PFCP: 8805/udp - Session management
# Diameter: 3868/sctp - HSS/PCRF

ENTRYPOINT ["/entrypoint.sh"]
CMD ["open5gs-hssd"]
