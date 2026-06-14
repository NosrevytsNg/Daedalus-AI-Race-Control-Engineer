import socket
import time
from datetime import datetime
from src.telemetry.display import display_live_telemetry

from src.telemetry.parser import parse_header, parse_car_telemetry, parse_lap_data, parse_session_history, parse_car_status, CompletedLapSectorTiming
from src.telemetry.packets import PACKET_NAMES, PACKET_ID_CAR_TELEMETRY, PACKET_ID_LAP_DATA, PACKET_ID_SESSION_HISTORY, PACKET_ID_CAR_STATUS

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

# ============================ Variable List =================================================

    # Telemetry Data (Packet ID 6) - Speed, Gear, RPM, Throttle, Brake, DRS
    latest_telemetry = None

    # Lap Data (Packet ID 2) - Lap Details (Position, Lap Number, Gap Ahead, Gap Behind)
    latest_lap_data = None

    # Session History (Packet ID 11) - Lap and Sector Times (Current, Best, Previous)
    latest_session_history = None 
    previous_lap_num = 0
    latest_completed_lap_sectors = None  # store sector times for most recently completed lap 

    # Car/Vehicle + Equipment Data (Packet ID 7) - Fuel, ERS, Tyre (Type & Health), DRS
    latest_car_status = None

# ============================================================================================
    last_display_update = 0
    DISPLAY_REFRESH_RATE = 0.25  # seconds

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
                    new_lap_data = parse_lap_data(data, header["player_car_index"])

                    # Added for previous sector timing records
                    if new_lap_data is not None:
                        if(
                            previous_lap_num is not None
                            and new_lap_data.current_lap_num > previous_lap_num
                            and latest_lap_data is not None
                        ):
                            sector_1 = latest_lap_data.sector_1_time_ms
                            sector_2 = latest_lap_data.sector_2_time_ms
                            sector_3 = latest_lap_data.current_lap_time_ms - sector_1 - sector_2

                            if sector_1 > 0 and sector_2 > 0 and sector_3 > 0:
                                latest_completed_lap_sectors = CompletedLapSectorTiming(
                                    lap_num=latest_lap_data.current_lap_num - 1,
                                    sector_1_time_ms=sector_1,
                                    sector_2_time_ms=sector_2,
                                    sector_3_time_ms=sector_3,
                                )

                        previous_lap_num = new_lap_data.current_lap_num
                        latest_lap_data = new_lap_data   
                        
                        
                    #print(f"Completed Lap {latest_completed_lap_sectors.lap_num} Sector Times: S1={format_time_ms(sector_1)}, S2={format_time_ms(sector_2)}, S3={format_time_ms(sector_3)}")
    
                elif packet_id == PACKET_ID_SESSION_HISTORY:
                    session_history = parse_session_history(data, header["player_car_index"])

                    if session_history is not None:
                        latest_session_history = session_history

                # ============================================================
                # Clear the console and display LIVE car telemetry terminal
                #if latest_telemetry is not None:                    
                #    print("\033c", end="")
                #    print("====================================")
                #    print("DAEDALUS LIVE TELEMETRY")
                #    print("====================================")
                #    print()
                #    print(f"Speed:     {latest_telemetry.speed} km/h")
                #    print(f"Gear:      {latest_telemetry.gear}")
                #    print(f"RPM:       {latest_telemetry.rpm}")
                #    print(f"Throttle:  {latest_telemetry.throttle * 100:.0f}%")
                #    print(f"Brake:     {latest_telemetry.brake * 100:.0f}%")
                #    print(f"DRS:       {'ON' if latest_telemetry.drs else 'OFF'}")

                    # Add to console and display LIVE Lap Data
                #    if latest_lap_data is not None:
                #        print()
                #        print(f"Position:  {latest_lap_data.car_position}")
                #        print(f"Lap:       {latest_lap_data.current_lap_num}")
                #        print(f"Sector:    {latest_lap_data.sector+1}")
                #        print(f"Lap Time:  {format_time_ms(latest_lap_data.current_lap_time_ms)}")
                #        print(f"Last Lap:  {format_time_ms(latest_lap_data.last_lap_time_ms)}")
                #        print(f"Gap Ahead: {latest_lap_data.delta_to_car_in_front_ms / 1000:.3f}s")
                #        print(f"Gap Leader: {latest_lap_data.delta_to_race_leader_ms / 1000:.3f}s")
                # ============================================================

                elif packet_id == PACKET_ID_CAR_STATUS:
                    latest_car_status = parse_car_status(
                        data,
                        header["player_car_index"]
                    )

                # Replaced with:               
                # display_live_telemetry(latest_telemetry, latest_lap_data, latest_session_history)

                current_time = time.time()

                if current_time - last_display_update >= DISPLAY_REFRESH_RATE:
                    display_live_telemetry(
                        latest_telemetry, 
                        latest_lap_data, 
                        latest_session_history, 
                        latest_completed_lap_sectors,
                        latest_car_status
                        )
                    last_display_update = current_time

            except socket.timeout:
                continue

    except KeyboardInterrupt:
        print("\nDaedalus Telemetry Core has stopped...")
        print("Shutting down...")
    finally:
        sock.close()