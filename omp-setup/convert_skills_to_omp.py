#!/usr/bin/env python3
import os
import json
import shutil
from pathlib import Path
import re

SKILLS_DIR = Path.home() / ".hermes" / "skills"
OUTPUT_DIR = Path("/root/omp-setup/omp_skills")
OUTPUT_DIR.mkdir(exist_ok=True)

def extract_frontmatter(content):
    """Extract YAML frontmatter from SKILL.md"""
    match = re.match(r'^---\n(.*?)\n---\n(.*)', content, re.DOTALL)
    if match:
        frontmatter = match.group(1)
        body = match.group(2)
        fm_dict = {}
        for line in frontmatter.split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                fm_dict[key.strip()] = val.strip().strip('"').strip("'")
        return fm_dict, body
    return {}, content

def convert_skill_to_omp(skill_path):
    """Convert Hermes SKILL.md to OMP format"""
    skill_md = skill_path / "SKILL.md"
    if not skill_md.exists():
        return None
    
    content = skill_md.read_text(encoding='utf-8')
    frontmatter, body = extract_frontmatter(content)
    
    skill_name = skill_path.name
    category = skill_path.parent.name if skill_path.parent.name != "skills" else "general"
    
    omp_data = {
        "name": skill_name,
        "version": "1.0.0",
        "category": category,
        "description": frontmatter.get("description", ""),
        "trigger": frontmatter.get("trigger", ""),
        "content": body.strip(),
        "files": {}
    }
    
    # Copy additional files (scripts, templates, references)
    for subdir in ["scripts", "templates", "references", "assets"]:
        subdir_path = skill_path / subdir
        if subdir_path.exists():
            for file in subdir_path.rglob("*"):
                if file.is_file():
                    rel_path = str(file.relative_to(skill_path))
                    try:
                        omp_data["files"][rel_path] = file.read_text(encoding='utf-8')
                    except:
                        omp_data["files"][rel_path] = f"[BINARY FILE: {file.name}]"
    
    return omp_data

skills_found = list(SKILLS_DIR.rglob("SKILL.md"))
print(f"Found {len(skills_found)} skills")

omp_skills = []
for skill_md in skills_found:
    skill_dir = skill_md.parent
    print(f"Converting: {skill_dir.name}")
    omp_skill = convert_skill_to_omp(skill_dir)
    if omp_skill:
        omp_skills.append(omp_skill)

output_file = OUTPUT_DIR / "all_skills.json"
output_file.write_text(json.dumps(omp_skills, indent=2, ensure_ascii=False), encoding='utf-8')

print(f"\n✓ Converted {len(omp_skills)} skills to {output_file}")
print(f"Total size: {output_file.stat().st_size / 1024 / 1024:.2f} MB")
