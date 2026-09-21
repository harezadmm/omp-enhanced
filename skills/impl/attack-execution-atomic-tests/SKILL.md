---
name: attack-execution-atomic-tests
description: >-
  ATT&CK Execution and Defense Impairment techniques with executable atomic tests. Use when
  validating detection coverage, emulating a specific technique, or building an adversary
  emulation plan on Windows or Linux. Covers technique selection, test execution, and the
  detection-validation loop.
---

# SKILL: ATT&CK Execution & Defense Impairment — Atomic Test Library

> **AI LOAD INSTRUCTION**: This skill is for **executing and validating** ATT&CK techniques, not
> for describing them. Atomic Red Team ships 1,839 executable tests across 344 techniques
> (872 technique-tactic mappings). The value is that every test is a concrete, reviewable
> command with declared dependencies and a cleanup path. Use this skill when the task is
> *"prove this technique works here"* or *"does our detection catch this?"* — not when the task
> is merely to understand a technique.

## 0. RELATED ROUTING

- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) — the LOLBin layer under many execution tests
- [windows-postexploit](../windows-postexploit/SKILL.md) / [linux-postexploit](../linux-postexploit/SKILL.md) — the surrounding flow
- [edr-bypass-advanced](../windows-av-evasion/SKILL.md) — when the test itself is blocked
- [detection-validation](../memory-forensics-volatility/SKILL.md) — the blue-side counterpart
- [living-off-the-land-lotl](../../core-subjects/living-off-the-land-lotl.md) — doctrine

---

## 1. THE TEST MODEL

Every atomic test has the same five parts. Understanding them is what makes the library usable
rather than a pile of commands.

| Part | Purpose | Operational significance |
|---|---|---|
| `name` + `description` | what it does and what success looks like | the description states the expected observable — that is your success criterion |
| `supported_platforms` | windows / linux / macos | filter before you select |
| `input_arguments` | parameters with `type` (path, url, string) and a `default` | these are the knobs; defaults usually work |
| `dependencies` + `get_prereq_command` | tooling that must exist first | **this is why tests fail** — run the prereq first |
| `executor` + `cleanup_command` | the actual invocation and how to undo it | cleanup is not optional in a production network |

**The dependency block is the single most important part.** A test with an unmet dependency
fails silently or noisily, and an operator who skips the prereq concludes the technique does not
work when in fact it was never attempted.

---

## 2. TACTIC LANDSCAPE

872 technique-tactic mappings, by tactic. Use this to know where the library is deep and where
it is thin — thin tactics are where you must build your own tests.

| Tactic | Techniques | Depth |
|---|---|---|
| **Stealth** (defense evasion) | 148 | deepest — where adversaries invest most |
| **Persistence** | 113 | deep |
| **Privilege Escalation** | 96 | deep |
| **Credential Access** | 67 | deep |
| **Execution** | 64 | deep |
| **Defense Impairment** | 56 | deep |
| **Resource Development** | 50 | moderate |
| **Discovery** | 49 | moderate |
| **Reconnaissance** | 46 | moderate |
| **Command & Control** | 45 | moderate |
| **Collection** | 41 | moderate |
| **Impact** | 33 | thin |
| **Lateral Movement** | 23 | **thin** — build your own |
| **Initial Access** | 22 | **thin** |
| **Exfiltration** | 19 | **thinnest** |

**Consequence:** lateral movement, initial access and exfiltration have the fewest ready tests but
are the operations most often assessed. For those three, the atomic library is a starting point,
not a solution.

---

## 3. EXECUTOR TYPES

1,839 tests break down by executor, which tells you what a host needs to run them.

| Executor | Count | Note |
|---|---|---|
| PowerShell | 1,130 | dominant on Windows; most-caught executor |
| command_prompt | 573 | quieter than PowerShell in many environments |
| `sh` | 572 | Linux |
| bash | 177 | Linux |
| manual | 16 | human-performed; use as a procedure, not a script |

**Operational note:** PowerShell is both the most common executor *and* the most logged. Where a
test offers both a PowerShell and a `command_prompt` variant, the latter is usually the quieter
choice — and the difference between them is itself a useful detection finding.

---

