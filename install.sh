#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_ROOT="${HOME}/.local/share/smartsh"
BIN_DIR="${HOME}/.local/bin"
VENV_DIR="${INSTALL_ROOT}/venv"
WRAPPER="${BIN_DIR}/smartsh"
LAZY_WRAPPER="${BIN_DIR}/lazyterminal"
BASHRC="${HOME}/.bashrc"
ZSHRC="${HOME}/.zshrc"

mkdir -p "${INSTALL_ROOT}" "${BIN_DIR}" "${HOME}/.config/smartsh"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required (3.10+)."
  exit 1
fi

python3 -m venv "${VENV_DIR}"
"${VENV_DIR}/bin/pip" install --upgrade pip >/dev/null
"${VENV_DIR}/bin/pip" install -r "${PROJECT_DIR}/requirements.txt" >/dev/null

rm -rf "${INSTALL_ROOT}/app"
mkdir -p "${INSTALL_ROOT}/app"
cp -r "${PROJECT_DIR}/smartsh" "${INSTALL_ROOT}/app/"

cat > "${WRAPPER}" <<EOF
#!/usr/bin/env bash
set -euo pipefail
PYTHONPATH="${INSTALL_ROOT}/app" exec "${VENV_DIR}/bin/python" -m smartsh.shell
EOF
chmod +x "${WRAPPER}"

cat > "${LAZY_WRAPPER}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
exec "${HOME}/.local/bin/smartsh" "$@"
EOF
chmod +x "${LAZY_WRAPPER}"

if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "${BASHRC}" 2>/dev/null; then
  echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${BASHRC}"
fi

if [[ -f "${ZSHRC}" ]]; then
  if ! grep -q 'export PATH="$HOME/.local/bin:$PATH"' "${ZSHRC}" 2>/dev/null; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "${ZSHRC}"
  fi
fi

if [[ -f "${HOME}/.config/smartsh/config.json" ]]; then
  :
else
  PYTHONPATH="${INSTALL_ROOT}/app" "${VENV_DIR}/bin/python" -c 'from smartsh.config import ensure_config; ensure_config()'
fi

cat <<'MSG'
Installation complete.

Usage:
  smartsh
  lazyterminal

Optional: make smartsh your default interactive shell launcher by adding this alias:
  echo 'alias t=smartsh' >> ~/.bashrc
  source ~/.bashrc
MSG
