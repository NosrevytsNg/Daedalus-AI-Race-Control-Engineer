import struct
from dataclasses import dataclass

# ==================================================================================
# Convert raw UDP byte packets from F1 25 into readable Python dataclasses.
# Decode only the packet types currently needed by Daedalus.
# Select the player's car data using player_car_index when packets contain all cars.
# ==================================================================================

# Python struct terms:

# < means Little Endian
# H means unsigned short (2 bytes = uint16)
# h means signed short (2 bytes = int16)
# B means unsigned char (1 bytes = uint8)
# b means signed char (1 bytes = int8)
# Q means unsigned long long (8 bytes = uint64)
# f means floating-point num (4 bytes = float)
# I means unsigned int (4 bytes = uint 32)
# "<HBBBBBQfIIBB" = H B B B B B Q f I I B B
# 1 uint16 -> 5 uint8 -> 1 uint64 -> 1 float -> 2 unint32 -> 2 uint8

# struct PacketHeader
# {
#   uint16 m_packetFormat;                       2025  
#   uint8  m_gameYear;                           Game Year = Last 2 Digits
#   uint8  m_gameMajorVersion;                   Major Version = "X.00"
#   uint8  m_gameMinorVersion;                   Minor Version = "1.XX"
#   uint8  m_packetVersion;                      Starts from 1
#   uint8  m_packetId;                           ** Packet Type Identifier ** [IMPORTANT]
#   uint64 m_sessionUID;                         Unique Session Identifier
#   float  m_sessionTime;                        Session Timestamp
#   uint32 m_frameIdentifier;                    Identifier for frame the data was retrieved on
#   uint32 m_overallFrameIdentifier;             Overall identifier for frame the data was retrieved on
#   uint8  m_playerCarIndex;                     Index of Player's Car in array 
#   uint8  m_secondaryPlayerCarIndex;            Index of Secondary Player's Car in array (Splitscreen)
# }

HEADER_FORMAT = "<HBBBBBQfIIBB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def parse_header(data_packet_bytes):

    # If the packet received is smaller than the header size, return None
    # Keeps the parser from crashing when receiving incomplete packets during struct.unpack_from().
    if len(data_packet_bytes) < HEADER_SIZE:
        return None

    values = struct.unpack_from(HEADER_FORMAT, data_packet_bytes, 0)
    # Obtain the header values from the packet using struct.unpack_from() with the defined HEADER_FORMAT.
    # Decode data_packet_bytes into a dictionary starting at offset 0, the beginning of the packet.     

    return {
        "packet_format": values[0],
        "game_year": values[1],
        "game_major_version": values[2],
        "game_minor_version": values[3],
        "packet_version": values[4],
        "packet_id": values[5],
        "session_uid": values[6],
        "session_time": values[7],
        "frame_identifier": values[8],
        "overall_frame_identifier": values[9],
        "player_car_index": values[10],
        "secondary_player_car_index": values[11],
    }



# ================================================================
# Car Telemetry Packet (Packet ID 6)

CAR_TELEMETRY_FORMAT = "<HfffBbHBBH4H4B4BH4f4B"
CAR_TELEMETRY_SIZE = struct.calcsize(CAR_TELEMETRY_FORMAT)

@dataclass
class CarTelemetry:
    speed: int
    throttle: float
    brake: float
    gear: int
    rpm: int
    drs: bool


def parse_car_telemetry(data, player_car_index):
    telemetry_start = HEADER_SIZE
    car_offset = telemetry_start + (player_car_index * CAR_TELEMETRY_SIZE)

    if len(data) < car_offset + CAR_TELEMETRY_SIZE:
        return None

    values = struct.unpack_from(CAR_TELEMETRY_FORMAT, data, car_offset)

    return CarTelemetry(
        speed=values[0],
        throttle=values[1],
        brake=values[3],
        gear=values[5],
        rpm=values[6],
        drs=bool(values[7]),
    )

# ================================================================
# Lap Data Packet (Packet ID 2)

@dataclass
class LapData:
    last_lap_time_ms: int
    current_lap_time_ms: int
    car_position: int
    current_lap_num: int
    sector: int
    delta_to_car_in_front_ms: int
    delta_to_race_leader_ms: int
    sector_1_time_ms: int 
    sector_2_time_ms: int

