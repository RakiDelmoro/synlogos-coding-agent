#!/usr/bin/env python3
"""Test the setup flow"""

import sys
import os
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, ".")

from src.skills import (
    generate_skill_from_prompt,
    save_skills,
    generate_config,
    save_config,
    is_setup_complete,
    get_skills_path,
    get_config_path,
)
from returns.result import Success


def test_setup_flow():
    """Test the complete setup flow"""
    print("Testing Synlogos Setup Flow")
    print("=" * 50)

    # Test 1: Check initial state
    print("\n1. Checking initial setup state...")
    print(f"   is_setup_complete: {is_setup_complete()}")

    # Test 2: Generate skill
    print("\n2. Generating skill from description...")
    user_desc = "A senior engineer who mentors me through complex refactors"
    result = generate_skill_from_prompt(user_desc, "togetherai/moonshotai/Kimi-K2.5")

    if isinstance(result, Success):
        skill = result.unwrap()
        print(f"   ✓ Skill generated: {skill.name}")
        print(f"   Who I Am: {skill.who_i_am[:60]}...")
        print(f"   Recommended agents: {skill.recommended_agents}")
        print(f"   Preferred model: {skill.preferred_model}")
    else:
        print(f"   ✗ Failed: {result.failure()}")
        return False

    # Test 3: Generate config
    print("\n3. Generating synlogos.json...")
    config = generate_config(skill, "togetherai/moonshotai/Kimi-K2.5")
    print(f"   ✓ Config generated")
    print(f"   Default model: {config['model']}")
    print(f"   Instructions: {config['instructions']}")
    print(f"   Agent types: {list(config['agent'].keys())}")

    # Test 4: Save files
    print("\n4. Saving files...")

    # Backup existing
    skills_path = get_skills_path()
    config_path = get_config_path()

    if skills_path.exists():
        skills_path.rename(skills_path.with_suffix(".md.test_backup"))
        print("   - Backed up existing skills.md")

    if config_path.exists():
        config_path.rename(config_path.with_suffix(".json.test_backup"))
        print("   - Backed up existing synlogos.json")

    # Save new files
    skill_result = save_skills(skill)
    config_result = save_config(config)

    if isinstance(skill_result, Success) and isinstance(config_result, Success):
        print(f"   ✓ Skill saved to: {skill_result.unwrap()}")
        print(f"   ✓ Config saved to: {config_result.unwrap()}")
    else:
        print("   ✗ Failed to save files")
        return False

    # Test 5: Verify setup complete
    print("\n5. Verifying setup...")
    print(f"   is_setup_complete: {is_setup_complete()}")

    # Test 6: Show generated files
    print("\n6. Generated files:")
    print("\n--- skills.md (first 20 lines) ---")
    with open("skills.md", "r") as f:
        lines = f.readlines()[:20]
        for line in lines:
            print(f"   {line.rstrip()}")

    print("\n--- synlogos.json (summary) ---")
    with open("synlogos.json", "r") as f:
        saved_config = json.load(f)
        print(f"   Model: {saved_config['model']}")
        print(f"   Agents: {list(saved_config['agent'].keys())}")

    # Cleanup - restore original files
    print("\n7. Restoring original files...")
    if Path("skills.md.test_backup").exists():
        Path("skills.md").unlink()
        Path("skills.md.test_backup").rename("skills.md")
        print("   - Restored skills.md")

    if Path("synlogos.json.test_backup").exists():
        Path("synlogos.json").unlink()
        Path("synlogos.json.test_backup").rename("synlogos.json")
        print("   - Restored synlogos.json")

    print("\n" + "=" * 50)
    print("✓ All tests passed!")
    return True


if __name__ == "__main__":
    success = test_setup_flow()
    sys.exit(0 if success else 1)
