#!/usr/bin/env python3
"""
OMP Skills Quick Test - Verify installation worked
"""
import json
from pathlib import Path

def test_omp_package():
    print("🔍 OMP Package Test\n")
    
    # Test 1: Package file exists
    omp_file = Path("/root/omp-setup/omp_skills/all_skills.json")
    if not omp_file.exists():
        print("❌ Package file not found!")
        return False
    print(f"✓ Package file found: {omp_file}")
    print(f"  Size: {omp_file.stat().st_size / 1024 / 1024:.2f} MB\n")
    
    # Test 2: Valid JSON
    try:
        data = json.loads(omp_file.read_text(encoding='utf-8'))
        print(f"✓ Valid JSON structure")
        print(f"  Total skills: {len(data)}\n")
    except Exception as e:
        print(f"❌ JSON parse error: {e}")
        return False
    
    # Test 3: Sample skills
    print("📋 Sample Skills:\n")
    categories = {}
    for skill in data[:10]:
        cat = skill.get("category", "unknown")
        categories[cat] = categories.get(cat, 0) + 1
        print(f"  • {skill['name']}")
        print(f"    Category: {cat}")
        print(f"    Description: {skill['description'][:60]}...")
        print()
    
    # Test 4: Category distribution
    print("📊 Category Distribution:\n")
    cat_count = {}
    for skill in data:
        cat = skill.get("category", "unknown")
        cat_count[cat] = cat_count.get(cat, 0) + 1
    
    for cat, count in sorted(cat_count.items(), key=lambda x: x[1], reverse=True)[:10]:
        print(f"  {cat:30s} {count:3d} skills")
    
    print(f"\n✅ Package test passed!")
    print(f"\nReady to install with:")
    print(f"  bash setup.sh")
    print(f"  or")
    print(f"  python3 omp_installer.py")
    
    return True

if __name__ == "__main__":
    test_omp_package()
