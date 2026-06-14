import struct
from dataclasses import dataclass

HEADER_FORMAT = "<HBBBBBQfIIBB"
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)


def parse_header(data):
    if len(data) < HEADER_SIZE:
        return None

    values = struct.unpack_from(HEADER_FORMAT, data, 0)

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
# Session History Packet (Packet ID 11)
# Used for Best Lap and Sector Times in the current session.

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