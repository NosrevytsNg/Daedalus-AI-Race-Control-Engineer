import random
import time
from collections import deque

recent_valid_laps = deque(maxlen=5)
last_consistency_lap_logged = None

last_coaching_lap_by_context = {}
last_coaching_time_by_context = {}

SESSION_MODE_UNKNOWN = "unknown"
SESSION_MODE_PRACTICE = "practice"
SESSION_MODE_QUALIFYING = "qualifying"
SESSION_MODE_RACE = "race"
SESSION_MODE_TIME_TRIAL = "time_trial"

CURRENT_SESSION_MODE = SESSION_MODE_UNKNOWN

recent_clean_sector_laps = deque(maxlen=5)
last_sector_trend_lap_logged = None
last_sector_trend_result = None

SECTOR_TREND_MIN_HISTORY = 5

SECTOR_TREND_LAP_LOSS_THRESHOLD_MS = 700
SECTOR_TREND_SECTOR_LOSS_THRESHOLD_MS = 300
SECTOR_TREND_SECTOR_SHARE_THRESHOLD_MS = 0.45

SECTOR_TREND_STD_WARNING_MS = 350
SECTOR_TREND_RANGE_WARNING_MS = 900


def get_session_mode(latest_session_data):
    if latest_session_data is None:
        return SESSION_MODE_UNKNOWN

    session_type = latest_session_data.session_type

    practice_sessions = {
        1,  # Practice 1
        2,  # Practice 2
        3,  # Practice 3
        4,  # Short Practice
    }

    qualifying_sessions = {
        5,  # Qualifying 1
        6,  # Qualifying 2
        7,  # Qualifying 3
        8,  # Short Qualifying
        9,  # One-Shot Qualifying
    }

    race_sessions = {
        10,  # Race
        11,  # Race 2
        12,  # Race 3
        15,  # F1 World Grand Prix
    }

    if session_type in practice_sessions:
        return SESSION_MODE_PRACTICE

    if session_type in qualifying_sessions:
        return SESSION_MODE_QUALIFYING

    if session_type in race_sessions:
        return SESSION_MODE_RACE

    if session_type == 13:
        return SESSION_MODE_TIME_TRIAL

    return SESSION_MODE_UNKNOWN


def update_current_session_mode(latest_session_data):
    global CURRENT_SESSION_MODE

    CURRENT_SESSION_MODE = get_session_mode(latest_session_data)
    return CURRENT_SESSION_MODE


def is_race_mode(latest_session_data):
    return get_session_mode(latest_session_data) == SESSION_MODE_RACE


def is_qualifying_mode(latest_session_data):
    return get_session_mode(latest_session_data) == SESSION_MODE_QUALIFYING


def is_practice_mode(latest_session_data):
    return get_session_mode(latest_session_data) == SESSION_MODE_PRACTICE


def is_time_trial_mode(latest_session_data):
    return get_session_mode(latest_session_data) == SESSION_MODE_TIME_TRIAL

PRIORITY_ORDER = {
    "CRITICAL": 1,
    "HIGH": 2,
    "MEDIUM": 3,
    "LOW": 4,
    "INFO": 5,
}

def make_engineer_message(priority, category, context, text):
    return {
        "priority": priority,
        "category": category,
        "context": context,
        "text": text,
    }

def sort_engineer_messages(messages):
    return sorted(
        messages,
        key=lambda message: PRIORITY_ORDER.get(message["priority"], 99)
    )

# ======================================================================================================
# v0.9.1B - Message Delivery Manager
# Purpose:
# - Keep all engineer messages internally.
# - Group related messages by situation/context.
# - Deliver only one radio-style message per active situation.
# - Rotate phrase variants so the engineer does not sound robotic.

active_delivery_groups = set()
last_phrase_variant = {}

# Uncomment desired personality choice when needed
#ENGINEER_PERSONALITY = "balanced" # DEFAULT
ENGINEER_PERSONALITY = "calm"
#ENGINEER_PERSONALITY = "aggresive"
#ENGINEER_PERSONALITY = "concise"

AVAILABLE_PERSONALITIES = {
    "balanced",
    "calm",
    "aggresive",
    "concise",
}

def get_engineer_personality():
    return ENGINEER_PERSONALITY

def set_engineer_personality(personality):
    global ENGINEER_PERSONALITY

    if personality not in AVAILABLE_PERSONALITIES:
        return False
    
    ENGINEER_PERSONALITY = personality
    return True

radio_message_queue = []
last_radio_delivery_time = 0

RADIO_DELIVERY_COOLDOWN_SECONDS = 4.0

last_radio_priority = None
RADIO_MIN_INTERRUPT_GAP_SECONDS = 1.0

NON_ESSENTIAL_RADIO_GROUPS = {
    "drs_available",
    "rain_possible",
    "floor_damage_low",
    "sidepod_damage_low",
    "diffuser_damage_low",
    "coach_reset_rhythm",
    "coach_sector_s1",
    "coach_sector_s2",
    "coach_consistency_variable",
    "coach_consistency_inconsistent",
    "coach_race_sector_trend_loss",
    "coach_race_sector_inconsistent",
}

RADIO_MESSAGE_LIFETIME_SECONDS = {
    "drs_available": 3.0,
    "rain_possible": 30.0,
    "rain_expected": 45.0,
    "ers_low": 10.0,
    "fuel_marginal": 12.0,
    "tyre_wear_high": 15.0,
    "tyre_damage_detected": 15.0, 
    "floor_damage_low": 8.0,
    "sidepod_damage_low": 8.0,
    "diffuser_damage_low": 8.0,
    "coach_reset_rhythm": 20.0,
    "coach_sector_s1": 20.0,
    "coach_sector_s2": 20.0,
    "coach_consistency_variable": 25.0,
    "coach_consistency_inconsistent": 25.0,
    "coach_race_sector_trend_loss": 30.0,
    "coach_race_sector_inconsistent": 30.0,
}

def get_radio_message_lifetime_seconds(delivery_group, priority):
    if priority == "CRITICAL":
        return None
    
    if delivery_group in RADIO_MESSAGE_LIFETIME_SECONDS:
        return RADIO_MESSAGE_LIFETIME_SECONDS[delivery_group]
    
    if priority == "HIGH":
        return 20.0
    
    if priority == "MEDIUM":
        return 15.0
    
    return 8.0

def is_radio_message_expired(message, current_time):
    expires_at = message.get("expires_at")

    if expires_at is None:
        return False
    
    return current_time >= expires_at

def should_suppress_radio_message(message, active_engineer_messages):
    priority = message.get("priority")
    delivery_group = get_delivery_group(message)

    critical_active = any(
        active_message.get("priority") == "CRITICAL"
        for active_message in active_engineer_messages
    )

    high_active = any(
        active_message.get("priority") == "HIGH"
        for active_message in active_engineer_messages
    )

    if critical_active and priority in ("MEDIUM", "LOW", "INFO"):
        return True
    
    if high_active and priority in ("LOW", "INFO"):
        return True
    
    if critical_active and delivery_group in NON_ESSENTIAL_RADIO_GROUPS:
        return True
    
    return False

def can_interrupt_radio_cooldown(message, time_since_last_delivery):
    priority = message.get("priority")

    if priority == "CRITICAL":
        return True
    
    if priority == "HIGH":
        if time_since_last_delivery < RADIO_MIN_INTERRUPT_GAP_SECONDS:
            return False
        
        return last_radio_priority in ("LOW", "INFO", None)
    
    return False


DELIVERY_CONTEXT_GROUPS = {
    # Front wing damage
    "front_wing_critical": "front_wing_critical",
    "pit_front_wing_critical": "front_wing_critical",

    "front_wing_damage": "front_wing_damage",
    "pit_front_wing_damage": "front_wing_damage",

    # Tyre damage
    "tyre_damage_critical": "tyre_damage_critical",
    "pit_tyre_critical": "tyre_damage_critical",

    "tyre_damage_detected": "tyre_damage_detected",

    # Tyre wear
    "tyre_wear_critical": "tyre_wear_critical",
    "pit_tyre_wear": "tyre_wear_critical",

    "tyre_wear_high": "tyre_wear_high",

    # Fuel
    "fuel_critical": "fuel_critical",
    "fuel_marginal": "fuel_marginal",
    "fuel_deficit": "fuel_deficit",
    "fuel_close": "fuel_close",

    # ERS
    "ers_critical": "ers_critical",
    "ers_low": "ers_low",

    # Damage
    "floor_damage_low": "floor_damage_low",
    "floor_damage_medium": "floor_damage_medium",
    "floor_damage_high": "floor_damage_high",
    "floor_damage_critical": "floor_damage_critical",
    
    "sidepod_damage_low": "sidepod_damage_low",
    "sidepod_damage_medium": "sidepod_damage_medium",
    "sidepod_damage_high": "sidepod_damage_high",
    "sidepod_damage_critical": "sidepod_damage_critical",

    "diffuser_damage_low": "diffuser_damage_low",
    "diffuser_damage_medium": "diffuser_damage_medium",
    "diffuser_damage_high": "diffuser_damage_high",
    "diffuser_damage_critical": "diffuser_damage_critical",

    # DRS
    "drs_fault": "drs_fault",
    "drs_available": "drs_available",

    # Weather
    "rain_expected": "rain_expected",
    "rain_possible": "rain_possible",

    # Safety car
    "safety_car": "safety_car",
    "virtual_safety_car": "virtual_safety_car",
    "formation_lap": "formation_lap",

    # Driver coaching
    "coach_reset_rhythm": "coach_reset_rhythm",
    "coach_sector_s1": "coach_sector_s1",
    "coach_sector_s2": "coach_sector_s2",
    "coach_consistency_variable": "coach_consistency_variable",
    "coach_consistency_inconsistent": "coach_consistency_inconsistent",
    "coach_race_sector_trend_loss": "coach_race_sector_trend_loss",
    "coach_race_sector_inconsistent": "coach_race_sector_inconsistent",
}