## 4. EXECUTION PRIMITIVES — SELECTION
```
1. Select technique   → from the tactic table in §2, by objective
2. Filter platform    → supported_platforms must include the target OS
3. READ the description → it states the expected observable. Write it down.
4. Run prerequisites  → get_prereq_command, before anything else
5. Execute            → executor.command, with input_arguments as needed
6. Verify             → against the observable from step 3, not against "it ran"
7. Run cleanup        → cleanup_command. Always.
8. Record detection   → what fired, what didn't, and how long it took (see §5)
```

**Step 3 is the discipline that separates emulation from noise.** A test whose expected
observable was never defined cannot be said to have succeeded or failed.

---

## 5. THE DETECTION-VALIDATION LOOP

This is the real value of the library. Each test is a **probe of the detection stack**.

| Outcome | What it means | What to do |
|---|---|---|
| Test ran, alert fired fast | detection works | record time-to-detect; it is the baseline |
| Test ran, no alert | **detection gap** | this is a finding — document the technique ID |
| Test blocked by EDR | prevention works, but it is a *different* control | distinguish prevention from detection in the report |
| Test failed on dependencies | **inconclusive — not a finding** | fix the prereq and re-run before reporting anything |

**Never report a dependency failure as "detection prevented it."** That inverts the finding and
is the most common error in emulation reporting.

**Measure time-to-detect, not just fire/no-fire.** A 30-second gap and a 6-hour gap are different
severities for the same technique.

---

## 6. DETECTION REALITY

Most atomic tests are loud by design — they are meant to be *caught*. Treat a test that produces
no telemetry as a signal about the environment, not as a stealthy technique.

| Signal | Where it surfaces |
|---|---|
| Process creation with the test's command line | Sysmon EID 1 / Windows 4688 |
| PowerShell script block content | EID 4104 (requires script-block logging) |
| LSASS handle access | Sysmon EID 10 |
| Service or scheduled-task creation | 4697 / 7045 / Sysmon 12-13 |
| Registry modification | Sysmon 12-14 |
| Network connection from a test binary | Sysmon 3 / firewall logs |

**If a technique tests clean, the first hypothesis is missing telemetry — not a stealthy
adversary.** Verify the log source is actually enabled and forwarded before writing it up.

---

## 7. EVIDENCE STANDARD

| Item | Why |
|---|---|
| technique ID + tactic + the specific atomic test name | unambiguous reference |
| expected observable (from the description) and what was actually observed | proves the test ran *and* was evaluated |
| executor type used | a command_prompt test and a PowerShell test are different findings |
| detection outcome + **time-to-detect** | the core deliverable |
| prevention vs detection, stated separately | different controls, different remediation |
| cleanup performed (yes/no) | an uncleaned test is a live risk on a production network |
| any dependency that had to be installed, and whether it was removed | attack surface you introduced |

---

## 8. REMEDIATION REFERENCE

1. **Close gaps by technique, not by tool.** A test that mapped to no alert tells you exactly which ATT&CK ID to build a rule for.
2. **Enable the telemetry first.** Script-block logging (4104), command-line audit policy, and Sysmon are prerequisites for most of this library being useful.
3. **Distinguish prevention from detection** in the control design — blocking a technique and seeing it are separate capabilities and both are needed.
4. **Lateral movement / initial access / exfiltration** have the fewest tests; prioritise custom rules there since the library will not cover them.
5. **Re-run periodically.** New atomics are published continuously; a coverage result is only valid for the library version and OS build tested.
6. **Time-to-detect is the metric to track over time**, not pass/fail counts.

---

## 9. CONFIRMING THE FINDING

| Step | Question | What it proves |
|---|---|---|
| 1 | Did the test's **stated observable actually appear** on the host? | the technique executed, not that the command returned |
| 2 | Was there a **control** - the same host before the test, or a host without the tool? | the test produced the artefact |
| 3 | Did you run the **prerequisite** and confirm it succeeded **before** the test? | the dependency is met |
| 4 | Did the **cleanup command run** and was its effect verified? | the host is as it was |
| 5 | Did you capture the **process tree, the created artefact, and the log line**? | the artefact and the detection opportunity |
| 6 | Is the **platform and the executor type** the right one for this host? | the test was applicable |
| 7 | Did the target's detection **alert, or stay silent**, and did you record which? | the detection result, positive or negative |

