# AION Auto-Simulator

AI-powered automation for AION using AutoHotkey for reliable input simulation.

## ⚡ Quick Start

1. **Install and Run**:
   ```bash
   # Option 1: Use the batch file
   run_as_admin.bat
   
   # Option 2: Run directly
   python main.py
   ```

2. **Start Automation**:
   - Select your AION game window
   - Click "Start" to begin automation
   - Press DELETE for emergency stop

## 🔧 Requirements

- **Windows 10/11**
- **Python 3.8+**
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

## 🎮 How It Works

### Input Methods

**Primary: Windows SendInput API** (default)
- ✅ Native Windows API for input simulation
- ✅ Works with protected games including AION
- ✅ Low-level input that games cannot easily block
- ✅ No third-party dependencies or drivers needed
- ✅ Fast and reliable

**Alternative: AutoHotkey Hardware Macro** (optional)
- ✅ True hardware-level inputs
- ✅ Manual control via hotkeys (F9/F10/F11)
- ✅ Runs independently in system tray
- ✅ Available as backup method
- 📖 See `AHK_HARDWARE_GUIDE.md` for details

### AI Detection
- Custom YOLO model (`models/aion.pt`) for real-time object detection
- Detects: mobs, map markers, UI elements
- Overlay visualization with bounding boxes

### Automation Logic
- Smart mob targeting (prioritizes cursor → near → far)
- Auto-navigation using map markers
- Health-based attack loops
- Emergency stop (DELETE key)

## 🛠️ Architecture

```
AION2_AutoSim/
├── main.py                    # Main application
├── input_controller.py        # AutoHotkey input control
├── detection.py               # AI detection loop
├── action_planner.py          # Game action logic
├── overlay.py                 # Visual overlay
├── capture.py                 # Screen capture
├── model_client.py            # YOLO model interface
├── utils.py                   # Utility functions
├── models/
│   └── aion.pt               # AI model weights
└── requirements.txt
```

## 🔒 Security & Safety

### Windows SendInput API
- **Official Windows API**: Part of the Windows operating system
- **No system modifications**: Uses built-in Windows functionality
- **No external dependencies**: Pure Python + Windows API
- **Microsoft recommended**: Official method for input simulation

## ⚙️ Configuration

### Simulate Mode (Disabled by Default)
The program now runs in **real mode** by default. Hardware inputs are sent directly to the game.

### Emergency Stop
- Press **DELETE** key at any time to stop automation
- Works even when AION window is focused

## 🐛 Troubleshooting

### Inputs not working in game
1. **Run as Administrator** (required for SendInput to work with games)
2. Make sure AION window is focused
3. Click in the game window first to activate it
4. Test with: `python test_sendinput.py`

### Mouse/keyboard not responding
1. Verify inputs work: `python test_sendinput.py`
2. Check Windows permissions
3. Disable any input blocking software

### Import errors
```bash
pip install -r requirements.txt
```

## 📝 Development

### Testing
```bash
# Test AutoHotkey
python test_ahk.py
```

### Adding New Features
1. All input functions are in `input_controller.py`
2. Game logic is in `action_planner.py`
3. Detection classes are in `detection.py`

## 📄 License

MIT License - See LICENSE file

## ⚠️ Disclaimer

This software is for educational purposes only. Use at your own risk. The developers are not responsible for any consequences of using this software, including but not limited to game bans or system instability.

## 🙏 Credits

- **AutoHotkey**: Python ahk library (https://github.com/spyoungtech/ahk)
- **YOLO**: Ultralytics (https://github.com/ultralytics/ultralytics)
- **Qt Framework**: Qt Company (PySide6)

---

## #AION2_AutoSim

Automated real-time combat macro for a 3D game using a real object detection model (YOLO/Ultralytics). This project provides:

- A PyQt5 dark-themed UI with game window selection, start/stop controls, an embedded log terminal, and overlay debugging.
- Real-time capture of the selected game window and inference pipeline using Ultralytics YOLO (user-provided or trained weights).
- Automatic double-clicking at detected target locations (e.g., "Highland Sparkle").
- Transparent overlay showing click positions and detection bounding boxes for debugging.

IMPORTANT: This repository provides a real inference and automation pipeline — you must provide/train a model that recognizes the in-game mob label (e.g., "Highland Sparkle"). See the Training and Usage sections.

Getting started
1. Create a Python 3.10+ virtual environment and install dependencies:

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1; pip install -r requirements.txt
```

2. Provide a YOLO-compatible weights file (Ultralytics YOLOv8 recommended) that has a class for the mob name you want to detect (e.g. "Highland Sparkle"). Place the weights file somewhere and note the path.

3. Run the app:

```powershell
python main.py
```

Training guidance
- Use the Ultralytics training workflow to collect screenshots of the mob from your game in the same resolution and camera setups you will run inference in. Label with the exact class name you will configure in the UI (e.g., "Highland Sparkle").
- Train a YOLOv8 model and export weights (best.pt) and use that path in the UI.

Usage notes and limitations
- Some games use exclusive DirectX surfaces; capturing may require running the game in windowed or borderless window mode.
- Synthetic input (pyautogui) may be blocked by some anti-cheat systems — test in a controlled environment.
- This tool does real-time vision and input automation. Use responsibly and with permission from the game provider.

Files
- `main.py` — main PyQt application, UI and orchestration.
- `detection.py` — capture + model inference loop.
- `overlay.py` — transparent overlay window drawing debugging visuals.
- `utils.py` — helper functions for window enumeration, coordinate mapping, and safe click implementation.


For Considerations:

 - Consider using Calibration when running the program first in order for fixed points to be detected more accurately
 - A Pop Up should first appear when hitting start so that in the pop up it will inform the user to make sure that the game window is already opened and that you are already in the game and logged in to the correct character and also inform the user for UI Calibration
 - Figure out how to automatically move the Player Character using the Detected Map
 - Optimization
 - Configurable Macro Inputs