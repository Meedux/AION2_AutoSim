# AION Auto-Simulator

AI-powered automation for AION with **advanced skill combo macros**, stealth attack modes, and hardware-level input simulation.

## ✨ Features

- 🎯 **Skill Combo Macro System** - 36 configurable keybinds with individual cooldown tracking
- 🎲 **Stealth Attack Mode** - Randomizes between double-click, single skills, and combo sets
- 🖱️ **Smart Clicking** - Clicks lower part of detection boxes, nearest mob targeting
- ⌨️ **Hardware-Level Input** - AutoHotkey for maximum game compatibility
- 🔄 **Smooth Mouse Movement** - Bezier curve dragging (no teleport)
- 🎮 **70° Turns** - Proper key holding for wide angle turns
- 🗺️ **Minimap Navigation** - Red dot detection and pathfinding
- 🤖 **CryEngine Anti-Cheat Evasion** - Ultra-slow timing, startup delays, idle simulation

## ⚡ Quick Start

1. **Run the program** (auto-elevates to admin):
   ```bash
   python main.py
   ```

2. **Configure in GUI**:
   - Select your AION game window
   - Adjust skill combo settings in the UI
   - Set attack mode weights (double-click/skill/combo)
   - Click "Start" to begin automation

3. **Emergency Controls**:
   - Press **DELETE** to toggle automation on/off
   - Click **EMERGENCY STOP** button to disable immediately

## 🔧 Requirements

- **Windows 10/11**
- **Python 3.8+**
- **Administrator privileges** (required for hardware-level input)
- **AutoHotkey** (automatically installed via pip)

## 📦 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Meedux/AION2_AutoSim.git
   cd AION2_AutoSim
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the program**:
   ```bash
   python main.py
   ```
   *(Will automatically prompt for admin elevation)*

---

## 🎮 Skill Combo Macro System

### Overview

The skill combo system provides **36 configurable keybind slots** with intelligent cooldown tracking and randomized attack patterns.

### Available Keybinds

- **Number Row**: `1`, `2`, `3`, `4`, `5`, `6`, `7`, `8`, `9`, `0`, `-`, `=`
- **Alt + Keys**: `alt+1` through `alt+=`
- **Ctrl + Keys**: `ctrl+1` through `ctrl+=`

**Total: 36 keybind slots** ✅

### Configuration

Edit `skill_combo_config.py`:

```python
# 1. Set individual skill cooldowns
SKILL_COOLDOWNS = {
    '1': 10.0,      # Skill on key 1 = 10s cooldown
    '2': 12.0,      # Skill on key 2 = 12s cooldown
    'alt+1': 20.0,  # Alt+1 skill = 20s cooldown
    'ctrl+1': 60.0, # Ctrl+1 = 60s cooldown (ultimate)
}

# 2. Create combo sets
COMBO_SETS = [
    {
        'name': 'Basic DPS Rotation',
        'skills': ['1', '2', '3', '4'],
        'cooldown': 60.0,
        'delay_between_skills': 0.5,
        'enabled': True,
    },
]
```

### GUI Configuration

The main program includes GUI controls for:
- ✅ **Enable/Disable** stealth attack mode
- ✅ **Attack Mode Weights** (double-click vs skills vs combos)
- ✅ **Health Requirement** (only use skills when health bar detected)
- ✅ **Open Config File** button for advanced settings

### Stealth Attack Mode

**Randomized Attack Patterns:**
- **50%** - Standard double-click attack
- **30%** - Single random skill press
- **20%** - Full combo set execution

**Smart Behavior:**
- ✅ Only uses skills when `mob_combat_health` is detected
- ✅ **Single click** + skill/combo (not double-click)
- ✅ **Double click** for standard attacks
- ✅ Tracks individual skill cooldowns
- ✅ Tracks combo set cooldowns
- ✅ Only executes when ALL skills ready

### How It Works

```
Combat Detected → Choose Attack Mode (random)
                       ↓
    ┌──────────────────┼──────────────────┐
    │                  │                  │
Standard (50%)    Single Skill (30%)   Combo (20%)
    │                  │                  │
Double-click      Single-click +      Single-click +
    mob           random skill         skill combo
```

**Example Execution:**
```
1. Bot detects mob with health bar
2. Chooses "Single Skill" mode (30% chance)
3. Single-clicks mob to target
4. Presses skill '2' (hardware-level)
5. Skill '2' goes on 12s cooldown
6. Next attack: might be double-click (50%) or combo (20%)
```

### Testing

```bash
# Validate configuration
python test_skill_combos.py
```

**Output:**
```
✓ Configuration is valid
✓ 36 keybind slots available
✓ Stealth attack mode: ENABLED
✓ Attack weights: Standard=50%, Skill=30%, Combo=20%
```

