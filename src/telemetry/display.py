import os

from src.telemetry.parser import format_time_ms
from src.engineer.race_engineer import config_engineer_messages, suggest_pit_window, config_strategy_advice, analyze_driver_performance, generate_driver_coaching, prepare_delivery_messages, get_radio_queue_size
from src.voice.tts import speak_radio_message

# Clear the console  
def clear_terminal(): 
    print("\033c", end="")

# ==================================================================================================================================================================================================================================================================
# HELPER FUNCTION
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

# Assign type compound with key
def format_tyre_compound(compound):
    compounds = {
        16: "Soft",
        17: "Medium",
        18: "Hard",
        7: "Intermediate",
        8: "Wet",
    }

    return compounds.get(compound, f"Unknown ({compound})")

# Assign ERS mode with key
def format_ers_mode(mode):
    modes = {
        0: "None",
        1: "Medium",
        2: "Hotlap",
        3: "Overtake",
    }

    return modes.get(mode, f"Unknown ({mode})")

# Assign function for ERS storage energy level
def format_ers_percentage(ers_energy_storage):
    if ers_energy_storage is None:
        return "--"

    ers_percentage = (ers_energy_storage / 4_000_000) * 100
    return f"{ers_percentage:.0f}%"

def format_weather(weather):
    weather_map = {
        0: "Clear",
        1: "Light Cloud",
        2: "Overcast",
        3: "Light Rain",
        4: "Heavy Rain",
        5: "Storm",
    }

    return weather_map.get(weather, f"Unknown ({weather})")


def format_session_type(session_type):
    session_map = {
        0: "Unknown",
        1: "Practice 1",
        2: "Practice 2",
        3: "Practice 3",
        4: "Short Practice",
        5: "Qualifying 1",
        6: "Qualifying 2",
        7: "Qualifying 3",
        8: "Short Qualifying",
        9: "One-Shot Qualifying",
        10: "Race",
        11: "Race 2",
        12: "Race 3",
        13: "Time Trial",
        15: "F1 World Grand Prix",
    }

    return session_map.get(session_type, f"Unknown ({session_type})")


def format_safety_car_status(status):
    safety_car_map = {
        0: "None",
        1: "Full Safety Car",
        2: "Virtual Safety Car",
        3: "Formation Lap",
    }

    return safety_car_map.get(status, f"Unknown ({status})")


def format_duration(seconds):
    if seconds is None or seconds < 0:
        return "--"

    minutes = seconds // 60
    remaining_seconds = seconds % 60

    return f"{minutes:02d}:{remaining_seconds:02d}"

def is_race_session(session_type):
    race_sessions = {
        10,  # Race
        11,  # Race 2
        12,  # Race 3
        15,  # F1 World Grand Prix
    }

    return session_type in race_sessions


def is_timed_session(session_type):
    timed_sessions = {
        1,  # Practice 1
        2,  # Practice 2
        3,  # Practice 3
        4,  # Short Practice
        5,  # Qualifying 1
        6,  # Qualifying 2
        7,  # Qualifying 3
        8,  # Short Qualifying
        9,  # One-Shot Qualifying
        13,  # Time Trial
    }

    return session_type in timed_sessions

# For engine condition (blown/seized)
def format_fault(status):
    return "Yes" if status else "No"

# Damage %
def format_percent(value):
    if value is None:
        return "--"

    return f"{value:.0f}%"

def format_forecast_accuracy(accuracy):
    accuracy_map = {
        0: "Perfect",
        1: "Approximate",
    }

    return accuracy_map.get(accuracy, f"Unknown ({accuracy})")


def get_nearest_weather_forecast(session_data):
    if session_data is None:
        return None

    if not session_data.weather_forecast_samples:
        return None

    return session_data.weather_forecast_samples[0]

# ==================================================================================================================================================================================================================================================================
# LIVE Dashboard Function
def display_live_telemetry(latest_telemetry, 
                           latest_lap_data, 
                           latest_session_history, 
                           latest_completed_lap_sectors, 
                           latest_car_status,
                           latest_session_data,
                           latest_car_damage,
                           latest_tyre_sets,
                           ):
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

#========================================================================================

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

#========================================================================================

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

#========================================================================================

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

