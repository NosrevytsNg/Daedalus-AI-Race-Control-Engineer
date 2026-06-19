def suggest_pit_window(latest_lap_data, latest_car_damage, latest_tyre_sets):
    if latest_tyre_sets is None or latest_tyre_sets.fitted_set is None:
        return "--"

    fitted = latest_tyre_sets.fitted_set

    if latest_car_damage is not None:
        max_tyre_damage = max(latest_car_damage.tyre_damage)
        max_front_wing_damage = max(
            latest_car_damage.front_left_wing_damage,
            latest_car_damage.front_right_wing_damage,
        )

        if max_tyre_damage >= 80:
            return "BOX BOX - tyre damage critical"
        
        if max_front_wing_damage >= 70:
            return "BOX BOX - severe front wing damage"
        
        if max_front_wing_damage >= 30:
            return "BOX SOON - your front wing is damage"

    if fitted.wear >= 70:
        return "BOX SOON - tyre wear high"

    if fitted.life_span <= 2:
        return "PIT WINDOW OPEN - tyre life low"

    if fitted.wear >= 55:
        return "Monitor tyres - approaching pit window"

    return "Stay out"

def get_tyre_warnings(latest_car_damage, latest_tyre_sets):
    warnings = []

    if latest_car_damage is not None:
        max_wear = max(latest_car_damage.tyre_wear)
        max_damage = max(latest_car_damage.tyre_damage)

        if max_wear >= 50:
            warnings.append(
                f"Tyre wear high ({max_wear:.0f}%)"
            )

        if max_wear >= 70:
            warnings.append(
                f"Tyres approaching end of life ({max_wear:.0f}%)"
            )

        if max_damage >= 50:
            warnings.append(
                f"Tyre damage detected ({max_damage:.0f}%)"
            )

        if max_damage >= 80:
            warnings.append(
                "CRITICAL TYRE DAMAGE - BOX NOW"
            )

    return warnings


def get_fuel_warnings(latest_car_status):
    warnings = []

    if latest_car_status is None:
        return warnings

    fuel_laps = latest_car_status.fuel_remaining_laps

    if fuel_laps < 2:
        warnings.append(
            "Fuel critical"
        )

    elif fuel_laps < 5:
        warnings.append(
            "Fuel marginal"
        )

    return warnings


def get_ers_warnings(latest_car_status):
    warnings = []

    if latest_car_status is None:
        return warnings

    ers_pct = (
        latest_car_status.ers_store_energy
        / 4_000_000
    ) * 100

    if ers_pct < 10:
        warnings.append(
            "ERS critically low"
        )

    elif ers_pct < 25:
        warnings.append(
            "ERS low"
        )

    return warnings


def get_damage_alerts(latest_car_damage):
    alerts = []

    if latest_car_damage is None:
        return alerts

    if (
        latest_car_damage.front_left_wing_damage > 20
        or
        latest_car_damage.front_right_wing_damage > 20
    ):
        alerts.append(
            "Front wing damage"
        )

    if latest_car_damage.floor_damage > 20:
        alerts.append(
            "Floor damage"
        )

    if latest_car_damage.sidepod_damage > 20:
        alerts.append(
            "Sidepod damage"
        )

    if latest_car_damage.diffuser_damage > 20:
        alerts.append(
            "Diffuser damage"
        )

    return alerts


def get_weather_alerts(latest_session_data):
    alerts = []

    if latest_session_data is None:
        return alerts

    if not latest_session_data.weather_forecast_samples:
        return alerts

    nearest = latest_session_data.weather_forecast_samples[0]

    if nearest.rain_percentage >= 30:
        alerts.append(
            f"Rain possible in {nearest.time_offset} min"
        )

    if nearest.rain_percentage >= 60:
        alerts.append(
            f"Rain expected in {nearest.time_offset} min"
        )

    return alerts


def get_safety_car_alerts(latest_session_data):
    alerts = []

    if latest_session_data is None:
        return alerts

    status = latest_session_data.safety_car_status

    if status == 1:
        alerts.append(
            "Safety Car deployed"
        )

    elif status == 2:
        alerts.append(
            "Virtual Safety Car"
        )

    elif status == 3:
        alerts.append(
            "Formation Lap"
        )

    return alerts