---

## 🎯 Combat System

### Detection & Targeting

- **Nearest Mob Selection**: Always attacks closest mob to player
- **Click Position**: Lower part of detection box (70-90% down)
- **Mouse Jitter**: ±15 pixels for human-like variation
- **Health Bar Detection**: Continues attacking until health disappears

### Attack Modes

1. **Standard Attack (Double-Click)**:
   - Double-clicks mob location
   - Most common (50% default)
   - No skill cooldowns

2. **Single Skill Attack**:
   - Single-clicks to target mob
   - Presses one random skill
   - Skill goes on individual cooldown

3. **Combo Set Attack**:
   - Single-clicks to target mob
   - Executes full skill rotation
   - All skills + combo go on cooldown

### Movement & Navigation

- **Minimap Red Dots**: Detects and navigates toward enemies
- **70° Turns**: Holds A/D keys for full turns (not just tap)
- **Movement Macros**: 7 randomized patterns (zigzag, circles, etc.)
- **Smooth Mouse**: Bezier curve dragging (0.15-0.40s)

---

## 🛡️ CryEngine Anti-Cheat Evasion

### Stealth Timing System

- **Detection Rate**: 1 FPS (ultra-conservative)
- **Startup Delay**: 8-15 seconds before any actions
- **Warmup Period**: First 10 actions extra slow
- **Action Cooldown**: 0.8-2.0s randomized delays
- **Idle Simulation**: Random 4-12s pauses (35% chance)
- **Mouse Jitter**: ±15 pixels randomization

### Why These Features?

AION uses CryEngine with aggressive anti-cheat. The bot:
1. Runs at **1 FPS** to avoid detection polling
2. Adds **startup delay** (simulates loading)
3. Uses **randomized timing** (unpredictable behavior)
4. Simulates **idle periods** (human "thinking")
5. Uses **hardware input** (bypasses software blocks)

---

## 🎮 How It Works

### Input Methods

**Primary: AutoHotkey Hardware-Level** (default)
- ✅ True hardware simulation
- ✅ Bypasses most anti-cheat systems
- ✅ Supports modifier keys (Alt+, Ctrl+)
- ✅ Reliable key holding for turns

**Fallback: Windows SendInput API**
- ✅ Native Windows API for input simulation
- ✅ Direct DirectX-compatible input
- ✅ Used when AutoHotkey unavailable

### AI Object Detection

- **YOLOv8 Model**: Real-time detection at 1 FPS
- **Classes Detected**:
  - `mob_target` - Enemy mobs
  - `mob_combat_health` - Active health bars
  - `minimap_red_dot` - Minimap indicators
- **Custom Training**: Model trained on AION screenshots

---

## 🔧 Configuration Files

### `skill_combo_config.py`

**Main configuration file for skill macros:**

```python
# ===== STEALTH ATTACK MODE =====
STEALTH_ATTACK_MODE_ENABLED = True  # Enable randomized attack patterns

# Attack mode weights (must sum to ~1.0)
ATTACK_MODE_WEIGHTS = {
    'standard_attack': 0.50,  # 50% - Double-click attack
    'single_skill': 0.30,     # 30% - Single skill press
    'combo_set': 0.20,        # 20% - Full combo execution
}

# Only use skills when health bar detected
REQUIRE_MOB_HEALTH_FOR_SKILLS = True

# ===== SINGLE SKILL CONFIGURATION =====
SINGLE_SKILL_POOL = ['1', '2', '3', '4']  # Skills for random selection
SINGLE_SKILL_GLOBAL_COOLDOWN = 1.5        # GCD between single skills

# ===== INDIVIDUAL SKILL COOLDOWNS =====
SKILL_COOLDOWNS = {
    # Number row
    '1': 10.0,
    '2': 12.0,
    '3': 15.0,
    '4': 8.0,
    '5': 20.0,
    # Alt combinations
    'alt+1': 30.0,
    'alt+2': 25.0,
    # Ctrl combinations (ultimates)
    'ctrl+1': 60.0,
    'ctrl+2': 90.0,
}

# ===== COMBO SETS =====
COMBO_SETS = [
    {
        'name': 'Basic DPS Rotation',
        'skills': ['1', '2', '3', '4'],
        'cooldown': 60.0,                  # Combo set cooldown
        'delay_between_skills': 0.5,       # 500ms between skills
        'enabled': True,
    },
    {
        'name': 'Burst Rotation',
        'skills': ['5', 'alt+1', 'alt+2', '1'],
        'cooldown': 120.0,
        'delay_between_skills': 0.3,
        'enabled': True,
    },
]
```

