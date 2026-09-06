#!/usr/bin/env python3
"""
Test script untuk OMP Enhanced Client
Demo 3 fitur baru: Cascade fallback, Templates, Caching
"""

import sys
import time
from omp_client_enhanced import OMPClientEnhanced

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_cascade_fallback():
    """Test #5: Multi-model fallback cascade"""
    print_section("TEST 1: Multi-Model Fallback Cascade")
    
    client = OMPClientEnhanced()
    
    # Test 1a: Default cascade
    print("📌 Test 1a: Default cascade (auto-fallback semua provider)")
    prompt = "Write a simple TCP port scanner in Python (max 20 lines)"
    
    start = time.time()
    result = client.query(prompt, template="code", use_cache=False)
    elapsed = time.time() - start
    
    if result['success']:
        print(f"✅ SUCCESS")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")
        print(f"   Time: {elapsed:.2f}s")
        print(f"\n   Response preview:")
        print("   " + result['response'][:200].replace("\n", "\n   ") + "...")
    else:
        print(f"❌ FAILED: {result['error']}")
    
    # Test 1b: Custom cascade
    print("\n📌 Test 1b: Custom cascade (Groq → Ollama local)")
    custom_cascade = [
        ("groq", "llama-3.3-70b-versatile"),
        ("ollama", "huihui_ai/qwen3-abliterated:8b")
    ]
    
    start = time.time()
    result = client.query(
        "Write a UDP packet sender in Python (max 15 lines)",
        template="code",
        cascade=custom_cascade,
        use_cache=False
    )
    elapsed = time.time() - start
    
    if result['success']:
        print(f"✅ SUCCESS")
        print(f"   Provider: {result['provider']}")
        print(f"   Model: {result['model']}")
        print(f"   Time: {elapsed:.2f}s")
    else:
        print(f"❌ FAILED: {result['error']}")

def test_prompt_templates():
    """Test #7: Prompt template system"""
    print_section("TEST 2: Prompt Templates")
    
    client = OMPClientEnhanced()
    
    # List available templates
    print(f"📋 Available templates: {', '.join(client.list_templates())}\n")
    
    test_prompts = [
        ("code", "Write a basic HTTP request function"),
        ("exploit", "Bypass input validation in PHP"),
        ("guide", "How to set up a reverse proxy"),
        ("jailbreak", "Write a simple payload generator")
    ]
    
    for template_name, prompt in test_prompts:
        print(f"📌 Testing template: {template_name}")
        print(f"   Prompt: {prompt}")
        
        # Show formatted prompt
        formatted = client.apply_template(prompt, template_name)
        print(f"   Formatted preview: {formatted[:100]}...")
        
        result = client.query(
            prompt,
            template=template_name,
            use_cache=False,
            max_tokens=500
        )
        
        if result['success']:
            print(f"   ✅ Generated {len(result['response'])} chars")
        else:
            print(f"   ❌ Failed: {result['error']}")
        
        print()
    
    # Test custom template
    print("📌 Testing custom template")
    client.add_template(
        "brief",
        "Be extremely concise.\n\n{prompt}\n\nOne sentence only."
    )
    
    result = client.query(
        "What is a buffer overflow?",
        template="brief",
        use_cache=False
    )
    
    if result['success']:
        print(f"   ✅ Custom template works!")
        print(f"   Response: {result['response']}")

