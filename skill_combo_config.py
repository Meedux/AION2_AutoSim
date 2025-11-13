"""Skill Combo Macro Configuration System

Highly configurable skill combo system with:
- Individual cooldown tracking for each keybind
- Multiple combo sets with their own cooldowns
- Hardware-level input execution
- Flexible key combinations (1-9, 0, -, =, Alt+, Ctrl+)
"""
import time
from typing import List, Dict, Tuple, Optional
from loguru import logger
import random


# ============================================================================
# SKILL KEYBIND COOLDOWN CONFIGURATION
# ============================================================================

# Individual skill cooldowns (in seconds) for each keybind
# User can modify these values for each skill they use
SKILL_COOLDOWNS = {
    # Number row skills
    '1': 10.0,
    '2': 12.0,
    '3': 15.0,
    '4': 8.0,
    '5': 20.0,
    '6': 18.0,
    '7': 25.0,
    '8': 30.0,
    '9': 15.0,
    '0': 10.0,
    '-': 45.0,
    '=': 60.0,
    
    # Alt + number row skills
    'alt+1': 10.0,
    'alt+2': 12.0,
    'alt+3': 15.0,
    'alt+4': 8.0,
    'alt+5': 20.0,
    'alt+6': 18.0,
    'alt+7': 25.0,
    'alt+8': 30.0,
    'alt+9': 15.0,
    'alt+0': 10.0,
    'alt+-': 45.0,
    'alt+=': 60.0,
    
    # Ctrl + number row skills
    'ctrl+1': 10.0,
    'ctrl+2': 12.0,
    'ctrl+3': 15.0,
    'ctrl+4': 8.0,
    'ctrl+5': 20.0,
    'ctrl+6': 18.0,
    'ctrl+7': 25.0,
    'ctrl+8': 30.0,
    'ctrl+9': 15.0,
    'ctrl+0': 10.0,
    'ctrl+-': 45.0,
    'ctrl+=': 60.0,
}


# ============================================================================
# COMBO SET CONFIGURATION
# ============================================================================

# Each combo set has:
# - name: Descriptive name for the combo
# - skills: List of skill keybinds to execute in order
# - cooldown: Combo set cooldown (seconds) - how long before combo can be used again
# - delay_between_skills: Delay between each skill activation (seconds)
# - enabled: Whether this combo is active

COMBO_SETS = [
    {
        'name': 'Basic DPS Rotation',
        'skills': ['1', '2', '3', '4'],  # Execute skills 1, 2, 3, 4 in order
        'cooldown': 60.0,  # Can use this combo every 60 seconds
        'delay_between_skills': 0.5,  # 0.5s delay between each skill
        'enabled': True,
    },
    {
        'name': 'Buff Combo',
        'skills': ['alt+1', 'alt+2', 'alt+3'],
        'cooldown': 120.0,  # 2 minute cooldown
        'delay_between_skills': 0.8,
        'enabled': True,
    },
    {
        'name': 'Ultimate Combo',
        'skills': ['ctrl+1', '5', '6', '7', 'ctrl+2'],
        'cooldown': 180.0,  # 3 minute cooldown
        'delay_between_skills': 1.0,
        'enabled': True,
    },
    # Add more combo sets here as needed
    # Example:
    # {
    #     'name': 'AOE Combo',
    #     'skills': ['8', '9', '0', 'alt+4'],
    #     'cooldown': 90.0,
    #     'delay_between_skills': 0.6,
    #     'enabled': True,
    # },
]


# ============================================================================
# SKILL EXECUTION SETTINGS
# ============================================================================

# Randomize delays slightly for human-like behavior (±X%)
DELAY_RANDOMIZATION = 0.15  # ±15% random variation

# Enable/disable the entire skill combo system
SKILL_COMBO_ENABLED = True

# Priority order: which combo sets to try first (by index)
# If not specified, will try combos in the order they appear in COMBO_SETS
COMBO_PRIORITY = None  # None = use default order, or [2, 0, 1] for custom priority

# ============================================================================
# STEALTH ATTACK MODE CONFIGURATION
# ============================================================================

# Attack mode randomization - makes bot behavior unpredictable
# The bot will randomly choose between:
# 1. Standard attack (double-click)
# 2. Single skill press
# 3. Full combo set

STEALTH_ATTACK_MODE_ENABLED = True

# Probability weights for each attack type (must sum to 1.0)
ATTACK_MODE_WEIGHTS = {
    'standard_attack': 0.50,    # 50% chance - double-click only
    'single_skill': 0.30,        # 30% chance - press one skill
    'combo_set': 0.20,           # 20% chance - execute full combo
}

# Only trigger skills when mob has health bar (mob_combat_health detected)
REQUIRE_MOB_HEALTH_FOR_SKILLS = False

# When using single skill mode, pick from this pool (empty = use all skills)
SINGLE_SKILL_POOL = ['1', '2', '3', '4', '5']  # Only use these skills for single-skill attacks

# Cooldown for single skill attacks (seconds)
SINGLE_SKILL_GLOBAL_COOLDOWN = 1.5  # GCD between single skill uses


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_skill_cooldown(skill: str) -> float:
    """Get the cooldown for a specific skill keybind."""
    skill_lower = skill.lower()
    return SKILL_COOLDOWNS.get(skill_lower, 10.0)  # Default 10s if not found


