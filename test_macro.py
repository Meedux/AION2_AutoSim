"""Macro test harness — simulates detection events and validates the simplified macro flow

This script runs the simplified Tab -> R/T -> Combat -> Cooldown -> loop entirely
using the driver-backed input layer. No YOLO/detection required.
"""

import time
import random
from driver_input import open_driver, tap_key, focus_window


def simulated_monster_sequence(window_w=1280, window_h=720, monster_pos=(640, 520)):
    print("Starting simulated macro sequence")
    h = open_driver()
    if not h:
        print("Driver not open — ensure driver is installed and accessible at \\.\AIONVirtualHID")
        return

    # Step 1: simulate detection -> press Tab, then R or T
    print("Detected monster at", monster_pos)
    focus_window(None)  # best-effort; driver doesn't need hwnd here but keep interface parity
    tap_key('tab')
    time.sleep(0.08)
    choice = 'r' if random.random() < 0.5 else 't'
    print(f"Sent keys: Tab + {choice.upper()}")
    tap_key(choice)

    # Step 2: compute combat duration based on distance to lower-center region
    mx, my = monster_pos
    anchor_x = window_w/2.0
    anchor_y = window_h * 0.85
    dist = ((mx - anchor_x)**2 + (my - anchor_y)**2)**0.5
    norm = dist / max(1.0, max(window_w, window_h))
    combat_duration = max(0.75, min(4.0, 0.75 + norm*3.5))
    print(f"Entering Combat Period for {combat_duration:.2f} seconds (simulated)")
    time.sleep(combat_duration)

    # Step 3: cooldown - press F
    print("Combat ended — entering cooldown and pressing F")
    tap_key('f')
    # Simulate cooldown (short wait)
    time.sleep(stealth_cooldown := 2.0)

    print("Cooldown complete — returning to detection mode")


if __name__ == '__main__':
    # Run a few simulated cycles
    for i in range(3):
        simulated_monster_sequence(window_w=1280, window_h=720, monster_pos=(640, 520 + i*10))
        time.sleep(1.0)
