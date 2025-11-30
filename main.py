
"""Main GUI application for AION.
Uses a local YOLO weight (models/aion.pt) to run realtime detections
and draw a click-through overlay on the selected game window.
"""
import sys
import os
import ctypes
from PySide6 import QtWidgets, QtCore
from loguru import logger
from utils import list_windows, get_window_rect
from overlay import OverlayWindow
from detection import DetectionController
import input_controller as ic


def is_admin():
    """Check if the program is running with administrator privileges."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


def run_as_admin():
    """Restart the program with administrator privileges."""
    try:
        # Build the full command line: script path + any additional arguments
        # sys.argv[0] is the script being run (main.py)
        script_path = os.path.abspath(sys.argv[0])
        # Build quoted argument string including the script itself
        args = f'"{script_path}"'
        if len(sys.argv) > 1:
            args += ' ' + ' '.join([f'"{arg}"' for arg in sys.argv[1:]])
        
        # Use the current Python executable (this will be the venv interpreter when using the venv)
        # ShellExecuteW with verb "runas" prompts for elevation and starts a new elevated process.
        ret = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, args, os.getcwd(), 1)
        # ShellExecuteW returns a value > 32 on success
        if int(ret) <= 32:
            raise OSError(f"ShellExecuteW failed with code {ret}")
        # If ShellExecute succeeded we should exit this (non-elevated) process so only elevated instance runs
        sys.exit(0)
    except Exception as e:
        logger.error(f"Failed to elevate privileges: {e}")
        return False
    return True


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("AION Autoplay")
        self.resize(900, 640)

        central = QtWidgets.QWidget()
        self.setCentralWidget(central)
        # Main layout: left navigation sidebar + right stacked pages
        main_h = QtWidgets.QHBoxLayout(central)

        # Sidebar (navigation)
        self.sidebar = QtWidgets.QWidget()
        self.sidebar.setFixedWidth(180)
        sb_layout = QtWidgets.QVBoxLayout(self.sidebar)
        sb_layout.setContentsMargins(8, 8, 8, 8)
        sb_layout.setSpacing(12)

        # Create nav buttons
        def _nav_btn(text):
            b = QtWidgets.QPushButton(text)
            b.setCursor(QtCore.Qt.PointingHandCursor)
            b.setCheckable(True)
            b.setStyleSheet(self._nav_button_style())
            b.setFixedHeight(44)
            return b

        self.btn_dashboard = _nav_btn('Dashboard')
        self.btn_skills = _nav_btn('Skills')
        self.btn_combos = _nav_btn('Combos')
        self.btn_cooldowns = _nav_btn('Cooldowns')
        self.btn_logs = _nav_btn('Logs')
        self.btn_settings = _nav_btn('Settings')

        for b in (self.btn_dashboard, self.btn_skills, self.btn_combos, self.btn_cooldowns, self.btn_logs, self.btn_settings):
            sb_layout.addWidget(b)
        sb_layout.addStretch()

        # Right side: stacked pages
        self.pages = QtWidgets.QStackedWidget()
        self.pages.setObjectName('pages')

        main_h.addWidget(self.sidebar)
        main_h.addWidget(self.pages, stretch=1)

        # Create pages
        self.page_dashboard = QtWidgets.QWidget()
        self.page_skills = QtWidgets.QWidget()
        self.page_combos = QtWidgets.QWidget()
        self.page_cooldowns = QtWidgets.QWidget()
        self.page_logs = QtWidgets.QWidget()
        self.page_settings = QtWidgets.QWidget()

        self.page_dashboard_layout = QtWidgets.QVBoxLayout(self.page_dashboard)
        self.page_skills_layout = QtWidgets.QVBoxLayout(self.page_skills)
        self.page_combos_layout = QtWidgets.QVBoxLayout(self.page_combos)
        self.page_cooldowns_layout = QtWidgets.QVBoxLayout(self.page_cooldowns)
        self.page_logs_layout = QtWidgets.QVBoxLayout(self.page_logs)
        self.page_settings_layout = QtWidgets.QVBoxLayout(self.page_settings)

        for p in (self.page_dashboard, self.page_skills, self.page_combos, self.page_cooldowns, self.page_logs, self.page_settings):
            self.pages.addWidget(p)

        # Connect nav buttons
        self.btn_dashboard.clicked.connect(lambda: self.change_page(0))
        self.btn_skills.clicked.connect(lambda: self.change_page(1))
        self.btn_combos.clicked.connect(lambda: self.change_page(2))
        self.btn_cooldowns.clicked.connect(lambda: self.change_page(3))
        self.btn_logs.clicked.connect(lambda: self.change_page(4))
        self.btn_settings.clicked.connect(lambda: self.change_page(5))

        # Select dashboard by default
        self.btn_dashboard.setChecked(True)
        self.pages.setCurrentIndex(0)

        # top controls (placed on Dashboard page)
        form = QtWidgets.QFormLayout()
        self.win_combo = QtWidgets.QComboBox()
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        self.refresh_btn.clicked.connect(self._refresh_windows)
        h = QtWidgets.QHBoxLayout()
        h.addWidget(self.win_combo)
        h.addWidget(self.refresh_btn)
        form.addRow("Game window:", h)

        # Using local model weights placed at models/aion.pt
        info = QtWidgets.QLabel("Using local model weights: models/aion.pt (Ultralytics YOLO)")
        info.setWordWrap(True)
        form.addRow("Settings:", info)

        # Input backend controls (UI toggle)
        backend_layout = QtWidgets.QHBoxLayout()
        self.backend_combo = QtWidgets.QComboBox()
        # Available backends (interception-only build)
        self.backend_combo.addItems(['interception'])
        # Use stored config if present, otherwise reflect runtime value
        try:
            import skill_combo_config as scc
            initial_backend = getattr(scc, 'INPUT_BACKEND', ic.INPUT_BACKEND)
        except Exception:
            initial_backend = ic.INPUT_BACKEND
        idx = self.backend_combo.findText(initial_backend)
        if idx >= 0:
            self.backend_combo.setCurrentIndex(idx)
        self.backend_combo.currentTextChanged.connect(self._on_backend_changed)

        self.simulate_cb = QtWidgets.QCheckBox("Simulate mode (log only, no real inputs)")
        try:
            initial_dry = getattr(scc, 'INPUT_DRY_RUN', ic.INPUT_DRY_RUN)
        except Exception:
            initial_dry = ic.INPUT_DRY_RUN
        self.simulate_cb.setChecked(bool(initial_dry))
        self.simulate_cb.toggled.connect(self._on_dry_run_toggled)

        # Small status indicator for backend availability
        self.backend_status = QtWidgets.QLabel("")
        self.backend_status.setFixedWidth(140)
        backend_layout.addWidget(self.backend_combo)
        backend_layout.addWidget(self.backend_status)
        backend_layout.addWidget(self.simulate_cb)
        form.addRow("Input backend:", backend_layout)

        # initialize backend status indicator
        try:
            self._update_backend_status(initial_backend)
        except Exception:
            pass

        # Add the top form to the dashboard page
        self.page_dashboard_layout.addLayout(form)

        # Skill Combo Configuration Section
        skill_group = QtWidgets.QGroupBox("Skill Combo Configuration")
        skill_layout = QtWidgets.QVBoxLayout()
        
        # Load existing configuration
        import skill_combo_config
        
        # Attack mode randomization checkbox
        self.stealth_attack_cb = QtWidgets.QCheckBox("Enable randomized attack mode (randomize attacks)")
        self.stealth_attack_cb.setChecked(skill_combo_config.STEALTH_ATTACK_MODE_ENABLED)
        self.stealth_attack_cb.stateChanged.connect(self._update_skill_config)
        skill_layout.addWidget(self.stealth_attack_cb)
        
        # Attack mode weights
        weights_layout = QtWidgets.QFormLayout()
        self.standard_attack_weight = QtWidgets.QDoubleSpinBox()
        self.standard_attack_weight.setRange(0.0, 1.0)
        self.standard_attack_weight.setSingleStep(0.05)
        self.standard_attack_weight.setValue(skill_combo_config.ATTACK_MODE_WEIGHTS.get('standard_attack', 0.50))
        self.standard_attack_weight.setSuffix(f" ({int(skill_combo_config.ATTACK_MODE_WEIGHTS.get('standard_attack', 0.50)*100)}%)")
        self.standard_attack_weight.valueChanged.connect(lambda v: self.standard_attack_weight.setSuffix(f" ({int(v*100)}%)"))
        self.standard_attack_weight.valueChanged.connect(self._update_skill_config)
        weights_layout.addRow("Standard Attack Weight (Tab-target):", self.standard_attack_weight)
        
        self.single_skill_weight = QtWidgets.QDoubleSpinBox()
        self.single_skill_weight.setRange(0.0, 1.0)
        self.single_skill_weight.setSingleStep(0.05)
        self.single_skill_weight.setValue(skill_combo_config.ATTACK_MODE_WEIGHTS.get('single_skill', 0.30))
        self.single_skill_weight.setSuffix(f" ({int(skill_combo_config.ATTACK_MODE_WEIGHTS.get('single_skill', 0.30)*100)}%)")
        self.single_skill_weight.valueChanged.connect(lambda v: self.single_skill_weight.setSuffix(f" ({int(v*100)}%)"))
        self.single_skill_weight.valueChanged.connect(self._update_skill_config)
        weights_layout.addRow("Single Skill Weight:", self.single_skill_weight)
        
        self.combo_set_weight = QtWidgets.QDoubleSpinBox()
        self.combo_set_weight.setRange(0.0, 1.0)
        self.combo_set_weight.setSingleStep(0.05)
        self.combo_set_weight.setValue(skill_combo_config.ATTACK_MODE_WEIGHTS.get('combo_set', 0.20))
        self.combo_set_weight.setSuffix(f" ({int(skill_combo_config.ATTACK_MODE_WEIGHTS.get('combo_set', 0.20)*100)}%)")
        self.combo_set_weight.valueChanged.connect(lambda v: self.combo_set_weight.setSuffix(f" ({int(v*100)}%)"))
        self.combo_set_weight.valueChanged.connect(self._update_skill_config)
        weights_layout.addRow("Combo Set Weight:", self.combo_set_weight)
        
        skill_layout.addLayout(weights_layout)
        
        # Require mob health checkbox
        self.require_health_cb = QtWidgets.QCheckBox("Only use skills when mob health bar detected")
        self.require_health_cb.setChecked(skill_combo_config.REQUIRE_MOB_HEALTH_FOR_SKILLS)
        self.require_health_cb.stateChanged.connect(self._update_skill_config)
        skill_layout.addWidget(self.require_health_cb)

        # Combat skills & combos toggle
        self.combat_skills_cb = QtWidgets.QCheckBox("Enable skills & combos during combat")
        # New config key: COMBAT_USE_SKILLS
        self.combat_skills_cb.setChecked(getattr(skill_combo_config, 'COMBAT_USE_SKILLS', True))
        self.combat_skills_cb.stateChanged.connect(self._update_skill_config)
        skill_layout.addWidget(self.combat_skills_cb)
        
        # Configuration buttons in a horizontal layout
        config_buttons_layout = QtWidgets.QHBoxLayout()
        
        # Edit Individual Skills button
        # edit_skills_btn = QtWidgets.QPushButton("⚙️ Edit Individual Skills")
        # edit_skills_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 8px; }")
        # # Navigate to the Skills screen (embedded editor) instead of opening a dialog
        # edit_skills_btn.clicked.connect(lambda: self.change_page(1))
        # config_buttons_layout.addWidget(edit_skills_btn)
        
        # Edit Combo Sets button
        edit_combos_btn = QtWidgets.QPushButton("🎯 Edit Combo Sets")
        edit_combos_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        # Navigate to the Combos screen (embedded editor) instead of opening a dialog
        edit_combos_btn.clicked.connect(lambda: self.change_page(2))
        config_buttons_layout.addWidget(edit_combos_btn)
        
        skill_layout.addLayout(config_buttons_layout)
        
        skill_group.setLayout(skill_layout)
        # Add skill group to Skills page
        self.page_skills_layout.addWidget(skill_group)
        # Embed the full skill editor as a screen under the Skills page
        try:
            self.skill_editor_screen = SkillEditorScreen(self)
            self.page_skills_layout.addWidget(self.skill_editor_screen)
        except Exception:
            pass
        # Cooldown monitor panel placed on Cooldowns page
        self._setup_cooldown_panel(self.page_cooldowns_layout)
        # Embed the combo editor on the Combos page
        try:
            self.combo_editor_screen = ComboEditorScreen(self)
            self.page_combos_layout.addWidget(self.combo_editor_screen)
        except Exception:
            pass

        # Anti-detection GUI removed (no stealth_config support)

        # Start/Stop and Emergency Stop
        btns = QtWidgets.QHBoxLayout()
        self.start_btn = QtWidgets.QPushButton("Start")
        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.emergency_stop_btn = QtWidgets.QPushButton("EMERGENCY STOP")
        self.emergency_stop_btn.setStyleSheet("QPushButton { background-color: red; color: white; font-weight: bold; }")
        self.emergency_stop_btn.clicked.connect(self.emergency_stop)
        self.stop_btn.setEnabled(False)
        self.start_btn.clicked.connect(self.start)
        self.stop_btn.clicked.connect(self.stop)
        btns.addWidget(self.start_btn)
        btns.addWidget(self.stop_btn)
        btns.addWidget(self.emergency_stop_btn)
        # Start/Stop buttons go on Dashboard page
        self.page_dashboard_layout.addLayout(btns)

        # Log terminal
        self.log_view = QtWidgets.QPlainTextEdit()
        self.log_view.setReadOnly(True)
        # Logs page contains the log view
        self.page_logs_layout.addWidget(self.log_view, stretch=1)
        # track desired automation state (applies to controller when created)
        # Default automation ON as requested
        self._automation_enabled = True
        self._overlay = OverlayWindow()
        # ensure overlay matches the desired automation default immediately
        try:
            self._overlay.set_automation_enabled(self._automation_enabled)
        except Exception:
            pass
        self._controller = None
        # start a global hotkey listener for Pause/Break to toggle automation
        self._hotkey_thread = None
        self._start_hotkey_listener()
        self._pos_timer = QtCore.QTimer(self)
        self._pos_timer.setInterval(300)  # ms
        self._pos_timer.timeout.connect(self._reposition_overlay)

        self._refresh_windows()

    def _setup_cooldown_panel(self, parent_layout):
        """Create a small panel showing skill/combo cooldowns."""
        cooldown_group = QtWidgets.QGroupBox("Cooldown Monitor")
        v = QtWidgets.QVBoxLayout()

        # Skills table
        self._skills_table = QtWidgets.QTableWidget(0, 2)
        self._skills_table.setHorizontalHeaderLabels(["Skill", "Remaining(s)"])
        self._skills_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self._skills_table)

        # Combos table
        self._combos_table = QtWidgets.QTableWidget(0, 2)
        self._combos_table.setHorizontalHeaderLabels(["Combo", "Status"])
        self._combos_table.horizontalHeader().setStretchLastSection(True)
        v.addWidget(self._combos_table)

        cooldown_group.setLayout(v)
        parent_layout.addWidget(cooldown_group)

        # Timer to refresh cooldowns periodically
        self._cooldown_timer = QtCore.QTimer(self)
        self._cooldown_timer.setInterval(500)
        self._cooldown_timer.timeout.connect(self._refresh_cooldown_panel)

    def _nav_button_style(self) -> str:
        """Return stylesheet for sidebar nav buttons (modern purple theme)."""
        return (
            "QPushButton { background-color: transparent; color: #EDE7F6; border: none; text-align: left; "
            "padding-left: 12px; font-size: 12pt; }"
            "QPushButton:checked { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #6A1B9A, stop:1 #8E24AA); "
            "border-radius: 6px; color: white; font-weight: bold; }"
            "QPushButton:hover { background-color: rgba(255,255,255,0.03); }"
        )

    def change_page(self, index: int):
        """Animate transition and switch to the given page index."""
        # Immediate, robust page switch without animations to ensure reliability.
        try:
            if index < 0 or index >= self.pages.count():
                return
            self.pages.setCurrentIndex(index)
            # update sidebar checked state
            for i, btn in enumerate((self.btn_dashboard, self.btn_skills, self.btn_combos, self.btn_cooldowns, self.btn_logs, self.btn_settings)):
                try:
                    btn.setChecked(i == index)
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"change_page failed: {e}")

    def log(self, text: str):
        # append thread-safely
        QtCore.QMetaObject.invokeMethod(self.log_view, "appendPlainText", QtCore.Qt.QueuedConnection, QtCore.Q_ARG(str, text))

    def _update_skill_config(self):
        """Update skill combo configuration based on GUI settings."""
        try:
            import skill_combo_config
            
            # Update stealth attack mode
            skill_combo_config.STEALTH_ATTACK_MODE_ENABLED = self.stealth_attack_cb.isChecked()
            # Update combat skill usage toggle
            skill_combo_config.COMBAT_USE_SKILLS = self.combat_skills_cb.isChecked()
            
            # Update attack mode weights
            skill_combo_config.ATTACK_MODE_WEIGHTS['standard_attack'] = self.standard_attack_weight.value()
            skill_combo_config.ATTACK_MODE_WEIGHTS['single_skill'] = self.single_skill_weight.value()
            skill_combo_config.ATTACK_MODE_WEIGHTS['combo_set'] = self.combo_set_weight.value()
            
            # Update health requirement
            skill_combo_config.REQUIRE_MOB_HEALTH_FOR_SKILLS = self.require_health_cb.isChecked()
            
            # Persist to JSON-backed config for durability
            try:
                skill_combo_config.update_config({
                    'STEALTH_ATTACK_MODE_ENABLED': skill_combo_config.STEALTH_ATTACK_MODE_ENABLED,
                    'ATTACK_MODE_WEIGHTS': skill_combo_config.ATTACK_MODE_WEIGHTS,
                    'REQUIRE_MOB_HEALTH_FOR_SKILLS': skill_combo_config.REQUIRE_MOB_HEALTH_FOR_SKILLS,
                    'COMBAT_USE_SKILLS': skill_combo_config.COMBAT_USE_SKILLS,
                })
            except Exception:
                # Fallback: attempt to save inline to the python file
                self._save_main_config_to_file()
            
            self.log("✓ Skill combo configuration updated")
        except Exception as e:
            self.log(f"Failed to update skill config: {e}")
    
    def _save_main_config_to_file(self):
        """Save main window configuration to file."""
        try:
            import skill_combo_config
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'skill_combo_config.py')
            
            # Read the current file
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and replace configuration values
            new_lines = []
            
            for i, line in enumerate(lines):
                # Replace STEALTH_ATTACK_MODE_ENABLED
                if 'STEALTH_ATTACK_MODE_ENABLED = ' in line and not line.strip().startswith('#'):
                    new_lines.append(f'STEALTH_ATTACK_MODE_ENABLED = {skill_combo_config.STEALTH_ATTACK_MODE_ENABLED}\n')
                
                # Replace REQUIRE_MOB_HEALTH_FOR_SKILLS
                elif 'REQUIRE_MOB_HEALTH_FOR_SKILLS = ' in line and not line.strip().startswith('#'):
                    new_lines.append(f'REQUIRE_MOB_HEALTH_FOR_SKILLS = {skill_combo_config.REQUIRE_MOB_HEALTH_FOR_SKILLS}\n')
                
                # Replace ATTACK_MODE_WEIGHTS dictionary
                elif 'ATTACK_MODE_WEIGHTS = {' in line:
                    new_lines.append('ATTACK_MODE_WEIGHTS = {\n')
                    new_lines.append(f"    'standard_attack': {skill_combo_config.ATTACK_MODE_WEIGHTS['standard_attack']},\n")
                    new_lines.append(f"    'single_skill': {skill_combo_config.ATTACK_MODE_WEIGHTS['single_skill']},\n")
                    new_lines.append(f"    'combo_set': {skill_combo_config.ATTACK_MODE_WEIGHTS['combo_set']},\n")
                    new_lines.append('}\n')
                    # Skip old dictionary content
                    while i < len(lines) - 1 and '}' not in lines[i]:
                        i += 1
                
                else:
                    new_lines.append(line)
            
            # Also ensure INPUT_BACKEND / INPUT_DRY_RUN entries are updated
            backend_written = False
            dry_written = False
            for i, line in enumerate(new_lines):
                if 'INPUT_BACKEND = ' in line and not line.strip().startswith('#'):
                    new_lines[i] = f"INPUT_BACKEND = '{ic.INPUT_BACKEND}'\n"
                    backend_written = True
                if 'INPUT_DRY_RUN = ' in line and not line.strip().startswith('#'):
                    new_lines[i] = f"INPUT_DRY_RUN = {ic.INPUT_DRY_RUN}\n"
                    dry_written = True

            if not backend_written:
                new_lines.append('\n# Input backend (interception)\n')
                new_lines.append(f"INPUT_BACKEND = '{ic.INPUT_BACKEND}'\n")
            if not dry_written:
                new_lines.append(f"INPUT_DRY_RUN = {ic.INPUT_DRY_RUN}\n")

            # Write back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info("✓ Main configuration saved to file")
            
        except Exception as e:
            logger.error(f"Failed to save main configuration to file: {e}")

    def _refresh_cooldown_panel(self):
        """Refresh the cooldown tables from the runtime SkillComboManager if available."""
        scm = None
        try:
            if self._controller and hasattr(self._controller, 'action_planner'):
                scm = getattr(self._controller.action_planner, 'skill_combo_manager', None)
        except Exception:
            scm = None

        # Skills
        skill_names = []
        try:
            import skill_combo_config as scc
            if hasattr(scc, 'SKILL_COOLDOWNS'):
                skill_names = list(scc.SKILL_COOLDOWNS.keys())
        except Exception:
            skill_names = []

        self._skills_table.setRowCount(len(skill_names))
        for r, name in enumerate(skill_names):
            try:
                item_name = QtWidgets.QTableWidgetItem(name)
                if scm:
                    rem = scm.get_skill_cooldown_remaining(name)
                    txt = f"{rem:.1f}" if rem > 0 else "Ready"
                else:
                    txt = "Ready"
                self._skills_table.setItem(r, 0, item_name)
                self._skills_table.setItem(r, 1, QtWidgets.QTableWidgetItem(txt))
            except Exception:
                pass

        # Combos
        combo_names = []
        try:
            import skill_combo_config as scc
            if hasattr(scc, 'COMBO_SETS'):
                combo_names = list(scc.COMBO_SETS.keys())
        except Exception:
            combo_names = []

        self._combos_table.setRowCount(len(combo_names))
        for r, cname in enumerate(combo_names):
            try:
                item_name = QtWidgets.QTableWidgetItem(cname)
                status = "Unknown"
                if scm:
                    rem = scm.get_combo_cooldown_remaining(cname)
                    # try to get skills for the combo to determine readiness
                    skills = []
                    if hasattr(scm, 'get_combo_skills'):
                        try:
                            skills = scm.get_combo_skills(cname)
                        except Exception:
                            skills = []
                    all_ready = True
                    if hasattr(scm, 'are_all_skills_ready') and skills:
                        all_ready = scm.are_all_skills_ready(skills)
                    if rem > 0:
                        status = f"Cooldown {rem:.1f}s"
                    else:
                        status = "Ready" if all_ready else "Waiting"
                else:
                    status = "Ready"
                self._combos_table.setItem(r, 0, item_name)
                self._combos_table.setItem(r, 1, QtWidgets.QTableWidgetItem(status))
            except Exception:
                pass

    def _on_backend_changed(self, backend: str):
        """User changed the input backend from the UI dropdown."""
        try:
            # Validate availability and persist via JSON-backed config
            try:
                import skill_combo_config as scc
                # Validate backend and show a dialog if unavailable
                try:
                    ic.validate_backend(backend)
                    scc.update_config({'INPUT_BACKEND': backend})
                    ic.INPUT_BACKEND = backend
                    self.log(f"Input backend set to: {backend}")
                except RuntimeError as ve:
                    # Persist selection so UI reflects user's choice, but inform the user
                    try:
                        scc.update_config({'INPUT_BACKEND': backend})
                    except Exception:
                        pass
                    ic.INPUT_BACKEND = backend
                    QtWidgets.QMessageBox.warning(self, 'Backend Unavailable', f"Selected backend '{backend}' appears unavailable:\n\n{ve}")
                    self.log(f"Selected backend '{backend}' may be unavailable: {ve}")
            except Exception:
                # Fallback: set module var and try to save main config
                ic.INPUT_BACKEND = backend
                self._save_main_config_to_file()
                self.log(f"Input backend set to: {backend}")
            # update status indicator after attempting to set backend
            try:
                self._update_backend_status(backend)
            except Exception:
                pass
        except Exception as e:
            self.log(f"Failed to set input backend: {e}")

    def _on_dry_run_toggled(self, enabled: bool):
        """User toggled DRY_RUN simulate mode in the UI."""
        try:
            ic.INPUT_DRY_RUN = bool(enabled)
            try:
                import skill_combo_config as scc
                scc.update_config({'INPUT_DRY_RUN': bool(enabled)})
            except Exception:
                # fall back to saving main config file
                self._save_main_config_to_file()
            self.log(f"Simulate mode (DRY_RUN) set to: {bool(enabled)}")
        except Exception as e:
            self.log(f"Failed to toggle simulate mode: {e}")
    
    def _update_backend_status(self, backend: str):
        """Update the small status label next to the backend selector."""
        try:
            ic.validate_backend(backend)
            self.backend_status.setText('Available')
            self.backend_status.setStyleSheet('color: green; font-weight: bold;')
            self.backend_status.setToolTip(f"Backend '{backend}' is available")
        except RuntimeError as e:
            self.backend_status.setText('Unavailable')
            self.backend_status.setStyleSheet('color: red; font-weight: bold;')
            self.backend_status.setToolTip(str(e))
        except Exception:
            self.backend_status.setText('Unknown')
            self.backend_status.setStyleSheet('color: orange;')
            self.backend_status.setToolTip('Unable to determine backend status')
    
    def _open_skill_config(self):
        """Open skill configuration file in default editor."""
        try:
            import os
            import subprocess
            config_path = os.path.join(os.path.dirname(__file__), 'skill_combo_config.py')
            
            if os.path.exists(config_path):
                if sys.platform == 'win32':
                    os.startfile(config_path)
                else:
                    subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', config_path])
                self.log(f"✓ Opened {config_path}")
            else:
                self.log(f"Config file not found: {config_path}")
        except Exception as e:
            self.log(f"Failed to open config file: {e}")

    def _refresh_windows(self):
        self.win_combo.clear()
        wins = list_windows()
        for title, hwnd in wins:
            self.win_combo.addItem(f"{title} (hwnd={hwnd})", hwnd)

    def start(self):
        idx = self.win_combo.currentIndex()
        if idx < 0:
            self.log("No window selected")
            return
        hwnd = self.win_combo.currentData()
        try:
            ic.set_active_hwnd(hwnd)
        except Exception:
            pass
        rect = get_window_rect(hwnd)
        if not rect:
            self.log("Unable to get window rect")
            return
        left, top, w, h = rect
        # show overlay aligned to window
        self._overlay.setGeometry(left, top, w, h)
        self._overlay.show()
        self._overlay.make_clickthrough()

        # create controller (local model) - use default FPS (None uses default inside detection controller)
        self._controller = DetectionController(hwnd=hwnd, overlay_update=self._overlay.update_overlay, log_fn=self.log, fps=None)
        # apply stored automation preference
        try:
            self._controller.action_planner.set_enabled(self._automation_enabled)
        except Exception:
            pass
        self._controller.start()
        # Focus the game window immediately when starting
        try:
            ic.focus_window(hwnd)
        except Exception:
            pass
        # start periodic overlay repositioning to follow the target window
        self._pos_timer.start()
        # start cooldown monitor refresh
        try:
            self._cooldown_timer.start()
        except Exception:
            pass
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.log("Started detection")

    def stop(self):
        if self._controller:
            self._controller.stop()
            self._controller = None
        self._overlay.hide()
        self._pos_timer.stop()
        try:
            self._cooldown_timer.stop()
        except Exception:
            pass
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.log("Stopped")

    def emergency_stop(self):
        # Immediately disable automation and stop controller
        self._automation_enabled = False
        try:
            self._overlay.set_automation_enabled(False)
        except Exception:
            pass
        if self._controller:
            try:
                self._controller.action_planner.set_enabled(False)
            except Exception:
                pass
        self.log("EMERGENCY STOP: Automation disabled")

    def _reposition_overlay(self):
        # Keep overlay aligned to the target window while running
        idx = self.win_combo.currentIndex()
        if idx < 0:
            return
        hwnd = self.win_combo.currentData()
        rect = get_window_rect(hwnd)
        if rect:
            left, top, w, h = rect
            self._overlay.setGeometry(left, top, w, h)

    def toggle_automation(self):
        # toggle desired automation state and apply to controller if present
        self._automation_enabled = not self._automation_enabled
        enabled = self._automation_enabled
        # update overlay indicator
        try:
            self._overlay.set_automation_enabled(enabled)
        except Exception:
            pass
        # apply to running controller
        if self._controller:
            try:
                self._controller.action_planner.set_enabled(enabled)
            except Exception:
                pass

    def _start_hotkey_listener(self):
        # Start background thread that registers a global Delete hotkey and
        # invokes toggle_automation when pressed.
        import threading, ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        WM_HOTKEY = 0x0312
        VK_DELETE = 0x2E

        def _hotkey_thread_fn():
            HOTKEY_ID = 1
            # Try RegisterHotKey first (simple, preferred)
            if user32.RegisterHotKey(None, HOTKEY_ID, 0, VK_DELETE):
                # registration succeeded
                try:
                    self.log("Hotkey registered: Delete (RegisterHotKey)")
                except Exception:
                    pass
                msg = wintypes.MSG()
                try:
                    while True:
                        b = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if b == 0:
                            break
                        if msg.message == WM_HOTKEY:
                            try:
                                QtCore.QMetaObject.invokeMethod(self, "toggle_automation", QtCore.Qt.QueuedConnection)
                            except Exception:
                                pass
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                finally:
                    try:
                        user32.UnregisterHotKey(None, HOTKEY_ID)
                    except Exception:
                        pass
                return

            # If RegisterHotKey failed, fall back to a low-level keyboard hook
            try:
                self.log("RegisterHotKey failed; falling back to low-level keyboard hook")
            except Exception:
                pass

            # WH_KEYBOARD_LL hook to catch Delete presses
            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100

            kernel32 = ctypes.windll.kernel32

            # define KBDLLHOOKSTRUCT
            class KBDLLHOOKSTRUCT(ctypes.Structure):
                _fields_ = [("vkCode", wintypes.DWORD),
                            ("scanCode", wintypes.DWORD),
                            ("flags", wintypes.DWORD),
                            ("time", wintypes.DWORD),
                            ("dwExtraInfo", wintypes.ULONG_PTR)]

            LowLevelKeyboardProc = ctypes.WINFUNCTYPE(wintypes.LRESULT, wintypes.INT, wintypes.WPARAM, wintypes.LPARAM)

            @LowLevelKeyboardProc
            def _ll_keyboard_proc(nCode, wParam, lParam):
                try:
                    if nCode >= 0 and wParam == WM_KEYDOWN:
                        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
                        if kb.vkCode == VK_DELETE:
                            try:
                                QtCore.QMetaObject.invokeMethod(self, "toggle_automation", QtCore.Qt.QueuedConnection)
                            except Exception:
                                pass
                except Exception:
                    pass
                return user32.CallNextHookEx(None, nCode, wParam, lParam)

            # install hook
            hook_id = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _ll_keyboard_proc, kernel32.GetModuleHandleW(None), 0)
            if not hook_id:
                try:
                    self.log("Failed to install low-level keyboard hook for Delete key")
                except Exception:
                    pass
                return

            # message loop to keep the hook alive
            msg = wintypes.MSG()
            try:
                while True:
                    b = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                    if b == 0:
                        break
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            finally:
                try:
                    user32.UnhookWindowsHookEx(hook_id)
                except Exception:
                    pass

        t = threading.Thread(target=_hotkey_thread_fn, daemon=True)
        t.start()
        self._hotkey_thread = t

    def _open_skill_editor(self):
        """Navigate to the embedded skill editor screen."""
        try:
            self.change_page(1)
        except Exception:
            pass
    
    def _open_combo_editor(self):
        """Navigate to the embedded combo editor screen."""
        try:
            self.change_page(2)
        except Exception:
            pass

    # Anti-detection dialog removed (stealth_config no longer supported)

    def closeEvent(self, event):
        # ensure controller stopped and leave
        try:
            if self._controller:
                self._controller.stop()
        except Exception:
            pass
        return super().closeEvent(event)


class KeybindCaptureDialog(QtWidgets.QDialog):
    """Dialog for capturing a keybind press."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Press a Key")
        self.setModal(True)
        self.setFixedSize(400, 200)
        
        self.captured_key = None
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Instructions
        instruction_label = QtWidgets.QLabel("Press a skill key:\n\nSupported: F1-F9, 1-9, 0, -, =")
        instruction_label.setAlignment(QtCore.Qt.AlignCenter)
        instruction_label.setStyleSheet("font-size: 14pt; padding: 20px;")
        layout.addWidget(instruction_label)
        
        # Display captured key
        self.key_display = QtWidgets.QLabel("Waiting...")
        self.key_display.setAlignment(QtCore.Qt.AlignCenter)
        self.key_display.setStyleSheet("font-size: 18pt; font-weight: bold; color: #4CAF50; padding: 10px;")
        layout.addWidget(self.key_display)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        self.confirm_btn = QtWidgets.QPushButton("✓ Confirm")
        self.confirm_btn.setEnabled(False)
        self.confirm_btn.clicked.connect(self.accept)
        self.confirm_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        
        cancel_btn = QtWidgets.QPushButton("✗ Cancel")
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("QPushButton { background-color: #f44336; color: white; font-weight: bold; padding: 8px; }")
        
        button_layout.addWidget(self.confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
    
    def keyPressEvent(self, event):
        """Capture key press."""
        key = event.key()
        modifiers = event.modifiers()
        
        # Map numeric and punctuation keys
        key_map = {
            QtCore.Qt.Key_1: '1', QtCore.Qt.Key_2: '2', QtCore.Qt.Key_3: '3',
            QtCore.Qt.Key_4: '4', QtCore.Qt.Key_5: '5', QtCore.Qt.Key_6: '6',
            QtCore.Qt.Key_7: '7', QtCore.Qt.Key_8: '8', QtCore.Qt.Key_9: '9',
            QtCore.Qt.Key_0: '0', QtCore.Qt.Key_Minus: '-', QtCore.Qt.Key_Equal: '=',
        }

        # Accept F1-F9 and numeric keys only; explicitly ignore modifier keys
        if key in key_map and not (modifiers & (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier)):
            self.captured_key = key_map[key]
            self.key_display.setText(self.captured_key)
            self.confirm_btn.setEnabled(True)
            return

        # Function keys F1..F9
        f_keys = {QtCore.Qt.Key_F1: 'f1', QtCore.Qt.Key_F2: 'f2', QtCore.Qt.Key_F3: 'f3',
                  QtCore.Qt.Key_F4: 'f4', QtCore.Qt.Key_F5: 'f5', QtCore.Qt.Key_F6: 'f6',
                  QtCore.Qt.Key_F7: 'f7', QtCore.Qt.Key_F8: 'f8', QtCore.Qt.Key_F9: 'f9'}
        if key in f_keys and not (modifiers & (QtCore.Qt.AltModifier | QtCore.Qt.ControlModifier)):
            self.captured_key = f_keys[key]
            self.key_display.setText(self.captured_key.upper())
            self.confirm_btn.setEnabled(True)
            return

        # Otherwise invalid for skill binds
        self.key_display.setText("Invalid key! Use F1-F9 or 1-9, 0, -, =")
        self.key_display.setStyleSheet("font-size: 18pt; font-weight: bold; color: #f44336; padding: 10px;")


class SkillEditorScreen(QtWidgets.QWidget):
    """Embedded screen for editing individual skill cooldowns."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('skill_editor_screen')
        self.setMinimumSize(700, 500)

        import skill_combo_config
        self.config = skill_combo_config
        # Create a clean two-column layout: left = pool + GCD, right = cooldowns table
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setSpacing(12)

        # Left column: Pool and GCD
        left_col = QtWidgets.QVBoxLayout()
        left_col.setSpacing(10)

        title = QtWidgets.QLabel("Skill Editor")
        title.setStyleSheet('font-size:18pt; font-weight:600; padding:6px;')
        left_col.addWidget(title)

        pool_group = QtWidgets.QGroupBox("Single Skill Pool")
        pool_group.setToolTip('Comma separated skill keys used for single-skill selection')
        pool_layout = QtWidgets.QVBoxLayout()

        # Compact controls: input + add button on one row
        pool_row = QtWidgets.QHBoxLayout()
        self.skill_pool_edit = QtWidgets.QLineEdit()
        self.skill_pool_edit.setPlaceholderText("e.g. 1,2,3,f1")
        self.skill_pool_edit.setText(", ".join(self.config.SINGLE_SKILL_POOL))
        pool_row.addWidget(self.skill_pool_edit)
        add_pool_skill_btn = QtWidgets.QPushButton("Add")
        add_pool_skill_btn.setFixedWidth(80)
        add_pool_skill_btn.setToolTip('Capture a key to add to the pool')
        add_pool_skill_btn.clicked.connect(self._add_skill_to_pool)
        pool_row.addWidget(add_pool_skill_btn)
        pool_layout.addLayout(pool_row)

        # GCD control
        gcd_row = QtWidgets.QHBoxLayout()
        gcd_row.addWidget(QtWidgets.QLabel("Single Skill GCD:"))
        self.gcd_spin = QtWidgets.QDoubleSpinBox()
        self.gcd_spin.setRange(0.1, 10.0)
        self.gcd_spin.setSingleStep(0.1)
        self.gcd_spin.setValue(self.config.SINGLE_SKILL_GLOBAL_COOLDOWN)
        gcd_row.addWidget(self.gcd_spin)
        gcd_row.addStretch()
        pool_layout.addLayout(gcd_row)

        pool_group.setLayout(pool_layout)
        left_col.addWidget(pool_group)

        # Helpful hint area
        hint = QtWidgets.QLabel("Tip: Use the Add button to capture keys or type a comma-separated list.")
        hint.setStyleSheet('color: #bdbdbd;')
        left_col.addWidget(hint)
        left_col.addStretch()

        # Save / Cancel buttons (left column bottom)
        actions_row = QtWidgets.QHBoxLayout()
        save_btn = QtWidgets.QPushButton("Save Changes")
        save_btn.setStyleSheet('background-color:#4CAF50; color:white;')
        save_btn.clicked.connect(self._save_and_accept)
        cancel_btn = QtWidgets.QPushButton("Cancel")
        cancel_btn.setStyleSheet('background-color:#f44336; color:white;')
        cancel_btn.clicked.connect(self._on_cancel)
        actions_row.addWidget(save_btn)
        actions_row.addWidget(cancel_btn)
        left_col.addLayout(actions_row)

        # Right column: Skill cooldowns table with Add/Remove
        right_col = QtWidgets.QVBoxLayout()
        right_col.setSpacing(8)

        cooldown_group = QtWidgets.QGroupBox("Individual Skill Cooldowns")
        cooldown_layout = QtWidgets.QVBoxLayout()

        self.skill_table = QtWidgets.QTableWidget()
        self.skill_table.setColumnCount(2)
        self.skill_table.setHorizontalHeaderLabels(["Keybind", "Cooldown (s)"])
        self.skill_table.horizontalHeader().setStretchLastSection(True)
        self.skill_table.setAlternatingRowColors(True)
        cooldown_layout.addWidget(self.skill_table)

        # toolbar layout for add/remove
        tb = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("➕ Add")
        add_btn.setFixedWidth(90)
        add_btn.clicked.connect(self._add_skill)
        remove_btn = QtWidgets.QPushButton("➖ Remove")
        remove_btn.setFixedWidth(90)
        remove_btn.clicked.connect(self._remove_skill)
        tb.addWidget(add_btn)
        tb.addWidget(remove_btn)
        tb.addStretch()
        cooldown_layout.addLayout(tb)

        cooldown_group.setLayout(cooldown_layout)
        right_col.addWidget(cooldown_group)

        # Populate initial data
        self._load_skills()

        # Assemble main layout
        main_layout.addLayout(left_col, 0)
        main_layout.addLayout(right_col, 1)
    
    def _load_skills(self):
        """Load skills from config into table."""
        self.skill_table.setRowCount(len(self.config.SKILL_COOLDOWNS))
        for i, (keybind, cooldown) in enumerate(self.config.SKILL_COOLDOWNS.items()):
            # Keybind column
            keybind_item = QtWidgets.QTableWidgetItem(keybind)
            self.skill_table.setItem(i, 0, keybind_item)
            
            # Cooldown spinbox
            cooldown_spin = QtWidgets.QDoubleSpinBox()
            cooldown_spin.setRange(0.1, 600.0)
            cooldown_spin.setSingleStep(0.5)
            cooldown_spin.setValue(cooldown)
            cooldown_spin.setSuffix(" sec")
            self.skill_table.setCellWidget(i, 1, cooldown_spin)
    
    def _add_skill(self):
        """Add a new skill row with keybind capture."""
        # Open keybind capture dialog
        capture_dialog = KeybindCaptureDialog(self)
        if capture_dialog.exec() and capture_dialog.captured_key:
            keybind = capture_dialog.captured_key
            
            # Check if keybind already exists
            for row in range(self.skill_table.rowCount()):
                existing_item = self.skill_table.item(row, 0)
                if existing_item and existing_item.text() == keybind:
                    QtWidgets.QMessageBox.warning(
                        self, 
                        "Duplicate Keybind", 
                        f"Keybind '{keybind}' already exists!"
                    )
                    return
            
            # Add new row
            row = self.skill_table.rowCount()
            self.skill_table.insertRow(row)
            
            # Set keybind
            keybind_item = QtWidgets.QTableWidgetItem(keybind)
            self.skill_table.setItem(row, 0, keybind_item)
            
            # Default cooldown = 60 seconds
            cooldown_spin = QtWidgets.QDoubleSpinBox()
            cooldown_spin.setRange(0.1, 600.0)
            cooldown_spin.setSingleStep(0.5)
            cooldown_spin.setValue(60.0)  # DEFAULT: 60 seconds
            cooldown_spin.setSuffix(" sec")
            self.skill_table.setCellWidget(row, 1, cooldown_spin)
    
    def _remove_skill(self):
        """Remove selected skill row."""
        current_row = self.skill_table.currentRow()
        if current_row >= 0:
            self.skill_table.removeRow(current_row)
    
    def _add_skill_to_pool(self):
        """Add a skill to the single skill pool using keybind capture."""
        capture_dialog = KeybindCaptureDialog(self)
        if capture_dialog.exec() and capture_dialog.captured_key:
            keybind = capture_dialog.captured_key
            
            # Get current pool skills
            current_text = self.skill_pool_edit.text().strip()
            if current_text:
                # Parse existing skills
                existing_skills = [s.strip() for s in current_text.split(',')]
                
                # Check for duplicates
                if keybind in existing_skills:
                    QtWidgets.QMessageBox.warning(
                        self, 
                        "Duplicate Skill", 
                        f"Skill '{keybind}' is already in the pool!"
                    )
                    return
                
                # Add new skill
                self.skill_pool_edit.setText(current_text + ", " + keybind)
            else:
                self.skill_pool_edit.setText(keybind)
    
    def _save_and_accept(self):
        """Save configuration when embedded (no dialog close)."""
        # Update single skill pool
        pool_text = self.skill_pool_edit.text().strip()
        if pool_text:
            self.config.SINGLE_SKILL_POOL = [s.strip() for s in pool_text.split(",")]
        
        # Update GCD
        self.config.SINGLE_SKILL_GLOBAL_COOLDOWN = self.gcd_spin.value()
        
        # Update skill cooldowns
        new_cooldowns = {}
        for row in range(self.skill_table.rowCount()):
            keybind_item = self.skill_table.item(row, 0)
            cooldown_spin = self.skill_table.cellWidget(row, 1)
            if keybind_item and cooldown_spin:
                keybind = keybind_item.text().strip()
                cooldown = cooldown_spin.value()
                if keybind:
                    new_cooldowns[keybind] = cooldown
        
        self.config.SKILL_COOLDOWNS = new_cooldowns
        
        # Save to file for persistence
        self._save_config_to_file()
        # Notify parent/main window that skills were updated
        try:
            parent = self.parent()
            if parent and hasattr(parent, '_update_skill_config'):
                parent._update_skill_config()
            if parent and hasattr(parent, 'log'):
                parent.log("✓ Individual skills updated")
        except Exception:
            pass
    
    def _save_config_to_file(self):
        """Save configuration back to skill_combo_config.py file."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'skill_combo_config.py')
            
            # Read the current file
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and replace the configuration sections
            new_lines = []
            skip_until = None
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Replace SINGLE_SKILL_POOL
                if 'SINGLE_SKILL_POOL = [' in line:
                    pool_str = ', '.join([f"'{s}'" for s in self.config.SINGLE_SKILL_POOL])
                    new_lines.append(f'SINGLE_SKILL_POOL = [{pool_str}]\n')
                    # Skip until next configuration
                    while i < len(lines) and not lines[i].strip().startswith(('SINGLE_SKILL_GLOBAL_COOLDOWN', '#', '\n')):
                        i += 1
                    continue
                
                # Replace SINGLE_SKILL_GLOBAL_COOLDOWN
                elif 'SINGLE_SKILL_GLOBAL_COOLDOWN = ' in line and not line.strip().startswith('#'):
                    new_lines.append(f'SINGLE_SKILL_GLOBAL_COOLDOWN = {self.config.SINGLE_SKILL_GLOBAL_COOLDOWN}\n')
                    i += 1
                    continue
                
                # Replace SKILL_COOLDOWNS dictionary
                elif 'SKILL_COOLDOWNS = {' in line:
                    new_lines.append('SKILL_COOLDOWNS = {\n')
                    # Write all cooldowns
                    for keybind, cooldown in sorted(self.config.SKILL_COOLDOWNS.items()):
                        new_lines.append(f"    '{keybind}': {cooldown},\n")
                    new_lines.append('}\n')
                    # Skip old dictionary content
                    i += 1
                    while i < len(lines) and '}' not in lines[i]:
                        i += 1
                    i += 1  # Skip the closing brace
                    continue
                
                else:
                    new_lines.append(line)
                
                i += 1
            
            # Write back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info("✓ Skill configuration saved to file")
            
        except Exception as e:
            logger.error(f"Failed to save configuration to file: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Save Warning",
                f"Configuration updated in memory but failed to save to file:\n{e}\n\nChanges will be lost on restart."
            )

    def _on_cancel(self):
        """Handle cancel action for embedded editor: navigate back to Dashboard."""
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'change_page'):
                parent.change_page(0)
        except Exception:
            pass


