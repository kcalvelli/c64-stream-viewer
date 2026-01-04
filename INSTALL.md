# Installation Instructions

## NixOS (Recommended)

See the main [README.md](README.md) for NixOS installation instructions using flakes.

## Traditional Linux Distributions

### Prerequisites

**System Dependencies:**

Debian/Ubuntu:
```bash
sudo apt install python3 python3-pip portaudio19-dev python3-dev
```

Fedora:
```bash
sudo dnf install python3 python3-pip portaudio-devel python3-devel
```

Arch Linux:
```bash
sudo pacman -S python python-pip portaudio
```

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/kcalvelli/c64-stream-viewer.git
cd c64-stream-viewer
```

2. **Run the installation script:**
```bash
./install.sh
```

This will:
- Install Python dependencies to your user directory
- Install scripts to `/usr/local/bin`
- Install the desktop file and icon
- Update desktop database and icon cache

### Alternative: Manual Installation

If you prefer not to use the install script:

1. **Install Python dependencies:**
```bash
pip3 install --user -r requirements.txt
```

2. **Run directly:**
```bash
python3 c64_stream_viewer_av.py
```

Or create symlinks/wrappers as needed.

### Custom Installation Prefix

To install to a different location (e.g., `~/.local`):

```bash
PREFIX="$HOME/.local" ./install.sh
```

Make sure `~/.local/bin` is in your `$PATH`.

### Uninstallation

To remove installed files:

```bash
sudo rm -f /usr/local/bin/c64-stream-viewer-av
sudo rm -f /usr/local/bin/c64-stream-viewer
sudo rm -f /usr/local/bin/c64-stream-viewer-headless
sudo rm -f /usr/local/share/applications/c64-stream-viewer-av.desktop
sudo rm -f /usr/local/share/icons/hicolor/256x256/apps/c64-stream-viewer.png
sudo update-desktop-database /usr/local/share/applications
```

And uninstall Python packages:
```bash
pip3 uninstall numpy pygame opencv-python pyaudio
```

## Windows / macOS

This application is designed for Linux with Wayland support. For other platforms:

1. Install Python 3.9+
2. Install dependencies: `pip install -r requirements.txt`
3. Run directly: `python c64_stream_viewer_av.py`

Note: You may need to remove or modify the `SDL_VIDEODRIVER=wayland` export in scripts.

## Troubleshooting

### PyAudio Installation Fails

PyAudio requires portaudio development headers. Install them first:
- Debian/Ubuntu: `sudo apt install portaudio19-dev`
- Fedora: `sudo dnf install portaudio-devel`
- Arch: `sudo pacman -S portaudio`

### No Icon in Launcher

After installation, log out and log back in, or run:
```bash
update-desktop-database ~/.local/share/applications
gtk-update-icon-cache -f -t ~/.local/share/icons/hicolor
```

### SDL2 Errors

Ensure SDL2 libraries are installed:
- Debian/Ubuntu: `sudo apt install libsdl2-2.0-0`
- Fedora: `sudo dnf install SDL2`
- Arch: `sudo pacman -S sdl2`