RADIO_PHRASES = {
    "front_wing_critical": [
        "Box now. Severe front wing damage.",
        "Severe front wing damage. Box this lap.",
        "You've got major front wing damage. We recommend boxing.",
        "Front wing damage is severe. Pit this lap.",
    ],

    "front_wing_damage": [
        "Front wing damage detected. Manage the car.",
        "You've picked up front wing damage. Be careful on entry.",
        "Front wing has damage. Expect reduced front grip.",
    ],

    "tyre_damage_critical": [
        "Critical tyre damage. Box now.",
        "Tyre damage is critical. We need to pit.",
        "Box this lap. Tyre condition is critical.",
        "Tyre damage is too high. Bring it in.",
    ],

    "tyre_damage_detected": [
        "Tyre damage detected. Keep an eye on the car.",
        "You've got tyre damage. Avoid heavy kerbs.",
        "Tyre damage is building. Manage the load.",
    ],

    "tyre_wear_critical": [
        "Tyres are near the end of life. Prepare to box.",
        "Tyre wear is high. We should consider boxing soon.",
        "The tyres are dropping off. Pit window is approaching.",
        "Tyres are struggling now. Be ready for the stop.",
    ],

    "tyre_wear_high": [
        "Tyre wear is getting high. Manage the tyres.",
        "The tyres are starting to wear. Keep them alive.",
        "Tyre wear is building. Smooth inputs now.",
    ],

    "fuel_critical": [
        "Fuel is critical. Start saving immediately.",
        "We are short on fuel. Lift and coast now.",
        "Fuel target is critical. We need saving every lap.",
        "We're not going to make it at this consumption. Save fuel now.",
    ],

    "fuel_marginal": [
        "Fuel is looking tight. Short shift and save where you can.",
        "Fuel is marginal. Start some lift and coast.",
        "We need a bit of fuel saving. Manage consumption.",
        "Fuel is close to the limit. Save where possible.",
    ],

    "fuel_deficit": [
        "Fuel deficit. Start saving where possible.",
        "We are slightly short on fuel. Lift and coast where you can.",
        "Fuel is below target. Manage consumption.",
    ],

    "fuel_close": [
        "Fuel is close to target. Keep it tidy.",
        "Fuel is tight but still positive.",
        "Fuel margin is small. Avoid unnecessary burn.",
    ],

    "ers_critical": [
        "ERS is critically low. Harvest this lap.",
        "Battery is very low. We need to recover energy.",
        "ERS is nearly empty. Reduce deployment.",
    ],

    "ers_low": [
        "ERS is low. Manage deployment.",
        "Battery is low. Harvest where you can.",
        "ERS is running low. Be selective with deployment.",
    ],

    "floor_damage_low": [
        "Minor floor damage detected.",
        "Small amount of floor damage showing.",
        "Light floor damage. Keep monitoring the car.",
    ],

    "floor_damage_medium": [
        "Floor damage detected. Expect some loss of downforce.",
        "You've picked up floor damage. Manage the high-speed corners.",
        "Floor has taken some damage. The car may feel less stable.",
    ],

    "floor_damage_high": [
        "Major floor damage. Expect a significant loss of grip.",
        "Floor damage is high. Be careful in fast corners.",
        "The floor is badly damaged. The car will be unstable at speed.",
    ],

    "floor_damage_critical": [
        "Critical floor damage. The car is heavily compromised.",
        "Severe floor damage. Expect major loss of downforce.",
        "The floor damage is critical. Focus on keeping the car under control.",
    ],

    "sidepod_damage_low": [
        "Minor sidepod damage detected.",
        "Small amount of sidepod damage showing.",
        "Light sidepod damage. Keep monitoring the car.",
    ],

    "sidepod_damage_medium": [
        "Sidepod damage detected.",
        "You've picked up sidepod damage. Keep monitoring the balance.",
        "Sidepod has taken some damage. Watch the car behaviour.",
    ],

    "sidepod_damage_high": [
        "Major sidepod damage. The car balance may be affected.",
        "Sidepod damage is high. Manage the car carefully.",
        "The sidepod has heavy damage. Watch for instability.",
    ],

    "sidepod_damage_critical": [
        "Critical sidepod damage. The car is heavily compromised.",
        "Severe sidepod damage. Manage the car and avoid further contact.",
        "Sidepod damage is critical. Keep the car under control.",
    ],

    "diffuser_damage_low": [
        "Minor diffuser damage detected.",
        "Small amount of diffuser damage showing.",
        "Light diffuser damage. Watch rear stability.",
    ],

    "diffuser_damage_medium": [
        "Diffuser damage detected. Rear grip may be affected.",
        "You've picked up diffuser damage. Be careful on traction.",
        "Diffuser has taken some damage. Watch rear stability.",
    ],

    "diffuser_damage_high": [
        "Major diffuser damage. Expect reduced rear stability.",
        "Diffuser damage is high. Be careful on throttle.",
        "The diffuser is badly damaged. Rear grip will be compromised.",
    ],

    "diffuser_damage_critical": [
        "Critical diffuser damage. Rear stability is heavily compromised.",
        "Severe diffuser damage. Be very careful on traction.",
        "Diffuser damage is critical. Manage the rear of the car.",
    ],

    "drs_fault": [
        "DRS fault detected.",
        "DRS issue confirmed. You may not have rear wing activation.",
        "We have a DRS fault. Overtaking will be harder.",
    ],

    "drs_available": [
        "DRS available.",
        "DRS is enabled.",
        "You have DRS this lap.",
    ],

    "rain_expected": [
        "Rain is expected soon. Prepare for changing conditions.",
        "Rain is coming. Be ready for the crossover.",
        "We are expecting rain soon. Keep the tyres in mind.",
    ],

    "rain_possible": [
        "Rain is possible later. Keep an eye on the forecast.",
        "There is a chance of rain later.",
        "Weather may change later. We'll keep monitoring.",
    ],

    "safety_car": [
        "Safety car deployed. Stay alert and manage delta.",
        "Safety car is out. Watch the delta.",
        "Full safety car deployed. Reduce pace and manage temperatures.",
    ],

    "virtual_safety_car": [
        "Virtual safety car deployed. Watch the delta.",
        "VSC is out. Stay positive on the delta.",
        "Virtual safety car. Manage the pace carefully.",
    ],

    "formation_lap": [
        "Formation lap. Build tyre temperature.",
        "Formation lap underway. Warm the tyres and brakes.",
        "Formation lap. Prepare the car for the start.",
    ],

    "coach_reset_rhythm": [
        "Reset the rhythm. Focus on a clean lap.",
        "Take a reset lap mentally. Build the pace back up.",
        "Focus on rhythm now. Clean inputs, clean exits.",
    ],

    "coach_sector_s1": [
        "Focus on Sector 1. Prioritise braking stability and clean exits.",
        "Time loss is mainly Sector 1. Keep the entry stable and avoid overdriving.",
        "Sector 1 needs attention. Brake cleanly and focus on traction out.",
    ],

    "coach_sector_s2": [
        "Focus on Sector 2. Keep the rhythm smooth through the middle sector.",
        "Most time loss is in Sector 2. Prioritise clean exits and avoid sliding.",
        "Sector 2 is costing time. Keep it smooth and build momentum corner to corner.",
    ],

    "coach_consistency_variable": [
        "Pace is varying. Prioritise repeatable laps over peak pace.",
        "Focus on consistency. Same braking points, same exits.",
        "Lap times are moving around. Build a cleaner rhythm.",
    ],

    "coach_consistency_inconsistent": [
        "Pace is inconsistent. Slow it down slightly and rebuild control.",
        "Consistency is the target now. Keep the car tidy and repeat the lap.",
        "Focus on repeatability. Do not chase the lap time too hard.",
    ],

    "coach_race_sector_trend_loss": [
        "Recent race pace shows one sector is costing most of the lap time.",
        "One sector is repeatedly costing time compared to recent race pace.",
        "Sector trend shows a repeated time loss. Focus on cleaning that sector up.",
    ],

    "coach_race_sector_inconsistent": [
        "One sector is varying more than the others. Focus on repeatability.",
        "Sector consistency is the issue. Use the same references each lap.",
        "The sector trend is unstable. Prioritise repeatable braking points and exits.",
    ],
}