# Change LAP_DATA_FORMAT = "<IIHBHBHBHfffBBBBBBBBBBHBBHBB" -> "<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB"
LAP_DATA_FORMAT = "<IIHBHBHBHBfffBBBBBBBBBBBBBBBHHBfB"
LAP_DATA_SIZE = struct.calcsize(LAP_DATA_FORMAT)


def parse_lap_data(data, player_car_index):
    lap_data_start = HEADER_SIZE
    car_offset = lap_data_start + (player_car_index * LAP_DATA_SIZE)

    if len(data) < car_offset + LAP_DATA_SIZE:
        return None

    values = struct.unpack_from(LAP_DATA_FORMAT, data, car_offset)

    delta_to_car_in_front_ms = (values[7] * 60000) + values[6]
    delta_to_race_leader_ms = (values[9] * 60000) + values[8]

    return LapData(
        last_lap_time_ms=values[0],
        current_lap_time_ms=values[1],
        car_position=values[13],
        current_lap_num=values[14],
        sector=values[17],
        delta_to_car_in_front_ms=delta_to_car_in_front_ms,
        delta_to_race_leader_ms=delta_to_race_leader_ms,
        sector_1_time_ms=(values[3] * 60000) + (values[2]),
        sector_2_time_ms=(values[5] * 60000) + (values[4]),
    )


def format_time_ms(milliseconds):
    if milliseconds <= 0:
        return "--"

    minutes = milliseconds // 60000
    seconds = (milliseconds % 60000) / 1000

    return f"{minutes}:{seconds:06.3f}"


# ================================================================
# Session History Packet (Packet ID 11)
# Used for Best Lap and Sector Times in the current session.
# class [SessionHistory] & class [CompletedLapSectorTiming]

@dataclass
class SessionHistory:
    best_lap_num: int
    best_lap_time_ms: int
    best_sector1_time_ms: int
    best_sector2_time_ms: int
    best_sector3_time_ms: int

SESSION_HISTORY_HEADER_FORMAT = "<BBBBBBB"
SESSION_HISTORY_HEADER_SIZE = struct.calcsize(SESSION_HISTORY_HEADER_FORMAT)

LAP_HISTORY_FORMAT = "<IHBHBHBB"
LAP_HISTORY_SIZE = struct.calcsize(LAP_HISTORY_FORMAT)

def combine_session_time(milliseconds, minutes):
    return (minutes * 60000) + milliseconds

def parse_session_history(data, player_car_index):
    session_history_start = HEADER_SIZE

    if len(data) < session_history_start + SESSION_HISTORY_HEADER_SIZE:
        return None
    
    values = struct.unpack_from(
        SESSION_HISTORY_HEADER_FORMAT, data, session_history_start)
    
    car_idx = values[0]
    num_laps = values[1]
    best_lap_time_lap_num = values[3]
    best_sector_1_lap_num = values[4]
    best_sector_2_lap_num = values[5]   
    best_sector_3_lap_num = values[6]

    if car_idx != player_car_index:
        return None
    
    lap_history_start = session_history_start + SESSION_HISTORY_HEADER_SIZE

    def get_lap_history(lap_num):
        if lap_num == 0 or lap_num > num_laps:
            return None
        
        lap_index = lap_num - 1

        if lap_index >= num_laps:
            return None
        
        lap_offset = lap_history_start + (lap_index * LAP_HISTORY_SIZE)

        if len(data) < lap_offset + LAP_HISTORY_SIZE:
            return None
        
        return struct.unpack_from(LAP_HISTORY_FORMAT, data, lap_offset)
        
    best_lap = get_lap_history(best_lap_time_lap_num)
    best_sector_1_lap = get_lap_history(best_sector_1_lap_num)
    best_sector_2_lap = get_lap_history(best_sector_2_lap_num)
    best_sector_3_lap = get_lap_history(best_sector_3_lap_num)

    if best_lap is None:
        return None
    
    best_sector_1_ms = 0
    best_sector_2_ms = 0
    best_sector_3_ms = 0

    if best_sector_1_lap is not None:
        best_sector_1_ms = combine_session_time(
            best_sector_1_lap[1], best_sector_1_lap[2])
        
    if best_sector_2_lap is not None:
        best_sector_2_ms = combine_session_time(
            best_sector_2_lap[3], best_sector_2_lap[4])
        
    if best_sector_3_lap is not None:
        best_sector_3_ms = combine_session_time(
            best_sector_3_lap[5], best_sector_3_lap[6])
        
    return SessionHistory(
        best_lap_num=best_lap_time_lap_num,
        best_lap_time_ms=best_lap[0],
        best_sector1_time_ms=best_sector_1_ms,
        best_sector2_time_ms=best_sector_2_ms,
        best_sector3_time_ms=best_sector_3_ms,
    )

