#!/usr/bin/env python3
"""
C64 Ultimate64 Audio/Video Stream Viewer - Wayland Native
Complete A/V package with synchronized audio and video
"""

import socket
import struct
import numpy as np
import pygame
import signal
import sys
import time
import argparse
import threading
import queue
import os

# Constants from c64-protocol.h
VIDEO_PACKET_SIZE = 780
VIDEO_HEADER_SIZE = 12
AUDIO_PACKET_SIZE = 770
AUDIO_HEADER_SIZE = 2
PIXELS_PER_LINE = 384
BYTES_PER_LINE = 192
LINES_PER_PACKET = 4
PAL_HEIGHT = 272
NTSC_HEIGHT = 240

# Audio constants
AUDIO_SAMPLE_RATE = 47976  # C64 Ultimate exact sample rate
AUDIO_SAMPLES_PER_PACKET = 192
AUDIO_CHANNELS = 2  # Stereo
AUDIO_FORMAT = -16  # 16-bit signed

# VIC-II color palette (RGB tuples)
VIC_COLORS_BGRA = [
    0xFF000000, 0xFFEFEFEF, 0xFF342F8D, 0xFFCDD46A,
    0xFFA43598, 0xFF42B44C, 0xFFB1292C, 0xFF5DEFEF,
    0xFF204E98, 0xFF00385B, 0xFF6D67D1, 0xFF4A4A4A,
    0xFF7B7B7B, 0xFF93EF9F, 0xFFEF6A6D, 0xFFB2B2B2
]

VIC_COLORS_RGB = []
for bgra in VIC_COLORS_BGRA:
    r, g, b = bgra & 0xFF, (bgra >> 8) & 0xFF, (bgra >> 16) & 0xFF
    VIC_COLORS_RGB.append((r, g, b))


def send_ultimate64_stream_command(ultimate_host, stream_id, enable, local_ip, port):
    """
    Send stream control command to Ultimate64 via TCP command port (port 64)
    Based on c64stream OBS plugin protocol

    Args:
        ultimate_host: Ultimate64 IP address
        stream_id: 0 for video, 1 for audio
        enable: True to start stream, False to stop
        local_ip: IP address to send stream to
        port: UDP port to send stream to
    """
    COMMAND_PORT = 64

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2.0)
        sock.connect((ultimate_host, COMMAND_PORT))

        if enable:
            # Start stream command
            ip_port_str = f"{local_ip}:{port}"
            ip_port_bytes = ip_port_str.encode('ascii')
            param_len = 2 + len(ip_port_bytes)  # 2 bytes duration + IP:PORT string

            cmd = bytearray()
            cmd.append(0x20 + stream_id)  # 0x20 for video, 0x21 for audio
            cmd.append(0xFF)
            cmd.append(param_len & 0xFF)
            cmd.append((param_len >> 8) & 0xFF)
            cmd.append(0x00)  # Duration: 0x0000 = forever (little endian)
            cmd.append(0x00)
            cmd.extend(ip_port_bytes)
        else:
            # Stop stream command
            cmd = bytearray()
            cmd.append(0x30 + stream_id)  # 0x30 for video, 0x31 for audio
            cmd.append(0xFF)
            cmd.append(0x00)  # No parameters
            cmd.append(0x00)

        sent = sock.send(cmd)
        if sent != len(cmd):
            print(f"Warning: Only sent {sent}/{len(cmd)} bytes")
            sock.close()
            return False

        sock.close()
        return True

    except socket.timeout:
        print(f"Error: Timeout connecting to Ultimate64 command port")
        return False
    except Exception as e:
        print(f"Error sending stream command: {e}")
        return False


class C64FrameAssembler:
    """Assembles video packets into complete frames"""

    def __init__(self):
        self.current_frame_num = None
        self.packets = {}
        self.expected_packets = 0
        self.height = PAL_HEIGHT

    def add_packet(self, frame_num, line_num, lines_per_packet, pixel_data, is_last):
        if self.current_frame_num != frame_num:
            self.current_frame_num = frame_num
            self.packets = {}
            self.expected_packets = 0

        packet_index = line_num // lines_per_packet
        self.packets[packet_index] = (line_num, pixel_data)

        if is_last:
            self.expected_packets = packet_index + 1
            self.height = line_num + lines_per_packet

    def is_complete(self):
        return self.expected_packets > 0 and len(self.packets) >= self.expected_packets

    def get_frame_surface(self):
        if not self.is_complete():
            return None

        surface = pygame.Surface((PIXELS_PER_LINE, self.height))

        for packet_idx, (line_num, pixel_data) in self.packets.items():
            for line_offset in range(LINES_PER_PACKET):
                current_line = line_num + line_offset
                if current_line >= self.height:
                    break

                line_start = line_offset * BYTES_PER_LINE
                line_end = line_start + BYTES_PER_LINE
                line_data = pixel_data[line_start:line_end]

                for byte_idx, byte_val in enumerate(line_data):
                    pixel1 = byte_val & 0x0F
                    pixel2 = (byte_val >> 4) & 0x0F

                    x = byte_idx * 2
                    if x < PIXELS_PER_LINE:
                        surface.set_at((x, current_line), VIC_COLORS_RGB[pixel1])
                    if x + 1 < PIXELS_PER_LINE:
                        surface.set_at((x + 1, current_line), VIC_COLORS_RGB[pixel2])

        return surface