personality_radio_messages = {
    "balanced": {},
    "calm": {
        "floor_damage_critical": [
            "You have severe front wing damage. Box this lap. Box",
            "Front wing damage. Box now. Box",
            "We need to pit to replace the front wing, keep it steady and box this lap",
        ],
        "floor_damage_critical": [
            "Critical floor damage. The car will be difficult to drive",
            "There is floor damage on the car, you will experience a lot of loss in downforce",
            "The floor is heavily damage, be careful you will lose a lot of downforce",
        ],
        "fuel_critical": [
            "Fuel is critical. Begin saving as much as possible",
            "We need to save fuel. Lift and coast where possible",
            "LICO, LICO. Fuel is at a critical level. LICO where possible",
        ],
        "ers_critical": [
            "ERS is critical low. Harvest it this lap.",
            "Battery is low. Remember to harvest it this lap.",
            "ERS low, change mode to harvest"
        ],
        "safety_car": [
            "Safety car deployed. I repeat, safety car deployed",
            "Full safety car. Watch your delta and maintain position. No overtaking.",
            "Safety car is out. Manage your delta and reduce pace",
        ],
    },
    "aggresive": {
        "floor_damage_critical": [
            "Box now. Box this lap. You have front wing damage",
            "Front wing damage. Pit this lap. Box now box.",
            "We need to pit to replace the front wing, bring it in now",
        ],
        "floor_damage_critical": [
            "Critical floor damage. The car is heavily compromised. Expect the unexpected",
            "There is severe floor damage on the car, you will experience a lot of loss in downforce",
            "The floor is heavily damage, do your best, keep it on the track ",
        ],
        "fuel_critical": [
            "Fuel is critical. Save it now",
            "We are short on fuel. Lift and coast immediately",
            "LICO, LICO. Fuel is at a critical level. LICO now",
        ],
        "ers_critical": [
            "ERS is critical low. Harvest it this lap.",
            "Battery is low. Remember to harvest it this lap.",
            "ERS low, change mode to harvest"
        ],
        "safety_car": [
            "Safety car deployed. I repeat, safety car deployed. Watch your delta.",
            "Full safety car. Watch your delta and maintain position. No overtaking.",
            "Safety car is out. Manage your delta and reduce pace",
        ],
    },
    "concise": {
        "floor_damage_critical": [
            "Front wing damage. Box this lap.",
            "Severe wing damage, pit now",
            "Front wing critical. Box.",
        ],
        "floor_damage_critical": [
            "Floor critical.",
            "Severe floor damage.",
            "Floor damage high. Careful.",
        ],
        "fuel_critical": [
            "Fuel is critical.",
            "Save fuel now. Lift and coast",
            "LICO, LICO.",
        ],
        "ers_critical": [
            "ERS low. Harvest. Harvest.",
            "Battery is low. Harvest it this lap.",
            "ERS low, change mode to harvest"
        ],
        "safety_car": [
            "Safety car deployed.",
            "Full safety car.",
            "Safety car is out.",
        ],
    },
}

SESSION_RADIO_PHRASES = {
    SESSION_MODE_RACE: {
        "tyre_wear_critical": [
            "Tyres are near the end of life. Prepare to box.",
            "Tyre wear is high. We should consider the stop soon.",
            "The tyres are dropping off. Pit window is approaching.",
        ],

        "fuel_critical": [
            "Fuel is critical. Start saving immediately.",
            "We are short on fuel. Lift and coast now.",
            "Fuel target is critical. Save fuel every lap.",
        ],

        "safety_car": [
            "Safety car deployed. Stay alert and manage delta.",
            "Safety car is out. Watch the delta and keep temperatures up.",
            "Full safety car. Reduce pace and manage the car.",
        ],

        "virtual_safety_car": [
            "Virtual safety car deployed. Watch the delta.",
            "VSC is out. Stay positive on the delta.",
            "Virtual safety car. Manage the pace carefully.",
        ],

        "rain_expected": [
            "Rain is expected soon. Prepare for changing conditions.",
            "Rain is coming. Be ready for the tyre crossover.",
            "We are expecting rain soon. Keep the next tyre in mind.",
        ],
    },

    SESSION_MODE_QUALIFYING: {
        "tyre_wear_critical": [
            "Tyres are past their peak. This run may be compromised.",
            "Tyre grip is dropping. Next push lap may be slower.",
            "Tyres are fading. Consider a reset or fresh set.",
        ],

        "tyre_wear_high": [
            "Tyres are starting to go away. Push lap performance may drop.",
            "Tyre wear is building. This may affect the next sector.",
            "Tyres are no longer at peak performance.",
        ],

        "ers_critical": [
            "ERS is critically low. Recharge before the next push lap.",
            "Battery is too low for a proper push lap. Harvest now.",
            "ERS is nearly empty. Build charge before attacking.",
        ],

        "ers_low": [
            "ERS is low. Recharge before the next push attempt.",
            "Battery is low. Prepare the car before pushing.",
            "ERS needs recovery before the next fast lap.",
        ],

        "rain_expected": [
            "Rain is expected soon. Prioritise an early lap.",
            "Weather is coming in. We should get a banker lap.",
            "Rain threat is increasing. Track position matters now.",
        ],
    },

    SESSION_MODE_PRACTICE: {
        "tyre_wear_critical": [
            "Tyres are heavily worn. This is useful degradation data.",
            "Tyre wear is high. Good long-run information here.",
            "The tyres are near the limit. This helps our degradation read.",
        ],

        "tyre_wear_high": [
            "Tyre wear is building. Good data point for the run.",
            "Tyres are starting to wear. Keep gathering long-run data.",
            "Wear is increasing. Useful information for strategy planning.",
        ],

        "floor_damage_critical": [
            "Critical floor damage. Balance data may no longer be reliable.",
            "Severe floor damage. This run is compromised for setup data.",
            "The floor is badly damaged. Be careful interpreting car balance.",
        ],

        "rain_expected": [
            "Rain is expected soon. This may be useful mixed-condition data.",
            "Weather is changing. Good chance to gather crossover information.",
            "Rain is coming. Monitor how the car behaves as conditions change.",
        ],
    },

    SESSION_MODE_TIME_TRIAL: {
        "tyre_wear_critical": [
            "Tyres are worn. Reset may be faster.",
            "Tyres are past the limit. Consider restarting the run.",
            "Grip is gone. A reset may be the better option.",
        ],

        "tyre_wear_high": [
            "Tyres are starting to wear. Lap time may drop.",
            "Tyre grip is fading. Reset if the lap is compromised.",
            "Tyres are losing performance.",
        ],

        "front_wing_critical": [
            "Front wing damage. Reset the run if possible.",
            "Severe front wing damage. This attempt is compromised.",
            "Front wing is damaged. Better to restart the run.",
        ],

        "floor_damage_critical": [
            "Critical floor damage. This run is compromised.",
            "Severe floor damage. Reset if possible.",
            "Floor damage is critical. This lap will not be representative.",
        ],

        "ers_low": [
            "ERS is low. Recharge before the next push attempt.",
            "Battery is low. Build energy before pushing again.",
            "ERS needs recovery before another fast lap.",
        ],
    },
}


def get_delivery_group(message):
    context = message.get("context")
    return DELIVERY_CONTEXT_GROUPS.get(context, context)

def get_radio_phrase_pool(delivery_group):
    session_phrases = SESSION_RADIO_PHRASES.get(
        CURRENT_SESSION_MODE,
        {}
    )

    if delivery_group in session_phrases:
        return session_phrases[delivery_group]

    personality_phrases = personality_radio_messages.get(
        ENGINEER_PERSONALITY,
        {}
    )

    if delivery_group in personality_phrases:
        return personality_phrases[delivery_group]

    return RADIO_PHRASES.get(delivery_group)


def select_radio_phrase(delivery_group, fallback_text):
    phrases = get_radio_phrase_pool(delivery_group)

    if not phrases:
        return fallback_text

    if len(phrases) == 1:
        return phrases[0]

    phrase_key = (
        f"{ENGINEER_PERSONALITY}:"
        f"{CURRENT_SESSION_MODE}:"
        f"{delivery_group}"
    )

    previous_index = last_phrase_variant.get(phrase_key)

    available_indexes = [
        index for index in range(len(phrases))
        if index != previous_index
    ]

    selected_index = random.choice(available_indexes)

    last_phrase_variant[phrase_key] = selected_index

    return phrases[selected_index]


# def prepare_delivery_messages(engineer_messages):
#     global active_delivery_groups

#     delivery_messages = []
#     current_delivery_groups = set()

#     for message in engineer_messages:
#         delivery_group = get_delivery_group(message)

#         if delivery_group is None:
#             continue

#         current_delivery_groups.add(delivery_group)

#         # Option D behaviour:
#         # Once a situation has been delivered, do not deliver it again
#         # until the condition disappears and later returns.
#         if delivery_group in active_delivery_groups:
#             continue

#         radio_text = select_radio_phrase(
#             delivery_group,
#             message["text"]
#         )

#         delivery_messages.append(
#             {
#                 "priority": message["priority"],
#                 "category": message["category"],
#                 "context": message["context"],
#                 "delivery_group": delivery_group,
#                 "text": radio_text,
#                 "source_text": message["text"],
#             }
#         )

#         active_delivery_groups.add(delivery_group)

#     # If a condition disappears, remove it from active tracking.
#     # This allows it to be delivered again if it returns later.
#     active_delivery_groups = active_delivery_groups.intersection(
#         current_delivery_groups
#     )

#     return sort_engineer_messages(delivery_messages)
def get_message_delivery_group(message):
    if message.get("delivery_group") is not None:
        return message["delivery_group"]

    return get_delivery_group(message)

def get_radio_queue_size():
    return len(radio_message_queue)

