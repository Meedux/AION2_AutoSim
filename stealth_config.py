"""Stealth configuration for avoiding anti-cheat detection in CryEngine games.

CryEngine games like AION have sophisticated anti-cheat systems that detect:
- Consistent timing patterns
- Unnatural mouse movements
- Rapid repeated actions
- Overlay/injection detection
- Memory scanning

This module provides human-like randomization to avoid detection.
"""
import random
import time
from loguru import logger

class StealthConfig:
    """Configuration for stealth/anti-detection features."""
    
    # Human-like timing randomization
    MIN_ACTION_DELAY = 0.15  # Minimum delay between actions (seconds)
    MAX_ACTION_DELAY = 0.45  # Maximum delay between actions (seconds)
    
    MIN_CLICK_DELAY = 0.08   # Minimum delay between clicks
    MAX_CLICK_DELAY = 0.25   # Maximum delay between clicks
    
    MIN_KEY_DELAY = 0.12     # Minimum delay between key presses
    MAX_KEY_DELAY = 0.35     # Maximum delay between key presses
    
    # Mouse movement humanization
    MOUSE_JITTER_PIXELS = 3  # Random offset when clicking (±pixels)
    
    # Detection frequency (lower = less detectable but slower response)
    STEALTH_FPS = 3          # Reduced FPS for stealth mode (was 6)
    NORMAL_FPS = 6           # Normal FPS
    
    # Periodic "idle" behavior to appear human
    IDLE_CHECK_INTERVAL = 120  # Check every 2 minutes
    IDLE_PROBABILITY = 0.15    # 15% chance to idle
    IDLE_DURATION_MIN = 2.0    # Minimum idle time (seconds)
    IDLE_DURATION_MAX = 8.0    # Maximum idle time (seconds)
    
    def __init__(self, stealth_mode: bool = True):
        self.stealth_mode = stealth_mode
        self.last_idle_check = time.time()
        logger.info(f"Stealth mode: {'ENABLED' if stealth_mode else 'DISABLED'}")
    
    def get_action_delay(self) -> float:
        """Get randomized delay between actions."""
        if not self.stealth_mode:
            return 0.08
        return random.uniform(self.MIN_ACTION_DELAY, self.MAX_ACTION_DELAY)
    
    def get_click_delay(self) -> float:
        """Get randomized delay between mouse clicks."""
        if not self.stealth_mode:
            return 0.05
        return random.uniform(self.MIN_CLICK_DELAY, self.MAX_CLICK_DELAY)
    
    def get_key_delay(self) -> float:
        """Get randomized delay between key presses."""
        if not self.stealth_mode:
            return 0.05
        return random.uniform(self.MIN_KEY_DELAY, self.MAX_KEY_DELAY)
    
    def get_mouse_jitter(self) -> tuple[int, int]:
        """Get random mouse offset to make clicks look more human."""
        if not self.stealth_mode:
            return (0, 0)
        jitter_x = random.randint(-self.MOUSE_JITTER_PIXELS, self.MOUSE_JITTER_PIXELS)
        jitter_y = random.randint(-self.MOUSE_JITTER_PIXELS, self.MOUSE_JITTER_PIXELS)
        return (jitter_x, jitter_y)
    
    def get_detection_fps(self) -> int:
        """Get detection FPS based on stealth mode."""
        return self.STEALTH_FPS if self.stealth_mode else self.NORMAL_FPS
    
    def should_idle(self) -> float:
        """Check if bot should idle to appear human. Returns idle duration or 0."""
        if not self.stealth_mode:
            return 0.0
        
        now = time.time()
        if now - self.last_idle_check < self.IDLE_CHECK_INTERVAL:
            return 0.0
        
        self.last_idle_check = now
        
        if random.random() < self.IDLE_PROBABILITY:
            duration = random.uniform(self.IDLE_DURATION_MIN, self.IDLE_DURATION_MAX)
            logger.info(f"🕐 Human-like idle: {duration:.1f}s")
            return duration
        
        return 0.0
    
    def add_human_variance(self, base_value: float, variance_pct: float = 0.2) -> float:
        """Add human-like variance to a numeric value (±variance_pct)."""
        if not self.stealth_mode:
            return base_value
        variance = base_value * variance_pct
        return random.uniform(base_value - variance, base_value + variance)


# Global stealth configuration instance
stealth = StealthConfig(stealth_mode=True)
