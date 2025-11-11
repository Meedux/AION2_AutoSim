"""Skill Combo Manager - Handles cooldown tracking and combo execution.

This manager:
- Tracks individual skill cooldowns
- Tracks combo set cooldowns
- Executes combos when all skills are available
- Uses hardware-level inputs via input_controller
- Supports stealth attack mode (randomized between double-click, single skill, combo)
"""
import time
import random
from typing import Dict, Optional, List, Tuple
from loguru import logger
import skill_combo_config
from input_controller import focus_window, tap_key, hold_key


class SkillComboManager:
    """Manages skill combo execution with cooldown tracking."""
    
    def __init__(self, hwnd: int):
        """Initialize the skill combo manager.
        
        Args:
            hwnd: Window handle for the game
        """
        self.hwnd = hwnd
        
        # Cooldown trackers: skill_key -> last_used_time
        self._skill_cooldowns: Dict[str, float] = {}
        
        # Combo cooldown trackers: combo_name -> last_used_time
        self._combo_cooldowns: Dict[str, float] = {}
        
        # Last combo check time (for logging)
        self._last_check_time = 0
        
        # Single skill global cooldown tracker
        self._last_single_skill_use = 0.0
        
        # Validate configuration on init
        if not skill_combo_config.validate_configuration():
            logger.error("Skill combo configuration is invalid!")
        
        logger.info("✓ Skill Combo Manager initialized")
    
    def is_skill_ready(self, skill: str) -> bool:
        """Check if a skill is off cooldown.
        
        Args:
            skill: Skill keybind (e.g., '1', 'alt+2', 'ctrl+5')
        
        Returns:
            True if skill is ready to use, False if on cooldown
        """
        skill_lower = skill.lower()
        cooldown = skill_combo_config.get_skill_cooldown(skill_lower)
        
        if skill_lower not in self._skill_cooldowns:
            return True  # Never used, ready to use
        
        last_used = self._skill_cooldowns[skill_lower]
        time_since_use = time.time() - last_used
        
        return time_since_use >= cooldown
    
    def is_combo_ready(self, combo: Dict) -> bool:
        """Check if a combo set is off cooldown.
        
        Args:
            combo: Combo set dictionary
        
        Returns:
            True if combo cooldown is ready, False if on cooldown
        """
        combo_name = combo.get('name', 'unnamed')
        combo_cooldown = combo.get('cooldown', 60.0)
        
        if combo_name not in self._combo_cooldowns:
            return True  # Never used, ready to use
        
        last_used = self._combo_cooldowns[combo_name]
        time_since_use = time.time() - last_used
        
        return time_since_use >= combo_cooldown
    
    def are_all_skills_ready(self, skills: List[str]) -> bool:
        """Check if all skills in a list are off cooldown.
        
        Args:
            skills: List of skill keybinds
        
        Returns:
            True if all skills are ready, False if any are on cooldown
        """
        for skill in skills:
            if not self.is_skill_ready(skill):
                return False
        return True
    
    def get_skill_cooldown_remaining(self, skill: str) -> float:
        """Get remaining cooldown time for a skill.
        
        Args:
            skill: Skill keybind
        
        Returns:
            Remaining cooldown in seconds (0 if ready)
        """
        skill_lower = skill.lower()
        cooldown = skill_combo_config.get_skill_cooldown(skill_lower)
        
        if skill_lower not in self._skill_cooldowns:
            return 0.0
        
        last_used = self._skill_cooldowns[skill_lower]
        time_since_use = time.time() - last_used
        remaining = cooldown - time_since_use
        
        return max(0.0, remaining)
    
    def get_combo_cooldown_remaining(self, combo: Dict) -> float:
        """Get remaining cooldown time for a combo.
        
        Args:
            combo: Combo set dictionary
        
        Returns:
            Remaining cooldown in seconds (0 if ready)
        """
        combo_name = combo.get('name', 'unnamed')
        combo_cooldown = combo.get('cooldown', 60.0)
        
        if combo_name not in self._combo_cooldowns:
            return 0.0
        
        last_used = self._combo_cooldowns[combo_name]
        time_since_use = time.time() - last_used
        remaining = combo_cooldown - time_since_use
        
        return max(0.0, remaining)
    
    def execute_skill(self, skill: str) -> bool:
        """Execute a single skill using hardware-level input.
        
        Args:
            skill: Skill keybind (e.g., '1', 'alt+2', 'ctrl+5')
        
        Returns:
            True if skill was executed, False if failed
        """
        try:
            # Parse skill into modifier + key
            modifier, key = skill_combo_config.parse_skill_keybind(skill)
            
            # Focus game window
            focus_window(self.hwnd)
            
            # Execute the skill with hardware-level input
            if modifier is None:
                # Simple key press
                tap_key(key)
                logger.debug(f"Skill executed: {key}")
            elif modifier == 'alt':
                # Alt + key combination
                # Hold Alt, press key, release Alt
                from input_controller import press_key_combination
                press_key_combination('alt', key)
                logger.debug(f"Skill executed: Alt+{key}")
            elif modifier == 'ctrl':
                # Ctrl + key combination
                from input_controller import press_key_combination
                press_key_combination('ctrl', key)
                logger.debug(f"Skill executed: Ctrl+{key}")
            else:
                logger.warning(f"Unknown modifier: {modifier}")
                return False
            
            # Mark skill as used
            skill_lower = skill.lower()
            self._skill_cooldowns[skill_lower] = time.time()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to execute skill '{skill}': {e}")
            return False
    
    def execute_combo(self, combo: Dict) -> bool:
        """Execute a combo set (all skills in sequence).
        
        Args:
            combo: Combo set dictionary
        
        Returns:
            True if combo was executed successfully, False otherwise
        """
        combo_name = combo.get('name', 'unnamed')
        skills = combo.get('skills', [])
        delay = combo.get('delay_between_skills', 0.5)
        
        logger.info(f"Executing combo: {combo_name} ({len(skills)} skills)")
        
        try:
            for idx, skill in enumerate(skills):
                # Execute the skill
                if not self.execute_skill(skill):
                    logger.warning(f"Combo '{combo_name}' interrupted at skill {idx+1}/{len(skills)}")
                    return False
                
                # Wait between skills (except after the last one)
                if idx < len(skills) - 1:
                    randomized_delay = skill_combo_config.get_randomized_delay(delay)
                    logger.debug(f"Delay {randomized_delay:.2f}s before next skill")
                    time.sleep(randomized_delay)
            
            # Mark combo as used
            self._combo_cooldowns[combo_name] = time.time()
            
            logger.success(f"✓ Combo '{combo_name}' executed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error executing combo '{combo_name}': {e}")
            return False
    
    def try_execute_combos(self) -> bool:
        """Try to execute any available combo.
        
        Checks all enabled combos in priority order and executes the first one
        that is ready (all skills off cooldown and combo cooldown ready).
        
        Returns:
            True if a combo was executed, False if none were ready
        """
        if not skill_combo_config.SKILL_COMBO_ENABLED:
            return False
        
        # Get enabled combos in priority order
        combos = skill_combo_config.get_enabled_combo_sets()
        
        if not combos:
            return False
        
        # Try each combo in order
        for combo in combos:
            combo_name = combo.get('name', 'unnamed')
            skills = combo.get('skills', [])
            
            # Check if combo cooldown is ready
            if not self.is_combo_ready(combo):
                combo_cd_remaining = self.get_combo_cooldown_remaining(combo)
                logger.debug(f"Combo '{combo_name}' on cooldown: {combo_cd_remaining:.1f}s remaining")
                continue
            
            # Check if all skills are ready
            if not self.are_all_skills_ready(skills):
                # Find which skills are on cooldown
                skills_on_cd = []
                for skill in skills:
                    if not self.is_skill_ready(skill):
                        cd_remaining = self.get_skill_cooldown_remaining(skill)
                        skills_on_cd.append(f"{skill}({cd_remaining:.1f}s)")
                logger.debug(f"Combo '{combo_name}' waiting for skills: {', '.join(skills_on_cd)}")
                continue
            
            # Combo is ready! Execute it
            logger.info(f"⚡ Combo '{combo_name}' ready - executing!")
            return self.execute_combo(combo)
        
        # No combos were ready
        return False
    
    def get_status_summary(self) -> str:
        """Get a summary of all combo and skill cooldown statuses.
        
        Returns:
            Formatted string with cooldown information
        """
        lines = []
        lines.append("=== Skill Combo Status ===")
        
        combos = skill_combo_config.get_enabled_combo_sets()
        for combo in combos:
            combo_name = combo.get('name', 'unnamed')
            combo_cd = self.get_combo_cooldown_remaining(combo)
            
            if combo_cd > 0:
                status = f"⏱ Cooldown: {combo_cd:.1f}s"
            else:
                skills = combo.get('skills', [])
                if self.are_all_skills_ready(skills):
                    status = "✅ READY"
                else:
                    skills_on_cd = []
                    for skill in skills:
                        if not self.is_skill_ready(skill):
                            cd = self.get_skill_cooldown_remaining(skill)
                            skills_on_cd.append(f"{skill}({cd:.1f}s)")
                    status = f"⏳ Waiting: {', '.join(skills_on_cd)}"
            
            lines.append(f"  {combo_name}: {status}")
        
        return '\n'.join(lines)
    
    def reset_cooldowns(self):
        """Reset all cooldowns (for testing/debugging)."""
        self._skill_cooldowns.clear()
        self._combo_cooldowns.clear()
        self._last_single_skill_use = 0.0
        logger.info("All cooldowns reset")
    
    def choose_attack_mode(self) -> str:
        """Choose attack mode based on stealth configuration.
        
        Returns:
            'standard_attack', 'single_skill', or 'combo_set'
        """
        if not skill_combo_config.STEALTH_ATTACK_MODE_ENABLED:
            return 'combo_set'  # Default to combo execution
        
        weights = skill_combo_config.ATTACK_MODE_WEIGHTS
        modes = list(weights.keys())
        probabilities = list(weights.values())
        
        # Normalize probabilities
        total = sum(probabilities)
        if total != 1.0:
            probabilities = [p / total for p in probabilities]
        
        chosen = random.choices(modes, weights=probabilities, k=1)[0]
        return chosen
    
    def is_single_skill_ready(self) -> bool:
        """Check if single skill global cooldown is ready.
        
        Returns:
            True if can use single skill, False if on GCD
        """
        gcd = skill_combo_config.SINGLE_SKILL_GLOBAL_COOLDOWN
        time_since_use = time.time() - self._last_single_skill_use
        return time_since_use >= gcd
    
    def execute_single_skill(self) -> bool:
        """Execute a single random skill from the pool.
        
        Returns:
            True if skill was executed, False otherwise
        """
        if not self.is_single_skill_ready():
            logger.debug("Single skill on global cooldown")
            return False
        
        # Get skill pool
        skill_pool = skill_combo_config.SINGLE_SKILL_POOL
        if not skill_pool:
            # If pool is empty, use all configured skills
            skill_pool = list(skill_combo_config.SKILL_COOLDOWNS.keys())
        
        # Filter to only skills that are off cooldown
        available_skills = [s for s in skill_pool if self.is_skill_ready(s)]
        
        if not available_skills:
            logger.debug("No skills available in single skill pool")
            return False
        
        # Pick a random skill
        skill = random.choice(available_skills)
        
        logger.info(f"⚡ Single skill attack: {skill}")
        
        # Execute the skill
        if self.execute_skill(skill):
            self._last_single_skill_use = time.time()
            return True
        
        return False
    
    def try_stealth_attack(self, has_health: bool) -> Tuple[str, bool]:
        """Try to execute an attack using stealth mode.
        
        Args:
            has_health: Whether mob_combat_health is detected
        
        Returns:
            (attack_mode, success) tuple
            attack_mode: 'standard_attack', 'single_skill', or 'combo_set'
            success: True if action was taken
        """
        # If health requirement enabled and no health detected, use standard attack only
        if skill_combo_config.REQUIRE_MOB_HEALTH_FOR_SKILLS and not has_health:
            logger.debug("No mob health detected - using standard attack only")
            return ('standard_attack', True)
        
        # Choose attack mode
        mode = self.choose_attack_mode()
        
        if mode == 'standard_attack':
            # Standard double-click attack (handled by caller)
            logger.debug("Attack mode: Standard (double-click)")
            return ('standard_attack', True)
        
        elif mode == 'single_skill':
            # Execute single skill
            logger.debug("Attack mode: Single skill")
            success = self.execute_single_skill()
            return ('single_skill', success)
        
        elif mode == 'combo_set':
            # Try to execute a combo
            logger.debug("Attack mode: Combo set")
            success = self.try_execute_combos()
            return ('combo_set', success)
        
        # Fallback to standard attack
        return ('standard_attack', True)
