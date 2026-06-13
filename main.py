from src.telemetry.listener import start_listener


def main():
    print("================================")
    print("DAEDALUS")
    print("AI Race Engineer & Strategy Platform")
    print("================================\n")

    start_listener()


if __name__ == "__main__":
    main()





# ===============================================
# Roadmap
# ===============================================
#1. Decode live car telemetry -> Packet 6: Car Telemetry (Speed, gear, RPM, throttle, brake, DRS) - [Completed]
#2. Decode race data -> Packet 2: Lap Data (Position, lap number, sector, current lap time, gap ahead, gap behind) - [Completed]
#3. Display clean live telemetry (dashboard-style terminal output, not packet spam) - [Completed]
#4. Decode weather/session data -> Packet 5: Weather & Session Data (Weather, track temp, air temp, session type, session duration, etc.)
#5. Decode tyre/wear/damage data -> Packet 7/10/12 (Tyres, fuel, ERS, damage))
#6. Build rule-based race engineer
#7. Build strategy advisor (pit stop timing, tyre choice, fuel management)
#8. Performance Analysis
#9. Driving Recommendations (Braking points, throttle application, optimal racing line)
#10. Add voice later (Daedalus speaks key warnings only)
#11. LLM Race Engineer

# ===============================================

#1. Decode live car telemetry - [Completed]
#   -> Packet 6: Car Telemetry (Speed, Gear, RPM, Throttle, Brake, DRS)

#2. Decode race data - [Completed]
#   -> Packet 2: Lap Data (Position, Lap Number, Sector, Current Lap Time, Gap Ahead, Gap Behind)

#3. Display clean live telemetry - [Completed]
#   (Dashboard-style terminal output, not packet spam)

#4. Decode vehicle state
#   -> Packet 7/10/12 (Tyres, Fuel, ERS, Damage)

#5. Decode weather/session data
#   -> Packet 1: Session Data (Weather, Track Temp, Air Temp, Session Type, Session Duration)

#6. Build rule-based race engineer
#   (Tyre warnings, Fuel warnings, ERS management, Damage alerts)

#7. Build strategy advisor
#   (Pit stop timing, Tyre choice, Fuel management, Undercut/Overcut)

#8. Performance analysis
#   (Sector comparison, Lap comparison, Time-loss analysis)

#9. Driving recommendations
#   (Braking points, Throttle application, Corner exit analysis, Racing line insights)

#10. Add voice interface
#    (Daedalus speaks key warnings and answers questions)

#11. LLM Race Engineer
#    (Natural language race discussions, strategy conversations, personalised coaching)