@dataclass
class CompletedLapSectorTiming:
    lap_num: int
    sector_1_time_ms: int
    sector_2_time_ms: int
    sector_3_time_ms: int

# ================================================================
# Car Status Packet (Packet ID 7) & Car Damage Packet (Packet ID 10)
# For vehicle condition and equipment info   
@dataclass
class CarStatus:
    fuel_in_tank: float
    fuel_capacity: float
    fuel_remaining_laps: float
    drs_allowed: bool
    drs_activation_distance: int
    actual_tyre_compound: int
    visual_tyre_compound: int
    tyres_age_laps: int
    ers_energy_storage: float
    ers_deploy_mode: int
    pit_limiter_status: bool 

CAR_STATUS_FORMAT = "<BBBBBfffHHBBHBBBbfffBfffB" #"<BBBBBfffHHBBHBBBbffBfffB"
CAR_STATUS_SIZE = struct.calcsize(CAR_STATUS_FORMAT)

ERS_MAX_ENERGY = 4_000_000

def parse_car_status(data, player_car_index):
    car_status_start = HEADER_SIZE
    car_offset = car_status_start + (player_car_index * CAR_STATUS_SIZE)

    if len(data) < car_offset + CAR_STATUS_SIZE:
        return None

    values = struct.unpack_from(CAR_STATUS_FORMAT, data, car_offset)

    return CarStatus(
        fuel_in_tank=values[5],
        fuel_capacity=values[6],
        fuel_remaining_laps=values[7],
        pit_limiter_status=bool(values[4]),
        drs_allowed=bool(values[11]),
        drs_activation_distance=values[12],
        actual_tyre_compound=values[13],
        visual_tyre_compound=values[14],
        tyres_age_laps=values[15],
        ers_energy_storage=values[19],
        ers_deploy_mode=values[20],
    )

# For component status and damage info 
@dataclass
class CarDamage:
    tyre_wear: list
    tyre_damage: list
    brake_damage: list
    front_left_wing_damage: int
    front_right_wing_damage: int
    rear_wing_damage: int
    floor_damage: int
    diffuser_damage: int
    sidepod_damage: int
    drs_fault: bool
    ers_fault: bool
    gearbox_damage: int
    engine_damage: int

CAR_DAMAGE_FORMAT = "<4f4B4B4B6B2B2B6B2B" #"<4f4B4B4B6B2B2B6B2B" / "<4f4B4B7B2B3B4B" / "<4f4B4B6B2B2B6B2B"
CAR_DAMAGE_SIZE = struct.calcsize(CAR_DAMAGE_FORMAT)

# CAR_DAMAGE_FIELDS = [
#     "tyres_wear_rl",
#     "tyres_wear_rr",
#     "tyres_wear_fl",
#     "tyres_wear_fr",

#     "tyres_damage_rl",
#     "tyres_damage_rr",
#     "tyres_damage_fl",
#     "tyres_damage_fr",

#     "brakes_damage_rl",
#     "brakes_damage_rr",
#     "brakes_damage_fl",
#     "brakes_damage_fr",

#     "tyre_blisters_rl",
#     "tyre_blisters_rr",
#     "tyre_blisters_fl",
#     "tyre_blisters_fr",

#     "front_left_wing_damage",
#     "front_right_wing_damage",
#     "rear_wing_damage",
#     "floor_damage",
#     "diffuser_damage",
#     "sidepod_damage",

#     "drs_fault",
#     "ers_fault",

#     "gearbox_damage",
#     "engine_damage",