**The description's stated observable, on the host, with the prereq met and the cleanup verified, is the
bar.** A command exiting `0` is not the bar; the test's own description says what success looks like.

---

## 10. EXECUTION PRIMITIVES — PROOF
Atomic tests are proven by **the test's declared observable appearing on the host, with the prereq run
first, a pre-test control, and a verified cleanup**. Every block ends at a verified observable.

### 9.1 Selecting a test, and reading its contract

```bash
# the library is data. Select by technique, by platform, and by name before running anything.
LIB="atomics"          # a checkout of the atomic-red-team repository
echo "=== the tests for one technique, with their platforms ==="
ls "$LIB/atomics/T1059.001/" 2>/dev/null
python3 - <<'PY'
import yaml, glob, os
LIB = "atomics"
def load(p):
    try: return yaml.safe_load(open(p, encoding="utf-8"))
    except Exception as e: return {"__err__": str(e)}
print("%-14s %-10s %-9s %-44s %s" % ("technique", "platform", "executor", "name", "deps?"))
rows = []
for idx in sorted(glob.glob(os.path.join(LIB, "atomics", "T*/T*.yaml"))):
    d = load(idx)
    tid = d.get("attack_technique", os.path.basename(os.path.dirname(idx)))
    for t in (d.get("atomic_tests") or []):
        ex = t.get("executor") or {}
        plats = ",".join(t.get("supported_platforms") or [])
        deps = t.get("dependencies") or []
        rows.append((tid, plats, ex.get("name", "?"), t.get("name", "?"), len(deps), idx, t.get("auto_generated")))
print("total tests:", len(rows))
for r in rows[:25]:
    print("%-14s %-10s %-9s %-44s %s" % (r[0], r[1][:10], r[2][:9], r[3][:44], "yes" if r[4] else "-"))
print()
print("FILTERS to apply, in order:")
print("  1. platform must match the host")
print("  2. the executor type must be available (command_prompt, powershell, bash, sh, manual)")
print("  3. dependencies must be satisfiable, and get_prereq_command must exist for each")
print("  4. skip auto_generated tests where a hand-written one exists for the same technique")
PY
```

**Select on the four filters before running anything.** Platform, executor, dependencies, and a
preference for hand-written tests over generated ones - the generated ones are the least reliable.

### 9.2 The prerequisite gate, which is where tests fail

```bash
# the dependency block is the single most common reason a test silently fails
run_prereqs() {
  local idx="$1"
  python3 - "$idx" <<'PY'
import yaml, sys, subprocess, shlex
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
for ti, t in enumerate(d.get("atomic_tests") or []):
    for dep in (t.get("dependencies") or []):
        pre = dep.get("get_prereq_command") or ""
        ppt = (dep.get("prereq_command") or "").strip()
        print(f"--- test {ti}: {t.get('name')}")
        print(f"    prereq_command : {ppt or '<none declared>'}")
        if not pre:
            print("    get_prereq_command: MISSING - the dependency must be provisioned manually")
            continue
        print(f"    get_prereq_command: {pre}")
        p = subprocess.run(pre, shell=True, capture_output=True, text=True, timeout=180)
        print(f"    provisioning exit={p.returncode}  {(p.stdout or p.stderr)[:120].strip()}")
        if ppt:
            c = subprocess.run(ppt, shell=True, capture_output=True, text=True, timeout=60)
            print(f"    VERIFY exit={c.returncode}  -> {'SATISFIED' if c.returncode == 0 else 'STILL MISSING'}")
PY
}
echo "usage: run_prereqs atomics/atomics/T1059.001/T1059.001.yaml"
```

