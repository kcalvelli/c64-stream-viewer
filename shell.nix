{ pkgs ? import <nixpkgs> {} }:

pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.numpy
    python3Packages.pygame
    python3Packages.opencv4
    SDL2
  ];

  # Force SDL2 to use Wayland
  shellHook = ''
    export SDL_VIDEODRIVER=wayland

    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║  C64 Ultimate64 Stream Viewer - Wayland Native            ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    echo "Display: $XDG_SESSION_TYPE ($DISPLAY)"
    echo "Video Driver: $SDL_VIDEODRIVER"
    echo ""
    echo "Quick Start:"
    echo "  python c64_stream_viewer_av.py        # Complete A/V viewer"
    echo "  python c64_stream_viewer_wayland.py   # Video only"
    echo "  python c64_stream_viewer.py --headless # Stats only"
    echo ""
    echo "Controls (A/V viewer):"
    echo "  ESC or Q - Quit"
    echo "  F        - Toggle fullscreen"
    echo "  M        - Mute/unmute audio"
    echo ""
    echo "See README.md for full documentation"
    echo ""
  '';
}
