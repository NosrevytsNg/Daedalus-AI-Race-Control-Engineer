PACKET_NAMES = {
    0: "Motion",
    1: "Session",
    2: "Lap Data",
    3: "Event",
    4: "Participants",
    5: "Car Setups",
    6: "Car Telemetry",
    7: "Car Status",
    8: "Final Classification",
    9: "Lobby Info",
    10: "Car Damage",
    11: "Session History",
    12: "Tyre Sets",
    13: "Motion Ex",
    14: "Time Trial",
    15: "Lap Positions",
}

# 1. Car Telemetry Data
PACKET_ID_CAR_TELEMETRY = 6 # [6: "Car Telemetry"]

# 2. Lap and Sector Data
PACKET_ID_LAP_DATA = 2 # [2: "Lap Data"]
PACKET_ID_SESSION_HISTORY = 11  # [11: "Session History"]

# 3. Vehicle and Session Data
PACKET_ID_CAR_STATUS = 7 # [7: "Car Status"]

# 4. Session Data (Weather and Track)
PACKET_ID_SESSION = 1 # [1: "Session"]

# 5. Vehicle Health (Damage %)
PACKET_ID_CAR_DAMAGE = 10 # [10: "Car Damage"]

# 6. Tyre Intelligence and Strats
PACKET_ID_TYRE_SETS = 12 # [12: "Tyre Sets"]

MAX_CARS = 22