def get_drs_alerts(
    latest_car_status,
    latest_car_damage,
):
    alerts = []

    if latest_car_status is None:
        return alerts

    if latest_car_status.drs_allowed:
        alerts.append(
            "DRS available"
        )

    if (
        latest_car_damage is not None
        and latest_car_damage.drs_fault
    ):
        alerts.append(
            "DRS fault"
        )

    return alerts

def config_engineer_messages(
    latest_car_status,
    latest_car_damage,
    latest_session_data,
    latest_tyre_sets,
):
    pit_advice = suggest_pit_window(
    None,
    latest_car_damage,
    latest_tyre_sets,
    )

    pit_messages = []

    if pit_advice != "Stay out" and pit_advice != "--":
        pit_messages.append(pit_advice)


    return {
        "tyre" : get_tyre_warnings(latest_car_damage, latest_tyre_sets),
        "fuel": get_fuel_warnings(latest_car_status),
        "ers": get_ers_warnings(latest_car_status),
        "damage": get_damage_alerts(latest_car_damage),
        "weather": get_weather_alerts(latest_session_data),
        "safety_car": get_safety_car_alerts(latest_session_data),
        "drs": get_drs_alerts(latest_car_status, latest_car_damage), 
        "pit": pit_messages,  
    }
#======================================================================================================
# Strats + Predictation Framework/Logic 
def config_strategy_advice(
        latest_lap_data,
        latest_car_status,
        latest_car_damage,
        latest_session_data,
        latest_tyre_sets,
):
    advice = []

    advice.extend(
        get_pit_timing_advice(
            latest_lap_data,
            latest_car_damage,
            latest_tyre_sets,
        )
    )

    advice.extend(
        get_tyre_choice_advice(
            latest_session_data,
            latest_tyre_sets,
        )
    )

    advice.extend(
        get_fuel_management_advice(
            latest_car_status,
        )
    )

    advice.extend(
        get_ers_deployment_advice(
            # latest_lap_data,
            latest_car_status,
        )
    )

    advice.extend(
        get_weather_tyre_advice(
            latest_session_data,
            latest_tyre_sets,
        )
    )

    advice.extend(
        get_undercut_overcut_advice(
            latest_lap_data,
            latest_tyre_sets,
        )
    )

    return advice

# Pit Timings and Schedule Logic
def get_pit_timing_advice(
    latest_lap_data,
    latest_car_damage,
    latest_tyre_sets,
):
    advice = []

    pit_advice = suggest_pit_window(
        latest_lap_data,
        latest_car_damage,
        latest_tyre_sets,
    )

    if pit_advice not in ("--", "Stay out"):
        advice.append(pit_advice)

    return advice

# Tyre Compound Helper Function
def get_compound_name(compound):
    compounds = {
        16: "Soft",
        17: "Medium",
        18: "Hard",
        7: "Intermediate",
        8: "Wet",
    }

    return compounds.get(compound, f"Unknown ({compound})")

# Tyre Strategy & Recommendations Logic
def get_tyre_choice_advice(
        latest_session_data,
        latest_tyre_sets,
):
    advice = []

    if latest_tyre_sets is None:
        return advice
    
    available_sets = [
        tyre_set for tyre_set in latest_tyre_sets.tyre_sets
        if tyre_set.available and not tyre_set.fitted
    ]

    if not available_sets:
        return advice
    
    dry_sets = [
        tyre_set for tyre_set in available_sets
        if tyre_set.visual_tyre_compound in (16, 17 ,18)
    ]

    wet_sets = [
        tyre_set for tyre_set in available_sets
        if tyre_set.visual_tyre_compound in (7 ,8)
    ]

    rain_expected = False
    
    if latest_session_data is not None:
        for sample in latest_session_data.weather_forecast_samples[:3]:
            if sample.rain_percentage >= 50 or sample.weather in (3, 4, 5):
                rain_expected = True
                break

    if rain_expected and wet_sets:
        best_wet = min(wet_sets, key=lambda tyre:tyre.wear)
        advice.append(
            f"Next Tyre Option: {get_compound_name(best_wet.visual_tyre_compound)}"
            f"({best_wet.wear}% wear)"
        )
        return advice

    if dry_sets:
        best_dry = min(dry_sets, key=lambda tyre: tyre.wear)
        advice.append(
            f"Next Tyre Option: {get_compound_name(best_dry.visual_tyre_compound)}"
            f"({best_dry.wear}% wear)"
        )
    
    return advice

