#!/usr/bin/env python3
"""
OMP Enhanced - Quick Verification Script
Verify semua 3 fitur baru bekerja dengan benar
"""

import sys
import time
from pathlib import Path

def check_imports():
    """Check if module can be imported"""
    print("🔍 Checking imports...")
    try:
        from omp_client_enhanced import OMPClientEnhanced
        print("   ✅ OMPClientEnhanced imported successfully")
        return True
    except ImportError as e:
        print(f"   ❌ Import failed: {e}")
        return False

def check_initialization():
    """Check if client can be initialized"""
    print("\n🔍 Checking initialization...")
    try:
        from omp_client_enhanced import OMPClientEnhanced
        client = OMPClientEnhanced()
        print("   ✅ Client initialized")
        print(f"   📁 Cache dir: {client.cache_dir}")
        print(f"   📋 Providers: {len(client.providers)}")
        print(f"   📝 Templates: {len(client.templates)}")
        return client
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return None

def check_feature_1_cascade(client):
    """Check feature #5: Multi-model fallback cascade"""
    print("\n🔍 Feature #1: Multi-model fallback cascade")

    bandelbanget = client.providers.get("bandelbanget")
    if not bandelbanget:
        print("   ❌ bandelbanget provider missing")
        return False

    models = bandelbanget["models"]
    print(f"   bandelbanget models: {len(models)}")
    for model in models:
        print(f"      - {model}")

    required = {
        "deepseek-v4-mod",
        "deepseek-v4-flash",
        "deepseek-v4-flash-0731",
        "deepseek-v4-flash-vision-exp",
        "deepseek-v4-pro",
        "deepseek-v4-pro-0813",
        "claude-opus-5",
        "glm-5.1",
        "glm-5.2",
        "glm-5.3",
        "glm-5.3-flash",
        "gpt-5.6-luna",
        "gpt-5.6-sol",
        "gpt-5.6-terra",
        "hy3",
        "kimi-k2.7-code",
        "kimi-k2.7-code-highspeed",
        "kimi-k3",
        "mimo-v2.5-pro",
        "minimax-m3",
        "auto",
    }

    if set(models) != required:
        print("   ❌ bandelbanget model list is incomplete")
        return False

    if not client.default_cascade or client.default_cascade[0][0] != "bandelbanget":
        print("   ❌ Default cascade does not start with bandelbanget")
        return False

    print("   ✅ bandelbanget cascade: OK")
    return True

def check_feature_2_templates(client):
    """Check feature #7: Prompt template system"""
    print("\n🔍 Feature #2: Prompt template system")
    
    # Check built-in templates
    templates = client.list_templates()
    print(f"   Built-in templates: {len(templates)}")
    for tmpl in templates:
        print(f"      - {tmpl}")
    
    # Check template application
    test_prompt = "Write a hello world program"
    formatted = client.apply_template(test_prompt, "code")
    
    if "Write a hello world program" in formatted:
        print(f"   ✅ Template application: OK")
    else:
        print(f"   ❌ Template application: FAILED")
        return False
    
    # Check custom template
    client.add_template("test", "TEST: {prompt}")
    formatted = client.apply_template("test", "test")
    
    if "TEST: test" in formatted:
        print(f"   ✅ Custom template: OK")
    else:
        print(f"   ❌ Custom template: FAILED")
        return False
    
    return True

def check_feature_3_caching(client):
    """Check feature #8: Response caching"""
    print("\n🔍 Feature #3: Response caching")
    
    # Check cache directory
    if client.cache_dir.exists():
        print(f"   ✅ Cache directory exists: {client.cache_dir}")
    else:
        print(f"   ❌ Cache directory missing: {client.cache_dir}")
        return False
    
    # Check cache key generation
    key = client._cache_key("test", "provider", "model", "template")
    if len(key) == 64:  # SHA256 hex
        print(f"   ✅ Cache key generation: OK (SHA256)")
    else:
        print(f"   ❌ Cache key generation: FAILED")
        return False
    
    # Check cache operations
    test_key = "test_verification_key"
    client._set_cache(test_key, "test response")
    
    cached = client._get_cached(test_key, max_age=3600)
    if cached == "test response":
        print(f"   ✅ Cache set/get: OK")
    else:
        print(f"   ❌ Cache set/get: FAILED")
        return False

    # Check cache clearing
    cleared = client.clear_cache()
    print(f"   ✅ Cache clearing: OK ({cleared} files cleared)")

    return True

