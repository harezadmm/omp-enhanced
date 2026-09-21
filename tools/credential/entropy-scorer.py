#!/usr/bin/env python3
"""Entropy-based password strength scorer. Pipeline mode.
Usage: cat wordlist.txt | python3 entropy-scorer.py [--threshold 3.5]"""
import sys, math, collections
THRESHOLD = float(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[1] == "--threshold" else 3.5
for line in sys.stdin:
    pw = line.strip()
    if not pw: continue
    freq = collections.Counter(pw)
    entropy = -sum((c/len(pw))*math.log2(c/len(pw)) for c in freq.values())
    strength = "WEAK" if entropy < 2.5 else ("MEDIUM" if entropy < 4 else "STRONG")
    if entropy >= THRESHOLD:
        print(f"{pw}\tH={entropy:.2f}\t{strength}")
