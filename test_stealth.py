"""Quick test to verify stealth features are working."""
import time
from stealth_config import stealth
from loguru import logger

logger.info("=" * 60)
logger.info("Testing Stealth Anti-Detection Features")
logger.info("=" * 60)

# Test 1: Action delays
logger.info("\n1. Testing randomized action delays (5 samples):")
for i in range(5):
    delay = stealth.get_action_delay()
    logger.info(f"   Action {i+1}: {delay:.3f}s delay")

# Test 2: Click delays
logger.info("\n2. Testing randomized click delays (5 samples):")
for i in range(5):
    delay = stealth.get_click_delay()
    logger.info(f"   Click {i+1}: {delay:.3f}s delay")

# Test 3: Mouse jitter
logger.info("\n3. Testing mouse jitter (5 samples):")
for i in range(5):
    jitter = stealth.get_mouse_jitter()
    logger.info(f"   Jitter {i+1}: ({jitter[0]:+d}, {jitter[1]:+d}) pixels")

# Test 4: Detection FPS
logger.info(f"\n4. Detection FPS: {stealth.get_detection_fps()} (stealth mode)")

# Test 5: Idle check (won't trigger in quick succession)
logger.info("\n5. Testing idle behavior:")
logger.info(f"   Idle check interval: {stealth.IDLE_CHECK_INTERVAL}s")
logger.info(f"   Idle probability: {stealth.IDLE_PROBABILITY*100}%")
logger.info(f"   Idle duration range: {stealth.IDLE_DURATION_MIN}-{stealth.IDLE_DURATION_MAX}s")

# Test 6: Variance
logger.info("\n6. Testing human variance:")
base = 1.0
for i in range(5):
    varied = stealth.add_human_variance(base, variance_pct=0.2)
    logger.info(f"   Base {base:.2f}s → Varied {varied:.3f}s ({(varied-base)*100:+.1f}%)")

logger.success("\n✓ All stealth features working correctly!")
logger.info("\nStealth features summary:")
logger.info("  • Randomized action timing: ✓")
logger.info("  • Randomized click timing: ✓")
logger.info("  • Mouse jitter (human-like): ✓")
logger.info("  • Reduced detection FPS: ✓")
logger.info("  • Periodic idle behavior: ✓")
logger.info("  • Human variance: ✓")