def prepare_delivery_messages(engineer_messages):
    global active_delivery_groups
    global radio_message_queue
    global last_radio_delivery_time
    global last_radio_priority

    current_time = time.time()

    current_delivery_groups = set()
    queued_or_active_groups = set(active_delivery_groups)

    # Step 1:
    # Look at all current engineer messages and decide which new situations
    # should be added into the radio queue.
    for message in engineer_messages:
        delivery_group = get_delivery_group(message)

        if delivery_group is None:
            continue

        current_delivery_groups.add(delivery_group)

        # If this situation is already active or already queued,
        # do not add it again.
        if should_suppress_radio_message(message, engineer_messages):
            continue

        if delivery_group in queued_or_active_groups:
            continue

        radio_text = select_radio_phrase(
            delivery_group,
            message["text"]
        )

        lifetime_seconds = get_radio_message_lifetime_seconds(
            delivery_group,
            message["priority"]
        )

        if lifetime_seconds is None:
            expires_at = None
        else:
            expires_at = current_time + lifetime_seconds

        radio_message_queue.append(
            {
                "priority": message["priority"],
                "category": message["category"],
                "context": message["context"],
                "delivery_group": delivery_group,
                "text": radio_text,
                "source_text": message["text"],
                "created_at": current_time,
                "expires_at": expires_at,
            }
        )

        queued_or_active_groups.add(delivery_group)
        active_delivery_groups.add(delivery_group)

    # Step 2:
    # If a condition disappears from the current engineer messages,
    # remove it from active tracking.
    active_delivery_groups = active_delivery_groups.intersection(
        current_delivery_groups
    )

    # Step 3:
    # Remove queued messages if their condition no longer exists.
    # Example: VSC appears briefly, disappears, and the queued radio message
    # has not been delivered yet.
    radio_message_queue = [
        message for message in radio_message_queue
        if (message["delivery_group"] in current_delivery_groups
        and not is_radio_message_expired(message, current_time))
    ]

    # Step 4:
    # Sort the queue so the most important message is delivered first.
    radio_message_queue = sort_engineer_messages(radio_message_queue)

    # Step 5:
    # If nothing is queued, nothing to deliver.
    if not radio_message_queue:
        return []

    # Step 6:
    # Cooldown control.
    # Do not speak too many radio messages back-to-back.
    next_message = radio_message_queue[0]

    time_since_last_delivery = current_time - last_radio_delivery_time

    cooldown_active = (
        last_radio_delivery_time != 0
        and time_since_last_delivery < RADIO_DELIVERY_COOLDOWN_SECONDS
    )

    if cooldown_active:
        if not can_interrupt_radio_cooldown(
            next_message,
            time_since_last_delivery
        ):
            return []

    # Step 7:
    # Release only one message.
    next_message = radio_message_queue.pop(0)
    last_radio_delivery_time = current_time
    last_radio_priority = next_message["priority"]

    return [next_message]

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

    if fuel_laps <= -0.50:
        warnings.append(
            f"Fuel critical ({fuel_laps:+.2f} laps)"
        )

    elif fuel_laps < 0:
        warnings.append(
            "Fuel deficit ({fuel_laps:+.2f} laps)"
        )

    elif fuel_laps <= 0.20:
        warnings.append(
            "Fuel close to target ({fuel_laps:+.2f} laps)"
        )

    return warnings


def get_ers_warnings(latest_car_status):
    warnings = []

    if latest_car_status is None:
        return warnings

    ers_pct = (
        latest_car_status.ers_energy_storage
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

def create_aero_damage_message(component_name, damage_value, context_prefix):
    if damage_value is None:
        return None

    if damage_value >= 80:
        return make_engineer_message(
            "CRITICAL",
            "damage",
            f"{context_prefix}_critical",
            f"Critical {component_name} damage ({damage_value:.0f}%)"
        )

    if damage_value >= 50:
        return make_engineer_message(
            "HIGH",
            "damage",
            f"{context_prefix}_high",
            f"Major {component_name} damage ({damage_value:.0f}%)"
        )

    if damage_value >= 20:
        return make_engineer_message(
            "MEDIUM",
            "damage",
            f"{context_prefix}_medium",
            f"{component_name.capitalize()} damage ({damage_value:.0f}%)"
        )
    
    if damage_value >= 1:
        return make_engineer_message(
            "LOW",
            "damage",
            f"{context_prefix}_low",
            f"{component_name.capitalize()} damage ({damage_value:.0f}%)"
        )

    return None


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

# def config_engineer_messages(
#     latest_car_status,
#     latest_car_damage,
#     latest_session_data,
#     latest_tyre_sets,
# ):
#     pit_advice = suggest_pit_window(
#     None,
#     latest_car_damage,
#     latest_tyre_sets,
#     )

#     pit_messages = []

#     if pit_advice != "Stay out" and pit_advice != "--":
#         pit_messages.append(pit_advice)


#     return {
#         "tyre" : get_tyre_warnings(latest_car_damage, latest_tyre_sets),
#         "fuel": get_fuel_warnings(latest_car_status),
#         "ers": get_ers_warnings(latest_car_status),
#         "damage": get_damage_alerts(latest_car_damage),
#         "weather": get_weather_alerts(latest_session_data),
#         "safety_car": get_safety_car_alerts(latest_session_data),
#         "drs": get_drs_alerts(latest_car_status, latest_car_damage), 
#         "pit": pit_messages,  
#     }

def config_engineer_messages(
    latest_car_status,
    latest_car_damage,
    latest_session_data,
    latest_tyre_sets,
):
    messages = []

    update_current_session_mode(latest_session_data)

    # Tyre warnings
    if latest_car_damage is not None:
        max_wear = max(latest_car_damage.tyre_wear)
        max_damage = max(latest_car_damage.tyre_damage)

        if max_damage >= 80:
            hello = make_engineer_message(
                        "CRITICAL",
                        "tyre",
                        "tyre_damage_critical",
                        "CRITICAL TYRE DAMAGE - BOX NOW"
                    )
            messages.append(hello)
            #     make_engineer_message(
            #         "CRITICAL",
            #         "tyre",
            #         "tyre_damage_critical",
            #         "CRITICAL TYRE DAMAGE - BOX NOW"
            #     )
            # )

        elif max_damage >= 50:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "tyre",
                    "tyre_damage_detected",
                    f"Tyre damage detected ({max_damage:.0f}%)"
                )
            )

        if max_wear >= 70:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "tyre",
                    "tyre_wear_critical",
                    f"Tyres approaching end of life ({max_wear:.0f}%)"
                )
            )

        elif max_wear >= 50:
            messages.append(
                make_engineer_message(
                    "MEDIUM",
                    "tyre",
                    "tyre_wear_high",
                    f"Tyre wear high ({max_wear:.0f}%)"
                )
            )

    # Fuel warnings
    if latest_car_status is not None:
        fuel_laps = latest_car_status.fuel_remaining_laps

        if fuel_laps <= -0.50 :
            messages.append(
                make_engineer_message(
                    "CRITICAL",
                    "fuel",
                    "fuel_critical",
                    f"Fuel critical ({fuel_laps: +.2f} laps"
                )
            )

        elif fuel_laps < 0:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "fuel",
                    "fuel_deficit",
                    f"Fuel deficit ({fuel_laps: +.2f} laps)"
                )
            )    

        elif fuel_laps <= 0.20:
            messages.append(
                make_engineer_message(
                    "LOW",
                    "fuel",
                    "fuel_close",
                    f"Fuel close to target ({fuel_laps: +.2f} laps"
                )
            )

    # ERS warnings
    if latest_car_status is not None:
        ers_pct = (
            latest_car_status.ers_energy_storage
            / 4_000_000
        ) * 100

        if ers_pct < 10:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "ers",
                    "ers_critical",
                    "ERS critically low"
                )
            )

        elif ers_pct < 25:
            messages.append(
                make_engineer_message(
                    "MEDIUM",
                    "ers",
                    "ers_low",
                    "ERS low"
                )
            )

    # Damage alerts
    if latest_car_damage is not None:
        front_wing_damage = max(
            latest_car_damage.front_left_wing_damage,
            latest_car_damage.front_right_wing_damage,
        )

        if front_wing_damage >= 70:
            messages.append(
                make_engineer_message(
                    "CRITICAL",
                    "damage",
                    "front_wing_critical",
                    "Severe front wing damage - BOX NOW"
                )
            )

        elif front_wing_damage > 20:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "damage",
                    "front_wing_damage",
                    "Front wing damage"
                )
            )

        aero_damage_messages = [
            create_aero_damage_message(
                "floor",
                latest_car_damage.floor_damage,
                "floor_damage"
            ),
            create_aero_damage_message(
                "sidepod",
                latest_car_damage.sidepod_damage,
                "sidepod_damage"
            ),
            create_aero_damage_message(
                "diffuser",
                latest_car_damage.diffuser_damage,
                "diffuser_damage"
            ),
        ]

        for aero_message in aero_damage_messages:
            if aero_message is not None:
                messages.append(aero_message)

        if latest_car_damage.drs_fault:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "drs",
                    "drs_fault",
                    "DRS fault"
                )
            )

    # Weather alerts
    if latest_session_data is not None and latest_session_data.weather_forecast_samples:
        nearest = latest_session_data.weather_forecast_samples[0]

        if nearest.rain_percentage >= 60:
            messages.append(
                make_engineer_message(
                    "MEDIUM",
                    "weather",
                    "rain_expected",
                    f"Rain expected in {nearest.time_offset} min"
                )
            )

        elif nearest.rain_percentage >= 30:
            messages.append(
                make_engineer_message(
                    "LOW",
                    "weather",
                    "rain_possible",
                    f"Rain possible in {nearest.time_offset} min"
                )
            )

    # Safety Car alerts
    if latest_session_data is not None:
        status = latest_session_data.safety_car_status

        if status == 1:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "safety_car",
                    "safety_car",
                    "Safety Car deployed"
                )
            )

        elif status == 2:
            messages.append(
                make_engineer_message(
                    "HIGH",
                    "safety_car",
                    "virtual_safety_car",
                    "Virtual Safety Car"
                )
            )

        elif status == 3:
            messages.append(
                make_engineer_message(
                    "INFO",
                    "safety_car",
                    "formation_lap",
                    "Formation Lap"
                )
            )

    # DRS availability
    if latest_car_status is not None and latest_car_status.drs_allowed:
        messages.append(
            make_engineer_message(
                "LOW",
                "drs",
                "drs_available",
                "DRS available"
            )
        )

    # Pit advice
    pit_advice = suggest_pit_window(
        None,
        latest_car_damage,
        latest_tyre_sets,
    )

    if pit_advice not in ("--", "Stay out"):
        if "tyre damage critical" in pit_advice:
            priority = "CRITICAL"
            context = "pit_tyre_critical"
            
        elif "severe front wing damage" in pit_advice:
            priority = "CRITICAL"
            context = "pit_front_wing_critical"
            
        elif "front wing" in pit_advice:
            priority = "HIGH"
            context = "pit_front_wing_damage"
            
        elif "tyre wear" in pit_advice:
            priority = "HIGH"
            context = "pit_tyre_wear"
            
        else:
            priority = "MEDIUM"
            context = "pit_window"
            

        messages.append(
            make_engineer_message(
                priority,
                "pit",
                context,
                pit_advice
            )
        )

    return sort_engineer_messages(messages)

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

    session_mode = update_current_session_mode(latest_session_data)

    if session_mode == SESSION_MODE_TIME_TRIAL:
        advice.extend(
            get_time_trial_strategy_advice(
                latest_lap_data,
                latest_car_status,
                latest_car_damage,
                latest_session_data,
                latest_tyre_sets,
            )
        )

        return advice
    
    if session_mode == SESSION_MODE_QUALIFYING:
        advice.extend(
            get_qualifying_strategy_advice(
                latest_lap_data,
                latest_car_status,
                latest_car_damage,
                latest_session_data,
                latest_tyre_sets,
            )
        )

        advice.extend(
            get_weather_tyre_advice(
                latest_session_data,
                latest_tyre_sets,
            )
        )

        return advice

    if session_mode == SESSION_MODE_PRACTICE:
        advice.extend(
            get_practice_strategy_advice(
                latest_lap_data,
                latest_car_status,
                latest_car_damage,
                latest_session_data,
                latest_tyre_sets,
            )
        )

        advice.extend(
            get_ers_deployment_advice(
                latest_car_status,
            )
        )

        advice.extend(
            get_weather_tyre_advice(
                latest_session_data,
                latest_tyre_sets,
            )
        )

        return advice
        
    # For Race and Unknown Sessions (Race-Style Strategy Logic)
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

