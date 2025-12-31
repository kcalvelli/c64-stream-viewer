# Quick Usage Guide

## Installation

### Option 1: NixOS System Installation (Recommended)

Add as a flake input to your NixOS system configuration.

**Step 1:** Add to your system `flake.nix`:

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

**Step 2:** Rebuild your system:

```bash
sudo nixos-rebuild switch --flake .#yourhostname
```

**Step 3:** Run from anywhere:

```bash
c64-stream-viewer-av
```

### Option 2: Run Directly from GitHub (No Installation)

Perfect for trying out the viewer without committing to an installation:

```bash
# Complete A/V viewer (video + audio)
nix run github:kcalvelli/c64-stream-viewer#av

# Video only
nix run github:kcalvelli/c64-stream-viewer#video

# Headless (stats only)
nix run github:kcalvelli/c64-stream-viewer#headless -- --headless

# Save frames to disk
nix run github:kcalvelli/c64-stream-viewer#headless -- --save-frames /tmp/frames
```

## Running the Viewers

### From GitHub (No Clone)

```bash
# Complete A/V viewer (video + audio)
nix run github:kcalvelli/c64-stream-viewer#av

# Video only
nix run github:kcalvelli/c64-stream-viewer#video

# Headless (stats only)
nix run github:kcalvelli/c64-stream-viewer#headless -- --headless

# Save frames to disk
nix run github:kcalvelli/c64-stream-viewer#headless -- --save-frames /tmp/frames
```

### From Cloned Repository

```bash
cd ~/Projects/c64-stream-viewer

# Complete A/V viewer (video + audio)
nix run .#av

# Video only
nix run .#video

# Headless (stats only)
nix run .#headless -- --headless

# Save frames to disk
nix run .#headless -- --save-frames /tmp/frames
```

### Development Shell

```bash
# Enter dev environment
nix develop

# Then run any viewer:
python c64_stream_viewer_av.py
python c64_stream_viewer_wayland.py
python c64_stream_viewer.py --headless
```

### Traditional Nix Shell

```bash
nix-shell shell.nix
python c64_stream_viewer_av.py
```

## Viewer Comparison

| Viewer | Audio | Video | GUI | Use Case |
|--------|-------|-------|-----|----------|
| `av` | ✓ | ✓ | ✓ | Best overall experience |
| `video` | ✗ | ✓ | ✓ | Lower latency, lighter |
| `headless` | ✗ | ✓ | ✗ | Remote/testing/capture |

## Controls

### A/V Viewer
- `ESC` or `Q` - Quit
- `F` - Toggle fullscreen
- `M` - Mute/unmute audio
- `Space` - (future: pause)

### All Viewers
- `Ctrl+C` - Quit (terminal)

## Command Line Options

### A/V Viewer
```bash
python c64_stream_viewer_av.py [options]

Options:
  --video-port PORT    Video UDP port (default: 11000)
  --audio-port PORT    Audio UDP port (default: 11001)
  --scale N            Display scale (default: 2)
  --fullscreen         Start fullscreen
  --no-audio           Disable audio
  --local-ip IP        Local IP for stream (default: 192.168.68.62)
```

### Video-Only Viewer
```bash
python c64_stream_viewer_wayland.py [options]

Options:
  --port PORT          UDP port (default: 11000)
  --scale N            Display scale (default: 2)
  --fullscreen         Start fullscreen
  --local-ip IP        Local IP (default: 192.168.68.62)
```

### Headless Viewer
```bash
python c64_stream_viewer.py [options]

Options:
  --headless           Run without GUI (stats only)
  --save-frames DIR    Save frames as PNG files
  --port PORT          UDP port (default: 11000)
  --scale N            Scale for saved frames (default: 2)
  --local-ip IP        Local IP (default: 192.168.68.62)
```

## Examples

### Basic Usage
```bash
# Just watch the stream
nix run .#av

# Watch at 3x scale
nix run .#av -- --scale 3

# Fullscreen mode
nix run .#av -- --fullscreen

# Video only, no audio
nix run .#video
```

### Recording/Capture
```bash
# Save all frames as PNG
nix run .#headless -- --save-frames ~/c64-recording

# Monitor stream stats
nix run .#headless -- --headless
```

### Custom Network Setup
```bash
# Different ports
nix run .#av -- --video-port 12000 --audio-port 12001

# Different local IP
nix run .#av -- --local-ip 192.168.1.100
```

## Troubleshooting

### No Video
1. Check stream is active on Ultimate64
2. Verify correct local IP: `ip addr show`
3. Check firewall: `sudo ufw allow 11000/udp`
4. Test with headless: `nix run .#headless -- --headless`

### No Audio
1. Ensure Ultimate64 audio stream is started
2. Check audio port: `nc -ul 11001`
3. Try muting/unmuting with `M` key
4. Use `--no-audio` to disable if not needed

### Performance Issues
1. Lower scale: `--scale 1`
2. Use video-only viewer (lighter than A/V)
3. Check CPU usage with `htop`

### Wayland Issues
1. Check `$XDG_SESSION_TYPE` is "wayland"
2. SDL2 should auto-detect, fallback to X11 works
3. Try `export SDL_VIDEODRIVER=wayland`

## Network Configuration

### Default Ports
- Video: 11000 (UDP)
- Audio: 11001 (UDP)

### Firewall Rules
```bash
# UFW
sudo ufw allow 11000/udp
sudo ufw allow 11001/udp

# firewalld
sudo firewall-cmd --add-port=11000/udp --permanent
sudo firewall-cmd --add-port=11001/udp --permanent
sudo firewall-cmd --reload
```

## Tips

1. **Best Quality**: Use `--scale 2` or higher
2. **Lowest Latency**: Use video-only viewer with `--scale 1`
3. **Recording**: Use headless with `--save-frames`, then convert to video:
   ```bash
   ffmpeg -framerate 50 -i frame_%06d.png -c:v libx264 output.mp4
   ```
4. **Development**: Use `nix develop` for fast iteration
5. **Distribution**: Share the flake URL or git repository