#========================================================================================
    
    print()
    print("----------------------------------------------------")
    print("CAR STATUS")
    print("----------------------------------------------------")

    if latest_car_status is not None:
        print(f"Fuel:        {latest_car_status.fuel_remaining_laps:+.2f} laps")
        print(f"Fuel Tank:   {latest_car_status.fuel_in_tank:.2f} kg")
        
        print(f"ERS:         {format_ers_percentage(latest_car_status.ers_energy_storage)}")
        print(f"ERS Mode:    {format_ers_mode(latest_car_status.ers_deploy_mode)}")
        
        print(f"DRS Allowed: {'Yes' if latest_car_status.drs_allowed else 'No'}")
        print(f"Pit Limiter: {'On' if latest_car_status.pit_limiter_status else 'Off'}")

        print(f"Compound:    {format_tyre_compound(latest_car_status.visual_tyre_compound)}")
        print(f"Tyre Age:    {latest_car_status.tyres_age_laps} laps")
    else:   
        print("Fuel:        --")
        print("Fuel Tank:   --")
        
        print("ERS:         --")
        print("ERS Mode:    --")
        
        print("DRS Allowed: --")
        print("Pit Limiter: --")

        print("Compound:    --")
        print("Tyre Age:    --")

    print()
    print("----------------------------------------------------")
    print("VEHICLE HEALTH")
    print("----------------------------------------------------")

    if latest_car_damage is not None:
        brake_damage = latest_car_damage.brake_damage
        print(
            "Brake Damage:"
            f" FL {format_percent(brake_damage[2])} | "
            f"FR {format_percent(brake_damage[3])} | "
            f"RL {format_percent(brake_damage[0])} | "
            f"RR {format_percent(brake_damage[1])}"
        )

        print()
        print(
            f"Front Wing:  L {format_percent(latest_car_damage.front_left_wing_damage)} | "
            f"R {format_percent(latest_car_damage.front_right_wing_damage)}"
        )
        print(f"Rear Wing:   {format_percent(latest_car_damage.rear_wing_damage)}")
        print()
        print(f"Floor:       {format_percent(latest_car_damage.floor_damage)}")
        print(f"Sidepod:     {format_percent(latest_car_damage.sidepod_damage)}")
        print(f"Diffuser:    {format_percent(latest_car_damage.diffuser_damage)}")
        print()
        print(f"DRS Fault:   {format_fault(latest_car_damage.drs_fault)}")
        print(f"ERS Fault:   {format_fault(latest_car_damage.ers_fault)}")
        print(f"Gearbox:     {format_percent(latest_car_damage.gearbox_damage)}")
        print(f"Engine:      {format_percent(latest_car_damage.engine_damage)}")
    else:
        print("Tyre Wear:   --")
        print("Tyre Damage: --")
        print("Brake Damage:--")
        print()
        print("Front Wing:  --")
        print("Rear Wing:   --")
        print("Floor:       --")
        print("Sidepod:     --")
        print("Diffuser:    --")
        print()
        print("DRS Fault:   --")
        print("ERS Fault:   --")
        print("Gearbox:     --")
        print("Engine:      --")

#========================================================================================
    print()
    print("----------------------------------------------------")
    print("SESSION")
    print("----------------------------------------------------")
    #print()

    nearest_forecast = get_nearest_weather_forecast(latest_session_data)

    if latest_session_data is not None:
        print(f"Session:     {format_session_type(latest_session_data.session_type)}")
        print(f"Weather:     {format_weather(latest_session_data.weather)}")
        print(f"Track Temp:  {latest_session_data.track_temperature}°C")
        print(f"Air Temp:    {latest_session_data.air_temperature}°C")
        print(f"Total Dist:  {latest_session_data.track_length} m")
        print()
        if is_race_session(latest_session_data.session_type):
            print(f"Total Laps:  {latest_session_data.total_laps}")
        elif is_timed_session(latest_session_data.session_type):
            print(f"Time Left:   {format_duration(latest_session_data.session_time_left)}")
        else:
            print("Time Left:   --")

        print(f"Safety Car:  {format_safety_car_status(latest_session_data.safety_car_status)}")
        print()
        if nearest_forecast is not None:
            print(
                f"Forecast:    {format_weather(nearest_forecast.weather)} "
                f"in {nearest_forecast.time_offset} min"
            )
            print(f"Rain Chance: {nearest_forecast.rain_percentage}%")
            print(
                f"Forecast:    {format_forecast_accuracy(latest_session_data.forecast_accuracy)}"
            )
        else:
            print("Forecast:    --")
            print("Rain Chance: --")

    else:
        print("Session:     --")
        print("Weather:     --")
        print("Track Temp:  --")
        print("Air Temp:    --")
        print("Total Dist:  --")
        print("Time Left:   --")
        print("Safety Car:  --")