def get_front_wing_damage_level(latest_car_damage):
    if latest_car_damage is None:
        return 0

    return max(
        latest_car_damage.front_left_wing_damage,
        latest_car_damage.front_right_wing_damage,
    )


def get_max_aero_damage_level(latest_car_damage):
    if latest_car_damage is None:
        return 0

    return max(
        latest_car_damage.floor_damage,
        latest_car_damage.sidepod_damage,
        latest_car_damage.diffuser_damage,
    )


def get_qualifying_strategy_advice(
    latest_lap_data,
    latest_car_status,
    latest_car_damage,
    latest_session_data,
    latest_tyre_sets,
):
    advice = []

    if latest_car_status is not None:
        ers_pct = (
            latest_car_status.ers_energy_storage
            / 4_000_000
        ) * 100

        if ers_pct < 40:
            advice.append(
                "Qualifying: recharge ERS before the next push lap"
            )

        elif ers_pct > 80:
            advice.append(
                "Qualifying: ERS ready for a push lap"
            )

    if latest_tyre_sets is not None and latest_tyre_sets.fitted_set is not None:
        fitted = latest_tyre_sets.fitted_set

        if fitted.wear >= 30:
            advice.append(
                "Qualifying: tyres may be past peak performance"
            )

        elif fitted.wear <= 10:
            advice.append(
                "Qualifying: tyres are in a good window for a push lap"
            )

    if latest_session_data is not None:
        for sample in latest_session_data.weather_forecast_samples[:3]:
            if sample.rain_percentage >= 50 or sample.weather in (3, 4, 5):
                advice.append(
                    "Qualifying: rain threat detected - prioritise an early banker lap"
                )
                break

    if (
        get_front_wing_damage_level(latest_car_damage) > 20
        or
        get_max_aero_damage_level(latest_car_damage) > 20
    ):
        advice.append(
            "Qualifying: car damage detected - this run may be compromised"
        )

    return advice


def get_practice_strategy_advice(
    latest_lap_data,
    latest_car_status,
    latest_car_damage,
    latest_session_data,
    latest_tyre_sets,
):
    advice = []

    if latest_tyre_sets is not None and latest_tyre_sets.fitted_set is not None:
        fitted = latest_tyre_sets.fitted_set

        if fitted.wear >= 50:
            advice.append(
                "Practice: useful tyre degradation data - monitor long-run pace"
            )

        elif fitted.wear >= 25:
            advice.append(
                "Practice: tyre wear is building - continue collecting run data"
            )

    if get_max_aero_damage_level(latest_car_damage) >= 50:
        advice.append(
            "Practice: aero damage is high - balance data may no longer be reliable"
        )

    elif get_front_wing_damage_level(latest_car_damage) > 20:
        advice.append(
            "Practice: front wing damage detected - setup feedback may be affected"
        )

    if latest_session_data is not None:
        for sample in latest_session_data.weather_forecast_samples[:3]:
            if sample.rain_percentage >= 50 or sample.weather in (3, 4, 5):
                advice.append(
                    "Practice: changing weather may provide useful crossover data"
                )
                break

    return advice


