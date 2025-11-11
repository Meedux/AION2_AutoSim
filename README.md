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

### Configuration (100% GUI - No File Editing!)

**All configuration is done through the GUI:**

1. **Main Window Controls:**
   - ✅ **Enable/Disable** stealth attack mode
   - ✅ **Attack Mode Weights** (double-click vs skills vs combos)
   - ✅ **Health Requirement** (only use skills when health bar detected)

2. **⚙️ Edit Individual Skills Button:**
   - Configure skill cooldowns for each keybind
   - Set single skill pool for random selection
   - Adjust GCD (Global Cooldown) for single skills
   - Add/remove skills with visual table editor

3. **🎯 Edit Combo Sets Button:**
   - Create/edit/delete combo sets
   - Set combo names, cooldowns, and delays
   - Define skill sequences (one per line)
   - Enable/disable specific combos
   - Visual list management

**No more editing `skill_combo_config.py` manually!**

See `GUI_SKILL_EDITOR_GUIDE.md` for detailed instructions.

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

## 🔧 GUI Configuration (No File Editing Required!)

### Main Window Controls

**Directly in the main program:**
- **Stealth Attack Mode** - Checkbox to enable randomized attacks
- **Attack Mode Weights** - Spinboxes for probability distribution:
  - Double-Click Weight (default: 50%)
  - Single Skill Weight (default: 30%)
  - Combo Set Weight (default: 20%)
- **Health Requirement** - Checkbox to only use skills when mob health detected

### ⚙️ Individual Skills Editor

**Click "⚙️ Edit Individual Skills" button:**
- **Single Skill Pool** - Text field for skills used in random selection (e.g., `1, 2, 3, 4`)
- **GCD Setting** - Global cooldown for single skill mode (default: 1.5 sec)
- **Cooldowns Table** - Visual editor with Add/Remove buttons:
  - Column 1: Keybind (e.g., `1`, `alt+1`, `ctrl+1`)
  - Column 2: Cooldown in seconds (0.1-600 range)
- **Add Skill** - Button to add new skill row
- **Remove Skill** - Button to delete selected skill

### 🎯 Combo Sets Editor

**Click "🎯 Edit Combo Sets" button:**
- **Combo List** - Shows all combo sets with enable/disable status
- **New Combo** - Button to create new combo set
- **Delete Combo** - Button to remove combo set
- **Combo Details Panel:**
  - Combo Name (text field)
  - Enabled checkbox
  - Combo Cooldown (0-600 seconds)
  - Delay Between Skills (0-5 seconds)
  - Skills List (multi-line text, one skill per line)
- **Save Combo** - Button to apply changes

### Key Settings Reference

| Setting | Location | Default | Description |
|---------|----------|---------|-------------|
| Stealth Mode | Main Window | Enabled | Randomize attack patterns |
| Double-Click Weight | Main Window | 0.50 | Standard attack probability |
| Single Skill Weight | Main Window | 0.30 | Single skill probability |
| Combo Set Weight | Main Window | 0.20 | Combo execution probability |
| Health Requirement | Main Window | Enabled | Only use skills with health bar |
| Single Skill Pool | Skills Editor | `1,2,3,4` | Skills for random selection |
| GCD | Skills Editor | 1.5 sec | Global cooldown for single skills |
| Individual Cooldowns | Skills Editor | Various | Per-skill cooldown timers |
| Combo Sets | Combo Editor | Various | Skill rotation sequences |

---

## 📋 Usage Examples (All GUI-Based!)

### Example 1: Pure Double-Click Bot (No Skills)

**In Main Window:**
- ✓ Uncheck "Enable Stealth Attack Mode"

**Result:** Bot will **only** double-click mobs (no skills used)

---

### Example 2: Always Use Combo Sets

**In Main Window:**
- ✓ Check "Enable Stealth Attack Mode"
- Set Double-Click Weight: **0.00** (0%)
- Set Single Skill Weight: **0.00** (0%)
- Set Combo Set Weight: **1.00** (100%)

**Result:** Bot will **only** execute combo sets (when ready)

---

### Example 3: Balanced Combat (Default)

**In Main Window:**
- ✓ Check "Enable Stealth Attack Mode"
- Set Double-Click Weight: **0.50** (50%)
- Set Single Skill Weight: **0.30** (30%)
- Set Combo Set Weight: **0.20** (20%)

**Result:** Randomized attacks with balanced distribution

---

### Example 4: High Skill Usage (Aggressive)

**In Main Window:**
- ✓ Check "Enable Stealth Attack Mode"
- Set Double-Click Weight: **0.20** (20%)
- Set Single Skill Weight: **0.50** (50%)
- Set Combo Set Weight: **0.30** (30%)

**Result:** Bot uses skills 80% of the time (more aggressive)

---

### Example 5: Create Custom Combo

**Step-by-step:**
1. Click **"🎯 Edit Combo Sets"** button
2. Click **"➕ New Combo"**
3. Enter name: `My Ultimate Rotation`
4. Check **"Enabled"**
5. Set cooldown: `120` seconds
6. Set delay: `0.5` seconds
7. Enter skills (one per line):
   ```
   1
   2
   alt+1
   ctrl+1
   3
   ```
8. Click **"💾 Save Combo"**
9. Click **"Close"**

**Result:** New combo set ready to use!

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