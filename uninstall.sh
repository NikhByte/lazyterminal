#!/usr/bin/env bash
set -euo pipefail

INSTALL_ROOT="${HOME}/.local/share/smartsh"
WRAPPER="${HOME}/.local/bin/smartsh"
LAZY_WRAPPER="${HOME}/.local/bin/lazyterminal"

rm -rf "${INSTALL_ROOT}"
rm -f "${WRAPPER}"
rm -f "${LAZY_WRAPPER}"

echo "Removed smartsh runtime files."
echo "User config remains at ~/.config/smartsh (delete manually if desired)."
