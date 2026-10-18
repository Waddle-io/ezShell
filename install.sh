#!/usr/bin/env bash
# ==============================================================================
# ezShell — One-line Universal Installer
# ==============================================================================
# Installs ezShell into ~/.local/share/ezshell with binary symlinks in ~/.local/bin
# Supports: Linux (Ubuntu, Debian, Fedora, Arch, RHEL) and macOS
#
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/Waddle-io/ezShell/main/install.sh | bash
#   or locally: ./install.sh
# ==============================================================================

set -e

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0m' # No Color

echo -e "${BOLD}${BLUE}"
echo "             _____ __         ____  "
echo "  ___  ____ / ___// /_  ___  / / / "
echo " / _ \/_  / \__ \/ __ \/ _ \/ / /  "
echo "/  __/ / /____/ / / / /  __/ / /   "
echo "\___/ /___/____/_/ /_/\___/_/_/    "
echo -e "${NC}"
echo -e "${BOLD}ezShell Installer - Intelligent Terminal Assistant${NC}"
echo "=========================================================="
echo ""

# 1. Check Python 3 (>= 3.10)
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[✘] Python 3 is required but not installed.${NC}"
    echo "Please install Python 3.10 or newer and re-run this script."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}[✘] Python 3.10+ is required (found Python $PYTHON_VERSION).${NC}"
    exit 1
fi
echo -e "${GREEN}[✓] Python $PYTHON_VERSION detected.${NC}"

# 2. Check Git
if ! command -v git &> /dev/null; then
    echo -e "${RED}[✘] Git is required but not installed.${NC}"
    echo "Please install git (e.g. 'sudo apt install git' or 'sudo dnf install git')."
    exit 1
fi
echo -e "${GREEN}[✓] Git detected.${NC}"

# 3. Determine Installation Directories
BIN_DIR="${EZSHELL_BIN_DIR:-$HOME/.local/bin}"

# If running directly inside a cloned ezShell directory, install from here
if [ -f "$PWD/pyproject.toml" ] && grep -q '^name = "ezshell"' "$PWD/pyproject.toml" && [ -f "$PWD/src/main.py" ]; then
    INSTALL_DIR="$PWD"
    echo -e "${BLUE}[i] Installing from local repository: $INSTALL_DIR${NC}"
else
    INSTALL_DIR="${EZSHELL_INSTALL_DIR:-$HOME/.local/share/ezshell}"
    if [ -d "$INSTALL_DIR/.git" ]; then
        echo -e "${BLUE}[i] Updating existing ezShell installation in $INSTALL_DIR...${NC}"
        git -C "$INSTALL_DIR" pull --quiet --rebase origin main || true
    else
        echo -e "${BLUE}[i] Cloning ezShell repository into $INSTALL_DIR...${NC}"
        mkdir -p "$(dirname "$INSTALL_DIR")"
        git clone --quiet --depth 1 https://github.com/Waddle-io/ezShell.git "$INSTALL_DIR"
    fi
fi

# 4. Create / Update Virtual Environment
echo -e "${BLUE}[i] Setting up Python virtual environment...${NC}"
if [ ! -d "$INSTALL_DIR/.venv" ]; then
    python3 -m venv "$INSTALL_DIR/.venv"
fi

VENV_PIP="$INSTALL_DIR/.venv/bin/pip"
VENV_PYTHON="$INSTALL_DIR/.venv/bin/python"

echo -e "${BLUE}[i] Installing dependencies...${NC}"
"$VENV_PIP" install --quiet --upgrade pip || true
"$VENV_PIP" install --quiet -r "$INSTALL_DIR/requirements.txt" || true
"$VENV_PIP" install --quiet --no-build-isolation -e "$INSTALL_DIR" || "$VENV_PIP" install --quiet -e "$INSTALL_DIR"

# 5. Create Executable Symlinks in ~/.local/bin
echo -e "${BLUE}[i] Creating symlinks in $BIN_DIR...${NC}"
mkdir -p "$BIN_DIR"

ln -sf "$INSTALL_DIR/.venv/bin/ezsh" "$BIN_DIR/ezsh"
ln -sf "$INSTALL_DIR/.venv/bin/ezshell" "$BIN_DIR/ezshell"

# 6. Check if ~/.local/bin is in $PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo -e "${BLUE}[i] Adding $BIN_DIR to your shell PATH...${NC}"
    CURRENT_SHELL=$(basename "$SHELL")
    if [ "$CURRENT_SHELL" = "zsh" ]; then
        RC_FILE="$HOME/.zshrc"
    else
        RC_FILE="$HOME/.bashrc"
    fi

    if [ -f "$RC_FILE" ] && ! grep -q 'export PATH=.*\.local/bin' "$RC_FILE"; then
        echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$RC_FILE"
    fi
fi

# 7. Install Automatic Shell Integration (Hooks & Alt+E shortcut)
echo -e "${BLUE}[i] Installing shell hook and Alt+E shortcut...${NC}"
"$BIN_DIR/ezsh" init --install || true

# 8. Check Tkinter GUI support
if ! "$VENV_PYTHON" -c "import tkinter" &> /dev/null; then
    echo -e "${RED}[!] Note: Tkinter GUI library was not detected on your system.${NC}"
    echo "    ezShell will run in terminal popup mode ('ezsh --tui')."
    echo "    To enable the graphical desktop window, install python3-tk:"
    echo "      - Ubuntu / Debian: sudo apt install python3-tk"
    echo "      - Fedora / RHEL:   sudo dnf install python3-tkinter"
    echo "      - Arch Linux:      sudo pacman -S tk"
fi

echo ""
echo -e "${BOLD}${GREEN}==========================================================${NC}"
echo -e "${BOLD}${GREEN}[✓] ezShell installed successfully!${NC}"
echo -e "${BOLD}${GREEN}==========================================================${NC}"
echo ""
echo -e "${BOLD}Next steps:${NC}"
echo "  1. Reload your shell:"
echo -e "     ${BLUE}source ~/.bashrc${NC}  (or ${BLUE}source ~/.zshrc${NC})"
echo ""
echo -e "  2. Run a command that fails, then press ${BOLD}Alt+E${NC}."
echo "     No API key needed: ezShell uses its hosted service (https://ezshell.vercel.app)."
echo ""
echo "  3. Or open the desktop assistant:"
echo -e "     ${BLUE}ezsh${NC}"
echo ""
