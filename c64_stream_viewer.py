#!/usr/bin/env python3
"""
C64 Ultimate64 Video Stream Viewer
Self-contained viewer that manages the stream lifecycle
"""

import socket
import struct
import numpy as np
import cv2
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

# VIC-II color palette (converted from BGRA to BGR for OpenCV)
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

# Convert BGRA to BGR for OpenCV
VIC_COLORS_BGR = []
for bgra in VIC_COLORS_BGRA:
    r = bgra & 0xFF
    g = (bgra >> 8) & 0xFF
    b = (bgra >> 16) & 0xFF
    VIC_COLORS_BGR.append((b, g, r))


class C64StreamManager:
    """Manages Ultimate64 video stream lifecycle"""

    def __init__(self, local_ip, local_port, u64_host):
        self.local_ip = local_ip
        self.local_port = local_port
        self.u64_host = u64_host
        self.stream_started = False

    def start_stream(self):
        """Start the video stream using Ultimate64 REST API"""
        print(f"Starting video stream to {self.local_ip}:{self.local_port}...")
        try:
            import urllib.request
            import urllib.error

            url = f"http://{self.u64_host}/v1/streams/video?ip={self.local_ip}:{self.local_port}"
            req = urllib.request.Request(url, method='POST')

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print("✓ Video stream started successfully")
                    self.stream_started = True
                    return True
                else:
                    print(f"✗ Failed to start stream: HTTP {response.status}")
                    return False
        except urllib.error.URLError as e:
            print(f"✗ Error starting stream: {e}")
            return False
        except Exception as e:
            print(f"✗ Error starting stream: {e}")
            return False

    def stop_stream(self):
        """Stop the video stream using Ultimate64 REST API"""
        if not self.stream_started:
            return

        print("Stopping video stream...")
        try:
            import urllib.request
            import urllib.error

            url = f"http://{self.u64_host}/v1/streams/video"
            req = urllib.request.Request(url, method='DELETE')

            with urllib.request.urlopen(req, timeout=5) as response:
                if response.status == 200:
                    print("✓ Video stream stopped successfully")
                else:
                    print(f"✗ Failed to stop stream: HTTP {response.status}")
        except Exception as e:
            print(f"✗ Error stopping stream: {e}")
        finally:
            self.stream_started = False


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

    def get_frame(self):
        """Assemble and return the complete frame as numpy array"""
        if not self.is_complete():
            return None

        # Create frame buffer
        frame = np.zeros((self.height, PIXELS_PER_LINE, 3), dtype=np.uint8)

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

                # Convert 4-bit pixels to RGB
                for byte_idx, byte_val in enumerate(line_data):
                    pixel1 = byte_val & 0x0F
                    pixel2 = (byte_val >> 4) & 0x0F

                    x = byte_idx * 2
                    if x < PIXELS_PER_LINE:
                        frame[current_line, x] = VIC_COLORS_BGR[pixel1]
                    if x + 1 < PIXELS_PER_LINE:
                        frame[current_line, x + 1] = VIC_COLORS_BGR[pixel2]

        return frame


def main():
    parser = argparse.ArgumentParser(description='C64 Ultimate64 Video Stream Viewer')
    parser.add_argument('--u64-host', type=str, default='192.168.68.140',
                       help='Ultimate64 IP address (default: 192.168.68.140)')
    parser.add_argument('--local-ip', type=str, default='192.168.68.62',
                       help='Local IP address to receive stream (default: 192.168.68.62)')
    parser.add_argument('--port', type=int, default=11000,
                       help='UDP port to listen on (default: 11000)')
    parser.add_argument('--scale', type=int, default=2,
                       help='Display scale factor (default: 2)')
    parser.add_argument('--save-frames', type=str, default=None,
                       help='Save frames to directory instead of displaying')
    parser.add_argument('--headless', action='store_true',
                       help='Run in headless mode (no GUI, just stats)')
    args = parser.parse_args()

    # Initialize stream manager
    stream_mgr = C64StreamManager(args.local_ip, args.port, args.u64_host)
    sock = None

    # Setup signal handlers for clean shutdown
    def signal_handler(signum, frame_arg):
        print("\n\nShutdown requested...")
        if sock:
            sock.close()
        if not args.headless and not args.save_frames:
            cv2.destroyAllWindows()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("Note: Make sure the Ultimate64 video stream is already running!")
    print(f"      (Stream should be sending to {args.local_ip}:{args.port})")
    print()

    # Create UDP socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(('0.0.0.0', args.port))
        sock.settimeout(1.0)
    except Exception as e:
        print(f"Failed to create socket: {e}")
        return 1

    print(f"Listening for C64 video stream on UDP port {args.port}...")

    if args.save_frames:
        import os
        os.makedirs(args.save_frames, exist_ok=True)
        print(f"Saving frames to: {args.save_frames}")
        print("Press Ctrl+C to quit")
    elif args.headless:
        print("Running in headless mode (stats only)")
        print("Press Ctrl+C to quit")
    else:
        print("Press 'q' in the video window to quit")
        cv2.namedWindow('C64 Stream', cv2.WINDOW_NORMAL)

    assembler = C64FrameAssembler()
    frame_count = 0
    last_stats_time = time.time()
    fps_counter = 0

    try:
        while True:
            try:
                # Receive packet
                data, addr = sock.recvfrom(VIDEO_PACKET_SIZE + 100)

                if len(data) != VIDEO_PACKET_SIZE:
                    continue

                # Parse header (12 bytes total: 3x uint16, 1x uint16, 2x uint8, 2 padding)
                # Bytes: seq(2), frame(2), line(2), pixels(2), lines(1), bits(1), padding(2)
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
                    frame = assembler.get_frame()
                    if frame is not None:
                        frame_count += 1
                        fps_counter += 1

                        # Save frame to disk if requested
                        if args.save_frames:
                            import os
                            filename = os.path.join(args.save_frames, f"frame_{frame_count:06d}.png")
                            cv2.imwrite(filename, frame)

                        # Display frame if not headless
                        elif not args.headless:
                            # Scale up for better visibility
                            if args.scale > 1:
                                display_frame = cv2.resize(frame, None, fx=args.scale, fy=args.scale,
                                                 interpolation=cv2.INTER_NEAREST)
                            else:
                                display_frame = frame

                            # Display frame
                            cv2.imshow('C64 Stream', display_frame)

                        # Print stats every second
                        current_time = time.time()
                        if current_time - last_stats_time >= 1.0:
                            fps = fps_counter / (current_time - last_stats_time)
                            format_name = "PAL" if assembler.height == PAL_HEIGHT else "NTSC"
                            print(f"FPS: {fps:.1f} | Frames: {frame_count} | Format: {format_name} ({PIXELS_PER_LINE}x{assembler.height})")
                            fps_counter = 0
                            last_stats_time = current_time

                    # Reset for next frame
                    assembler = C64FrameAssembler()

            except socket.timeout:
                pass

            # Check for quit key (only in GUI mode)
            if not args.headless and not args.save_frames:
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        print(f"\nTotal frames received: {frame_count}")
        if sock:
            sock.close()
        if not args.headless and not args.save_frames:
            cv2.destroyAllWindows()

    return 0


if __name__ == '__main__':
    sys.exit(main())
