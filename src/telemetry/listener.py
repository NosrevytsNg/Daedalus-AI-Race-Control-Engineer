# ✅
# [listener.py] functions as a LIVE telemetry coordinator, and a traffic controller
# 
# 1. Receives UDP Packet from F1 game
# 2. Asks [parser.py] to identify (packetID) and decode the UDP Packets
# 3. Stores the latest decoded data
# 4. Sends the latest data to [display.py]
# 5. Sends completed lap captures to [telemetry_logger.py]


import socket                      # Allows Python to listen for UDP Packets
import time                        # Used to control refresh rate of Dashboard
from datetime import datetime      # Used for Timestamp (Messages, Logs and Events)

# Sends latest stored or LIVE telemetry info to Dashboard
from src.telemetry.display import display_live_telemetry

# Consults parser.py about decoding each packet type
from src.telemetry.parser import (parse_header, parse_car_telemetry, parse_lap_data, 
                                  parse_session_history, parse_car_status, CompletedLapSectorTiming, 
                                  parse_session_data, parse_car_damage, parse_tyre_sets,)

# Align with project's packet dictionary (packets.py)
from src.telemetry.packets import (PACKET_NAMES, PACKET_ID_CAR_TELEMETRY, PACKET_ID_LAP_DATA, 
                                   PACKET_ID_SESSION_HISTORY, PACKET_ID_CAR_STATUS, PACKET_ID_SESSION, 
                                   PACKET_ID_CAR_DAMAGE,PACKET_ID_TYRE_SETS,)

# Save completed laps to CSV
from src.telemetry.telemetry_logger import (TelemetryLogger)

# from src.engineer.race_engineer import (reset_race_sector_trend_state)


# UDP_IP = "0.0.0.0" # Potential security risk (Traffic originating from ANY network)
UDP_IP = "127.0.0.1" # Traffic originating from LOCAL computer
UDP_PORT = 20777
BUFFER_SIZE = 4096 # Packet size limit


def start_listener():
    print("Daedalus Telemetry Core Started")
    print(f"Listening on UDP port {UDP_PORT}...")
    print("Waiting for F1 telemetry packets...\n")

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # AF_INET = IPv4 | SOCK_DGRAM = UDP socket
    sock.bind((UDP_IP, UDP_PORT))                           # Instructs Windows to route UDP traffic from port 20777 to this Python program
    sock.settimeout(1.0)                                    # Timeout Settings (1s)

    # The timeout setting is used in conjunction with the exception condition for "data, address = sock.recvfrom(BUFFER_SIZE)" LINE 85
    # The purpose of "sock.settimeout(1.0)" & "except socket.timeout: continue" is to stop UDP Receiver from getting stuck in an infinite loop
    # Without timeout: "The guard waits at the door forever until a UDP Packet knocks"
    # With timeout: "The guard waits at the door for a UDP Packet knocks for 1s, does something else then checks on the door again"

# ============================ Variable List =================================================

    # Telemetry Data (Packet ID 6) - Speed, Gear, RPM, Throttle, Brake, DRS
    latest_telemetry = None

    # Lap Data (Packet ID 2) - Lap Details (Position, Lap Number, Gap Ahead, Gap Behind)
    latest_lap_data = None

    # Session History (Packet ID 11) - Lap and Sector Times (Current, Best, Previous)
    latest_session_history = None 
    previous_lap_num = 0
    latest_completed_lap_sectors = None  # store sector times for most recently completed lap 
    invalid_lap_detected = None  # Flag to indicate if an invalid lap was detected

    # Car/Vehicle + Equipment Data (Packet ID 7) - Fuel, ERS, Tyre (Type & Health), DRS
    latest_car_status = None

    # Session Data (Packet ID 1) - Weather and Track Condition
    latest_session_data = None

    # Car Damage Data (Packet ID 10) - Component Damage %
    latest_car_damage = None

    # Tyre Stats Data (Packet ID 12) - Detailed Compound Stats and Inventory
    latest_tyre_sets = None

