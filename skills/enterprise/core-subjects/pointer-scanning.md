# Pointer Scanning

**Domain:** GAME HACKING & MEMORY EDITING — CHEAT ENGINE OPERATIONS

## Overview
```
Base Address (static, module+offset)
  → + Offset1 → Pointer Level 1
    → + Offset2 → Pointer Level 2

## Full Doctrine

```
Base Address (static, module+offset)
  → + Offset1 → Pointer Level 1
    → + Offset2 → Pointer Level 2
      → + Offset3 → Target Address (dynamic, changes per restart)
```
- Save pointer map for reuse
- Max offset depth: typically 3-7 levels
- Validate pointer map against new game session

## References
- LTX-QUASAR CORE.md (persona doctrine)