#========================================================================================
    print()
    print("----------------------------------------------------")
    print("TYRE INTELLIGENCE")
    print("----------------------------------------------------")

    if latest_tyre_sets is not None and latest_tyre_sets.fitted_set is not None:
        fitted = latest_tyre_sets.fitted_set

        print(f"Current Set: {format_tyre_compound(fitted.visual_tyre_compound)}")
        print(f"Set Index:   {latest_tyre_sets.fitted_idx}")
        print(f"Set Wear:    {fitted.wear}%")
        print(f"Life Span:   {fitted.life_span} laps")
        print(f"Usable Life: {fitted.usable_life} laps")
        print()

        if latest_car_damage is not None:
            tyre_wear = latest_car_damage.tyre_wear
            tyre_damage = latest_car_damage.tyre_damage

        print(
            "Tyre Wear:   "
            f"FL {format_percent(tyre_wear[2])} | "
            f"FR {format_percent(tyre_wear[3])} | "
            f"RL {format_percent(tyre_wear[0])} | "
            f"RR {format_percent(tyre_wear[1])}"
        )

        print(
            "Tyre Damage: "
            f"FL {format_percent(tyre_damage[2])} | "
            f"FR {format_percent(tyre_damage[3])} | "
            f"RL {format_percent(tyre_damage[0])} | "
            f"RR {format_percent(tyre_damage[1])}"
        )

        print()
        print("Available Sets:")

        for i, tyre_set in enumerate(latest_tyre_sets.tyre_sets):
            if tyre_set.available:
                fitted_marker = " <- fitted" if i == latest_tyre_sets.fitted_idx else ""
                print(
                    f"[{i:02}] "
                    f"{format_tyre_compound(tyre_set.visual_tyre_compound):<13} "
                    f"Wear {tyre_set.wear:>3}% | "
                    f"Life {tyre_set.life_span:>2} | "
                    f"Usable {tyre_set.usable_life:>2}"
                    f"{fitted_marker}"
                )
    else:
        print("Current Set: --")
        print("Available Sets: --")
    print()
    print(f"Pit Advice:  {suggest_pit_window(latest_lap_data, latest_car_damage, latest_tyre_sets)}")

    engineer_messages = config_engineer_messages(
        latest_car_status,
        latest_car_damage,
        latest_session_data,
        latest_tyre_sets,
    )

    print()
    print("----------------------------------------------------")
    print("RACE ENGINEER")
    print("----------------------------------------------------")

    # has_messages = False

    # for category, messages in engineer_messages.items():
    #     for message in messages:
    #         if message != "--":
    #             print(f"{message}")
    #             has_messages = True

    # if not has_messages:
    #     print("All systems stable")

    if engineer_messages:
        for message in engineer_messages:
            print(
                f"[{message['priority']}] "
                f"({message['context']}) "
                f"{message['text']}"
            )
    else:
        print("All systems stable")

    # delivery_messages = prepare_delivery_messages(engineer_messages)

    # print()
    # print("----------------------------------------------------")
    # print("RADIO DELIVERY DEBUG")
    # print("----------------------------------------------------")

    # if delivery_messages:
    #     for message in delivery_messages:
    #         print(
    #             f"[{message['priority']}] "
    #             f"({message['delivery_group']}) "
    #             f"{message['text']}"
    #         )

    #         speak_radio_message(message["text"])
    # else:
    #     print("No new radio messages")

    # print(f"Radio Queue: {get_radio_queue_size()} pending")       

    # strategy_advice = config_strategy_advice(
    #     latest_lap_data,
    #     latest_car_status,
    #     latest_car_damage,
    #     latest_session_data,
    #     latest_tyre_sets,
    # )

    # print()
    # print("----------------------------------------------------")
    # print("STRATEGY ADVISOR")
    # print("----------------------------------------------------")

    # if strategy_advice:
    #     for message in strategy_advice:
    #         print(f"- {message}")
    # else:
    #     print("No strategic action required")
        
        
