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


LAP_DATA_FORMAT = "<IIHBHBHBHfffBBBBBBBBBBHBBHBB"
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
        sector=values[18],
        delta_to_car_in_front_ms=delta_to_car_in_front_ms,
        delta_to_race_leader_ms=delta_to_race_leader_ms,
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