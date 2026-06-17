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