```python
# the same gate, without running anything - a dry selection pass you can review
import yaml, glob, os
READY, NEEDS, MANUAL = [], [], []
for idx in sorted(glob.glob("atomics/atomics/T*/T*.yaml")):
    d = yaml.safe_load(open(idx, encoding="utf-8")) or {}
    for t in (d.get("atomic_tests") or []):
        deps = t.get("dependencies") or []
        if not deps: READY.append((d.get("attack_technique"), t.get("name"))); continue
        if all((x.get("get_prereq_command") or "").strip() for x in deps): NEEDS.append((d.get("attack_technique"), t.get("name"), len(deps)))
        else: MANUAL.append((d.get("attack_technique"), t.get("name")))
print("runnable without a prereq :", len(READY))
print("runnable after provisioning:", len(NEEDS))
print("manual provisioning needed :", len(MANUAL))
print()
print("start with READY, then NEEDS. MANUAL tests need a human and should be sequenced last.")
```

**A test with an unmet dependency is not a failed technique.** The gate distinguishes "the tool was
missing" from "the technique did not work", and that distinction belongs in the report.

### 9.3 The execution, with the description's observable as the check

```bash
# the execution pattern: control capture, run, observable check, log capture, cleanup
run_atomic() {
  local idx="$1" ti="${2:-0}" LOG="/tmp/atomic-$1-$2"
  mkdir -p "$LOG"
  python3 - "$idx" "$ti" "$LOG" <<'PY'
import yaml, sys, subprocess, os, json, datetime, re
idx, ti, LOG = sys.argv[1], int(sys.argv[2]), sys.argv[3]
d = yaml.safe_load(open(idx, encoding="utf-8"))
t = (d.get("atomic_tests") or [])[ti]
ex = t.get("executor") or {}
print("technique :", d.get("attack_technique"))
print("test      :", t.get("name"))
print("observable:", (t.get("description") or "").strip().splitlines()[0][:160])
print("executor  :", ex.get("name"), "|", ex.get("command"))
print()
# 1. CONTROL: capture the pre-state the observable will change
subprocess.run(f"tasklist > {LOG}/pre.txt 2>&1 || ps aux > {LOG}/pre.txt 2>&1", shell=True)
# 2. RUN
cmd = ex.get("command") or ""
for a in (ex.get("command", "").split() and [] or []): pass
try:
    p = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=300)
    open(f"{LOG}/stdout.txt","w").write(p.stdout or "")
    open(f"{LOG}/stderr.txt","w").write(p.stderr or "")
    print("exit:", p.returncode)
except Exception as e:
    print("EXEC ERROR:", type(e).__name__)
# 3. OBSERVABLE: the post-state, diffed against the control
subprocess.run(f"tasklist > {LOG}/post.txt 2>&1 || ps aux > {LOG}/post.txt 2>&1", shell=True)
print()
print("pre/post captured in", LOG)
print("NEXT: diff pre.txt against post.txt - the ADDED line matching the description's observable IS success.")
PY
}
echo "usage: run_atomic atomics/atomics/T1059.001/T1059.001.yaml 0"
```

**The pre/post diff is the observable check.** The added process, file, registry key, or event matching
the test's description is what success looks like - not the exit code.

### 9.4 The cleanup, and its verification

```bash
# cleanup is a declared command, and it must be RUN and VERIFIED
clean_atomic() {
  local idx="$1" ti="${2:-0}"
  python3 - "$idx" "$ti" <<'PY'
import yaml, sys, subprocess
d = yaml.safe_load(open(sys.argv[1], encoding="utf-8"))
t = (d.get("atomic_tests") or [])[int(sys.argv[2])]
cl = (t.get("executor") or {}).get("cleanup_command") or ""
print("cleanup:", cl or "<none declared>")
if not cl:
    print("NO CLEANUP DECLARED - the artefact must be removed by hand, and the report must say so.")
    sys.exit(0)
p = subprocess.run(cl, shell=True, capture_output=True, text=True, timeout=180)
print("cleanup exit:", p.returncode)
print((p.stdout or p.stderr or "")[:200].strip())
print()
print("VERIFY the removal: re-run the observable check and confirm the artefact is gone.")
PY
}
echo "--> and then verify by hand:"
echo "    Windows: tasklist | findstr /i <artifact>   && reg query <key>"
echo "    Linux:   ps aux | grep -v grep | grep <artifact> ; ls -l <path>"
```

**A cleanup command that ran is not a cleanup that worked.** The post-cleanup observable check is what
confirms it, and an artefact left on the host is an incident.

### 9.5 The detection-validation loop

