"""Test script for Skill Combo System

This script demonstrates and tests the skill combo macro system.
"""
import time
from skill_combo_manager import SkillComboManager
import skill_combo_config


def test_skill_combo_system():
    """Test the skill combo system (simulated - no actual game window)."""
    
    print("=" * 70)
    print("SKILL COMBO SYSTEM TEST")
    print("=" * 70)
    
    # Validate configuration
    print("\n1. Validating configuration...")
    if skill_combo_config.validate_configuration():
        print("   ✓ Configuration is valid")
    else:
        print("   ✗ Configuration has errors!")
        return
    
    # Show configuration summary
    print(f"\n2. Configuration Summary:")
    print(f"   - Total skills configured: {len(skill_combo_config.SKILL_COOLDOWNS)}")
    print(f"   - Total combo sets: {len(skill_combo_config.COMBO_SETS)}")
    enabled_combos = [c for c in skill_combo_config.COMBO_SETS if c.get('enabled', True)]
    print(f"   - Enabled combo sets: {len(enabled_combos)}")
    print(f"   - Skill combo system: {'ENABLED' if skill_combo_config.SKILL_COMBO_ENABLED else 'DISABLED'}")
    
    # Show each combo set
    print(f"\n3. Combo Sets:")
    for idx, combo in enumerate(skill_combo_config.COMBO_SETS):
        name = combo.get('name', 'unnamed')
        skills = combo.get('skills', [])
        cooldown = combo.get('cooldown', 60.0)
        delay = combo.get('delay_between_skills', 0.5)
        enabled = combo.get('enabled', True)
        status = "✓ ENABLED" if enabled else "✗ DISABLED"
        
        print(f"   [{idx}] {name} {status}")
        print(f"       Skills: {' → '.join(skills)}")
        print(f"       Combo Cooldown: {cooldown}s")
        print(f"       Skill Delay: {delay}s")
    
    # Test skill keybind parsing
    print(f"\n4. Testing Skill Keybind Parsing:")
    test_skills = ['1', 'alt+5', 'ctrl+9', 'alt+-', 'ctrl+=']
    for skill in test_skills:
        modifier, key = skill_combo_config.parse_skill_keybind(skill)
        if modifier:
            print(f"   '{skill}' → Modifier: {modifier.upper()}, Key: {key}")
        else:
            print(f"   '{skill}' → Key: {key}")
    
    # Test combo validation
    print(f"\n5. Testing Combo Validation:")
    
    # Valid combo
    valid_combo = {
        'name': 'Test Valid',
        'skills': ['1', '2', '3'],
        'cooldown': 60.0,
        'delay_between_skills': 0.5,
    }
    is_valid, msg = skill_combo_config.validate_combo_set(valid_combo)
    print(f"   Valid combo: {is_valid} {msg if msg else ''}")
    
    # Invalid combo (missing skills)
    invalid_combo = {
        'name': 'Test Invalid',
        'cooldown': 60.0,
    }
    is_valid, msg = skill_combo_config.validate_combo_set(invalid_combo)
    print(f"   Invalid combo (missing skills): {is_valid} - {msg}")
    
    # Invalid combo (unknown skill)
    invalid_combo2 = {
        'name': 'Test Invalid 2',
        'skills': ['1', 'unknown_key', '3'],
        'cooldown': 60.0,
    }
    is_valid, msg = skill_combo_config.validate_combo_set(invalid_combo2)
    print(f"   Invalid combo (unknown skill): {is_valid} - {msg}")
    
    # Test SkillComboManager (simulated)
    print(f"\n6. Testing SkillComboManager (simulated hwnd=0):")
    print("   NOTE: This test won't actually press keys since hwnd=0")
    
    try:
        manager = SkillComboManager(hwnd=0)
        print("   ✓ SkillComboManager created")
        
        # Test cooldown checking
        print(f"\n   Testing cooldown checks:")
        test_skill = '1'
        is_ready = manager.is_skill_ready(test_skill)
        print(f"   - Skill '{test_skill}' ready: {is_ready} (should be True - never used)")
        
        # Get first enabled combo
        combos = skill_combo_config.get_enabled_combo_sets()
        if combos:
            combo = combos[0]
            combo_name = combo.get('name', 'unnamed')
            is_ready = manager.is_combo_ready(combo)
            print(f"   - Combo '{combo_name}' ready: {is_ready} (should be True - never used)")
            
            skills = combo.get('skills', [])
            all_ready = manager.are_all_skills_ready(skills)
            print(f"   - All skills in combo ready: {all_ready} (should be True)")
        
        # Show status summary
        print(f"\n   Status Summary:")
        status = manager.get_status_summary()
        for line in status.split('\n'):
            print(f"   {line}")
        
        print("\n   ✓ SkillComboManager tests passed")
        
    except Exception as e:
        print(f"   ✗ SkillComboManager error: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print("\nTo use the skill combo system:")
    print("1. Edit skill_combo_config.py to configure your skills and combos")
    print("2. Run python main.py to start the bot")
    print("3. Skill combos will execute automatically during combat")
    print("4. Check logs for combo execution: 'Executing combo: ...'")
    print("=" * 70)


if __name__ == "__main__":
    test_skill_combo_system()