# Fuel Management Logic
def get_fuel_management_advice(latest_car_status):
    advice = []

    if latest_car_status is None:
        return advice

    fuel_laps = latest_car_status.fuel_remaining_laps

    if fuel_laps < 0:
        advice.append(
            "Fuel deficit - lift and coast"
        )

    elif fuel_laps < 1:
        advice.append(
            "Fuel marginal - short shift and save fuel"
        )

    elif fuel_laps > 3:
        advice.append(
            "Fuel surplus - push if needed"
        )

    return advice        

# ERS Deployement Logic
def get_ers_deployment_advice(
    latest_car_status,
    # latest_lap_data,
):
    advice = []

    if latest_car_status is None:
        return advice

    ers_pct = (
        latest_car_status.ers_store_energy
        / 4_000_000
    ) * 100

    if ers_pct < 15:
        advice.append(
            "ERS low - harvest this lap"
        )

    elif ers_pct > 80:
        advice.append(
            "ERS high - deploy on straights"
        )

    return advice

# Rain, Wets & Inter Call Logic
def get_weather_tyre_advice(
    latest_session_data,
    latest_tyre_sets,
):
    advice = []

    if latest_session_data is None:
        return advice

    if not latest_session_data.weather_forecast_samples:
        return advice

    nearest = latest_session_data.weather_forecast_samples[0]

    if nearest.weather == 3:
        advice.append(
            f"Light rain expected in {nearest.time_offset} min - prepare intermediates"
        )

    elif nearest.weather in (4, 5):
        advice.append(
            f"Heavy rain expected in {nearest.time_offset} min - prepare wet tyres"
        )

    elif nearest.rain_percentage >= 60:
        advice.append(
            f"Rain risk high in {nearest.time_offset} min - monitor tyre crossover"
        )

    return advice

# Basic Undercut/Overcut Strat Calls
def get_undercut_overcut_advice(
    latest_lap_data,
    latest_tyre_sets,
):
    advice = []

    if latest_lap_data is None:
        return advice

    if latest_tyre_sets is None or latest_tyre_sets.fitted_set is None:
        return advice

    fitted = latest_tyre_sets.fitted_set

    if latest_lap_data.delta_to_car_in_front_ms is None:
        return advice

    gap_ahead_seconds = latest_lap_data.delta_to_car_in_front_ms / 1000

    if fitted.wear >= 55 and gap_ahead_seconds <= 3:
        advice.append(
            "Undercut possible - car ahead within range"
        )

    elif fitted.wear < 35 and gap_ahead_seconds <= 3:
        advice.append(
            "Overcut possible - tyres still healthy"
        )

    return advice

def analyze_driver_performance(
        latest_lap_data,
        latest_session_history,
):
    analysis = {"lap_comparison": None, 
                "sector_comparison": None, 
                "messages": []}
        
    if latest_lap_data is None and latest_session_history is None:
        return analysis
    
# Lap Comparison (Last vs Best)
    last_lap = latest_lap_data.lap_lap_time_ms
    best_lap = latest_session_history.best_lap_time_ms

    if last_lap is not None and best_lap is not None:
        if last_lap > 0 and best_lap > 0:
            lap_delta = last_lap - best_lap

            analysis["lap_comparison"] = {
                "last_lap": last_lap,
                "best_lap": best_lap,
                "lap_delta": lap_delta,
            }

            if lap_delta > 0:
                analysis["messages"].append(
                    f"Last lap was {lap_delta / 1000:.3f}s slower than your best"
                )

            elif lap_delta < 0:
                analysis["messages"].append(
                    f"Last lap was {lap_delta / 1000:.3f}s faster than your best"
                )

            else:
                analysis["messages"].append(
                    f"👍"
                )

# Sector Comparison (Current vs Best)    