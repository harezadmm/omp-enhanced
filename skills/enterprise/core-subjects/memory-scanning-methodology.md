# Memory Scanning Methodology

**Domain:** GAME HACKING & MEMORY EDITING — CHEAT ENGINE OPERATIONS

## Overview
1. **Initial Scan**: Search for known value (health=100, gold=5000) in process memory
   - Scan type: Exact Value, Unknown Initial Value, Range
   - Value type: 4-byte int, float, double, 8-byte, string, array of bytes
2. **Refine Scan**: Change value in-game (take damage, spend gold), rescan

## Full Doctrine

1. **Initial Scan**: Search for known value (health=100, gold=5000) in process memory
   - Scan type: Exact Value, Unknown Initial Value, Range
   - Value type: 4-byte int, float, double, 8-byte, string, array of bytes
2. **Refine Scan**: Change value in-game (take damage, spend gold), rescan
   - Next scan: decreased/increased/changed/unchanged value
   - Iterate until 1-5 addresses remain
3. **Verify Address**: Add to address list, freeze/edit value, confirm in-game effect
4. **Pointer Scan**: Find static pointer chain to survive game restart
   - Base address + offset chain → dynamic address
   - Multi-level pointers: pointer → pointer → target
   - Pointer map: save for trainer reuse

## References
- LTX-QUASAR CORE.md (persona doctrine)
