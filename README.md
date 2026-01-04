# C64 Ultimate64 Stream Viewer

Wayland-native video viewer for Ultimate64 video streaming. Decodes the proprietary UDP packet format used by the Ultimate64 device.

## Features

- **Native Wayland** rendering via SDL2/pygame
- Custom packet decoder for Ultimate64's 4-bit VIC-II color format
- Real-time video display at ~14-17 FPS
- PAL (384×272) and NTSC (384×240) auto-detection
- Hardware-accelerated scaling
- Audio support (16-bit stereo PCM, 47976 Hz)

## Quick Start

**Other Linux Distros?** See [INSTALL.md](INSTALL.md) for traditional installation instructions.

### NixOS System Installation (Recommended)

Add as a flake input to your NixOS configuration. In your `flake.nix`:

```nix
{
  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    c64-stream-viewer.url = "github:kcalvelli/c64-stream-viewer";
  };

  outputs = { self, nixpkgs, c64-stream-viewer }: {
    nixosConfigurations.yourhostname = nixpkgs.lib.nixosSystem {
      system = "x86_64-linux";
      modules = [
        ./configuration.nix
        {
          environment.systemPackages = [
            c64-stream-viewer.packages.x86_64-linux.av
            # Optional: Add other variants
            # c64-stream-viewer.packages.x86_64-linux.video
            # c64-stream-viewer.packages.x86_64-linux.headless
          ];
        }
      ];
    };
  };
}
```

Then rebuild your system:
```bash
sudo nixos-rebuild switch --flake .#yourhostname
```

After installation, run from anywhere:
```bash
c64-stream-viewer-av
```

### Run Directly from GitHub (No Installation)

**Try it out without installing:**
```bash
nix run github:kcalvelli/c64-stream-viewer#av            # Complete A/V viewer
nix run github:kcalvelli/c64-stream-viewer#video         # Video only
nix run github:kcalvelli/c64-stream-viewer#headless      # Headless mode
```

### Development

**Run from cloned repository:**
```bash
cd ~/Projects/c64-stream-viewer
nix run .#av            # Complete A/V viewer
nix run .#video         # Video only
nix run .#headless      # Headless mode
```

**Or enter development shell:**
```bash
nix develop
python c64_stream_viewer_av.py
```

### Alternative: Traditional Nix Shell

```bash
nix-shell shell.nix
python c64_stream_viewer_av.py
```

## Viewers

### 1. Complete A/V Viewer (Recommended)
```bash
nix run .#av
# or in dev shell:
python c64_stream_viewer_av.py
```

**Controls:**
- `ESC` or `Q` - Quit
- `F` - Toggle fullscreen
- `M` - Mute/unmute audio

**Options:**
```bash
python c64_stream_viewer_av.py --help
  --video-port PORT    Video UDP port (default: 11000)
  --audio-port PORT    Audio UDP port (default: 11001)
  --scale N            Display scale factor (default: 2)
  --fullscreen         Start in fullscreen
  --no-audio           Disable audio
```

### 2. Video-Only Viewer
```bash
python c64_stream_viewer_wayland.py
```

Lighter weight, video-only version.

### 3. Headless Viewer
```bash
python c64_stream_viewer.py --headless
```

No GUI, just statistics. Useful for testing or remote systems.

### 4. Frame Capture
```bash
python c64_stream_viewer.py --save-frames /path/to/output
```

Saves frames as PNG files for later viewing or processing.

## Technical Details

### Video Format
- **Packet Size**: 780 bytes
- **Header**: 12 bytes (seq, frame#, line#, dimensions, format)
- **Payload**: 768 bytes of 4-bit indexed color data
- **Format**: 4 lines × 384 pixels × 0.5 bytes = 768 bytes
- **Color Palette**: 16-color VIC-II palette (converted to RGB)

### Audio Format
- **Packet Size**: 770 bytes
- **Header**: 2 bytes (sequence number)
- **Payload**: 768 bytes = 192 stereo samples
- **Format**: 16-bit signed PCM, stereo, interleaved
- **Sample Rate**: 47976 Hz
- **Latency**: ~4ms per packet

## Prerequisites

The Nix shell provides all dependencies:
- Python 3
- pygame (with SDL2 Wayland support)
- numpy
- OpenCV (optional, for headless/save modes)

## How It Works

1. Receives UDP packets on ports 11000 (video) and 11001 (audio)
2. Parses custom packet headers
3. Decodes 4-bit VIC-II palette indices to RGB colors
4. Assembles multi-packet frames
5. Renders to Wayland display via SDL2
6. Plays synchronized audio via pygame mixer

## Project Structure

```
c64-stream-viewer/
├── c64_stream_viewer_av.py       # Complete A/V viewer (recommended)
├── c64_stream_viewer_wayland.py  # Video-only viewer
├── c64_stream_viewer.py          # Headless/save modes
├── shell.nix                     # Combined dependencies
├── c64-wayland-shell.nix         # Video-only shell
└── c64-viewer-shell.nix          # Headless shell
```

## Credits

Based on protocol analysis of the [c64stream OBS plugin](https://github.com/chrisgleissner/c64stream) by Christian Gleissner.

## License

MIT License - See individual files for details.
