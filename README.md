# AION Auto-Play / Auto-Hunt Simulation (Boilerplate)

This repository contains a skeleton Python project to simulate auto-hunt and
auto-play features in an MMORPG environment for educational purposes. The
implementation is intentionally minimal and documented to make it easy to
extend.

Structure
- `player.py` — Player and Skill dataclasses, sample player factory.
- `map.py` — GridMap, Enemy, ResourceNode and sample map generator.
- `combat.py` — CombatEngine skeleton with placeholder damage logic.
- `autoplay.py` — AutoPlayController implementing auto_hunt, auto_heal, loot.
- `logger.py` — Central logging configuration helper.
- `main.py` — Simple runner to execute a short simulation loop.
- `gui.py` — Minimal Tkinter GUI placeholder for visualization.
- `ml_adapter.py` — Placeholder adapter for ML integration (skill ordering).

How to run

1. Ensure you're using Python 3.8+.
2. From the project directory run:

```powershell
python main.py
```

Optional GUI:

```powershell
python gui.py
```

Next steps
- Implement pathfinding (A*, BFS) in `map.py` or a new `pathfinding.py`.
- Flesh out combat formulas and add skill effects.
- Implement more complete AI states and movement in `autoplay.py`.
- Add unit tests and CI, plus a small dataset and an ML experiment to tune
  skill rotations in `ml_adapter.py`.

Third-party packages and macro automation
---------------------------------------
- The project can use the packages listed in `requirements.txt` for ML and
  automation experiments (numpy, scikit-learn, torch, pyautogui, pynput, opencv).
- A `macro.py` adapter is included to exercise input automation in a safe
  manner. By default `MacroController` runs in `safe_mode=True` and only logs
  actions. Set `safe_mode=False` if you intentionally want to send events to
  your OS (be careful — this affects other windows and may be detected by
  some game clients).

Reference for keypress simulation
--------------------------------
This project references common approaches to simulate keypresses in Python
for educational purposes. One useful thread discussing approaches (pyautogui,
pynput, win32 APIs) is on StackOverflow: see the link you provided when using
these modules responsibly.

License
Educational / template code — adapt as needed.