# ============================================================================================
    last_display_update = 0
    DISPLAY_REFRESH_RATE = 0.25  # Refreshes roughly 4 times per second

    telemetry_logger = TelemetryLogger()
    current_session_uid = None
    

    try:
        while True:
            try:
                data_packet_bytes, address = sock.recvfrom(BUFFER_SIZE)
                timestamp = datetime.now().strftime("%H:%M:%S")

                # Packet Structure (Purpose and Concept of "player_car_index": values[10])
                # Sends 1 UDP Packet of 1 packet type with data of all cars

                # Packet Header <= Contains "player_car_index": values[10]
                # Car 0 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...
                # Car 1 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ... 
                # Car 2 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...
                # Car 3 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...
                # Car 4 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...
                # Car 5 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...
                # Car 6 Block: value[0], value[1], value[2], value[3], value[4], value[5], value[6], ...

                # Assuming player_car_index == 4, the parser skips all before and reads the 5th car block.
                # The index is zero-based: 0 = first car, 1 = second car, etc.

                header = parse_header(data_packet_bytes)

                if header is None:
                    print(f"[{timestamp}] Invalid packet received from {address[0]}:{address[1]}")
                    continue

                current_session_uid = header["session_uid"]

                packet_id = header["packet_id"]
                
                # For debugging: Print packet info (Initially we will print all packets, to verify we are receiving data correctly. Later we will focus on specific packets like telemetry and lap data)
                # ============================================================
                #packet_name = PACKET_NAMES.get(packet_id, "Unknown")
                #print(
                #    f"[{timestamp}] Packet received from "
                #    f"Packet {packet_id} | ({packet_name}) | "
                #    f"Format: {header['packet_format']} | "
                #    f"Player Car {header['player_car_index']} | "
                #    f"Size: {len(data)} bytes"
                #    f"{address[0]}:{address[1]} | Size: {len(data)} bytes")
                # ============================================================
                
                if packet_id == PACKET_ID_CAR_TELEMETRY:
                    latest_telemetry = parse_car_telemetry(data_packet_bytes, header["player_car_index"])

                elif packet_id == PACKET_ID_LAP_DATA:
                    new_lap_data = parse_lap_data(data_packet_bytes, header["player_car_index"])

                    new_completed_lap_detected = False
                    completed_lap_data_for_log = None

                    # Added for previous sector timing records
                    if new_lap_data is not None:

                        # Replay / Rewind Detection
                        
                        # Instant replay or flashback can make the game timeline move backwards.
                        # If that happens, the current lap should not be treated as a clean sector-trend lap.
                
                        if latest_lap_data is not None:
                            lap_number_went_back = (
                                new_lap_data.current_lap_num < latest_lap_data.current_lap_num
                            )

                            same_lap_time_went_back = (
                                new_lap_data.current_lap_num == latest_lap_data.current_lap_num
                                and new_lap_data.current_lap_time_ms + 2000 < latest_lap_data.current_lap_time_ms # 2000 = 2 seconds buffer to avoid false positives
                            )

                            if lap_number_went_back or same_lap_time_went_back:
                                invalid_lap_detected = new_lap_data.current_lap_num

                                print(
                                    f"Replay/rewind detected on lap "
                                    f"{invalid_lap_detected}. This lap will not be used for sector trend."
                                )

                        # clause to detect when a new lap has started, and the previous lap has ended.
                        # rewind_detected = False

                        # if latest_lap_data is not None:
                        #     lap_num_rewind = (
                        #         new_lap_data.current_lap_num < latest_lap_data.current_lap_num
                        #     ) 

                        #     same_lap_num_rewind = (
                        #         new_lap_data.current_lap_num == latest_lap_data.current_lap_num
                        #         and new_lap_data.current_lap_time_ms < latest_lap_data.current_lap_time_ms
                        #     )

                        #     rewind_detected = lap_num_rewind or same_lap_num_rewind

                        # if rewind_detected:
                        #     previous_lap_num = new_lap_data.current_lap_num
                        #     latest_lap_data = new_lap_data
                        #     latest_completed_lap_sectors = None
                        #     reset_race_sector_trend_state()

                        #     # Optional print
                        #     print("Rewind detected! - Lap tracking reset.")
                            
                        #     continue



                        # If the new and previous lap data is stored, and there is a greater number of new laps vs previous laps,
                        # then the previous lap has just ended.
                        # if "previous_lap_num = 4" and "new_lap_data.current_lap_num = 5" => Lap 4 ended, Lap 5 started.

                        if (previous_lap_num is not None and new_lap_data.current_lap_num > previous_lap_num and latest_lap_data is not None):

                            completed_source_lap_num = latest_lap_data.current_lap_num

                            if completed_source_lap_num == invalid_lap_detected:
                                latest_completed_lap_sectors = None
                                invalid_lap_detected = None
                                new_completed_lap_detected = False

                                print(f"Lap {completed_source_lap_num} invalidated because replay/rewind was used. ")

                            else:
                                # Stores the completed lap before replacing latest_lap_data.
                                # Important for telemetry_logger.py, to log the completed lap data, not the newly-started lap data.
                                completed_lap_data_for_log = latest_lap_data

                                # Sector 3 timing is removed when a new lap takes place.
                                # Sector 3 = Full Lap - S1 - S2
                                sector_1 = latest_lap_data.sector_1_time_ms
                                sector_2 = latest_lap_data.sector_2_time_ms
                                completed_lap_time = latest_lap_data.current_lap_time_ms


                                # Only accepts comppleted sector timing if all sectors are positive
                                if (sector_1 is not None and sector_2 is not None and completed_lap_time is not None):
                                    
                                    sector_3 = completed_lap_time - sector_1 - sector_2

                                    if sector_1 > 0 and sector_2 > 0 and sector_3 > 0:
                                        latest_completed_lap_sectors = CompletedLapSectorTiming(
                                            lap_num=latest_lap_data.current_lap_num - 1,
                                            sector_1_time_ms=sector_1,
                                            sector_2_time_ms=sector_2,
                                            sector_3_time_ms=sector_3,
                                        )

                                        new_completed_lap_detected = True

                        previous_lap_num = new_lap_data.current_lap_num
                        latest_lap_data = new_lap_data

                        # Sends current session UID and latest available state to logger  
                        # Only log when a new completed lap is detected
                        # Prevents the same completed lap to be recorded twice 
                        if new_completed_lap_detected:        
                            telemetry_logger.log_lap_capture(
                                current_session_uid,
                                completed_lap_data_for_log,
                                latest_telemetry,
                                latest_car_status,
                                latest_car_damage,
                                latest_completed_lap_sectors,
                            )   
                         
                    #print(f"Completed Lap {latest_completed_lap_sectors.lap_num} Sector Times: S1={format_time_ms(sector_1)}, S2={format_time_ms(sector_2)}, S3={format_time_ms(sector_3)}")
    
                elif packet_id == PACKET_ID_SESSION_HISTORY:
                    session_history = parse_session_history(data_packet_bytes, header["player_car_index"])

                    if session_history is not None:
                        latest_session_history = session_history


                elif packet_id == PACKET_ID_CAR_STATUS:
                    latest_car_status = parse_car_status(
                        data_packet_bytes,
                        header["player_car_index"]
                    )

                elif packet_id == PACKET_ID_SESSION:
                    latest_session_data = parse_session_data(data_packet_bytes)

                elif packet_id == PACKET_ID_CAR_DAMAGE:
                    latest_car_damage = parse_car_damage(
                        data_packet_bytes,
                        header["player_car_index"]
                    )

                elif packet_id == PACKET_ID_TYRE_SETS:
                    tyre_sets = parse_tyre_sets(
                        data_packet_bytes,
                        header["player_car_index"]
                    )

                    if tyre_sets is not None:
                        latest_tyre_sets = tyre_sets


                current_time = time.time()

                # UDP packets arrive many times per second, so if we refresh each time we received a packet, the terminal will refresh too quickly
                # [current_time - last_display_update] = duration since the dashboard was last refreshed
                if current_time - last_display_update >= DISPLAY_REFRESH_RATE:
                    display_live_telemetry(
                        latest_telemetry, 
                        latest_lap_data, 
                        latest_session_history, 
                        latest_completed_lap_sectors,
                        latest_car_status,
                        latest_session_data,
                        latest_car_damage,
                        latest_tyre_sets
                        )
                    last_display_update = current_time

                # Replaced: display_live_telemetry(latest_telemetry, latest_lap_data, latest_session_history)              


            except socket.timeout: # No UDP packet arrived within the socket timeout window.
                continue
                
                # continue sends the loop back to the top so Daedalus can wait again,
                # instead of crashing or freezing permanently.

    # Allows the user to stop Daedalus safely with Ctrl+C
    except KeyboardInterrupt:
        print("\nDaedalus Telemetry Core has stopped...")
        print("Shutting down...")
    finally:
        sock.close()
        # Always close the UDP socket before exiting.
        # Releases port 20777 properly so the program can be restarted cleanly.


# ================= Initial Dashboard Layout ===========================================
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
# ====================================================================================