#     "engine_mguh_wear",
#     "engine_es_wear",
#     "engine_ce_wear",
#     "engine_ice_wear",
#     "engine_mguk_wear",
#     "engine_tc_wear",

#     "engine_blown",
#     "engine_seized",
# ]

# def parse_packet_10_player_car(data, player_car_index):
#     offset = HEADER_SIZE + (player_car_index * CAR_DAMAGE_SIZE)
#     values = struct.unpack_from(CAR_DAMAGE_FORMAT, data, offset)
#     return values

# def debug_print_packet_10(values):
#     print("\n=== Packet 10 Car Damage Debug ===")

#     for i, (name, value) in enumerate(zip(CAR_DAMAGE_FIELDS, values)):
#         if isinstance(value, float):
#             print(f"[{i:02}] {name:<28} = {value:.2f}")
#         else:
#             print(f"[{i:02}] {name:<28} = {value}")

#     print("=" * 50)


def parse_car_damage(data, player_car_index):
    car_damage_start = HEADER_SIZE
    car_offset = car_damage_start + (player_car_index * CAR_DAMAGE_SIZE)

    if len(data) < car_offset + CAR_DAMAGE_SIZE:
        return None

    values = struct.unpack_from(CAR_DAMAGE_FORMAT, data, car_offset)

    # print()
    # print("=== CAR DAMAGE RAW VALUES ===")
    # print(values)
    # print()

    return CarDamage(
        tyre_wear=list(values[0:4]),
        tyre_damage=list(values[4:8]),
        brake_damage=list(values[8:12]),

        front_left_wing_damage=values[16],
        front_right_wing_damage=values[17],
        rear_wing_damage=values[18],
        floor_damage=values[19],
        diffuser_damage=values[20],
        sidepod_damage=values[21],

        drs_fault=bool(values[22]),
        ers_fault=bool(values[23]),

        gearbox_damage=values[24],
        engine_damage=values[25],
    )

# ================================================================
# Session Info Packet (Packet ID 1)
# Weather and Track Info
@dataclass
class SessionData:
    weather: int
    track_temperature: int
    air_temperature: int
    total_laps: int
    track_length: int
    session_type: int
    track_id: int
    session_time_left: int
    session_duration: int
    pit_speed_limit: int
    safety_car_status: int
    weather_forecast_samples: list
    forecast_accuracy: int
    
                       
SESSION_DATA_FORMAT = "<BbbBHBbBHHBBBBBB" # "<BbbBHBbBHBBBBBBBHBB"
SESSION_DATA_SIZE = struct.calcsize(SESSION_DATA_FORMAT)

MARSHAL_ZONE_SIZE = struct.calcsize("<fb")
MAX_MARSHAL_ZONES = 21


def parse_session_data(data):
    session_data_start = HEADER_SIZE

    if len(data) < session_data_start + SESSION_DATA_SIZE:
        return None

    values = struct.unpack_from(
        SESSION_DATA_FORMAT,
        data,
        session_data_start
    )

    marshal_zones_start = session_data_start + SESSION_DATA_SIZE
    safety_car_offset = marshal_zones_start + (MAX_MARSHAL_ZONES * MARSHAL_ZONE_SIZE)

    if len(data) < safety_car_offset + 1:
        safety_car_status = 0
    else:
        safety_car_status = struct.unpack_from("<B", data, safety_car_offset)[0]

        network_game_offset = safety_car_offset + 1
        num_weather_samples_offset = network_game_offset + 1

    if len(data) < num_weather_samples_offset + 1:
        num_weather_forecast_samples = 0
    else:
        num_weather_forecast_samples = struct.unpack_from(
            "<B",
            data,
            num_weather_samples_offset
        )[0]

    weather_forecast_samples = []

    weather_samples_start = num_weather_samples_offset + 1

    samples_to_parse = min(
        num_weather_forecast_samples,
        MAX_WEATHER_FORECAST_SAMPLES
    )

    for i in range(samples_to_parse):
        offset = weather_samples_start + (i * WEATHER_FORECAST_SAMPLE_SIZE)

        if len(data) < offset + WEATHER_FORECAST_SAMPLE_SIZE:
            break

        sample_values = struct.unpack_from(
            WEATHER_FORECAST_SAMPLE_FORMAT,
            data,
            offset
        )

        weather_forecast_samples.append(
            WeatherForecastSample(
                session_type=sample_values[0],
                time_offset=sample_values[1],
                weather=sample_values[2],
                track_temperature=sample_values[3],
                track_temperature_change=sample_values[4],
                air_temperature=sample_values[5],
                air_temperature_change=sample_values[6],
                rain_percentage=sample_values[7],
            )
        )

    forecast_accuracy_offset = weather_samples_start + (
        MAX_WEATHER_FORECAST_SAMPLES * WEATHER_FORECAST_SAMPLE_SIZE
    )

    if len(data) < forecast_accuracy_offset + 1:
        forecast_accuracy = 0
    else:
        forecast_accuracy = struct.unpack_from(
            "<B",
            data,
            forecast_accuracy_offset
        )[0]    


    return SessionData(
        weather=values[0],
        track_temperature=values[1],
        air_temperature=values[2],
        total_laps=values[3],
        track_length=values[4],
        session_type=values[5],
        track_id=values[6],
        session_time_left=values[9],
        session_duration=values[10],
        pit_speed_limit=values[14],
        safety_car_status=safety_car_status,
        weather_forecast_samples=weather_forecast_samples,
        forecast_accuracy=forecast_accuracy,
    )

