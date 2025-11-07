"""
STEALTH CONFIGURATION FOR CRYENGINE ANTI-CHEAT EVASION

CryEngine has AGGRESSIVE anti-cheat that detects:
- Too-fast action timing (instant responses)
- Perfect mouse movements (straight lines)
- Consistent timing patterns
- High detection polling rates

This config makes the bot look like a slow, cautious human player.
"""
import random

# ============================================================================
# CRITICAL: ULTRA-SLOW TIMING TO AVOID CRYENGINE DETECTION
# ============================================================================

# Detection loop FPS (how often we check for mobs/objects)
# MUST BE LOW - CryEngine detects high polling rates
DETECTION_FPS = 1  # Only check once per second (very human-like)

# Startup delay before ANY automation begins (seconds)
# Gives CryEngine time to see "player is idle after loading"
STARTUP_DELAY_MIN = 8.0
STARTUP_DELAY_MAX = 15.0

# Warmup period - first N actions have EXTRA delays
# This simulates a human "getting oriented" after starting
WARMUP_ACTIONS = 10
WARMUP_EXTRA_DELAY_MIN = 2.0  # Extra seconds per action
WARMUP_EXTRA_DELAY_MAX = 5.0

# ============================================================================
# ACTION TIMING - HUMAN-LIKE DELAYS
# ============================================================================

# Base cooldown between ANY actions (seconds)
# CryEngine WILL detect if actions are too frequent
ACTION_COOLDOWN_MIN = 0.8  # Minimum delay between actions
ACTION_COOLDOWN_MAX = 2.0  # Maximum delay between actions

# Additional delay after clicking a mob (seconds)
POST_CLICK_DELAY_MIN = 0.5
POST_CLICK_DELAY_MAX = 1.2

# Delay after pressing movement keys (seconds)
POST_MOVEMENT_DELAY_MIN = 0.3
POST_MOVEMENT_DELAY_MAX = 0.8

# ============================================================================
# MOUSE MOVEMENT - SMOOTH & HUMAN-LIKE
# ============================================================================

# Mouse movement duration (seconds)
MOUSE_MOVE_DURATION_MIN = 0.2
MOUSE_MOVE_DURATION_MAX = 0.5

# Mouse jitter/randomization (pixels)
# Adds random offset to click positions
MOUSE_JITTER_X = 15  # ±15 pixels horizontal
MOUSE_JITTER_Y = 15  # ±15 pixels vertical

# Target click position on mob (percentage down from top of the box)
# Clicking in the LOWER PART of the detection box (not center, not below)
MOB_CLICK_Y_MIN = 0.70  # 70% down from top of box (lower part)
MOB_CLICK_Y_MAX = 0.90  # 90% down from top of box (near bottom edge)

# ============================================================================
# IDLE SIMULATION - CRITICAL FOR STEALTH
# ============================================================================

# Periodic "thinking" pauses where bot does nothing
# This simulates human decision-making
IDLE_CHECK_INTERVAL = 30.0  # Check every 30 seconds
IDLE_PROBABILITY = 0.35     # 35% chance to idle when checked
IDLE_DURATION_MIN = 4.0     # Minimum idle time (seconds)
IDLE_DURATION_MAX = 12.0    # Maximum idle time (seconds)

# ============================================================================
# MOVEMENT KEY HOLD DURATION
# ============================================================================

# How long to hold W/A/S/D keys (seconds)
KEY_HOLD_DURATION_MIN = 0.4
KEY_HOLD_DURATION_MAX = 1.2

# Randomization for key hold (percentage)
# Adds ±X% variation to hold duration
KEY_HOLD_VARIATION = 0.25  # ±25%

# Turn duration for 70-degree turns (approximate)
# Depends on game sensitivity, but ~1-2s is typical for 70 degrees
TURN_70_DEGREES_MIN = 1.0  # seconds
TURN_70_DEGREES_MAX = 1.8  # seconds

# ============================================================================
# MOUSE DRAGGING - SMOOTH MOVEMENT (NO TELEPORT)
# ============================================================================

