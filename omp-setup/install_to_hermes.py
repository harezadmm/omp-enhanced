#!/usr/bin/env python3
"""
OMP Package Installer for Hermes Agent
Installs all skills from the package into Hermes profile
"""

import json
import shutil
import subprocess
from pathlib import Path

class OMPInstaller:
    def __init__(self, package_dir='/root/omp-setup'):
        self.package_dir = Path(package_dir)
        self.skills_dir = self.package_dir / 'omp_skills'
        self.manifest_file = self.package_dir / 'manifest.json'
        self.all_skills_file = self.skills_dir / 'all_skills.json'
        
        # Hermes profile path
        self.hermes_skills_dir = Path.home() / '.hermes' / 'profiles' / 'umi2' / 'skills'
        
    def load_manifest(self):
        """Load package manifest"""
        with open(self.manifest_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle nested package structure
            if 'package' in data:
                return data['package']
            return data
    
    def load_skills_index(self):
        """Load skills index"""
        with open(self.all_skills_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def install_skill(self, skill_file):
        """Install single skill to Hermes"""
        skill_name = skill_file.stem
        
        # Determine category from skill content
        content = skill_file.read_text(encoding='utf-8')
        category = 'security'  # default
        
        if content.startswith('---'):
            parts = content.split('---', 2)
            frontmatter = parts[1]
            for line in frontmatter.split('\n'):
                if line.startswith('category:'):
                    category = line.split(':', 1)[1].strip()
                    break
        
        # Create category directory
        target_dir = self.hermes_skills_dir / category
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy skill file
        target_file = target_dir / f'{skill_name}.md'
        shutil.copy2(skill_file, target_file)
        
        return target_file
    
    def install_all(self):
        """Install all skills from package"""
        manifest = self.load_manifest()
        skills_index = self.load_skills_index()
        
        print(f"📦 Installing OMP Package: {manifest['name']} v{manifest['version']}")
        print(f"   Author: {manifest['author']}")
        print(f"   Skills: {len(skills_index)}")
        print()
        
        installed = []
        failed = []
        
        # Install all .md files from omp_skills directory
        skill_files = list(self.skills_dir.glob('*.md'))
        
        for skill_file in skill_files:
            try:
                target = self.install_skill(skill_file)
                installed.append(skill_file.stem)
                print(f"  ✓ {skill_file.stem}")
            except Exception as e:
                failed.append((skill_file.stem, str(e)))
                print(f"  ✗ {skill_file.stem}: {e}")
        
        print()
        print(f"✓ Installation complete")
        print(f"  Installed: {len(installed)}")
        print(f"  Failed: {len(failed)}")
        
        if failed:
            print("\nFailed skills:")
            for name, error in failed:
                print(f"  - {name}: {error}")
        
        return installed, failed
    
    def verify_installation(self):
        """Verify skills are accessible in Hermes"""
        print("\n🔍 Verifying installation...")
        
        # Check if skills directory exists and has files
        security_dir = self.hermes_skills_dir / 'security'
        if security_dir.exists():
            skill_count = len(list(security_dir.glob('*.md')))
            print(f"✓ Skills directory exists")
            print(f"  Security skills installed: {skill_count}")
        else:
            print("✗ Skills directory not found")
        
        # List all installed skills
        total_skills = sum(1 for _ in self.hermes_skills_dir.rglob('*.md'))
        print(f"  Total skills in Hermes: {total_skills}")

def main():
    installer = OMPInstaller()
    
    print("=" * 60)
    print("OMP Package Installer for Hermes Agent")
    print("=" * 60)
    print()
    
    # Install
    installed, failed = installer.install_all()
    
    # Verify
    installer.verify_installation()
    
    print()
    print("=" * 60)
    print("Installation complete! Use 'hermes skills list' to see all skills")
    print("=" * 60)

if __name__ == '__main__':
    main()