def get_time_trial_strategy_advice(
    latest_lap_data,
    latest_car_status,
    latest_car_damage,
    latest_session_data,
    latest_tyre_sets,
):
    advice = []

    if latest_car_status is not None:
        ers_pct = (
            latest_car_status.ers_energy_storage
            / 4_000_000
        ) * 100

        if ers_pct < 40:
            advice.append(
                "Time Trial: recharge ERS before the next push attempt"
            )

        elif ers_pct > 80:
            advice.append(
                "Time Trial: ERS is ready for another push attempt"
            )

    if latest_tyre_sets is not None and latest_tyre_sets.fitted_set is not None:
        fitted = latest_tyre_sets.fitted_set

        if fitted.wear >= 30:
            advice.append(
                "Time Trial: tyres are worn - reset may be faster"
            )

    if (
        get_front_wing_damage_level(latest_car_damage) > 0
        or
        get_max_aero_damage_level(latest_car_damage) > 0
    ):
        advice.append(
            "Time Trial: car damage detected - reset this run if possible"
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

    if fuel_laps <= -0.50:
        advice.append(
            f"Fuel critical ({fuel_laps:+.2f}) - lift and coast immediately"
        )

    elif fuel_laps < 0:
        advice.append(
            f"Fuel deficit ({fuel_laps:+.2f}) - lift and coast where possible"
        )

    elif fuel_laps <= 0.20:
        advice.append(
            f"Fuel close to target ({fuel_laps:+.2f}) - avoid unnecessary burn"
        )

    elif fuel_laps >= 2.00:
        advice.append(
            f"Fuel surplus ({fuel_laps:+.2f}) - push if needed"
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
        latest_car_status.ers_energy_storage
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
        latest_car_damage=None,
        latest_session_data=None,
        latest_completed_lap_sectors=None,
):
    analysis = {"lap_comparison": None, 
                "sector_comparison": None, 
                "sector_trend": None,
                "consistency": None,
                "message": []}
        
    if latest_lap_data is None or latest_session_history is None:
        analysis["message"].append("Not enough data yet.")
        return analysis
    
    update_current_session_mode(latest_session_data)

    if is_safety_car_active(latest_session_data):
        analysis["message"].append(
            "Performance analysis paused - Safety Car/VSC active"
        )
        return analysis

    if is_major_damage_for_performance(latest_car_damage):
        analysis["message"].append(
            "Performance analysis paused - Car damage is affecting lap times."
        )
    
    # Lap Comparison (Last vs Best)
    last_lap = latest_lap_data.last_lap_time_ms
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
                analysis["message"].append(
                    f"Last lap was {lap_delta / 1000:.3f}s slower than your best"
                )

            elif lap_delta < 0:
                analysis["message"].append(
                    f"Last lap was {lap_delta / 1000:.3f}s faster than your best"
                )

            else:
                analysis["message"].append(
                    f"👍"
                )

# Sector Comparison (Current vs Best)    

    sector_data = {
        "S1": {
            "current_sec": latest_lap_data.sector_1_time_ms,
            "best_sec": latest_session_history.best_sector1_time_ms
        },
        "S2": {
            "current_sec": latest_lap_data.sector_2_time_ms,
            "best_sec": latest_session_history.best_sector2_time_ms
        },
    }

    sector_deltas = {}

    for sector_name, data in sector_data.items():
        current_sec = data["current_sec"]
        best_sec = data["best_sec"]

        if current_sec is None or best_sec is None:
            continue

        if current_sec <= 0 or best_sec <= 0:
            continue

        sector_deltas[sector_name] = current_sec - best_sec

    if sector_deltas:
        worst_sec = max(
            sector_deltas,
            key=sector_deltas.get,
        ) 

        worst_sec_delta = sector_deltas[worst_sec]

        analysis["sector_comparison"] = {
            "sector_deltas": sector_deltas,
            "worst_sec": worst_sec,
            "worst_sec_delta": worst_sec_delta
        }   

        if worst_sec_delta > 0:
            analysis["message"].append(
                f"Most time lost in {worst_sec}: "
                f"+{worst_sec_delta / 1000:.3f}s."
            )

        if worst_sec_delta < 0:
            analysis["message"].append(
                f"Strongest sector is {worst_sec}: "
                f"+{worst_sec_delta / 1000:.3f}s faster."
            ) 


    sector_trend = analyze_race_sector_trend(
        latest_completed_lap_sectors,
        latest_car_damage,
        latest_session_data,
    )

    analysis["sector_trend"] = sector_trend

    consistency_message = analyze_consistency(
        latest_lap_data,
        latest_session_history,
        latest_car_damage,
        latest_session_data,
    )

    analysis["consistency"] = consistency_message

    for message in consistency_message["messages"]:
        analysis["message"].append(message)        

    return analysis

def make_coaching_message(priority, context, text):
    return make_engineer_message(
        priority,
        "coaching",
        context,
        text,
    )

def should_emit_lap_coaching_message(context, completed_lap_num, min_lap_between=2):
    if completed_lap_num is not None:
        return False
    
    last_lap = last_coaching_lap_by_context.get(context)

    if last_lap is not None:
        laps_since_last = completed_lap_num - last_lap

        if laps_since_last < min_lap_between:
            return False
        
    last_coaching_lap_by_context[context] = completed_lap_num
    return True


def generate_driver_coaching(
    performance_analysis,
    latest_lap_data,
    latest_session_history,
    latest_car_damage=None,
    latest_session_data=None,
):
    coaching_messages = []

    if performance_analysis is None:
        return coaching_messages

    if latest_lap_data is None or latest_session_history is None:
        return coaching_messages

    if is_safety_car_active(latest_session_data):
        return coaching_messages

    if is_major_damage_for_performance(latest_car_damage):
        return coaching_messages

    lap_comparison = performance_analysis.get("lap_comparison")

    if lap_comparison is not None:
        lap_delta = lap_comparison.get("lap_delta")

        if lap_delta is not None:
            completed_lap_num = get_completed_lap_num(latest_lap_data)

            if completed_lap_num is None:
                return coaching_messages

            if lap_delta >= 3000:
                if should_emit_coaching_message(
                    "coach_reset_rhythm",
                    completed_lap_num,
                    min_laps_between=3,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            "LOW",
                            "coach_reset_rhythm",
                            "Last lap was well off your best. Reset the rhythm and focus on a clean lap."
                        )
                    )

            elif lap_delta >= 2000:
                if should_emit_coaching_message(
                    "coach_reset_rhythm",
                    completed_lap_num,
                    min_laps_between=3,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            "LOW",
                            "coach_reset_rhythm",
                            "Last lap was slower than your best. Focus on rhythm and clean exits."
                        )
                    )

    sector_comparison = performance_analysis.get("sector_comparison")

    if sector_comparison is not None:
        worst_sec = sector_comparison.get("worst_sec")
        worst_sec_delta = sector_comparison.get("worst_sec_delta")

        if worst_sec_delta is not None and worst_sec_delta >= 300:
            priority = "MEDIUM" if worst_sec_delta >= 1000 else "LOW"

            if worst_sec == "S1":
                if should_emit_coaching_message(
                    "coach_sector_s1",
                    completed_lap_num,
                    min_laps_between=2,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            priority,
                            "coach_sector_s1",
                            f"Focus on Sector 1. You are losing {worst_sec_delta / 1000:.3f}s there. Prioritise braking stability and clean exits."
                        )
                    )

            elif worst_sec == "S2":
                if should_emit_coaching_message(
                    "coach_sector_s2",
                    completed_lap_num,
                    min_laps_between=2,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            priority,
                            "coach_sector_s2",
                            f"Focus on Sector 2. You are losing {worst_sec_delta / 1000:.3f}s there. Keep the rhythm smooth and prioritise corner exits."
                        )
                    )

    consistency = performance_analysis.get("consistency")

    if consistency is not None:
        metrics = consistency.get("metrics")

        if metrics is not None:
            status = metrics.get("status")

            if status == "variable":
                coaching_messages.append(
                    make_coaching_message(
                        "LOW",
                        "coach_consistency_variable",
                        "Pace variation detected. Prioritise repeatable laps over peak lap time."
                    )
                )

            elif status == "inconsistent":
                coaching_messages.append(
                    make_coaching_message(
                        "MEDIUM",
                        "coach_consistency_inconsistent",
                        "Pace is inconsistent. Focus on cleaner inputs and repeatable braking points."
                    )
                )

        sector_trend = performance_analysis.get("sector_trend")

    if sector_trend is not None and sector_trend.get("ready"):
        current = sector_trend.get("current")
        deltas = sector_trend.get("deltas")

        if current is not None and deltas is not None:
            completed_lap_num = current.get("lap_num")

            if sector_trend.get("meaningful_loss"):
                weakest_sector = sector_trend.get("weakest_sector")

                if weakest_sector == "S1":
                    sector_delta = deltas["D1"]
                    sector_focus = "Sector 1"
                elif weakest_sector == "S2":
                    sector_delta = deltas["D2"]
                    sector_focus = "Sector 2"
                else:
                    sector_delta = deltas["D3"]
                    sector_focus = "Sector 3"

                if should_emit_lap_coaching_message(
                    "coach_race_sector_trend_loss",
                    completed_lap_num,
                    min_laps_between=3,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            "LOW",
                            "coach_race_sector_trend_loss",
                            f"{sector_focus} is costing most of the time compared to recent race pace "
                            f"({format_signed_seconds(sector_delta)})."
                        )
                    )

            if sector_trend.get("meaningful_inconsistency"):
                least_consistent_sector = sector_trend.get(
                    "least_consistent_sector"
                )

                if should_emit_lap_coaching_message(
                    "coach_race_sector_inconsistent",
                    completed_lap_num,
                    min_laps_between=4,
                ):
                    coaching_messages.append(
                        make_coaching_message(
                            "LOW",
                            "coach_race_sector_inconsistent",
                            f"{least_consistent_sector} is the least consistent sector over recent clean laps. "
                            "Focus on repeatability."
                        )
                    )

    return sort_engineer_messages(coaching_messages)[:2]

def should_emit_coaching_message(
    context,
    completed_lap_num,
    min_laps_between=2,
    min_seconds_between=60,
):
    current_time = time.time()

    last_lap = last_coaching_lap_by_context.get(context)
    last_time = last_coaching_time_by_context.get(context)

    if last_lap is not None:
        laps_since_last = completed_lap_num - last_lap

        if laps_since_last < min_laps_between:
            return False

    if last_time is not None:
        seconds_since_last = current_time - last_time

        if seconds_since_last < min_seconds_between:
            return False

    last_coaching_lap_by_context[context] = completed_lap_num
    last_coaching_time_by_context[context] = current_time

    return True


def get_completed_lap_num(latest_lap_data):
    if latest_lap_data is None:
        return None

    return latest_lap_data.current_lap_num - 1

def format_signed_seconds(milliseconds):
    if milliseconds is None:
        return "--"

    seconds = milliseconds / 1000

    if seconds > 0:
        return f"+{seconds:.3f}s"

    return f"{seconds:.3f}s"


def calculate_average(values):
    if not values:
        return None

    return sum(values) / len(values)


def calculate_range(values):
    if not values:
        return None

    return max(values) - min(values)


def calculate_standard_deviation(values):
    if not values:
        return None

    average = calculate_average(values)

    variance = sum(
        (value - average) ** 2
        for value in values
    ) / len(values)

    return variance ** 0.5


def get_completed_sector_lap_entry(latest_completed_lap_sectors):
    if latest_completed_lap_sectors is None:
        return None

    sector_1 = latest_completed_lap_sectors.sector_1_time_ms
    sector_2 = latest_completed_lap_sectors.sector_2_time_ms
    sector_3 = latest_completed_lap_sectors.sector_3_time_ms

    if sector_1 is None or sector_2 is None or sector_3 is None:
        return None

    if sector_1 <= 0 or sector_2 <= 0 or sector_3 <= 0:
        return None

    lap_time = sector_1 + sector_2 + sector_3

    return {
        "lap_num": latest_completed_lap_sectors.lap_num,
        "lap_time_ms": lap_time,
        "sector_1_time_ms": sector_1,
        "sector_2_time_ms": sector_2,
        "sector_3_time_ms": sector_3,
    }


