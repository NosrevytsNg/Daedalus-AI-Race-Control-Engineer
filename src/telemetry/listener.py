import socket
from datetime import datetime

from src.telemetry.parser import parse_header
from src.telemetry.packets import PACKET_NAMES

UDP_IP = "0.0.0.0"
UDP_PORT = 20777
BUFFER_SIZE = 4096


def start_listener():
    print("Daedalus Telemetry Core Started")
    print(f"Listening on UDP port {UDP_PORT}...")
    print("Waiting for F1 telemetry packets...\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    sock.settimeout(1.0)

    try:
        while True:
            try:
                data, address = sock.recvfrom(BUFFER_SIZE)
                timestamp = datetime.now().strftime("%H:%M:%S")

                header = parse_header(data)

                if header is None:
                    print(f"[{timestamp}] Invalid packet received from {address[0]}:{address[1]}")
                    continue

                packet_id = header["packet_id"]
                packet_name = PACKET_NAMES.get(packet_id, "Unknown")


                print(
                    f"[{timestamp}] Packet received from "
                    f"Packet {packet_id} | ({packet_name}) | "
                    f"Format: {header['packet_format']} | "
                    f"Player Car {header['player_car_index']} | "
                    f"Size: {len(data)} bytes"
                    #f"{address[0]}:{address[1]} | Size: {len(data)} bytes"
                )
            except socket.timeout:
                continue
    except KeyboardInterrupt:
        print("Daedalus Telemetry Core has stopped...")
        print("Shutting down...")
    finally:
        sock.close()