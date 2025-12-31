{ pkgs ? import <nixpkgs> {} }:

let
  # Build OpenCV with GUI support enabled
  opencv-gui = pkgs.python3Packages.opencv4.override {
    enableGtk3 = true;
    enableFfmpeg = true;
  };
in
pkgs.mkShell {
  buildInputs = with pkgs; [
    python3
    python3Packages.numpy
    opencv-gui
    gtk3
    glib
    libGL
    xorg.libX11
    xorg.libXext
  ];

  shellHook = ''
    echo "C64 Stream Viewer development environment"
    echo "Display: $XDG_SESSION_TYPE ($DISPLAY)"
    echo ""
    echo "Run: python c64_stream_viewer.py [options]"
    echo ""
    echo "Options:"
    echo "  --headless        No GUI, just stats"
    echo "  --save-frames DIR Save frames to directory"
    echo "  --local-ip IP     Local IP (default: 192.168.68.62)"
    echo "  --port PORT       UDP port (default: 11000)"
    echo "  --scale N         Display scale (default: 2)"
  '';
}
