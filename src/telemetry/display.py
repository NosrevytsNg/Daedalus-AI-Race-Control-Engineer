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

# Format sector and delta timing display
def format_sector_time(milliseconds):
    if milliseconds is None or milliseconds <= 0:
        return "--"        #"--:--.---" 
    
    seconds = milliseconds / 1000
    return f"{seconds:.3f}"

# Format delta times with + for positive and - for negative
def format_delta(milliseconds):
    if milliseconds is None:
        return "--"        #"--:--.---"  

    seconds = milliseconds / 1000

    if seconds > 0:
        return f"+{seconds:.3f}s"
    return f"{seconds:.3f}s"

# For gap display
def format_gap_ms(milliseconds):
    if milliseconds is None or milliseconds < 0:
        return "--"
    
    seconds = milliseconds / 1000

    if seconds < 0 or seconds > 600:
        return "--"

    return f"{seconds:.3f}s"

def display_live_telemetry(latest_telemetry, latest_lap_data, latest_session_history, latest_completed_lap_sectors,):
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
        #print()
        print(f"Gap Ahead: {format_gap_ms(latest_lap_data.delta_to_car_in_front_ms)}s")
        print(f"Gap Leader: {format_gap_ms(latest_lap_data.delta_to_race_leader_ms)}s")
        
        if latest_session_history is not None:
            print()
            print(f"Best Lap: {format_time_ms(latest_session_history.best_lap_time_ms)}")
        else:
            print("Best Lap: --")

        print(f"Current Lap :  {format_time_ms(latest_lap_data.current_lap_time_ms)}")
        print(f"Last Lap:  {format_time_ms(latest_lap_data.last_lap_time_ms)}")


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
        current_s3 = None  # Not provided in lap data packet, would need to be calculated based on lap time and sector times
    else:
        current_s1 = current_s2 = current_s3 = None

    if latest_completed_lap_sectors is not None:
        previous_s1 = format_time_ms_with_placeholder(
            latest_completed_lap_sectors.sector_1_time_ms
        )
        previous_s2 = format_time_ms_with_placeholder(
            latest_completed_lap_sectors.sector_2_time_ms
        )
        previous_s3 = format_time_ms_with_placeholder(
            latest_completed_lap_sectors.sector_3_time_ms
        )
    else:
        previous_s1 = previous_s2 = previous_s3 = "--"

    # Current Delta Information  
    delta_s1 = format_delta(
        current_s1 - best_s1
        if current_s1 and best_s1
        else None
    )
    delta_s2 = format_delta(
        current_s2 - best_s2
        if current_s2 and best_s2
        else None
    )
    delta_s3 = format_delta(
        current_s3 - best_s3
        if current_s3 and best_s3
        else None
    ) 

    best_s1 = format_time_ms_with_placeholder(best_s1)
    best_s2 = format_time_ms_with_placeholder(best_s2)
    best_s3 = format_time_ms_with_placeholder(best_s3)

    current_s1 = format_time_ms_with_placeholder(current_s1)
    current_s2 = format_time_ms_with_placeholder(current_s2)
    current_s3 = format_time_ms_with_placeholder(current_s3)

    # Phase 1: Display sector times and deltas
    #print()
    #print(f"Best Sectors:    S1: {best_s1} | S2: {best_s2} | S3: {best_s3}")
    #print(f"Current Sectors: S1: {current_s1} | S2: {current_s2} | S3: {current_s3}")
    #print(f"Delta to Best:   S1: {delta_s1}  | S2: {delta_s2}  | S3: {delta_s3}")

    # Phase 2: Edit sector times and deltas format (table format with headers)
    print()
    print("                     S1         S2         S3")
    print("----------------------------------------------------")
    print(f"Best Sector       {best_s1:<10} {best_s2:<10} {best_s3:<10}")
    print(f"Current Sector    {current_s1:<10} {current_s2:<10} {current_s3:<10}")
    print(f"Previous Sector   {previous_s1:<10} {previous_s2:<10} {previous_s3:<10}")
    print(f"Delta             {delta_s1:<10} {delta_s2:<10} {delta_s3:<10}")    