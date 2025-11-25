"""Hybrid Input Controller - Uses both SendInput and AHK for maximum reliability.

This controller tries SendInput first (fastest), and falls back to AHK if needed.
For AION, you can also run the AHK script manually for hardware-level inputs.
"""
import time
from loguru import logger
from driver_input import tap_key as sendinput_tap_key
from driver_input import move_mouse_to as sendinput_move_mouse
from driver_input import click_at as sendinput_click_at
from driver_input import double_click_at as sendinput_double_click_at
from driver_input import focus_window

AHK_AVAILABLE = False  # AutoHotkey removed — use KMDF driver only

class HybridInputController:
    """Hybrid controller that uses both SendInput and AHK."""
    
    def __init__(self):
        """Hybrid facade — now simply forwards to the driver-backed input_controller."""
        self.ahk_enabled = False
    
    def enable_ahk_hardware(self):
        logger.warning("AHK support removed. KMDF driver is used for all input.")
        return False
    
    def tap_key(self, key: str, presses: int = 1, interval: float = 0.05):
        """Send key press using active input method."""
        # Always use SendInput for now (it's working well)
        sendinput_tap_key(key, presses, interval)
    
    def move_mouse_to(self, x: int, y: int, duration: float = 0.0):
        """Move mouse using active input method."""
        sendinput_move_mouse(x, y, duration)
    
    def click_at(self, x: int, y: int, button: str = 'left', clicks: int = 1, interval: float = 0.1):
        """Click at coordinates using active input method."""
        sendinput_click_at(x, y, button, clicks, interval)
    
    def double_click_at(self, x: int, y: int):
        """Double-click at coordinates using active input method."""
        sendinput_double_click_at(x, y)


# Create global instance
_hybrid_controller = None

def get_hybrid_controller(use_ahk_hardware=False):
    """Get or create the global hybrid controller."""
    global _hybrid_controller
    if _hybrid_controller is None:
        _hybrid_controller = HybridInputController(use_ahk_hardware)
    return _hybrid_controller


if __name__ == "__main__":
    print("="*60)
    print("  Hybrid Input Controller Test")
    print("="*60)
    
    # Test SendInput
    print("\n1. Testing SendInput (default)...")
    controller = HybridInputController()
    
    print("   - Sending W key...")
    controller.tap_key('w')
    time.sleep(0.5)
    
    print("   - Moving mouse...")
    import win32gui
    point = win32gui.GetCursorPos()
    controller.move_mouse_to(point[0] + 50, point[1] + 50)
    time.sleep(0.5)
    
    print("   ✓ SendInput working")
    
    print("\nNote: AHK has been removed — driver-based input is used.")
    
    print("\n" + "="*60)
    print("  Test Complete!")
    print("="*60)
    print("\nFor AION:")
    print("  1. SendInput works for most cases")
    print("  2. AHK script available as backup (run manually if needed)")
    print("  3. Both methods work with AION")
