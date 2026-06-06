#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="$HOME/.local/bin"
AUTOSTART_DIR="$HOME/.config/autostart"

echo "=== SnippetTray Installer ==="
echo ""

# On Wayland (KDE/GNOME) pystray needs GTK/AppIndicator support (gi module).
# Use the system Python if it has gi, otherwise fall back to whatever python3 is in PATH.
if /usr/bin/python3 -c "import gi" 2>/dev/null; then
    PYTHON=/usr/bin/python3
    echo "Using system Python (/usr/bin/python3) — has GTK/gi support for Wayland tray"
else
    PYTHON=$(command -v python3)
    echo "Using $PYTHON"
fi

echo "[1/3] Installing Python dependencies (pystray, Pillow)..."
"$PYTHON" -m pip install --user pystray Pillow

echo "[2/3] Installing snippettray.py to $BIN_DIR ..."
mkdir -p "$BIN_DIR"
cp "$SCRIPT_DIR/snippettray.py" "$BIN_DIR/snippettray.py"
chmod +x "$BIN_DIR/snippettray.py"

echo "[3/3] Creating autostart entry..."
mkdir -p "$AUTOSTART_DIR"
cat > "$AUTOSTART_DIR/snippettray.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=SnippetTray
Exec=$PYTHON $BIN_DIR/snippettray.py
Icon=utilities-terminal
Hidden=false
NoDisplay=false
X-GNOME-Autostart-enabled=true
Comment=System tray snippet manager
Categories=Utility;
DESKTOP

echo ""
echo "Done! Log out and back in to start SnippetTray automatically"
echo ""
echo "To start SnippetTray now, run:"
echo "  $PYTHON $BIN_DIR/snippettray.py &"
echo ""

if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo "Note: $BIN_DIR is not in your PATH."
    echo "      Add this line to your ~/.bashrc or ~/.zshrc:"
    echo "      export PATH=\"\$HOME/.local/bin:\$PATH\""
fi
