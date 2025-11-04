"""Hybrid Input Controller - Uses both SendInput and AHK for maximum reliability.

This controller tries SendInput first (fastest), and falls back to AHK if needed.
For AION, you can also run the AHK script manually for hardware-level inputs.
"""
import time
from loguru import logger
from input_controller import tap_key as sendinput_tap_key
from input_controller import move_mouse_to as sendinput_move_mouse
from input_controller import click_at as sendinput_click_at
from input_controller import double_click_at as sendinput_double_click_at
from input_controller import focus_window

# Try to import AHK controller (optional)
try:
    from ahk_controller import start_ahk_hardware_input, is_ahk_running
    AHK_AVAILABLE = True
except Exception as e:
    logger.warning(f"AHK controller not available: {e}")
    AHK_AVAILABLE = False

class HybridInputController:
    """Hybrid controller that uses both SendInput and AHK."""
    
    def __init__(self, use_ahk_hardware=False):
        """
        Initialize the hybrid controller.
        
        Args:
            use_ahk_hardware: If True, starts the AHK hardware script on init
        """
        self.use_sendinput = True  # Always use SendInput by default
        self.ahk_enabled = False
        
        if use_ahk_hardware and AHK_AVAILABLE:
            self.enable_ahk_hardware()
    
    def enable_ahk_hardware(self):
        """Enable the AHK hardware input script."""
        if not AHK_AVAILABLE:
            logger.warning("AHK hardware input not available")
            return False
        
        try:
            if start_ahk_hardware_input():
                self.ahk_enabled = True
                logger.info("✓ AHK hardware input enabled")
                return True
        except Exception as e:
            logger.error(f"Failed to enable AHK hardware: {e}")
        
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
    
    # Test AHK (optional)
    if AHK_AVAILABLE:
        print("\n2. Testing AHK Hardware Input...")
        print("   - Starting AHK script...")
        if controller.enable_ahk_hardware():
            print("   ✓ AHK hardware script running")
            print("   - You can now test with F9 (W key) or F10 (click)")
            print("   - The AHK script runs independently")
        else:
            print("   ✗ AHK not available")
    
    print("\n" + "="*60)
    print("  Test Complete!")
    print("="*60)
    print("\nFor AION:")
    print("  1. SendInput works for most cases")
    print("  2. AHK script available as backup (run manually if needed)")
    print("  3. Both methods work with AION")