```python
# the point of the library for a blue team: does the SIEM see the test?
# THE NEGATIVE CONTROL is essential - a test that is too noisy proves nothing about the hunt.
LOOP = [
 "1. confirm the telemetry source is ON and forwarding BEFORE the test (the negative control)",
 "2. capture the baseline: the event count for the technique's expected event IDs in the last hour",
 "3. run the atomic test, recording the start and end timestamps to the second",
 "4. query the SIEM for the technique's expected event IDs in that window",
 "5. record: event present? alert fired? which rule? what was the latency?",
 "6. THE NEGATIVE CONTROL: run a BENIGN command that should also generate a similar event,",
 "   and confirm the rule does NOT alert on it. Without this the rule's precision is unknown.",
 "7. repeat with a MODIFIED test (an obfuscated variant) and see whether the rule still fires -",
 "   this measures the rule's robustness, not just its existence.",
 "8. record the coverage result per technique, and the gap as an action item.",
]
for s in LOOP: print(s)
print()
print("the artefact to keep, per test:")
for a in ["the start and end timestamps, to the second",
          "the command as executed, with its arguments",
          "the observable (the process, the file, the registry key, the event)",
          "the SIEM query and its result count for the window",
          "the alert, if any, with the rule name",
          "the negative control's result",
          "the cleanup command's exit AND the post-cleanup observable check"]:
    print("  -", a)
```

**The negative control is what makes a detection result meaningful.** A rule that fires on everything is
not a detection, and the benign-variant run is how you measure that.

### 9.6 The end-to-end harness

```bash
python3 - <<'PY'
import yaml, glob, os, subprocess, datetime, json
LIB = "atomics/atomics"
def tests(pat="T*"):
    for idx in sorted(glob.glob(os.path.join(LIB, pat, "*.yaml"))):
        d = yaml.safe_load(open(idx, encoding="utf-8")) or {}
        for i, t in enumerate(d.get("atomic_tests") or []):
            yield idx, i, d.get("attack_technique"), t

def platform_ok(t):
    import platform
    p = platform.system().lower()
    p = "windows" if p == "windows" else ("macos" if p == "darwin" else "linux")
    return p in (t.get("supported_platforms") or [])

def dep_ok(t):
    return all((d.get("get_prereq_command") or "").strip() for d in (t.get("dependencies") or []))

TARGET = os.environ.get("TECHNIQUE", "T1059.001")
rows = [(i, t) for (idx, i, tid, t) in tests(TARGET) if tid == TARGET]
print(f"=== {TARGET}: {len(rows)} tests ===")
print("%-4s %-8s %-9s %-42s %-7s %s" % ("#","platform","executor","name","deps","cleanup"))
for i, t in rows:
    ex = (t.get("executor") or {}).get("command", "")
    print("%-4s %-8s %-9s %-42s %-7s %s" % (
        i, "OK" if platform_ok(t) else "n/a",
        (t.get("executor") or {}).get("name","?")[:9], t.get("name","?")[:42],
        "ok" if dep_ok(t) else "MISS",
        "yes" if (t.get("executor") or {}).get("cleanup_command") else "NONE"))
print()
print("RUN ORDER: platform-ok AND deps-ok AND cleanup-present first.")
print("For each run, record: the pre/post diff, the SIEM window query, the negative control,")
print("and the verified cleanup. A test without a cleanup is sequenced last.")
PY
```

**The run order is platform, dependencies, then cleanup availability.** A test with no cleanup command
goes last, because an unremovable artefact is the highest-risk run in the set.

---

## 11. EVIDENCE STANDARD — EXECUTION ARTEFACTS

