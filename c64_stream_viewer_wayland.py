#!/usr/bin/env python3
"""
C64 Ultimate64 Video Stream Viewer - Wayland Native
Uses pygame with SDL2 for native Wayland support
"""

import socket
import struct
import numpy as np
import pygame
import signal
import sys
import time
import argparse

# Constants from c64-protocol.h
VIDEO_PACKET_SIZE = 780
VIDEO_HEADER_SIZE = 12
PIXELS_PER_LINE = 384
BYTES_PER_LINE = 192  # 384 pixels / 2 (4-bit per pixel)
LINES_PER_PACKET = 4
PAL_HEIGHT = 272
NTSC_HEIGHT = 240

# VIC-II color palette (RGB tuples)
VIC_COLORS_BGRA = [
    0xFF000000,  # 0: Black
    0xFFEFEFEF,  # 1: White
    0xFF342F8D,  # 2: Red
    0xFFCDD46A,  # 3: Cyan
    0xFFA43598,  # 4: Purple/Magenta
    0xFF42B44C,  # 5: Green
    0xFFB1292C,  # 6: Blue
    0xFF5DEFEF,  # 7: Yellow
    0xFF204E98,  # 8: Orange
    0xFF00385B,  # 9: Brown
    0xFF6D67D1,  # 10: Light Red
    0xFF4A4A4A,  # 11: Dark Grey
    0xFF7B7B7B,  # 12: Mid Grey
    0xFF93EF9F,  # 13: Light Green
    0xFFEF6A6D,  # 14: Light Blue
    0xFFB2B2B2   # 15: Light Grey
]

# Convert BGRA to RGB tuples for pygame
VIC_COLORS_RGB = []
for bgra in VIC_COLORS_BGRA:
    r = bgra & 0xFF
    g = (bgra >> 8) & 0xFF
    b = (bgra >> 16) & 0xFF
    VIC_COLORS_RGB.append((r, g, b))


class C64FrameAssembler:
    """Assembles video packets into complete frames"""

    def __init__(self):
        self.current_frame_num = None
        self.packets = {}
        self.expected_packets = 0
        self.height = PAL_HEIGHT

    def add_packet(self, frame_num, line_num, lines_per_packet, pixel_data, is_last):
        # Start new frame if needed
        if self.current_frame_num != frame_num:
            self.current_frame_num = frame_num
            self.packets = {}
            self.expected_packets = 0

        # Store packet
        packet_index = line_num // lines_per_packet
        self.packets[packet_index] = (line_num, pixel_data)

        # Update expected packet count from last packet
        if is_last:
            self.expected_packets = packet_index + 1
            self.height = line_num + lines_per_packet

    def is_complete(self):
        if self.expected_packets == 0:
            return False
        return len(self.packets) >= self.expected_packets

    def get_frame_surface(self):
        """Assemble and return the complete frame as pygame surface"""
        if not self.is_complete():
            return None

        # Create pygame surface
        surface = pygame.Surface((PIXELS_PER_LINE, self.height))

        # Assemble packets
        for packet_idx, (line_num, pixel_data) in self.packets.items():
            # Decode 4 lines from this packet
            for line_offset in range(LINES_PER_PACKET):
                current_line = line_num + line_offset
                if current_line >= self.height:
                    break

                # Extract pixel data for this line (192 bytes)
                line_start = line_offset * BYTES_PER_LINE
                line_end = line_start + BYTES_PER_LINE
                line_data = pixel_data[line_start:line_end]

                # Convert 4-bit pixels to RGB and draw
                for byte_idx, byte_val in enumerate(line_data):
                    pixel1 = byte_val & 0x0F
                    pixel2 = (byte_val >> 4) & 0x0F

                    x = byte_idx * 2
                    if x < PIXELS_PER_LINE:
                        surface.set_at((x, current_line), VIC_COLORS_RGB[pixel1])
                    if x + 1 < PIXELS_PER_LINE:
                        surface.set_at((x + 1, current_line), VIC_COLORS_RGB[pixel2])

        return surface


