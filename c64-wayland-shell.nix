{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.numpy
    python3Packages.pygame
    SDL2
  ];

  # Force SDL2 to use Wayland
  shellHook = ''
    export SDL_VIDEODRIVER=wayland
    echo "C64 Stream Viewer - Wayland Native (SDL2)"
    echo "Video Driver: $SDL_VIDEODRIVER"
    echo "Display: $XDG_SESSION_TYPE ($DISPLAY)"
    echo ""
    echo "Run: python c64_stream_viewer_wayland.py [options]"
    echo ""
    echo "Options:"
    echo "  --local-ip IP   Local IP (default: 192.168.68.62)"
    echo "  --port PORT     UDP port (default: 11000)"
    echo "  --scale N       Display scale (default: 2)"
    echo "  --fullscreen    Fullscreen mode"
    echo ""
    echo "Controls:"
    echo "  ESC or Q - Quit"
    echo "  F        - Toggle fullscreen"
  '';
}