def calculate_sector_history_stats(sector_laps):
    if not sector_laps:
        return None

    sector_map = {
        "S1": "sector_1_time_ms",
        "S2": "sector_2_time_ms",
        "S3": "sector_3_time_ms",
        "lap": "lap_time_ms",
    }

    stats = {}

    for sector_name, key in sector_map.items():
        values = [
            lap[key]
            for lap in sector_laps
            if lap.get(key) is not None and lap.get(key) > 0
        ]

        if not values:
            continue

        stats[sector_name] = {
            "average_ms": calculate_average(values),
            "std_ms": calculate_standard_deviation(values),
            "range_ms": calculate_range(values),
            "values": values,
        }

    return stats

def is_clean_sector_trend_lap(
    completed_sector_entry,
    latest_car_damage=None,
    latest_session_data=None,
):
    if completed_sector_entry is None:
        return False, "No completed sector data"

    if is_safety_car_active(latest_session_data):
        return False, "Safety Car or VSC active"

    if is_major_damage_for_performance(latest_car_damage):
        return False, "Car damage affecting lap time"

    if len(recent_clean_sector_laps) >= 3:
        stats = calculate_sector_history_stats(recent_clean_sector_laps)

        if stats is not None and "lap" in stats:
            average_lap = stats["lap"]["average_ms"]
            std_lap = stats["lap"]["std_ms"]

            lap_outlier_limit = max(
                3500,
                std_lap * 3
            )

            if completed_sector_entry["lap_time_ms"] > average_lap + lap_outlier_limit:
                return False, "Possible incident or outlier lap"

        sector_keys = {
            "S1": "sector_1_time_ms",
            "S2": "sector_2_time_ms",
            "S3": "sector_3_time_ms",
        }

        for sector_name, key in sector_keys.items():
            if stats is None or sector_name not in stats:
                continue

            average_sector = stats[sector_name]["average_ms"]
            std_sector = stats[sector_name]["std_ms"]

            sector_outlier_limit = max(
                1500,
                std_sector * 3
            )

            if completed_sector_entry[key] > average_sector + sector_outlier_limit:
                return False, f"Possible incident or outlier in {sector_name}"

    return True, "Clean lap"

def analyze_race_sector_trend(
    latest_completed_lap_sectors,
    latest_car_damage=None,
    latest_session_data=None,
):
    global last_sector_trend_lap_logged
    global last_sector_trend_result

    result = {
        "enabled": True,
        "ready": False,
        "recorded": False,
        "reason": None,
        "history_count": len(recent_clean_sector_laps),
        "reference": None,
        "current": None,
        "deltas": None,
        "weakest_sector": None,
        "least_consistent_sector": None,
        "meaningful_loss": False,
        "meaningful_inconsistency": False,
        "messages": [],
    }

    if not is_race_mode(latest_session_data):
        result["enabled"] = False
        result["reason"] = "Race sector trend disabled outside race mode"
        return result

    completed_sector_entry = get_completed_sector_lap_entry(
        latest_completed_lap_sectors
    )

    if completed_sector_entry is None:
        result["reason"] = "No completed sector data yet"
        return result

    completed_lap_num = completed_sector_entry["lap_num"]

    if last_sector_trend_lap_logged == completed_lap_num:
        if last_sector_trend_result is not None:
            return last_sector_trend_result

        result["reason"] = "Lap already processed"
        return result

    is_clean_lap, clean_reason = is_clean_sector_trend_lap(
        completed_sector_entry,
        latest_car_damage,
        latest_session_data,
    )

    if not is_clean_lap:
        last_sector_trend_lap_logged = completed_lap_num
        result["reason"] = clean_reason
        last_sector_trend_result = result
        return result

    if len(recent_clean_sector_laps) < SECTOR_TREND_MIN_HISTORY:
        recent_clean_sector_laps.append(completed_sector_entry)

        last_sector_trend_lap_logged = completed_lap_num

        result["recorded"] = True
        result["history_count"] = len(recent_clean_sector_laps)

        if len(recent_clean_sector_laps) < SECTOR_TREND_MIN_HISTORY:
            result["reason"] = (
                f"Collecting clean sector history "
                f"({len(recent_clean_sector_laps)}/{SECTOR_TREND_MIN_HISTORY})"
            )
        else:
            result["reason"] = "Clean sector baseline ready from next lap"

        last_sector_trend_result = result
        return result

    reference_stats = calculate_sector_history_stats(
        recent_clean_sector_laps
    )

    if reference_stats is None:
        result["reason"] = "Unable to calculate sector trend reference"
        return result

    reference = {
        "AS1": reference_stats["S1"]["average_ms"],
        "AS2": reference_stats["S2"]["average_ms"],
        "AS3": reference_stats["S3"]["average_ms"],
        "average_lap": reference_stats["lap"]["average_ms"],

        "STD1": reference_stats["S1"]["std_ms"],
        "STD2": reference_stats["S2"]["std_ms"],
        "STD3": reference_stats["S3"]["std_ms"],
        "std_lap": reference_stats["lap"]["std_ms"],

        "range1": reference_stats["S1"]["range_ms"],
        "range2": reference_stats["S2"]["range_ms"],
        "range3": reference_stats["S3"]["range_ms"],
        "range_lap": reference_stats["lap"]["range_ms"],
    }

    deltas = {
        "D1": completed_sector_entry["sector_1_time_ms"] - reference["AS1"],
        "D2": completed_sector_entry["sector_2_time_ms"] - reference["AS2"],
        "D3": completed_sector_entry["sector_3_time_ms"] - reference["AS3"],
        "lap_delta": completed_sector_entry["lap_time_ms"] - reference["average_lap"],
    }

    sector_deltas = {
        "S1": deltas["D1"],
        "S2": deltas["D2"],
        "S3": deltas["D3"],
    }

    sector_stds = {
        "S1": reference["STD1"],
        "S2": reference["STD2"],
        "S3": reference["STD3"],
    }

    sector_ranges = {
        "S1": reference["range1"],
        "S2": reference["range2"],
        "S3": reference["range3"],
    }

    weakest_sector = max(
        sector_deltas,
        key=sector_deltas.get,
    )

    least_consistent_sector = max(
        sector_stds,
        key=sector_stds.get,
    )

    weakest_sector_delta = sector_deltas[weakest_sector]
    least_consistent_std = sector_stds[least_consistent_sector]
    least_consistent_range = sector_ranges[least_consistent_sector]

    meaningful_loss = (
        deltas["lap_delta"] >= SECTOR_TREND_LAP_LOSS_THRESHOLD_MS
        and weakest_sector_delta >= SECTOR_TREND_SECTOR_LOSS_THRESHOLD_MS
        and weakest_sector_delta >= (
            deltas["lap_delta"] * SECTOR_TREND_SECTOR_SHARE_THRESHOLD
        )
    )

    meaningful_inconsistency = (
        least_consistent_std >= SECTOR_TREND_STD_WARNING_MS
        and least_consistent_range >= SECTOR_TREND_RANGE_WARNING_MS
    )

    result["ready"] = True
    result["recorded"] = True
    result["reason"] = "Race sector trend analysed"
    result["history_count"] = len(recent_clean_sector_laps)
    result["reference"] = reference
    result["current"] = completed_sector_entry
    result["deltas"] = deltas
    result["weakest_sector"] = weakest_sector
    result["least_consistent_sector"] = least_consistent_sector
    result["meaningful_loss"] = meaningful_loss
    result["meaningful_inconsistency"] = meaningful_inconsistency

    result["messages"].append(
        "Race sector trend: "
        f"lap {completed_lap_num} was "
        f"{format_signed_seconds(deltas['lap_delta'])} "
        "versus recent clean race pace."
    )

    if meaningful_loss:
        result["messages"].append(
            f"{weakest_sector} caused most of the lap loss "
            f"({format_signed_seconds(weakest_sector_delta)})."
        )

    if meaningful_inconsistency:
        result["messages"].append(
            f"{least_consistent_sector} is the least consistent sector "
            f"(STD {least_consistent_std / 1000:.3f}s, "
            f"range {least_consistent_range / 1000:.3f}s)."
        )

    if not meaningful_loss and not meaningful_inconsistency:
        result["messages"].append(
            "Race sector trend is stable."
        )

    recent_clean_sector_laps.append(completed_sector_entry)
    last_sector_trend_lap_logged = completed_lap_num
    last_sector_trend_result = result

    return result

def is_safety_car_active(latest_session_data):
    if latest_session_data is None:
        return False

    return latest_session_data.safety_car_status in (1, 2)

def get_performance_front_wing_damage(latest_car_damage):
    if latest_car_damage is None:
        return 0

    return max(latest_car_damage.front_left_wing_damage, latest_car_damage.front_right_wing_damage,)  

def get_performance_aero_damage(latest_car_damage):
    if latest_car_damage is None:
        return 0
    
    return max(latest_car_damage.floor_damage, latest_car_damage.sidepod_damage, latest_car_damage.diffuser_damage,)

def get_performance_tyre_damage(latest_car_damage):
    if latest_car_damage is None:
        return 0
    
    return max(latest_car_damage.tyre_damage)