class AudioPlayer:
    """Handles audio playback with buffering"""

    def __init__(self):
        # Initialize pygame mixer for audio
        pygame.mixer.init(frequency=AUDIO_SAMPLE_RATE, size=AUDIO_FORMAT,
                         channels=AUDIO_CHANNELS, buffer=2048)
        self.audio_queue = queue.Queue(maxsize=20)  # Buffer up to 20 packets (80ms)
        self.running = True
        self.thread = threading.Thread(target=self._play_audio, daemon=True)
        self.thread.start()
        self.packets_played = 0

        # DC offset removal state (per channel)
        self.dc_filter_state = np.array([0.0, 0.0], dtype=np.float32)

    def add_audio_packet(self, audio_data):
        """Add audio packet to playback queue"""
        try:
            self.audio_queue.put_nowait(audio_data)
        except queue.Full:
            pass  # Drop packet if buffer full

    def _remove_dc_offset(self, audio_array):
        """
        Remove DC offset using a first-order high-pass filter (DC blocker)
        This eliminates hum and low-frequency noise
        """
        # DC blocker coefficient (higher = more aggressive, 0.995 is standard)
        alpha = 0.995

        # Reshape to stereo (192 samples x 2 channels)
        stereo = audio_array.reshape(-1, 2)
        filtered = np.zeros_like(stereo, dtype=np.float32)

        for i in range(len(stereo)):
            for ch in range(2):
                # DC blocker: y[n] = x[n] - x[n-1] + alpha * y[n-1]
                sample = float(stereo[i, ch])
                filtered[i, ch] = sample - self.dc_filter_state[ch]
                if i > 0:
                    filtered[i, ch] += alpha * filtered[i-1, ch]

            # Store last input sample for next packet
            self.dc_filter_state = stereo[-1].astype(np.float32)

        # Convert back to int16
        return np.clip(filtered, -32768, 32767).astype(np.int16)

    def _play_audio(self):
        """Audio playback thread"""
        channel = pygame.mixer.Channel(0)

        while self.running:
            try:
                audio_data = self.audio_queue.get(timeout=0.1)

                # Convert to numpy array for pygame
                # Audio data is 768 bytes = 384 int16 samples (192 stereo pairs)
                audio_array = np.frombuffer(audio_data, dtype=np.int16)

                # Remove DC offset and low-frequency hum
                filtered_array = self._remove_dc_offset(audio_array)

                # Create pygame Sound from filtered array
                sound = pygame.sndarray.make_sound(filtered_array)

                # Play sound (will wait if previous sound still playing)
                channel.play(sound)
                while channel.get_busy() and self.running:
                    time.sleep(0.001)

                self.packets_played += 1

            except queue.Empty:
                continue
            except Exception as e:
                print(f"Audio playback error: {e}")

    def stop(self):
        """Stop audio playback"""
        self.running = False
        self.thread.join(timeout=1.0)
        pygame.mixer.quit()


