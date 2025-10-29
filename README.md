# AION2_AutoSim

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