#========================================================================================
    performance_analysis = analyze_driver_performance(
        latest_lap_data,
        latest_session_history,
        latest_car_damage,
        latest_session_data,
        latest_completed_lap_sectors,
    )

    sector_trend = performance_analysis.get("sector_trend")

    print()
    print("----------------------------------------------------")
    print("PERFORMANCE ANALYSIS")
    print("----------------------------------------------------")

    if performance_analysis["message"]:
        for message in performance_analysis["message"]:
            print(f"- {message}")
    else:
        print("Not enough lap data yet")

    

    print()
    print("----------------------------------------------------")
    print("RACE SECTOR TREND")
    print("----------------------------------------------------")

    if sector_trend is None:
        print("No sector trend data yet")

    elif not sector_trend.get("enabled"):
        print(sector_trend.get("reason"))

    elif not sector_trend.get("ready"):
        print(sector_trend.get("reason"))
        print(f"Clean sector history: {sector_trend.get('history_count')}/5")

    else:
        reference = sector_trend.get("reference")
        current = sector_trend.get("current")
        deltas = sector_trend.get("deltas")

        print(f"Reason: {sector_trend.get('reason')}")
        print(f"Clean sector history: {sector_trend.get('history_count')}/5")

        print()
        print("                     S1         S2         S3")
        print("----------------------------------------------------")
        print(
            f"Average Sector   "
            f"{format_time_ms_with_placeholder(reference['AS1']):<10} "
            f"{format_time_ms_with_placeholder(reference['AS2']):<10} "
            f"{format_time_ms_with_placeholder(reference['AS3']):<10}"
        )
        print(
            f"Current Sector   "
            f"{format_time_ms_with_placeholder(current['sector_1_time_ms']):<10} "
            f"{format_time_ms_with_placeholder(current['sector_2_time_ms']):<10} "
            f"{format_time_ms_with_placeholder(current['sector_3_time_ms']):<10}"
        )
        print(
            f"Delta vs AS      "
            f"{format_delta(deltas['D1']):<10} "
            f"{format_delta(deltas['D2']):<10} "
            f"{format_delta(deltas['D3']):<10}"
        )
        print(
            f"STD              "
            f"{format_sector_time(reference['STD1']):<10} "
            f"{format_sector_time(reference['STD2']):<10} "
            f"{format_sector_time(reference['STD3']):<10}"
        )
        print(
            f"Range            "
            f"{format_sector_time(reference['range1']):<10} "
            f"{format_sector_time(reference['range2']):<10} "
            f"{format_sector_time(reference['range3']):<10}"
        )

        print()
        for message in sector_trend.get("messages", []):
            print(f"- {message}")

#========================================================================================

    coaching_messages = generate_driver_coaching(
        performance_analysis,
        latest_lap_data,
        latest_session_history,
        latest_car_damage,
        latest_session_data,
        latest_car_damage,
        latest_tyre_sets,
    )

    print()
    print("----------------------------------------------------")
    print("DRIVER COACHING")
    print("----------------------------------------------------")

    if coaching_messages:
        for message in coaching_messages:
            print(
                f"[{message['priority']}] "
                f"({message['context']}) "
                f"{message['text']}"
            )
    else:
        print("No coaching advice yet")

    radio_candidates = engineer_messages + coaching_messages

    delivery_messages = prepare_delivery_messages(radio_candidates)

    print()
    print("----------------------------------------------------")
    print("RADIO DELIVERY DEBUG")
    print("----------------------------------------------------")

    if delivery_messages:
        for message in delivery_messages:
            print(
                f"[{message['priority']}] "
                f"({message['delivery_group']}) "
                f"{message['text']}"
            )

            speak_radio_message(message["text"])
    else:
        print("No new radio messages")

    print(f"Radio Queue: {get_radio_queue_size()} pending")









































































































































