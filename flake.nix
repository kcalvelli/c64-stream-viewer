{
  description = "C64 Ultimate64 Stream Viewer - Wayland-native video/audio viewer";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-unstable";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};

        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          numpy
          pygame
          opencv4
          requests
        ]);

        # Main A/V viewer script
        c64-stream-viewer-av = pkgs.writeScriptBin "c64-stream-viewer-av" ''
          #!${pkgs.bash}/bin/bash
          export SDL_VIDEODRIVER=wayland
          exec ${pythonEnv}/bin/python ${./c64_stream_viewer_av.py} "$@"
        '';

        # Video-only viewer
        c64-stream-viewer = pkgs.writeScriptBin "c64-stream-viewer" ''
          #!${pkgs.bash}/bin/bash
          export SDL_VIDEODRIVER=wayland
          exec ${pythonEnv}/bin/python ${./c64_stream_viewer_wayland.py} "$@"
        '';

        # Headless viewer
        c64-stream-viewer-headless = pkgs.writeScriptBin "c64-stream-viewer-headless" ''
          #!${pkgs.bash}/bin/bash
          exec ${pythonEnv}/bin/python ${./c64_stream_viewer.py} "$@"
        '';

      in
      {
        packages = {
          default = c64-stream-viewer-av;
          av = c64-stream-viewer-av;
          video = c64-stream-viewer;
          headless = c64-stream-viewer-headless;
        };

        apps = {
          default = {
            type = "app";
            program = "${c64-stream-viewer-av}/bin/c64-stream-viewer-av";
          };
          av = {
            type = "app";
            program = "${c64-stream-viewer-av}/bin/c64-stream-viewer-av";
          };
          video = {
            type = "app";
            program = "${c64-stream-viewer}/bin/c64-stream-viewer";
          };
          headless = {
            type = "app";
            program = "${c64-stream-viewer-headless}/bin/c64-stream-viewer-headless";
          };
        };

        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
            pythonEnv
            SDL2
          ];

          shellHook = ''
            export SDL_VIDEODRIVER=wayland

            echo "╔════════════════════════════════════════════════════════════╗"
            echo "║  C64 Ultimate64 Stream Viewer - Wayland Native            ║"
            echo "╚════════════════════════════════════════════════════════════╝"
            echo ""
            echo "Display: $XDG_SESSION_TYPE ($DISPLAY)"
            echo "Video Driver: $SDL_VIDEODRIVER"
            echo ""
            echo "Development Commands:"
            echo "  python c64_stream_viewer_av.py        # A/V viewer (dev)"
            echo "  python c64_stream_viewer_wayland.py   # Video only (dev)"
            echo "  python c64_stream_viewer.py --headless # Headless (dev)"
            echo ""
            echo "Flake Apps (from outside):"
            echo "  nix run .#av                          # A/V viewer"
            echo "  nix run .#video                       # Video only"
            echo "  nix run .#headless -- --headless      # Headless"
            echo ""
            echo "Controls (A/V viewer):"
            echo "  ESC or Q - Quit"
            echo "  F        - Toggle fullscreen"
            echo "  M        - Mute/unmute audio"
            echo ""
          '';
        };
      }
    );
}