| Item | Why |
|---|---|
| The **technique ID and test name**, with the library version or commit | reproducibility |
| The **prerequisite provisioning** and its verification exit | proves the failure was not a missing tool |
| The **exact command executed**, with its arguments resolved | reproducibility |
| The **pre-state and the post-state**, diffed | the observable |
| The **observable the description declares**, quoted | success is measured against the test's own criterion |
| The **cleanup command and the post-cleanup check** | the host is as it was |
| The **SIEM query and the result count for the window** | the detection result |
| The **negative control** (a benign variant, and the rule's result on it) | the rule's precision |
| Any **modification** you made to the test, and why | honesty about what was actually run |
| Confirmation that **no artefact was left on the host** | engagement integrity |

Report the **observable and the detection result**: "`T1059.001` test `6` (`powershell.exe` execution)
declares its observable as a PowerShell process spawning from `cmd.exe`. `get_prereq_command` was run
first and its `prereq_command` returned `0`, which verifies the dependency. The pre-state's
`tasklist` output contains no `powershell.exe` line and the post-state contains one with a parent
recorded in Sysmon event `1`, which is the declared observable. The SIEM query for event `1` with
`Image ends with powershell.exe` in the 12-second window returned `2` events and fired rule
`PROC-014`, with a 40-second latency. A benign `powershell.exe -Command Get-Date` also generated an
event but did not fire the rule, which is the negative control and shows the rule is not simply
matching the image name. The cleanup command removed the script and the post-cleanup `tasklist` check
shows no `powershell.exe` from the test", never "the technique can be executed".

### False positives - do not report these

| Observation | Why it is not a finding |
|---|---|
| A command exiting **`0`** with no observable | the exit code is not the test's success criterion |
| A test that **failed because a dependency was missing** | a prerequisite gap, not a detection failure |
| A test run on the **wrong platform** | not applicable |
| An observable that **already existed in the pre-state** | the control shows it was not the test |
| A detection rule that fired on the **negative control too** | the rule is unusable; that is the finding |
| A technique "working" in a **lab with protections disabled** | report the conditions, not the technique |
| A test whose artefact was **left on the host** | an incident you caused |
| A **`manual` executor test** that was skipped | not run; say so |
| A test marked **`auto_generated`** that failed | note the generation status; prefer a hand-written variant |
| A finding from a test run **outside the authorised scope or window** | out of scope |
| A detection result with **no negative control** | an unmeasured claim about the rule |

**The declared observable, the prereq, and the negative control.** Exit codes and missing dependencies
account for most of this family's false results.

---

## 12. REMEDIATION REFERENCE — TEST EXECUTION DISCIPLINE

1. **Run `get_prereq_command` and then `prereq_command` for every dependency before running the test, and record both exits** - the dependency block is the single largest source of false failures.
2. **Capture the pre-state and the post-state for the observable the description declares, and diff them** - it replaces the exit code with the test's own success criterion.
3. **Run the declared `cleanup_command` after every test and verify the removal by re-checking the observable** - a cleanup that was not verified is a cleanup that did not happen.
4. **Sequence tests so that those without a cleanup command run last, and never run one on a production host without written authorisation** - an unremovable artefact is the highest-risk run in the library.
5. **Keep the library at a pinned commit and record that commit with every result, so a later run can be attributed to a known state** - the tests change and the results must stay attributable.
6. **Run the negative control for every detection claim: a benign variant that should not alert** - without it, the rule's precision is unknown and the result is not usable.
7. **Record the telemetry state before the test, so a silent result is attributable to the rule rather than to a broken pipeline** - the detection-validation loop needs the pipe confirmed first.
8. **Prefer hand-written tests over `auto_generated` ones where both exist for a technique, and treat a generated failure as inconclusive** - the generated tests are the least reliable and the attribution matters.
9. **Store the artefact bundle per run: the command, the timestamps, the diff, the SIEM query, the alert, and the cleanup verification** - the bundle is the deliverable of this skill, not the running of the test.
10. **Escalate a scope or safety question before running, not after** - the library contains tests that will disable protections or modify the registry, and those need explicit authorisation.
11. **Re-run the same pinned test set after detection changes, so the coverage result is comparable across time** - the value of the library is the trend, not a single run.

---

## 13. RELATED SIBLINGS - LOAD TOGETHER

- [windows-lolbins-execution-bypass](../windows-lolbins-execution-bypass/SKILL.md) - the LOLBin layer under most execution tests
- [windows-postexploit](../windows-postexploit/SKILL.md) - the surrounding flow on Windows
- [linux-postexploit](../linux-postexploit/SKILL.md) - the surrounding flow on Linux
- [edr-bypass-techniques](../edr-bypass-techniques/SKILL.md) - when the test itself is blocked
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) - the blue-side validation counterpart
