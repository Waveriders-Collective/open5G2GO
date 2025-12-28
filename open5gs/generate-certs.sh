#!/bin/bash
# Generate self-signed certificates for freeDiameter
# These are used for Diameter protocol communication between HSS, MME, SMF

set -e

CERT_DIR="/etc/freeDiameter"
mkdir -p "$CERT_DIR"

# Only generate if not already present
if [ -f "$CERT_DIR/ca.cert.pem" ]; then
    echo "Certificates already exist, skipping generation"
    exit 0
fi

echo "Generating freeDiameter certificates..."

cd "$CERT_DIR"

# Generate DH parameters (2048-bit for security)
openssl dhparam -out dh.pem 2048

# Generate CA key and certificate
openssl genrsa -out ca.key.pem 2048
openssl req -new -x509 -days 3650 -key ca.key.pem -out ca.cert.pem \
    -subj "/CN=Open5G2GO-CA/O=Waveriders/C=US"

# Function to generate component certificate
generate_cert() {
    local name=$1
    local cn=$2

    openssl genrsa -out ${name}.key.pem 2048
    openssl req -new -key ${name}.key.pem -out ${name}.csr.pem \
        -subj "/CN=${cn}/O=Waveriders/C=US"
    openssl x509 -req -days 3650 -in ${name}.csr.pem \
        -CA ca.cert.pem -CAkey ca.key.pem -CAcreateserial \
        -out ${name}.cert.pem
    rm -f ${name}.csr.pem
}

# Generate certificates for each component
generate_cert "hss" "hss.open5g2go.local"
generate_cert "mme" "mme.open5g2go.local"
generate_cert "smf" "smf.open5g2go.local"
generate_cert "pcrf" "pcrf.open5g2go.local"

# Set permissions
chmod 644 *.pem
chmod 600 *.key.pem

echo "Certificate generation complete"
ls -la "$CERT_DIR"