# Always use smooth mouse dragging (Bezier curves)
MOUSE_DRAG_ENABLED = True
MOUSE_DRAG_CURVE = 0.15  # Bezier curve intensity (0-1, higher = more curved)
MOUSE_DRAG_MIN_DURATION = 0.15  # Minimum drag time (seconds)
MOUSE_DRAG_MAX_DURATION = 0.40  # Maximum drag time (seconds)

# ============================================================================
# MOVEMENT MACRO - RANDOMIZED PATTERNS
# ============================================================================

# Movement pattern types
MOVEMENT_PATTERNS = [
    "forward",           # Just move forward
    "forward_zigzag",    # Forward with slight left/right
    "circle_left",       # Circle strafe left
    "circle_right",      # Circle strafe right
    "backup_turn",       # Backup and turn
    "strafe_left",       # Strafe left
    "strafe_right",      # Strafe right
]

# Movement pattern duration (seconds)
MOVEMENT_PATTERN_MIN = 1.5
MOVEMENT_PATTERN_MAX = 4.0

# Chance to change movement pattern (0-1)
MOVEMENT_PATTERN_CHANGE_CHANCE = 0.25  # 25% chance per action

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_action_delay():
    """Get random delay between actions (seconds)."""
    return random.uniform(ACTION_COOLDOWN_MIN, ACTION_COOLDOWN_MAX)

def get_post_click_delay():
    """Get random delay after clicking (seconds)."""
    return random.uniform(POST_CLICK_DELAY_MIN, POST_CLICK_DELAY_MAX)

def get_post_movement_delay():
    """Get random delay after movement (seconds)."""
    return random.uniform(POST_MOVEMENT_DELAY_MIN, POST_MOVEMENT_DELAY_MAX)

def get_mouse_move_duration():
    """Get random mouse movement duration (seconds)."""
    return random.uniform(MOUSE_MOVE_DURATION_MIN, MOUSE_MOVE_DURATION_MAX)

def get_mouse_jitter():
    """Get random mouse position jitter (dx, dy in pixels)."""
    dx = random.randint(-MOUSE_JITTER_X, MOUSE_JITTER_X)
    dy = random.randint(-MOUSE_JITTER_Y, MOUSE_JITTER_Y)
    return dx, dy

def get_mob_click_offset(mob_height):
    """Get Y offset for clicking on mob (pixels from top of mob box)."""
    ratio = random.uniform(MOB_CLICK_Y_MIN, MOB_CLICK_Y_MAX)
    return int(mob_height * ratio)

def should_idle():
    """Check if bot should enter idle state (returns bool)."""
    return random.random() < IDLE_PROBABILITY

def get_idle_duration():
    """Get random idle duration (seconds)."""
    return random.uniform(IDLE_DURATION_MIN, IDLE_DURATION_MAX)

def get_key_hold_duration():
    """Get random key hold duration with variation (seconds)."""
    base = random.uniform(KEY_HOLD_DURATION_MIN, KEY_HOLD_DURATION_MAX)
    variation = base * KEY_HOLD_VARIATION * random.uniform(-1, 1)
    return max(0.1, base + variation)

def get_startup_delay():
    """Get random startup delay (seconds)."""
    return random.uniform(STARTUP_DELAY_MIN, STARTUP_DELAY_MAX)

def get_warmup_delay():
    """Get extra delay for warmup actions (seconds)."""
    return random.uniform(WARMUP_EXTRA_DELAY_MIN, WARMUP_EXTRA_DELAY_MAX)

def get_turn_70_degrees_duration():
    """Get duration to turn approximately 70 degrees (seconds)."""
    return random.uniform(TURN_70_DEGREES_MIN, TURN_70_DEGREES_MAX)

def get_mouse_drag_duration():
    """Get random mouse drag duration (seconds)."""
    return random.uniform(MOUSE_DRAG_MIN_DURATION, MOUSE_DRAG_MAX_DURATION)

def get_movement_pattern():
    """Get random movement pattern."""
    return random.choice(MOVEMENT_PATTERNS)

def get_movement_pattern_duration():
    """Get duration for movement pattern (seconds)."""
    return random.uniform(MOVEMENT_PATTERN_MIN, MOVEMENT_PATTERN_MAX)

def should_change_movement_pattern():
    """Check if movement pattern should change."""
    return random.random() < MOVEMENT_PATTERN_CHANGE_CHANCE
