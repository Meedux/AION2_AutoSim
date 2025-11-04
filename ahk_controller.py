"""AHK Hardware Input Controller - Python wrapper for AutoHotkey script.

This provides an alternative input method using AutoHotkey's hardware-level inputs.
The AHK script runs independently and can be controlled from Python.
"""
import subprocess
import os
import time
from pathlib import Path
from loguru import logger

class AHKHardwareController:
    """Controller for AutoHotkey hardware-level input script."""
    
    def __init__(self):
        self.script_path = Path(__file__).parent / "aion_hardware_macro.ahk"
        self.ahk_exe = self._find_ahk_exe()
        self.process = None
        self.is_running = False
    
    def _find_ahk_exe(self):
        """Find AutoHotkey.exe in the project."""
        # Check project ahk folder
        project_ahk = Path(__file__).parent / "ahk" / "AutoHotkeyU64.exe"
        if project_ahk.exists():
            return str(project_ahk)
        
        # Check other versions
        for exe_name in ["AutoHotkeyU32.exe", "AutoHotkeyA32.exe", "AutoHotkey.exe"]:
            ahk_path = Path(__file__).parent / "ahk" / exe_name
            if ahk_path.exists():
                return str(ahk_path)
        
        # Check system PATH
        import shutil
        system_ahk = shutil.which("AutoHotkey.exe")
        if system_ahk:
            return system_ahk
        
        logger.warning("AutoHotkey.exe not found - AHK hardware controller unavailable")
        return None
    
    def start(self):
        """Start the AHK script."""
        if not self.ahk_exe:
            logger.error("Cannot start AHK script - AutoHotkey.exe not found")
            return False
        
        if not self.script_path.exists():
            logger.error(f"AHK script not found: {self.script_path}")
            return False
        
        try:
            # Start AHK script as background process
            self.process = subprocess.Popen(
                [self.ahk_exe, str(self.script_path)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            self.is_running = True
            time.sleep(0.5)  # Give script time to initialize
            logger.info("✓ AHK hardware macro script started")
            return True
        except Exception as e:
            logger.error(f"Failed to start AHK script: {e}")
            return False
    
    def stop(self):
        """Stop the AHK script."""
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                self.is_running = False
                logger.info("AHK hardware macro script stopped")
            except Exception as e:
                logger.error(f"Error stopping AHK script: {e}")
                try:
                    self.process.kill()
                except:
                    pass
    
    def is_active(self):
        """Check if the AHK script is running."""
        if not self.process:
            return False
        return self.process.poll() is None
    
    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


# Global instance
_ahk_controller = None

def get_ahk_controller():
    """Get or create the global AHK controller instance."""
    global _ahk_controller
    if _ahk_controller is None:
        _ahk_controller = AHKHardwareController()
    return _ahk_controller

def start_ahk_hardware_input():
    """Start the AHK hardware input script."""
    controller = get_ahk_controller()
    return controller.start()

def stop_ahk_hardware_input():
    """Stop the AHK hardware input script."""
    controller = get_ahk_controller()
    controller.stop()

def is_ahk_running():
    """Check if AHK script is running."""
    controller = get_ahk_controller()
    return controller.is_active()


if __name__ == "__main__":
    # Test the AHK controller
    print("Testing AHK Hardware Controller...")
    print("="*60)
    
    controller = AHKHardwareController()
    
    if controller.ahk_exe:
        print(f"✓ Found AutoHotkey: {controller.ahk_exe}")
    else:
        print("✗ AutoHotkey not found")
        exit(1)
    
    if controller.script_path.exists():
        print(f"✓ Found script: {controller.script_path}")
    else:
        print("✗ Script not found")
        exit(1)
    
    print("\nStarting AHK script...")
    if controller.start():
        print("✓ AHK script started successfully")
        print("\nThe script is now running in the background.")
        print("Test it by pressing F9 (sends W key) or F10 (clicks at cursor)")
        print("Press F11 to toggle on/off, F12 to reload")
        print("\nPress Enter to stop the script...")
        input()
        controller.stop()
        print("✓ AHK script stopped")
    else:
        print("✗ Failed to start AHK script")