def check_api_keys():
    """Check if any API keys are configured"""
    print("\n🔍 Checking API keys...")

    import os
    keys = {
        "BANDELBANGET_API_KEY": os.getenv("BANDELBANGET_API_KEY"),
        "OPENAI_API_KEY": os.getenv("OPENAI_API_KEY"),
        "DEEPINFRA_API_KEY": os.getenv("DEEPINFRA_API_KEY"),
        "GROQ_API_KEY": os.getenv("GROQ_API_KEY"),
        "OPENROUTER_API_KEY": os.getenv("OPENROUTER_API_KEY"),
    }

    found = 0
    for name, value in keys.items():
        if value:
            print(f"   ✅ {name}: configured")
            found += 1
        else:
            print(f"   ⚠️  {name}: not set")

    # Check Ollama
    import subprocess
    try:
        result = subprocess.run(['which', 'ollama'], capture_output=True, timeout=2)
        if result.returncode == 0:
            print(f"   ✅ Ollama: installed")
        else:
            print(f"   ⚠️  Ollama: not installed")
    except:
        print(f"   ⚠️  Ollama: not installed")

    return found > 0

def check_files():
    """Check if all required files exist"""
    print("\n🔍 Checking files...")
    
    files = [
        "omp_client_enhanced.py",
        "README_ENHANCED.md",
        "ENHANCED_FEATURES.md",
        "CHANGELOG.md",
        "examples_enhanced.py",
        "cheatsheet.py",
        "test_enhanced_features.py",
        "install_enhanced.sh"
    ]
    
    missing = []
    for filename in files:
        path = Path(filename)
        if path.exists():
            size = path.stat().st_size
            print(f"   ✅ {filename} ({size} bytes)")
        else:
            print(f"   ❌ {filename} MISSING")
            missing.append(filename)
    
    return len(missing) == 0

def main():
    print("\n" + "="*70)
    print("  OMP Enhanced - Quick Verification")
    print("  Verifying 3 new features: Cascade, Templates, Caching")
    print("="*70)
    
    results = {
        "imports": False,
        "initialization": False,
        "cascade": False,
        "templates": False,
        "caching": False,
        "api_keys": False,
        "files": False
    }
    
    # Run checks
    results["imports"] = check_imports()
    
    if results["imports"]:
        client = check_initialization()
        results["initialization"] = client is not None
        
        if client:
            results["cascade"] = check_feature_1_cascade(client)
            results["templates"] = check_feature_2_templates(client)
            results["caching"] = check_feature_3_caching(client)
    
    results["api_keys"] = check_api_keys()
    results["files"] = check_files()
    
    # Summary
    print("\n" + "="*70)
    print("  VERIFICATION SUMMARY")
    print("="*70)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    
    for check, status in results.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {check.replace('_', ' ').title()}")
    
    print("\n" + "-"*70)
    print(f"   Score: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n   🎉 ALL CHECKS PASSED!")
        print("   OMP Enhanced is ready to use.")
        print("\n   Next steps:")
        print("      python3 examples_enhanced.py")
        print("      python3 test_enhanced_features.py --quick")
        print("      python3 omp_client_enhanced.py 'Write hello world' code")
        return 0
    elif passed >= total - 1 and not results["api_keys"]:
        print("\n   ⚠️  ALMOST READY!")
        print("   Set an API key to start using OMP Enhanced.")
        return 0
    else:
        print("\n   ❌ SOME CHECKS FAILED")
        print("   Review errors above and fix issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