def main():
    parser = argparse.ArgumentParser(description='C64 Ultimate64 Video Stream Viewer (Wayland Native)')
    parser.add_argument('--local-ip', type=str, default='192.168.68.62',
                       help='Local IP address to receive stream (default: 192.168.68.62)')
    parser.add_argument('--port', type=int, default=11000,
                       help='UDP port to listen on (default: 11000)')
    parser.add_argument('--scale', type=int, default=2,
                       help='Display scale factor (default: 2)')
    parser.add_argument('--fullscreen', action='store_true',
                       help='Run in fullscreen mode')
    args = parser.parse_args()

    print("C64 Stream Viewer (Wayland Native with SDL2)")
    print(f"Listening for stream on UDP port {args.port}...")
    print("Press ESC or Q to quit, F for fullscreen toggle")
    print()

    # Initialize pygame with SDL2 video driver
    pygame.init()

    # Create UDP socket
    sock = None
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', args.port))
        sock.setblocking(False)  # Non-blocking mode
    except Exception as e:
        print(f"Failed to create socket: {e}")
        return 1

    # Wait for first frame to determine resolution
    print("Waiting for first frame to determine resolution...")
    assembler = C64FrameAssembler()
    screen = None

    frame_count = 0
    last_stats_time = time.time()
    fps_counter = 0
    running = True
    fullscreen = args.fullscreen

    try:
        while running:
            # Handle pygame events
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE or event.key == pygame.K_q:
                        running = False
                    elif event.key == pygame.K_f:
                        fullscreen = not fullscreen
                        if screen:
                            if fullscreen:
                                screen = pygame.display.set_mode(
                                    (PIXELS_PER_LINE * args.scale, assembler.height * args.scale),
                                    pygame.FULLSCREEN | pygame.SCALED
                                )
                            else:
                                screen = pygame.display.set_mode(
                                    (PIXELS_PER_LINE * args.scale, assembler.height * args.scale),
                                    pygame.SCALED
                                )

            try:
                # Receive packet
                data, addr = sock.recvfrom(VIDEO_PACKET_SIZE + 100)

                if len(data) != VIDEO_PACKET_SIZE:
                    continue

                # Parse header
                seq_num, frame_num, line_num, pixels_per_line, lines_per_packet, bits_per_pixel = \
                    struct.unpack('<HHHHBB', data[:10])

                # Check for last packet flag
                is_last = (line_num & 0x8000) != 0
                line_num = line_num & 0x7FFF

                # Validate packet
                if pixels_per_line != PIXELS_PER_LINE or lines_per_packet != LINES_PER_PACKET or bits_per_pixel != 4:
                    continue

                # Extract pixel data
                pixel_data = data[VIDEO_HEADER_SIZE:]

                # Add packet to assembler
                assembler.add_packet(frame_num, line_num, lines_per_packet, pixel_data, is_last)

                # Check if frame is complete
                if assembler.is_complete():
                    frame_surface = assembler.get_frame_surface()
                    if frame_surface is not None:
                        frame_count += 1
                        fps_counter += 1

                        # Create window on first frame
                        if screen is None:
                            window_width = PIXELS_PER_LINE * args.scale
                            window_height = assembler.height * args.scale
                            if fullscreen:
                                screen = pygame.display.set_mode(
                                    (window_width, window_height),
                                    pygame.FULLSCREEN | pygame.SCALED
                                )
                            else:
                                screen = pygame.display.set_mode(
                                    (window_width, window_height),
                                    pygame.SCALED
                                )
                            pygame.display.set_caption('C64 Stream - Wayland Native')
                            format_name = "PAL" if assembler.height == PAL_HEIGHT else "NTSC"
                            print(f"Format detected: {format_name} ({PIXELS_PER_LINE}x{assembler.height})")

                        # Scale and display
                        if args.scale > 1:
                            scaled = pygame.transform.scale(
                                frame_surface,
                                (PIXELS_PER_LINE * args.scale, assembler.height * args.scale)
                            )
                            screen.blit(scaled, (0, 0))
                        else:
                            screen.blit(frame_surface, (0, 0))

                        pygame.display.flip()

                        # Print stats every second
                        current_time = time.time()
                        if current_time - last_stats_time >= 1.0:
                            fps = fps_counter / (current_time - last_stats_time)
                            print(f"FPS: {fps:.1f} | Frames: {frame_count}")
                            fps_counter = 0
                            last_stats_time = current_time

                    # Reset for next frame
                    assembler = C64FrameAssembler()

            except (BlockingIOError, OSError):
                pass

            # Small delay to prevent CPU spinning
            time.sleep(0.001)

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        print(f"\nTotal frames received: {frame_count}")
        if sock:
            sock.close()
        pygame.quit()

    return 0


if __name__ == '__main__':
    sys.exit(main())
