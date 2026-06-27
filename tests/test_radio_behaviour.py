import time
from src.engineer.race_engineer import (prepare_delivery_messages,get_radio_queue_size,)

critical_tyre = {
    "priority": "CRITICAL",
    "category": "tyre",
    "context": "tyre_damage_critical",
    "text": "CRITICAL TYRE DAMAGE - BOX NOW",
}

drs_available = {
    "priority": "LOW",
    "category": "drs",
    "context": "drs_available",
    "text": "DRS available",
}

ers_low = {
    "priority": "MEDIUM",
    "category": "ers",
    "context": "ers_low",
    "text": "ERS low",
}

print("TEST 1: only DRS")
print(prepare_delivery_messages([drs_available]))
print("queue:", get_radio_queue_size())

time.sleep(1)

print("TEST 2: critical tyre + DRS")
print(prepare_delivery_messages([critical_tyre, drs_available]))
print("queue:", get_radio_queue_size())

time.sleep(1)

print("TEST 3: ERS low only")
print(prepare_delivery_messages([ers_low]))
print("queue:", get_radio_queue_size())

time.sleep(4.2)

print("TEST 4: ERS low after cooldown")
print(prepare_delivery_messages([ers_low]))
print("queue:", get_radio_queue_size())

print("TEST 5: DRS expiry")

prepare_delivery_messages([drs_available])
print("queue after DRS input:", get_radio_queue_size())

time.sleep(3.5)

print(prepare_delivery_messages([drs_available]))
print("queue after expiry check:", get_radio_queue_size())