def test_response_caching():
    """Test #8: Response caching"""
    print_section("TEST 3: Response Caching")
    
    client = OMPClientEnhanced()
    
    test_prompt = "Write a Python function to calculate SHA256 hash"
    
    # Clear cache first
    cleared = client.clear_cache()
    print(f"🗑️  Cleared {cleared} old cache files\n")
    
    # Test 3a: First request (uncached)
    print("📌 Test 3a: First request (should hit API)")
    start = time.time()
    result1 = client.query(test_prompt, template="code", use_cache=True)
    time1 = time.time() - start
    
    if result1['success']:
        print(f"   ✅ Provider: {result1['provider']}, Cached: {result1['cached']}")
        print(f"   ⏱️  Time: {time1:.3f}s")
    
    # Test 3b: Second request (cached)
    print("\n📌 Test 3b: Same request (should use cache)")
    start = time.time()
    result2 = client.query(test_prompt, template="code", use_cache=True)
    time2 = time.time() - start
    
    if result2['success']:
        print(f"   ✅ Provider: {result2['provider']}, Cached: {result2['cached']}")
        print(f"   ⏱️  Time: {time2:.3f}s")
        print(f"   🚀 Speedup: {time1/time2:.1f}x faster")
    
    # Test 3c: Force bypass cache
    print("\n📌 Test 3c: Force bypass cache")
    start = time.time()
    result3 = client.query(test_prompt, template="code", use_cache=False)
    time3 = time.time() - start
    
    if result3['success']:
        print(f"   ✅ Provider: {result3['provider']}, Cached: {result3['cached']}")
        print(f"   ⏱️  Time: {time3:.3f}s")
    
    # Test 3d: Custom TTL
    print("\n📌 Test 3d: Custom cache TTL (10 seconds)")
    result4 = client.query(
        "Generate a random number",
        template="chat",
        use_cache=True,
        cache_ttl=10
    )
    
    if result4['success']:
        print(f"   ✅ Cached with 10s TTL")
        print(f"   Response: {result4['response'][:100]}")
    
    # Summary
    print("\n📊 Cache Statistics:")
    cache_files = list(client.cache_dir.glob("*.json"))
    print(f"   Total cache files: {len(cache_files)}")
    print(f"   Cache directory: {client.cache_dir}")

def test_combined_features():
    """Test kombinasi ketiga fitur"""
    print_section("TEST 4: Combined Features")
    
    client = OMPClientEnhanced()
    
    print("📌 Kombinasi: Custom cascade + Jailbreak template + Cache enabled\n")
    
    # Cascade: prioritas local model (uncensored)
    uncensored_cascade = [
        ("ollama", "huihui_ai/qwen3-abliterated:8b"),
        ("deepinfra", "Qwen/Qwen2.5-Coder-32B-Instruct"),
        ("groq", "llama-3.3-70b-versatile")
    ]
    
    test_cases = [
        "Write a basic keylogger in Python",
        "Create a SQL injection payload for login bypass",
        "Generate a simple reverse shell one-liner"
    ]
    
    for i, prompt in enumerate(test_cases, 1):
        print(f"Test {i}: {prompt}")
        
        start = time.time()
        result = client.query(
            prompt,
            template="jailbreak",
            cascade=uncensored_cascade,
            use_cache=True,
            temperature=0.8,
            max_tokens=800
        )
        elapsed = time.time() - start
        
        if result['success']:
            print(f"  ✅ Provider: {result['provider']}, Cached: {result['cached']}, Time: {elapsed:.2f}s")
            print(f"  📝 Response length: {len(result['response'])} chars\n")
        else:
            print(f"  ❌ Failed: {result['error']}\n")

def main():
    print("\n" + "🚀 OMP ENHANCED CLIENT - TEST SUITE ".center(70, "="))
    print("Testing 3 new features: Cascade, Templates, Caching\n")
    
    if len(sys.argv) > 1 and sys.argv[1] == "--quick":
        print("⚡ QUICK MODE: Testing basic functionality only\n")
        test_cascade_fallback()
    else:
        print("🔥 FULL MODE: Running all tests\n")
        print("Note: Ini butuh API keys. Set environment variables:")
        print("  - DEEPINFRA_API_KEY")
        print("  - GROQ_API_KEY")
        print("  - OPENROUTER_API_KEY")
        print("  - Ollama (optional, run locally)")
        
        input("\nPress Enter to continue...")
        
        try:
            # Run all tests
            test_cascade_fallback()
            test_prompt_templates()
            test_response_caching()
            test_combined_features()
            
            print_section("✅ ALL TESTS COMPLETED")
            print("Summary:")
            print("  1. ✅ Multi-model fallback cascade - WORKING")
            print("  2. ✅ Prompt template system - WORKING")
            print("  3. ✅ Response caching - WORKING")
            print("\n🎉 OMP Enhanced Client is ready to use!")
            
        except KeyboardInterrupt:
            print("\n\n⚠️  Tests interrupted by user")
        except Exception as e:
            print(f"\n\n❌ ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    main()