def is_major_damage_for_performance(latest_car_damage):
    if latest_car_damage is None:
        return False
    
    if get_performance_front_wing_damage(latest_car_damage) >= 20:
        return True
    
    if get_performance_aero_damage(latest_car_damage) >= 50:
        return True
    
    if get_performance_tyre_damage(latest_car_damage) >= 50:
        return True

    return False

def is_consistency_supported_session(latest_session_data):
    session_mode = get_session_mode(latest_session_data)

    return session_mode in (
        SESSION_MODE_RACE,
        SESSION_MODE_PRACTICE,
        SESSION_MODE_TIME_TRIAL,
    )

def get_consistency_thresholds(latest_session_data):
    session_mode = get_session_mode(latest_session_data)

    if session_mode == SESSION_MODE_TIME_TRIAL:
        return {"consistent": 400, "variable": 1000,} # 0.400s and 1.000s
    
    if session_mode == SESSION_MODE_PRACTICE:
        return {"consistent": 900, "variable": 1800,} # 0.900s and 1.800s
    
    if session_mode == SESSION_MODE_RACE:
        return {"consistent": 750, "variable": 1500,} # 0.750s and 1.500s


def analyze_consistency(latest_lap_data, latest_session_history, latest_car_damage=None, latest_session_data=None,):
    global last_consistency_lap_logged

    result = {
        "enabled": True,   # Whether the analysis is allowed in the current session
        "recorded": False, # Whether the current lap will be added to the recent lap list
        "reason": None,    # Why the analysis took place or did not take place
        "metrics": None,   # The calculated numbers
        "messages": [],    # The readable output
    }

    if latest_lap_data is None or latest_session_history is None:
        result["reason"] = "Not enough data"
        return result
    
    if not is_consistency_supported_session(latest_session_data):
        result["enabled"] = False
        result["reason"] = "Consistency analysis disabled"
        return result
    
    if is_safety_car_active(latest_session_data):
        result["reason"] = "Safety Car or VSC Active"
        return result
    
    if is_major_damage_for_performance(latest_car_damage):
        result["reason"] = "Car damage affecting lap time"
        return result
    
    # No lap data yet         -> "enabled" = True  -> Analysis allowed, but data is missing
    # No session history yet  -> "enabled" = True  -> Analysis allowed, but comparison data is missing
    # Safety Car/VSC          -> "enabled" = True  -> Analysis allowed, but temporarily paused
    # Major damage            -> "enabled" = True  -> Analysis allowed, but lap timing not useful
    # Invalid lap time        -> "enabled" = True  -> Analysis allowed, but this lap is unstable
    # Duplicate laps          -> "enabled" = True  -> Analysis allowed, but lap already recorded
    # Quali or Supported Mode -> "enabled" = False -> Analysis disabled, as not necessary

    
    completed_lap_num = get_completed_lap_num(latest_lap_data) # Current number of laps - 1
    last_lap = latest_lap_data.last_lap_time_ms                # The time of the most recently completed lap
    best_lap = latest_session_history.best_lap_time_ms         # Time of best lap in this race/session

    if completed_lap_num is None or completed_lap_num <= 0: # no completed lap = no consistency analysis yet.
        result["reason"] = "No completed laps"
        return result
    
    if last_lap is None or best_lap is None: # no lap times = no comparison = no consistency analysis
        result["reason"] = "Missing lap times"
        return result
    
    if last_lap <= 0 or best_lap <= 0: # cannot have negative laps
        result["reason"] = "Invalid lap time"
        return result
    
    if last_consistency_lap_logged == completed_lap_num: # avoids recorded the same lap twice, due to multiple refreshes per second
        result["reason"] = "Lap already recorded"
        return result
    
    if last_lap > best_lap * 1.10: # ignores laps more than 10% slower than best -> Pits, spins, crashes or safety car lap
        result["reason"]  = "Outlier lap ignored"
        return result
    
    last_consistency_lap_logged= completed_lap_num

    recent_valid_laps.append(
        {
            "lap_num": completed_lap_num,
            "lap_time_ms": last_lap, # <== Typo (lap_time_ms ✅ vs lap_times_ms)
            "delta_to_best_ms": last_lap - best_lap,
        }
    )

    # ^
    # saves laps into "recent_valid_lap" with a history limit of 5 valid laps (deque(maxlen=5))

    result["recorded"] = True
    result["reason"] = "Lap recorded"

    if len(recent_valid_laps) < 3: # waits for a minimum of 3 laps before conducting the consistency analysis
        result["reason"] = "Waiting for more valid laps"
        return result
    
    lap_times = [
        lap["lap_time_ms"] # <== Typo (lap_time_ms ✅ vs lap_times_ms)
        for lap in recent_valid_laps # converts the stored lap dictionaries into a simple list of lap times
    ]

    lap_range = max(lap_times) - min(lap_times) # consistency metrics (distance between best recent lap and worst recent lap)
    avg_lap = sum(lap_times) / len(lap_times) # average recent lap time

    variance = sum((lap_time - avg_lap) ** 2 for lap_time in lap_times) / len(lap_times)

    standard_deviation = variance ** 0.5 # how unstable the whole group of laps is

    thresholds = get_consistency_thresholds(latest_session_data)

    if lap_range <= thresholds["consistent"]: 
        status = "consistent"              # Small lap spread  → consistent
    elif lap_range <= thresholds["variable"]: 
        status = "variable"                # Medium lap spread → variable
    else:
        status = "inconsistent"            # Large lap spread  → inconsistent

    result["metrics"] = { # from dictionary "results", component ["metrics"] -> calculated numbers
        "status": status,
        "lap_count": len(recent_valid_laps),
        "lap_range_ms": lap_range,
        "average_lap_ms": avg_lap,
        "standard_deviation_ms": standard_deviation,
        "laps": list(recent_valid_laps),
    }

    lap_count = result["metrics"]["lap_count"] # <-- question
    # ======================================================================================
    # result = {
    #     "enabled": True,   # Whether the analysis is allowed in the current session
    #     "recorded": False, # Whether the current lap will be added to the recent lap list
    #     "reason": None,    # Why the analysis took place or did not take place
    #     "metrics": None,   # The calculated numbers
    #     "messages": [],    # The readable output
    # }
    # consistency = performance_analysis.get("consistency")
    # metrics = consistency.get("metrics")
    # lap_count = metrics.get("lap_count")
    # ======================================================================================

    lap_range_seconds = lap_range / 1000
    standard_deviation_seconds = standard_deviation / 1000

    session_mode = get_session_mode(latest_session_data)

    if status == "consistent":
        if session_mode == SESSION_MODE_PRACTICE:
            result["messages"].append(
                f"Consistent long-run pace - last {lap_count} valid laps within {lap_range_seconds:.3f}s."
            )

        elif session_mode == SESSION_MODE_TIME_TRIAL:
            result["messages"].append(
                f"Consistent attempts - last {lap_count} valid laps within {lap_range_seconds:.3f}s."
            )

        else:
            result["messages"].append(
                f"Consistent race pace - last {lap_count} valid laps within {lap_range_seconds:.3f}s."
            )

    elif status == "variable":
        result["messages"].append(
            f"Pace variation detected - last {lap_count} valid laps spread by {lap_range_seconds:.3f}s."
        )

    else:
        result["messages"].append(
            f"Inconsistent pace - last {lap_count} valid laps spread by {lap_range_seconds:.3f}s "
            f"(std dev {standard_deviation_seconds:.3f}s)."
        )

    return result

    # if lap_range <= 500:
    #     messages.append(
    #         f"Consistent pace - last {len(recent_valid_laps)} laps within {lap_range / 1000:.3f}s"
    #     )

    # elif lap_range <= 1500:
    #     messages.append(
    #         f"Pace variation detected - last {len(recent_valid_laps)} laps spread by {lap_range / 1000:.3f}s"
    #     )

    # else:
    #     messages.append(
    #         f"Inconsistent pace - lap time spread is {lap_range / 1000:.3f}s"
    #     )

    # return messages
    


    # =========================================================================================================================================== 
    # Previous consistency analysis matrix and system (Unverified/Untested)

    # messages = []

    # if latest_lap_data is None or latest_session_history is None:
    #     return messages

    # current_lap_num = latest_lap_data.current_lap_num
    # last_lap = latest_lap_data.last_lap_time_ms
    # best_lap = latest_session_history.best_lap_time_ms

    # if last_lap is None or best_lap is None:
    #     return messages

    # if last_lap <= 0 or best_lap <= 0:
    #     return messages

    # if last_consistency_lap_logged == current_lap_num:
    #     return messages

    # last_consistency_lap_logged = current_lap_num

    # if last_lap > best_lap * 1.10:
    #     return messages

    # recent_valid_laps.append(last_lap)

    # if len(recent_valid_laps) < 3:
    #     return messages

    # lap_range = max(recent_valid_laps) - min(recent_valid_laps)
    # avg_lap = sum(recent_valid_laps) / len(recent_valid_laps)

    # if lap_range <= 500:
    #     messages.append(
    #         f"Consistent pace - last {len(recent_valid_laps)} laps within {lap_range / 1000:.3f}s"
    #     )

    # elif lap_range <= 1500:
    #     messages.append(
    #         f"Pace variation detected - last {len(recent_valid_laps)} laps spread by {lap_range / 1000:.3f}s"
    #     )

    # else:
    #     messages.append(
    #         f"Inconsistent pace - lap time spread is {lap_range / 1000:.3f}s"
    #     )

    # return messages       