@dataclass
class WeatherForecastSample:
    session_type: int
    time_offset: int
    weather: int
    track_temperature: int
    track_temperature_change: int
    air_temperature: int
    air_temperature_change: int
    rain_percentage: int

WEATHER_FORECAST_SAMPLE_FORMAT = "<BBBbbbbB"
WEATHER_FORECAST_SAMPLE_SIZE = struct.calcsize(WEATHER_FORECAST_SAMPLE_FORMAT)
MAX_WEATHER_FORECAST_SAMPLES = 64

# ================================================================
# Tyre Set Packet (Packet ID 12)

@dataclass
class TyreSet:
    actual_tyre_compound: int
    visual_tyre_compound: int
    wear: int
    available: bool
    recommended_session: int
    life_span: int
    usable_life: int
    lap_delta_time: int
    fitted: bool


@dataclass
class TyreSets:
    car_idx: int
    fitted_idx: int
    tyre_sets: list
    fitted_set: TyreSet | None
    available_sets: list


TYRE_SET_FORMAT = "<BBBBBBBhB"
TYRE_SET_SIZE = struct.calcsize(TYRE_SET_FORMAT)

TYRE_SETS_COUNT = 20
TYRE_SETS_PACKET_SIZE = HEADER_SIZE + 1 + (TYRE_SET_SIZE * TYRE_SETS_COUNT) + 1


def parse_tyre_sets(data, player_car_index):
    tyre_sets_start = HEADER_SIZE

    if len(data) < TYRE_SETS_PACKET_SIZE:
        return None

    car_idx = struct.unpack_from("<B", data, tyre_sets_start)[0]

    if car_idx != player_car_index:
        return None

    tyre_sets = []
    tyre_data_start = tyre_sets_start + 1

    for i in range(TYRE_SETS_COUNT):
        offset = tyre_data_start + (i * TYRE_SET_SIZE)
        values = struct.unpack_from(TYRE_SET_FORMAT, data, offset)

        tyre_set = TyreSet(
            actual_tyre_compound=values[0],
            visual_tyre_compound=values[1],
            wear=values[2],
            available=bool(values[3]),
            recommended_session=values[4],
            life_span=values[5],
            usable_life=values[6],
            lap_delta_time=values[7],
            fitted=bool(values[8]),
        )

        tyre_sets.append(tyre_set)

    fitted_idx_offset = tyre_data_start + (TYRE_SET_SIZE * TYRE_SETS_COUNT)
    fitted_idx = struct.unpack_from("<B", data, fitted_idx_offset)[0]

    fitted_set = None
    if 0 <= fitted_idx < len(tyre_sets):
        fitted_set = tyre_sets[fitted_idx]

    available_sets = [
        tyre_set for tyre_set in tyre_sets
        if tyre_set.available
    ]

    return TyreSets(
        car_idx=car_idx,
        fitted_idx=fitted_idx,
        tyre_sets=tyre_sets,
        fitted_set=fitted_set,
        available_sets=available_sets,
    )