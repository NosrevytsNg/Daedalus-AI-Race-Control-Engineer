import struct

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

from dataclasses import dataclass


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