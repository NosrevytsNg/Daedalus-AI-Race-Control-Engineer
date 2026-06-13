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
        best_s1 = format_time_ms_with_placeholder(latest_session_history.best_sector1_time_ms)
        best_s2 = format_time_ms_with_placeholder(latest_session_history.best_sector2_time_ms)
        best_s3 = format_time_ms_with_placeholder(latest_session_history.best_sector3_time_ms)
    else:
        best_s1 = best_s2 = best_s3 = "--"

    # Placeholder for current sector times from lap data (will decode later)
    current_s1 = current_s2 = current_s3 = "--"

    # Placeholder for current delta from lap data (will decode later)  
    delta_s1 = delta_s2 = delta_s3 = "--"
    print()
    print(f"Best Sectors:    S1: {best_s1}    | S2: {best_s2}    | S3: {best_s3}")
    print(f"Current Sectors: S1: {current_s1} | S2: {current_s2} | S3: {current_s3}")
    print(f"Delta to Best:   S1: {delta_s1}   | S2: {delta_s2}   | S3: {delta_s3}")