def main():
    parser = argparse.ArgumentParser(description='C64 Ultimate64 A/V Stream Viewer (Wayland Native)')
    parser.add_argument('--ultimate-host', type=str,
                       help='Ultimate64 hostname or IP (default: from C64_HOST env var)')
    parser.add_argument('--local-ip', type=str, default='192.168.68.62',
                       help='Local IP address to receive stream (default: 192.168.68.62)')
    parser.add_argument('--video-port', type=int, default=11000,
                       help='Video UDP port (default: 11000)')
    parser.add_argument('--audio-port', type=int, default=11001,
                       help='Audio UDP port (default: 11001)')
    parser.add_argument('--scale', type=int, default=2,
                       help='Display scale factor (default: 2)')
    parser.add_argument('--fullscreen', action='store_true',
                       help='Run in fullscreen mode')
    parser.add_argument('--no-audio', action='store_true',
                       help='Disable audio playback')
    parser.add_argument('--no-auto-stream', action='store_true',
                       help='Do not automatically start/stop streams')
    args = parser.parse_args()

    # Get Ultimate64 host from argument or environment
    ultimate_host = args.ultimate_host or os.environ.get('C64_HOST')

    print("C64 Stream Viewer - Audio/Video (Wayland Native)")
    if ultimate_host:
        print(f"Ultimate64: {ultimate_host}")
    print(f"Video: UDP port {args.video_port}")
    print(f"Audio: UDP port {args.audio_port}" + (" (disabled)" if args.no_audio else ""))
    print("Controls: ESC/Q=Quit, F=Fullscreen, M=Mute")
    print()

    # Start streams if Ultimate64 host is provided
    streams_started = False
    if ultimate_host and not args.no_auto_stream:
        print("Starting streams...")
        video_started = send_ultimate64_stream_command(ultimate_host, 0, True, args.local_ip, args.video_port)
        audio_started = False
        if not args.no_audio:
            audio_started = send_ultimate64_stream_command(ultimate_host, 1, True, args.local_ip, args.audio_port)

        if video_started:
            print(f"✓ Video stream started (→ {args.local_ip}:{args.video_port})")
        else:
            print(f"✗ Failed to start video stream")

        if not args.no_audio:
            if audio_started:
                print(f"✓ Audio stream started (→ {args.local_ip}:{args.audio_port})")
            else:
                print(f"✗ Failed to start audio stream")

        streams_started = video_started or audio_started
        print()

    # Initialize pygame
    pygame.init()

    # Create UDP sockets
    video_sock = None
    audio_sock = None

    try:
        # Video socket
        video_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        video_sock.bind(('0.0.0.0', args.video_port))
        video_sock.setblocking(False)

        # Audio socket
        if not args.no_audio:
            audio_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            audio_sock.bind(('0.0.0.0', args.audio_port))
            audio_sock.setblocking(False)

    except Exception as e:
        print(f"Failed to create sockets: {e}")
        return 1

    # Initialize audio player
    audio_player = None
    if not args.no_audio:
        audio_player = AudioPlayer()
        audio_muted = False

    print("Waiting for first frame...")
    assembler = C64FrameAssembler()
    screen = None

    frame_count = 0
    audio_count = 0
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
                    elif event.key == pygame.K_m and audio_player:
                        audio_muted = not audio_muted
                        if audio_muted:
                            pygame.mixer.pause()
                            print("Audio muted")
                        else:
                            pygame.mixer.unpause()
                            print("Audio unmuted")

            # Receive video packets
            try:
                data, addr = video_sock.recvfrom(VIDEO_PACKET_SIZE + 100)

                if len(data) == VIDEO_PACKET_SIZE:
                    # Parse header
                    seq_num, frame_num, line_num, pixels_per_line, lines_per_packet, bits_per_pixel = \
                        struct.unpack('<HHHHBB', data[:10])

                    is_last = (line_num & 0x8000) != 0
                    line_num = line_num & 0x7FFF

                    if pixels_per_line == PIXELS_PER_LINE and lines_per_packet == LINES_PER_PACKET and bits_per_pixel == 4:
                        pixel_data = data[VIDEO_HEADER_SIZE:]
                        assembler.add_packet(frame_num, line_num, lines_per_packet, pixel_data, is_last)

                        if assembler.is_complete():
                            frame_surface = assembler.get_frame_surface()
                            if frame_surface is not None:
                                frame_count += 1
                                fps_counter += 1

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
                                    pygame.display.set_caption('C64 Stream - A/V')
                                    format_name = "PAL" if assembler.height == PAL_HEIGHT else "NTSC"
                                    print(f"Format: {format_name} ({PIXELS_PER_LINE}x{assembler.height})")

                                if args.scale > 1:
                                    scaled = pygame.transform.scale(
                                        frame_surface,
                                        (PIXELS_PER_LINE * args.scale, assembler.height * args.scale)
                                    )
                                    screen.blit(scaled, (0, 0))
                                else:
                                    screen.blit(frame_surface, (0, 0))

                                pygame.display.flip()

                            assembler = C64FrameAssembler()

            except (BlockingIOError, OSError):
                pass

            # Receive audio packets
            if audio_sock and audio_player and not audio_muted:
                try:
                    data, addr = audio_sock.recvfrom(AUDIO_PACKET_SIZE + 100)

                    if len(data) == AUDIO_PACKET_SIZE:
                        # Skip 2-byte header, get 768 bytes of audio
                        audio_data = data[AUDIO_HEADER_SIZE:AUDIO_HEADER_SIZE + 768]
                        audio_player.add_audio_packet(audio_data)
                        audio_count += 1

                except (BlockingIOError, OSError):
                    pass

            # Small delay to prevent CPU spinning
            time.sleep(0.001)

            # Print stats every second
            current_time = time.time()
            if current_time - last_stats_time >= 1.0:
                fps = fps_counter / (current_time - last_stats_time)
                audio_info = f" | Audio: {audio_count}" if audio_player else ""
                mute_info = " (MUTED)" if audio_player and audio_muted else ""
                print(f"FPS: {fps:.1f} | Frames: {frame_count}{audio_info}{mute_info}")
                fps_counter = 0
                last_stats_time = current_time

    except KeyboardInterrupt:
        print("\nStopped by user")
    finally:
        print(f"\nTotal - Video: {frame_count} frames")
        if audio_player:
            print(f"Total - Audio: {audio_count} packets ({audio_player.packets_played} played)")
            audio_player.stop()
        if video_sock:
            video_sock.close()
        if audio_sock:
            audio_sock.close()
        pygame.quit()

        # Stop streams if we started them
        if ultimate_host and not args.no_auto_stream and streams_started:
            print("\nStopping streams...")
            if send_ultimate64_stream_command(ultimate_host, 0, False, args.local_ip, args.video_port):
                print("✓ Video stream stopped")
            if not args.no_audio:
                if send_ultimate64_stream_command(ultimate_host, 1, False, args.local_ip, args.audio_port):
                    print("✓ Audio stream stopped")

    return 0


if __name__ == '__main__':
    sys.exit(main())