def get_randomized_delay(base_delay: float) -> float:
    """Add random variation to delay for human-like behavior."""
    variation = base_delay * DELAY_RANDOMIZATION
    return base_delay + random.uniform(-variation, variation)


def get_enabled_combo_sets() -> List[Dict]:
    """Get all enabled combo sets in priority order."""
    enabled = [combo for combo in COMBO_SETS if combo.get('enabled', True)]
    
    if COMBO_PRIORITY is not None:
        # Reorder based on priority
        try:
            ordered = []
            for idx in COMBO_PRIORITY:
                if 0 <= idx < len(enabled):
                    ordered.append(enabled[idx])
            # Add any combos not in priority list
            for combo in enabled:
                if combo not in ordered:
                    ordered.append(combo)
            return ordered
        except Exception as e:
            logger.warning(f"Invalid COMBO_PRIORITY, using default order: {e}")
    
    return enabled


def validate_combo_set(combo: Dict) -> Tuple[bool, str]:
    """Validate a combo set configuration.
    
    Returns:
        (is_valid, error_message)
    """
    if not isinstance(combo, dict):
        return False, "Combo must be a dictionary"
    
    if 'skills' not in combo:
        return False, "Combo missing 'skills' field"
    
    if not isinstance(combo['skills'], list) or len(combo['skills']) == 0:
        return False, "Combo 'skills' must be a non-empty list"
    
    # Validate each skill exists in SKILL_COOLDOWNS
    for skill in combo['skills']:
        skill_lower = skill.lower()
        if skill_lower not in SKILL_COOLDOWNS:
            return False, f"Unknown skill keybind: {skill}"
    
    if 'cooldown' in combo and combo['cooldown'] < 0:
        return False, "Combo cooldown cannot be negative"
    
    if 'delay_between_skills' in combo and combo['delay_between_skills'] < 0:
        return False, "Delay between skills cannot be negative"
    
    return True, ""


def parse_skill_keybind(skill: str) -> Tuple[Optional[str], str]:
    """Parse a skill keybind into (modifier, key).
    
    Examples:
        '1' -> (None, '1')
        'alt+1' -> ('alt', '1')
        'ctrl+5' -> ('ctrl', '5')
    
    Returns:
        (modifier, key) where modifier is None, 'alt', or 'ctrl'
    """
    skill_lower = skill.lower().strip()
    
    if 'alt+' in skill_lower:
        key = skill_lower.replace('alt+', '')
        return ('alt', key)
    elif 'ctrl+' in skill_lower:
        key = skill_lower.replace('ctrl+', '')
        return ('ctrl', key)
    else:
        return (None, skill_lower)


# ============================================================================
# CONFIGURATION VALIDATION
# ============================================================================

def validate_configuration() -> bool:
    """Validate the entire configuration on startup.
    
    Returns:
        True if configuration is valid, False otherwise
    """
    logger.info("Validating skill combo configuration...")
    
    errors = []
    
    # Validate SKILL_COOLDOWNS
    for skill, cooldown in SKILL_COOLDOWNS.items():
        if cooldown < 0:
            errors.append(f"Skill '{skill}' has negative cooldown: {cooldown}")
    
    # Validate each combo set
    for idx, combo in enumerate(COMBO_SETS):
        is_valid, error_msg = validate_combo_set(combo)
        if not is_valid:
            errors.append(f"Combo set {idx} ('{combo.get('name', 'unnamed')}'): {error_msg}")
    
    if errors:
        logger.error("Skill combo configuration errors:")
        for error in errors:
            logger.error(f"  - {error}")
        return False
    
    logger.success(f"✓ Skill combo configuration valid ({len(COMBO_SETS)} combo sets)")
    return True


# ============================================================================
# USER CONFIGURATION GUIDE
# ============================================================================

"""
HOW TO CONFIGURE:

1. SET INDIVIDUAL SKILL COOLDOWNS:
   Modify SKILL_COOLDOWNS dictionary with your actual skill cooldowns.
   Example:
       '1': 10.0,    # Skill on key 1 has 10 second cooldown
       'alt+5': 20.0, # Skill on Alt+5 has 20 second cooldown

2. CREATE COMBO SETS:
   Add entries to COMBO_SETS list. Each combo needs:
   - name: Description of the combo
   - skills: List of keys to press in order ['1', '2', 'alt+3']
   - cooldown: How long before combo can be used again (seconds)
   - delay_between_skills: Delay between each skill press (seconds)
   - enabled: True/False to enable/disable

3. ADJUST TIMING:
   - DELAY_RANDOMIZATION: How much to randomize delays (0.15 = ±15%)
   - Individual skill cooldowns in SKILL_COOLDOWNS

4. ENABLE/DISABLE:
   - SKILL_COMBO_ENABLED: Master on/off switch
   - Individual combo 'enabled' field: Enable/disable specific combos

5. PRIORITY:
   - COMBO_PRIORITY: [2, 0, 1] to execute combos in that order
   - None = use default order from COMBO_SETS

EXAMPLE COMBO:
{
    'name': 'My Custom Combo',
    'skills': ['1', '2', 'alt+1', '3', 'ctrl+1'],
    'cooldown': 90.0,  # 1.5 minutes
    'delay_between_skills': 0.7,
    'enabled': True,
}

The system will:
1. Check if combo cooldown is ready
2. Check if ALL skills in the combo are off cooldown
3. If ready, execute skills in order with delays
4. Track cooldowns for combo AND individual skills
5. Wait for next combo to become available
"""