### Key Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `STEALTH_ATTACK_MODE_ENABLED` | `True` | Enable randomized attacks |
| `ATTACK_MODE_WEIGHTS['standard_attack']` | `0.50` | Double-click probability |
| `ATTACK_MODE_WEIGHTS['single_skill']` | `0.30` | Single skill probability |
| `ATTACK_MODE_WEIGHTS['combo_set']` | `0.20` | Combo set probability |
| `REQUIRE_MOB_HEALTH_FOR_SKILLS` | `True` | Only use skills when health detected |
| `SINGLE_SKILL_GLOBAL_COOLDOWN` | `1.5` | GCD for single skill mode |

---

## 📋 Usage Examples

### Example 1: Pure Double-Click Bot (No Skills)

```python
# skill_combo_config.py
STEALTH_ATTACK_MODE_ENABLED = False  # Disable stealth mode
```
Result: Bot will **only** double-click mobs (no skills used)

---

### Example 2: Always Use Combo Sets

```python
STEALTH_ATTACK_MODE_ENABLED = True
ATTACK_MODE_WEIGHTS = {
    'standard_attack': 0.0,   # Never double-click
    'single_skill': 0.0,      # Never single skill
    'combo_set': 1.0,         # Always combo
}
```
Result: Bot will **only** execute combo sets (when ready)

---

### Example 3: Balanced Combat (Default)

```python
STEALTH_ATTACK_MODE_ENABLED = True
ATTACK_MODE_WEIGHTS = {
    'standard_attack': 0.50,  # 50% double-click
    'single_skill': 0.30,     # 30% single skill
    'combo_set': 0.20,        # 20% combo
}
```
Result: Randomized attacks with balanced distribution

---

### Example 4: High Skill Usage (Aggressive)

```python
ATTACK_MODE_WEIGHTS = {
    'standard_attack': 0.20,  # Rarely double-click
    'single_skill': 0.50,     # Often single skills
    'combo_set': 0.30,        # Often combos
}
```
Result: Bot uses skills 80% of the time (more aggressive)

---

## 🐛 Troubleshooting

### Skills Not Triggering

**Symptoms**: Bot only double-clicks, never uses skills

**Solutions**:
1. Check `STEALTH_ATTACK_MODE_ENABLED = True`
2. Verify attack weights sum to ~1.0
3. Ensure `REQUIRE_MOB_HEALTH_FOR_SKILLS = True` and health bars are detected
4. Check individual skill cooldowns (may still be on cooldown)
5. Run `python test_skill_combos.py` to validate config

---

### Skills Wrong Keys

**Symptoms**: Wrong skills being pressed

**Solutions**:
1. Check `SKILL_COOLDOWNS` dictionary keys match your game bindings
2. Verify `SINGLE_SKILL_POOL` contains correct keys
3. Check `COMBO_SETS` skill lists
4. Test with: `python -c "from skill_combo_manager import SkillComboManager; m = SkillComboManager(); print(m.skill_cooldowns)"`

---

### AutoHotkey Not Working

**Symptoms**: Skills with Alt/Ctrl not pressing

**Solutions**:
1. **Run as Administrator** (required for hardware input)
2. Check AutoHotkey installed: `pip install ahk`
3. Fallback to SendInput: Edit `input_controller.py` and remove AutoHotkey dependency
4. Verify game accepts modifier keys (some games block Alt+/Ctrl+)

---

### Combo Sets Not Executing

**Symptoms**: Single skills work, but combos don't

**Solutions**:
1. Check all skills in combo are off cooldown
2. Verify `combo_set` weight > 0.0
3. Check combo `enabled: True` in `COMBO_SETS`
4. Ensure `REQUIRE_MOB_HEALTH_FOR_SKILLS = True` and health detected

---

### "Emergency Stop" Not Responding

**Symptoms**: DELETE key doesn't stop bot

**Solutions**:
1. Click **EMERGENCY STOP** button in GUI (always works)
2. Close the program window
3. Task Manager → End Task on `python.exe`

---

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Test your changes
4. Submit a pull request

---

## 📄 License

This project is for educational purposes only. Use at your own risk.

---

## 🙏 Credits

- **YOLOv8**: Ultralytics object detection
- **AutoHotkey**: Hardware-level input simulation
- **PySide6**: Modern GUI framework
- **PyAutoGUI**: Fallback input method

---

## ⚠️ Disclaimer

**Use this bot at your own risk.** Game automation may violate terms of service. The developers are not responsible for account bans or other consequences.

---

## 📌 Future Considerations

- **UI Calibration**: Popup reminder to ensure game window is open and character logged in
- **Minimap Movement**: Automatically move player character using detected map markers
- **Optimization**: Performance improvements for detection and input
- **Advanced Macros**: More complex combo sequences and conditional logic