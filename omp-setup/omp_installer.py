#!/usr/bin/env python3
"""
OMP Skills Installer - Universal Hermes Agent Skills Setup
Loads all 103+ skills from all_skills.json into any Hermes Agent instance
"""
import json
import os
from pathlib import Path
import sys

def install_omp_skills(target_profile="default"):
    """Install all OMP skills to Hermes Agent profile"""
    
    # Load OMP skills package
    omp_file = Path(__file__).parent / "omp_skills" / "all_skills.json"
    if not omp_file.exists():
        print(f"❌ OMP package not found: {omp_file}")
        return False
    
    print(f"📦 Loading OMP skills package...")
    skills_data = json.loads(omp_file.read_text(encoding='utf-8'))
    print(f"✓ Loaded {len(skills_data)} skills")
    
    # Determine target directory
    hermes_home = Path.home() / ".hermes"
    if target_profile == "default":
        target_dir = hermes_home / "skills"
    else:
        target_dir = hermes_home / "profiles" / target_profile / "skills"
    
    target_dir.mkdir(parents=True, exist_ok=True)
    print(f"📂 Target: {target_dir}")
    
    installed = 0
    skipped = 0
    
    for skill in skills_data:
        name = skill["name"]
        category = skill["category"]
        
        # Create category/skill directory
        skill_dir = target_dir / category / name
        skill_dir.mkdir(parents=True, exist_ok=True)
        
        # Write SKILL.md
        frontmatter = f"""---
name: {name}
description: {skill["description"]}
trigger: {skill["trigger"]}
version: {skill["version"]}
category: {category}
---

"""
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(frontmatter + skill["content"], encoding='utf-8')
        
        # Write additional files
        for file_path, content in skill.get("files", {}).items():
            file_full = skill_dir / file_path
            file_full.parent.mkdir(parents=True, exist_ok=True)
            if not content.startswith("[BINARY FILE:"):
                file_full.write_text(content, encoding='utf-8')
        
        installed += 1
        print(f"  ✓ {category}/{name}")
    
    print(f"\n🎉 Installation complete!")
    print(f"   Installed: {installed} skills")
    print(f"   Location: {target_dir}")
    print(f"\nVerify with: hermes skills list")
    return True

if __name__ == "__main__":
    profile = sys.argv[1] if len(sys.argv) > 1 else "default"
    print(f"🚀 OMP Skills Installer")
    print(f"   Profile: {profile}\n")
    install_omp_skills(profile)
