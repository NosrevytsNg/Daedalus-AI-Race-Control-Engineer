import os

from src.telemetry.parser import format_time_ms

# # Clear the console  
def clear_terminal(): 
    print("\033c", end="")

# Insert placeholders for empty data (lap and sector timings)
def format_time_ms_with_placeholder(milliseconds):
    if milliseconds is None or milliseconds <= 0:
        return "--"        #"--:--.---"  
    return format_time_ms(milliseconds)

def format_sector_time(milliseconds):
    if milliseconds is None or milliseconds <= 0:
        return "--"        #"--:--.---" 
    
    seconds = milliseconds / 1000
    return f"{seconds:.3f}"

def format_delta(milliseconds):
    if milliseconds is None:
        return "--"        #"--:--.---"  

    seconds = milliseconds / 1000

    if seconds > 0:
        return f"{seconds:.3f}s"
    return f"{seconds:.3f}s"

def display_live_telemetry(latest_telemetry, latest_lap_data, latest_session_history):
    clear_terminal()

    # Display telemetry terminal
    #print("====================================")
    #print("DAEDALUS LIVE TELEMETRY")
    #print("====================================")
    #print()

    # LIVE car telemetry data 
    if latest_telemetry is not None:

        print(f"Speed:     {latest_telemetry.speed} km/h")
        print(f"Gear:      {latest_telemetry.gear}")
        print(f"RPM:       {latest_telemetry.rpm}")
        print(f"Throttle:  {latest_telemetry.throttle * 100:.0f}%")
        print(f"Brake:     {latest_telemetry.brake * 100:.0f}%")
        print(f"DRS:       {'ON' if latest_telemetry.drs else 'OFF'}")

    else:
        print()
        print("No telemetry data available yet.")

    # LIVE lap data
    if latest_lap_data is not None:
        print()
        print(f"Position:  {latest_lap_data.car_position}")
        print(f"Lap:       {latest_lap_data.current_lap_num}")
        
        if latest_session_history is not None:
            print()
            print(f"Best Lap: {format_time_ms(latest_session_history.best_lap_time_ms)}")
        else:
            print("Best Lap: --")

        print(f"Current Lap :  {format_time_ms(latest_lap_data.current_lap_time_ms)}")
        print(f"Last Lap:  {format_time_ms(latest_lap_data.last_lap_time_ms)}")

        print()
        print(f"Gap Ahead: {latest_lap_data.delta_to_car_in_front_ms / 1000:.3f}s")
        print(f"Gap Leader: {latest_lap_data.delta_to_race_leader_ms / 1000:.3f}s")

    else:
        print()
        print("No lap data available yet.")

    # LIVE session history data (sector records)
    
    if latest_session_history is not None: 

        # Best Sector Timings
        best_s1 = latest_session_history.best_sector1_time_ms
        best_s2 = latest_session_history.best_sector2_time_ms
        best_s3 = latest_session_history.best_sector3_time_ms
    else:
        best_s1 = best_s2 = best_s3 = None

    # Current Sector Timings
    if latest_lap_data is not None:
        current_s1 = latest_lap_data.sector_1_time_ms
        current_s2 = latest_lap_data.sector_2_time_ms
        current_s3 = latest_lap_data.sector_3_time_ms
    else:
        current_s1 = current_s2 = current_s3 = None

    # Current Delta Information  
    delta_s1 = format_delta(
        best_s1 - current_s1
        if current_s1 and best_s1
        else None
    )
    delta_s2 = format_delta(
        best_s2 - current_s2
        if current_s2 and best_s2
        else None
    )
    delta_s3 = format_delta(
        best_s3 - current_s3
        if current_s3 and best_s3
        else None
    ) 

    best_s1 = format_time_ms_with_placeholder(best_s1)
    best_s2 = format_time_ms_with_placeholder(best_s2)
    best_s3 = format_time_ms_with_placeholder(best_s3)

    current_s1 = format_time_ms_with_placeholder(current_s1)
    current_s2 = format_sector_time(current_s2)
    current_s3 = format_sector_time(current_s3)

    print()
    print(f"Best Sectors:    S1: {best_s1}    | S2: {best_s2}    | S3: {best_s3}")
    print(f"Current Sectors: S1: {current_s1} | S2: {current_s2} | S3: {current_s3}")
    print(f"Delta to Best:   S1: {delta_s1}   | S2: {delta_s2}   | S3: {delta_s3}")