class ComboEditorScreen(QtWidgets.QWidget):
    """Embedded screen for editing combo sets."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('combo_editor_screen')
        self.setMinimumSize(800, 600)

        import skill_combo_config
        self.config = skill_combo_config

        layout = QtWidgets.QVBoxLayout(self)

        # Instructions
        info = QtWidgets.QLabel(
            "Create and manage skill combo sets. Each combo set executes a sequence of skills with delays.\n"
            "Combo sets have their own cooldown timer and only execute when ALL skills are ready."
        )
        info.setWordWrap(True)
        info.setStyleSheet("background-color: #424242; padding: 10px; border-radius: 5px;")
        layout.addWidget(info)
        
        # Combo list
        splitter = QtWidgets.QSplitter(QtCore.Qt.Horizontal)
        
        # Left side: Combo list
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)
        left_layout.addWidget(QtWidgets.QLabel("Combo Sets:"))
        
        self.combo_list = QtWidgets.QListWidget()
        self.combo_list.currentRowChanged.connect(self._load_combo_details)
        left_layout.addWidget(self.combo_list)
        
        # List buttons
        list_btn_layout = QtWidgets.QHBoxLayout()
        new_combo_btn = QtWidgets.QPushButton("➕ New Combo")
        new_combo_btn.clicked.connect(self._new_combo)
        delete_combo_btn = QtWidgets.QPushButton("➖ Delete Combo")
        delete_combo_btn.clicked.connect(self._delete_combo)
        list_btn_layout.addWidget(new_combo_btn)
        list_btn_layout.addWidget(delete_combo_btn)
        left_layout.addLayout(list_btn_layout)
        
        splitter.addWidget(left_widget)
        
        # Right side: Combo details
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        
        # Combo name
        name_layout = QtWidgets.QFormLayout()
        self.combo_name_edit = QtWidgets.QLineEdit()
        name_layout.addRow("Combo Name:", self.combo_name_edit)
        right_layout.addLayout(name_layout)
        
        # Enabled checkbox
        self.combo_enabled_cb = QtWidgets.QCheckBox("Enabled")
        self.combo_enabled_cb.setChecked(True)
        right_layout.addWidget(self.combo_enabled_cb)
        
        # Cooldown
        cooldown_layout = QtWidgets.QHBoxLayout()
        cooldown_layout.addWidget(QtWidgets.QLabel("Combo Cooldown:"))
        self.combo_cooldown_spin = QtWidgets.QDoubleSpinBox()
        self.combo_cooldown_spin.setRange(0.0, 600.0)
        self.combo_cooldown_spin.setSingleStep(1.0)
        self.combo_cooldown_spin.setValue(60.0)
        self.combo_cooldown_spin.setSuffix(" sec")
        cooldown_layout.addWidget(self.combo_cooldown_spin)
        cooldown_layout.addStretch()
        right_layout.addLayout(cooldown_layout)
        
        # Delay between skills
        delay_layout = QtWidgets.QHBoxLayout()
        delay_layout.addWidget(QtWidgets.QLabel("Delay Between Skills:"))
        self.combo_delay_spin = QtWidgets.QDoubleSpinBox()
        self.combo_delay_spin.setRange(0.0, 5.0)
        self.combo_delay_spin.setSingleStep(0.1)
        self.combo_delay_spin.setValue(0.5)
        self.combo_delay_spin.setSuffix(" sec")
        delay_layout.addWidget(self.combo_delay_spin)
        delay_layout.addStretch()
        right_layout.addLayout(delay_layout)
        
        # Skills list
        skills_label_layout = QtWidgets.QHBoxLayout()
        skills_label_layout.addWidget(QtWidgets.QLabel("Skills (in execution order):"))
        add_skill_btn = QtWidgets.QPushButton("⌨️ Press Key to Add")
        add_skill_btn.setStyleSheet("QPushButton { background-color: #2196F3; color: white; font-weight: bold; padding: 5px; }")
        add_skill_btn.clicked.connect(self._add_skill_to_combo)
        skills_label_layout.addWidget(add_skill_btn)
        skills_label_layout.addStretch()
        right_layout.addLayout(skills_label_layout)
        
        self.combo_skills_edit = QtWidgets.QPlainTextEdit()
        self.combo_skills_edit.setPlaceholderText("Click 'Press Key to Add' button to add skills, or type manually:\n1\n2\nalt+1\n3")
        right_layout.addWidget(self.combo_skills_edit)
        
        # Save combo button
        save_combo_btn = QtWidgets.QPushButton("💾 Save Combo")
        save_combo_btn.clicked.connect(self._save_current_combo)
        save_combo_btn.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; }")
        right_layout.addWidget(save_combo_btn)
        
        splitter.addWidget(right_widget)
        splitter.setSizes([250, 550])
        
        layout.addWidget(splitter)
        
        # Load combo list
        self._load_combo_list()
        
        # Close button will navigate back to Dashboard when embedded
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Close
        )
        button_box.rejected.connect(self._on_close)
        layout.addWidget(button_box)
        
        self.current_combo_index = -1
    
    def _load_combo_list(self):
        """Load combo sets into list."""
        self.combo_list.clear()
        for combo in self.config.COMBO_SETS:
            enabled_icon = "✓" if combo.get('enabled', True) else "✗"
            self.combo_list.addItem(f"{enabled_icon} {combo['name']}")
    
    def _load_combo_details(self, row):
        """Load combo details when selected."""
        if row < 0 or row >= len(self.config.COMBO_SETS):
            return
        
        self.current_combo_index = row
        combo = self.config.COMBO_SETS[row]
        
        self.combo_name_edit.setText(combo['name'])
        self.combo_enabled_cb.setChecked(combo.get('enabled', True))
        self.combo_cooldown_spin.setValue(combo.get('cooldown', 60.0))
        self.combo_delay_spin.setValue(combo.get('delay_between_skills', 0.5))
        self.combo_skills_edit.setPlainText("\n".join(combo.get('skills', [])))
    
    def _new_combo(self):
        """Create a new combo set."""
        new_combo = {
            'name': f'Combo {len(self.config.COMBO_SETS) + 1}',
            'skills': [],
            'cooldown': 60.0,
            'delay_between_skills': 0.5,
            'enabled': True,
        }
        self.config.COMBO_SETS.append(new_combo)
        self._load_combo_list()
        self.combo_list.setCurrentRow(len(self.config.COMBO_SETS) - 1)
    
    def _delete_combo(self):
        """Delete selected combo set."""
        current_row = self.combo_list.currentRow()
        if current_row >= 0 and current_row < len(self.config.COMBO_SETS):
            combo_name = self.config.COMBO_SETS[current_row]['name']
            
            # Confirm deletion
            reply = QtWidgets.QMessageBox.question(
                self,
                'Delete Combo',
                f"Are you sure you want to delete combo '{combo_name}'?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
                QtWidgets.QMessageBox.No
            )
            
            if reply == QtWidgets.QMessageBox.Yes:
                del self.config.COMBO_SETS[current_row]
                self._save_combos_to_file()
                self._load_combo_list()
                self.combo_name_edit.clear()
                self.combo_skills_edit.clear()
    
    def _add_skill_to_combo(self):
        """Add a skill to the combo using keybind capture."""
        capture_dialog = KeybindCaptureDialog(self)
        if capture_dialog.exec() and capture_dialog.captured_key:
            keybind = capture_dialog.captured_key
            
            # Add to the end of the skills list
            current_text = self.combo_skills_edit.toPlainText().strip()
            if current_text:
                self.combo_skills_edit.setPlainText(current_text + "\n" + keybind)
            else:
                self.combo_skills_edit.setPlainText(keybind)
    
    def _save_current_combo(self):
        """Save current combo details."""
        if self.current_combo_index < 0 or self.current_combo_index >= len(self.config.COMBO_SETS):
            return
        
        combo = self.config.COMBO_SETS[self.current_combo_index]
        combo['name'] = self.combo_name_edit.text().strip() or f'Combo {self.current_combo_index + 1}'
        combo['enabled'] = self.combo_enabled_cb.isChecked()
        combo['cooldown'] = self.combo_cooldown_spin.value()
        combo['delay_between_skills'] = self.combo_delay_spin.value()
        
        # Parse skills
        skills_text = self.combo_skills_edit.toPlainText().strip()
        combo['skills'] = [s.strip() for s in skills_text.split("\n") if s.strip()]
        
        self._load_combo_list()
        self.combo_list.setCurrentRow(self.current_combo_index)
        
        # Save to file for persistence
        self._save_combos_to_file()
        
        # Show confirmation
        QtWidgets.QMessageBox.information(self, "Saved", f"Combo '{combo['name']}' saved successfully!")
    
    def _save_combos_to_file(self):
        """Save combo sets back to skill_combo_config.py file."""
        try:
            import os
            config_path = os.path.join(os.path.dirname(__file__), 'skill_combo_config.py')
            
            # Read the current file
            with open(config_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Find and replace COMBO_SETS
            new_lines = []
            i = 0
            
            while i < len(lines):
                line = lines[i]
                
                # Replace COMBO_SETS list
                if 'COMBO_SETS = [' in line:
                    new_lines.append('COMBO_SETS = [\n')
                    
                    # Write all combo sets
                    for combo in self.config.COMBO_SETS:
                        new_lines.append('    {\n')
                        new_lines.append(f"        'name': '{combo['name']}',\n")
                        
                        # Write skills list
                        skills_str = ', '.join([f"'{s}'" for s in combo['skills']])
                        new_lines.append(f"        'skills': [{skills_str}],\n")
                        
                        new_lines.append(f"        'cooldown': {combo['cooldown']},\n")
                        new_lines.append(f"        'delay_between_skills': {combo['delay_between_skills']},\n")
                        new_lines.append(f"        'enabled': {combo['enabled']},\n")
                        new_lines.append('    },\n')
                    
                    new_lines.append(']\n')
                    
                    # Skip old list content
                    i += 1
                    bracket_count = 1
                    while i < len(lines) and bracket_count > 0:
                        if '[' in lines[i]:
                            bracket_count += lines[i].count('[')
                        if ']' in lines[i]:
                            bracket_count -= lines[i].count(']')
                        i += 1
                    continue
                
                else:
                    new_lines.append(line)
                
                i += 1
            
            # Write back to file
            with open(config_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            
            logger.info("✓ Combo sets saved to file")
            
        except Exception as e:
            logger.error(f"Failed to save combo sets to file: {e}")
            QtWidgets.QMessageBox.warning(
                self,
                "Save Warning",
                f"Combo updated in memory but failed to save to file:\n{e}\n\nChanges will be lost on restart."
            )

    def _on_close(self):
        """Handle close action for embedded combo editor: navigate back to Dashboard."""
        try:
            parent = self.parent()
            if parent and hasattr(parent, 'change_page'):
                parent.change_page(0)
        except Exception:
            pass


    


def run_app():
    """Main application entry point."""
    app = QtWidgets.QApplication(sys.argv)
    # Apply a dark purple theme stylesheet for the whole app
    app.setStyleSheet("""
    QWidget { background-color: #1b1226; color: #EDE7F6; font-family: 'Segoe UI', Tahoma, Arial; }
    QGroupBox { background-color: #24132f; border: 1px solid #3a1f3b; border-radius: 8px; margin-top: 6px; }
    QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 4px 8px; color: #D1C4E9; }
    QPushButton { background-color: qlineargradient(spread:pad, x1:0, y1:0, x2:1, y2:0, stop:0 #5e35b1, stop:1 #7e57c2); color: white; border-radius: 6px; padding: 8px; }
    QPlainTextEdit, QTextEdit { background-color: #0f0815; border: 1px solid #2b1430; }
    QTableWidget { background-color: #120716; gridline-color: #2b1430; }
    QHeaderView::section { background-color: #2b1430; color: #EDE7F6; }
    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit { background-color: #120716; color: #EDE7F6; border: 1px solid #2b1430; }
    QStackedWidget#pages { background: transparent; }
    """)

    # Interception is the required backend for input control
    logger.info("Interception backend enforced; ensure interception driver is installed")

    # Pre-start checklist dialog
    class PreStartDialog(QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("Before You Start - Read Carefully")
            self.setModal(True)
            self.setMinimumSize(700, 520)

            layout = QtWidgets.QVBoxLayout(self)

            info = QtWidgets.QLabel(
                "Please verify the following BEFORE starting the macro:\n\n"
                "- Make sure the Game is running in Windowed Mode\n"
                "- Make sure the Player is already in the hunting/farming area\n"
                "- Ensure the Interception driver is installed (the program can install it)\n"
                "- Double-check and configure your Skills and Combos (no misinputs)\n\n"
                "Recommended In-Game Settings to verify:\n"
                "Graphics -> Display Mode -> Windowed Mode\n"
                "Graphics -> Nvidia Reflex -> BOOST (if using Nvidia)\n"
                "Key Settings -> Change Target -> Tab key\n"
                "Combat -> Target Scanning -> Preferred Search Direction -> Front of Camera\n"
                "Combat -> Target Scanning -> Target Scanning Detailed Settings -> Closest First\n"
                "Combat -> Controls -> Control Mode -> AION 1\n"
                "Combat -> Controls -> Click ground to Move -> Allow Both Sides\n"
                "Combat -> Controls -> Pursue Targets with Skill Activation -> ON\n"
                "Combat -> Controls -> Use Basic Attack Repeatedly -> ON\n"
                "Combat -> Controls -> Auto Target upon Skill use -> ON\n"
            )
            info.setWordWrap(True)
            layout.addWidget(info)

            # Spacer + button
            spacer = QtWidgets.QSpacerItem(20, 20, QtWidgets.QSizePolicy.Minimum, QtWidgets.QSizePolicy.Expanding)
            layout.addItem(spacer)

            btn = QtWidgets.QPushButton("I Understand and Done Everything")
            btn.setFixedHeight(44)
            btn.clicked.connect(self.accept)
            btn.setStyleSheet("QPushButton { font-weight: bold; font-size: 12pt; padding: 8px; }")
            h = QtWidgets.QHBoxLayout()
            h.addStretch()
            h.addWidget(btn)
            h.addStretch()
            layout.addLayout(h)

    def _check_and_install_interception(parent_window=None):
        """Check for driver sys files and attempt installation if missing.

        Returns True if drivers are present after this call (may require restart), False otherwise.
        """
        try:
            import subprocess
            from pathlib import Path
            sysroot = os.environ.get('SystemRoot', r'C:\Windows')
            drivers_dir = Path(sysroot) / 'System32' / 'drivers'
            required = [drivers_dir / 'mouse.sys', drivers_dir / 'keyboard.sys']
            missing = [p for p in required if not p.exists()]
            if not missing:
                return True

            # Attempt to run bundled installer (requires admin - run_app already ensures elevation)
            installer = Path(__file__).parent / 'Interception' / 'command line installer' / 'install-interception.exe'
            if installer.exists():
                try:
                    # Build a PowerShell command that opens an elevated PowerShell window,
                    # cds to the installer folder and runs the installer. We wait for the
                    # launched window to finish so we can notify the user afterwards.
                    installer_dir = str(installer.parent)
                    installer_name = installer.name

                    # Inner command executed inside the elevated PowerShell window
                    inner_cmd = (
                        f"Set-Location -LiteralPath '{installer_dir}';"
                        f" .\\{installer_name};"
                        " Read-Host -Prompt 'Press Enter to close';"
                        " exit"
                    )

                    # Outer PowerShell will Start-Process powershell -Verb runAs with -ArgumentList
                    # and -Wait so this call returns when the elevated window closes.
                    outer_cmd = (
                        "Start-Process powershell -Verb runAs -ArgumentList "
                        f"'-NoProfile -ExecutionPolicy Bypass -Command \"{inner_cmd}\"' -Wait"
                    )

                    # Execute the outer command using the system PowerShell and wait for completion
                    subprocess.run([
                        'powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass',
                        '-Command', outer_cmd
                    ], check=False)
                except Exception as e:
                    logger.error(f"Failed to run interception installer via PowerShell: {e}")
            else:
                logger.warning("Interception installer not found in repository; please install manually")

            # Re-check files
            missing = [p for p in required if not p.exists()]
            if missing:
                # Inform user to restart after manual install or that automatic install failed
                QtWidgets.QMessageBox.warning(parent_window, "Interception Driver",
                                              "Interception driver appears not to be installed.\n"
                                              "Automatic installation failed or requires manual steps.\n"
                                              "Please install the Interception driver and reboot your PC.")
                return False
            else:
                # Notify user to restart to finalize installation
                QtWidgets.QMessageBox.information(parent_window, "Interception Installed",
                                                  "Interception driver installed. Please RESTART your computer to ensure the driver is activated.")
                return True
        except Exception as e:
            logger.error(f"Error while checking/installing interception: {e}")
            return False

    # Show pre-start checklist and require explicit confirmation
    dlg = PreStartDialog()
    if dlg.exec() != QtWidgets.QDialog.Accepted:
        logger.info("User cancelled pre-start checklist; exiting")
        return

    # After user confirmation, check and attempt to install interception if necessary
    _check_and_install_interception()

    win = MainWindow()
    # Open maximized by default for improved UX
    try:
        win.showMaximized()
    except Exception:
        # Fallback to normal show if maximized fails
        win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    logger.info("Starting AION automation (Interception backend)")
    # REQUIRE administrator privileges - do not run without admin
    try:
        if not is_admin():
            logger.info("Not running as administrator - attempting to relaunch elevated...")
            # run_as_admin will exit on success; if it fails we MUST NOT continue
            run_as_admin()
            # If we reach here, elevation failed or was cancelled - EXIT IMMEDIATELY
            logger.error("Administrator privileges are REQUIRED to run this program.")
            logger.error("Please right-click the script and select 'Run as administrator'")
            input("\nPress Enter to exit...")
            sys.exit(1)
    except Exception as e:
        logger.error(f"Admin elevation failed: {e}")
        logger.error("Administrator privileges are REQUIRED to run this program.")
        input("\nPress Enter to exit...")
        sys.exit(1)

    # Only reach here if running as admin
    logger.success("✓ Running with administrator privileges")
    run_app()
