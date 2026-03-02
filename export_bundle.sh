#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIST_DIR="${PROJECT_DIR}/dist"
STAMP="$(date +%Y%m%d_%H%M%S)"
NAME="smartsh_bundle_${STAMP}"
TARGET_DIR="${DIST_DIR}/${NAME}"

rm -rf "${TARGET_DIR}"
mkdir -p "${TARGET_DIR}"

cp -r "${PROJECT_DIR}/smartsh" "${TARGET_DIR}/"
cp "${PROJECT_DIR}/requirements.txt" "${TARGET_DIR}/"
cp "${PROJECT_DIR}/install.sh" "${TARGET_DIR}/"
cp "${PROJECT_DIR}/uninstall.sh" "${TARGET_DIR}/"
cp "${PROJECT_DIR}/README.md" "${TARGET_DIR}/"
chmod +x "${TARGET_DIR}/install.sh" "${TARGET_DIR}/uninstall.sh"

tar -C "${DIST_DIR}" -czf "${DIST_DIR}/${NAME}.tar.gz" "${NAME}"
rm -rf "${TARGET_DIR}"

echo "Bundle created: ${DIST_DIR}/${NAME}.tar.gz"
