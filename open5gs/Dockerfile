# Open5GS 4G EPC + 5G SA Core Dockerfile
# Provides all 4G EPC and 5G SA core network functions

FROM ubuntu:22.04

LABEL maintainer="Waveriders Collective <info@waveriders.io>"
LABEL description="Open5GS 4G EPC + 5G SA Core for Open5G2GO private network deployment"

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
    && curl -fsSL https://www.mongodb.org/static/pgp/server-6.0.asc | gpg -o /usr/share/keyrings/mongodb-server-6.0.gpg --dearmor \
    && echo "deb [ arch=amd64,arm64 signed-by=/usr/share/keyrings/mongodb-server-6.0.gpg ] https://repo.mongodb.org/apt/ubuntu jammy/mongodb-org/6.0 multiverse" > /etc/apt/sources.list.d/mongodb-org-6.0.list \
    && add-apt-repository ppa:open5gs/latest \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
    mongodb-org-shell \
    open5gs-common \
    open5gs-hss \
    open5gs-mme \
    open5gs-sgwc \
    open5gs-sgwu \
    open5gs-smf \
    open5gs-upf \
    open5gs-pcrf \
    open5gs-nrf \
    open5gs-amf \
    open5gs-ausf \
    open5gs-udm \
    open5gs-udr \
    open5gs-pcf \
    open5gs-nssf \
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
# 4G: S1AP: 36412/sctp - eNodeB connection
# 5G: NGAP: 38412/sctp - gNodeB connection
# GTP-U: 2152/udp - User data
# GTP-C: 2123/udp - Control plane (4G)
# PFCP: 8805/udp - Session management
# Diameter: 3868/sctp - HSS/PCRF (4G)
# SBI: 7777/tcp - Service-based interface (5G)

ENTRYPOINT ["/entrypoint.sh"]
CMD ["open5gs-hssd"]
