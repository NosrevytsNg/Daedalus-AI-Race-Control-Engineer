import csv 
import os 
from datetime import datetime

class TelemetryLogger:
    def __init__(self, log_dir="logs"):
        
        PROJECT_ROOT = os.path.dirname (
            os.path.dirname(
                os.path.dirname(
                    os.path.abspath(__file__)
                )
            )
        )

        self.log_dir = os.path.join(PROJECT_ROOT, "logs")


        self.session_file = None
        self.latest_logged_lap = None

        os.makedirs(self.log_dir, exist_ok=True)

    def start_session(self, session_uid):
        filename = f"Session_{session_uid}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        self.session_file = os.path.join(self.log_dir, filename)

        with open(self.session_file, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                "timestamp",
                "session_uid",
                "lap_num",
                "last_lap_num",
                "current_lap_num",
                "sector_1_ms"
                "sector_2_ms",
                "sector_3_ms",
                "speed",
                "throttle",
                "brake",
                "ers_energy_storage",
                "fuel_remaining_laps"
                "fuel_in_tank",
                "tyre_wear_rl",
                "tyre_wear_rr",
                "tyre_wear_fl",
                "tyre_wear_fr",
            ])

    def log_lap_capture(
            self,
            session_uid,
            latest_lap_data,
            latest_telemetry,
            latest_car_status,
            latest_car_damage,
            latest_completed_lap_sectors,
    ):
        if self.session_file is None:
            self.start_session(session_uid)

        if latest_lap_data is None:
            return
        
        current_lap_num = latest_lap_data.current_lap_num

        if self.latest_logged_lap == current_lap_num:
            return
        
        self.latest_logged_lap == current_lap_num

        sector_3 = None
        if latest_completed_lap_sectors is not None:
            sector_3 = latest_completed_lap_sectors.sector_3_time_ms

        tyre_wear = [None, None, None, None]
        if latest_car_damage is not None:
            tyre_wear = latest_car_damage.tyre_wear

        with open(self.session_file, "a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([
                datetime.now().isoformat(),
                session_uid,
                latest_lap_data.current_lap_num,
                latest_lap_data.last_lap_time_ms,
                latest_lap_data.sector_1_time_ms,
                latest_lap_data.sector_2_time_ms,
                sector_3,
                latest_telemetry.speed if latest_telemetry else None,
                latest_telemetry.throttle if latest_telemetry else None,
                latest_telemetry.brake if latest_telemetry else None,
                latest_car_status.ers_energy_storage if latest_car_status else None,
                latest_car_status.fuel_remaining_laps if latest_car_status else None,
                latest_car_status.fuel_in_tank if latest_car_status else None,
                tyre_wear[0],
                tyre_wear[1],
                tyre_wear[2],
                tyre_wear[3],
            ])
