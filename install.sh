#!/bin/bash
# Installation script for c64-stream-viewer on traditional Linux distros

set -e

PREFIX="${PREFIX:-/usr/local}"
PYTHON="${PYTHON:-python3}"

echo "Installing C64 Stream Viewer..."
echo "PREFIX: $PREFIX"
echo "Python: $PYTHON"
echo

# Check for Python
if ! command -v "$PYTHON" &> /dev/null; then
    echo "Error: Python 3 not found"
    exit 1
fi

# Install Python dependencies
echo "Installing Python dependencies..."
if command -v pip3 &> /dev/null; then
    pip3 install --user -r requirements.txt
elif command -v pip &> /dev/null; then
    pip install --user -r requirements.txt
else
    echo "Warning: pip not found. Please install dependencies manually:"
    cat requirements.txt
    echo
fi

# Install scripts
echo "Installing scripts to $PREFIX/bin..."
sudo mkdir -p "$PREFIX/bin"
sudo install -m 755 c64_stream_viewer_av.py "$PREFIX/bin/c64-stream-viewer-av"
sudo install -m 755 c64_stream_viewer_wayland.py "$PREFIX/bin/c64-stream-viewer"
sudo install -m 755 c64_stream_viewer.py "$PREFIX/bin/c64-stream-viewer-headless"

# Install icon
echo "Installing icon..."
sudo mkdir -p "$PREFIX/share/icons/hicolor/256x256/apps"
sudo install -m 644 commodore.png "$PREFIX/share/icons/hicolor/256x256/apps/c64-stream-viewer.png"

# Install desktop file
echo "Installing desktop file..."
sudo mkdir -p "$PREFIX/share/applications"
sudo install -m 644 c64-stream-viewer-av.desktop "$PREFIX/share/applications/"

# Update desktop database
if command -v update-desktop-database &> /dev/null; then
    echo "Updating desktop database..."
    sudo update-desktop-database "$PREFIX/share/applications"
fi

# Update icon cache
if command -v gtk-update-icon-cache &> /dev/null; then
    echo "Updating icon cache..."
    sudo gtk-update-icon-cache -f -t "$PREFIX/share/icons/hicolor" 2>/dev/null || true
fi

echo
echo "Installation complete!"
echo
echo "Run with: c64-stream-viewer-av"
echo "Or find 'C64 Stream Viewer' in your application menu"
