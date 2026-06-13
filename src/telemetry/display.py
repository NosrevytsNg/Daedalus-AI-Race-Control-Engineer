import os

from src.telemetry.parser import format_time_ms

# # Clear the console  
def clear_terminal(): 
    print("\033c", end="")

def display_live_telemetry(latest_telemetry, latest_lap_data):
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
        print(f"Sector:    {latest_lap_data.sector+1}")
        print(f"Lap Time:  {format_time_ms(latest_lap_data.current_lap_time_ms)}")
        print(f"Last Lap:  {format_time_ms(latest_lap_data.last_lap_time_ms)}")
        print(f"Gap Ahead: {latest_lap_data.delta_to_car_in_front_ms / 1000:.3f}s")
        print(f"Gap Leader: {latest_lap_data.delta_to_race_leader_ms / 1000:.3f}s")

    else:
        print()
        print("No lap data available yet.")

