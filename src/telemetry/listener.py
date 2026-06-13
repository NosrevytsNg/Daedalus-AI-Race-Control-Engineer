import socket
from datetime import datetime

from src.telemetry.parser import parse_header, parse_car_telemetry, parse_lap_data, format_time_ms
from src.telemetry.packets import PACKET_NAMES, PACKET_ID_CAR_TELEMETRY, PACKET_ID_LAP_DATA

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

    latest_telemetry = None
    latest_lap_data = None

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
                
                # For debugging: Print packet info (Initially we will print all packets, to verify we are receiving data correctly. Later we will focus on specific packets like telemetry and lap data)
                # ============================================================
                #packet_name = PACKET_NAMES.get(packet_id, "Unknown")
                #print(
                #    f"[{timestamp}] Packet received from "
                #    f"Packet {packet_id} | ({packet_name}) | "
                #    f"Format: {header['packet_format']} | "
                #   f"Player Car {header['player_car_index']} | "
                #    f"Size: {len(data)} bytes"
                #    f"{address[0]}:{address[1]} | Size: {len(data)} bytes")
                # ============================================================
                
                if packet_id == PACKET_ID_CAR_TELEMETRY:
                    latest_telemetry = parse_car_telemetry(data, header["player_car_index"])

                elif packet_id == PACKET_ID_LAP_DATA:
                    latest_lap_data = parse_lap_data(data, header["player_car_index"])

                if latest_telemetry is not None:
                    # Clear the console and display LIVE car telemetry terminal
                    print("\033c", end="")
                    print("====================================")
                    print("DAEDALUS LIVE TELEMETRY")
                    print("====================================")
                    print()
                    print(f"Speed:     {latest_telemetry.speed} km/h")
                    print(f"Gear:      {latest_telemetry.gear}")
                    print(f"RPM:       {latest_telemetry.rpm}")
                    print(f"Throttle:  {latest_telemetry.throttle * 100:.0f}%")
                    print(f"Brake:     {latest_telemetry.brake * 100:.0f}%")
                    print(f"DRS:       {'ON' if latest_telemetry.drs else 'OFF'}")

                    # Add to console and display LIVE Lap Data
                    if latest_lap_data is not None:
                        print()
                        print(f"Position:  {latest_lap_data.car_position}")
                        print(f"Lap:       {latest_lap_data.current_lap_num}")
                        print(f"Sector:    {latest_lap_data.sector+1}")
                        print(f"Lap Time:  {format_time_ms(latest_lap_data.current_lap_time_ms)}")
                        print(f"Last Lap:  {format_time_ms(latest_lap_data.last_lap_time_ms)}")
                        print(f"Gap Ahead: {latest_lap_data.delta_to_car_in_front_ms / 1000:.3f}s")
                        print(f"Gap Leader: {latest_lap_data.delta_to_race_leader_ms / 1000:.3f}s")

            except socket.timeout:
                continue

    except KeyboardInterrupt:
        print("\nDaedalus Telemetry Core has stopped...")
        print("Shutting down...")
    finally:
        sock.close()