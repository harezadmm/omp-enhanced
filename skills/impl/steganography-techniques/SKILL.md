---
name: steganography-techniques
description: >-
  Steganography detection and extraction playbook. Use when analyzing images (LSB, PNG chunks, JPEG DCT, EXIF), audio (spectrogram, DTMF), files (polyglots, appended data, ADS), and text (whitespace, zero-width, homoglyphs) for hidden data.
---

# SKILL: Steganography Techniques — Expert Analysis Playbook

> **AI LOAD INSTRUCTION**: Expert steganography detection and extraction techniques. Covers image steganography (LSB, PNG chunk hiding, JPEG DCT, EXIF metadata, dimension tricks, palette manipulation), audio steganography (spectrogram, LSB, DTMF, morse), file steganography (polyglots, binwalk, NTFS ADS, steghide), and text steganography (whitespace, zero-width Unicode, homoglyphs). Base models miss the systematic file-type-based analysis approach and tool-specific extraction workflows.

## 0. RELATED ROUTING

Before going deep, consider loading:

- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) for extracting files from network captures before stego analysis
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) for extracting files from memory dumps
- [classical-cipher-analysis](../classical-cipher-analysis/SKILL.md) if extracted hidden data is further encrypted/encoded

### Tool Reference

Also load [STEGO_TOOLS_GUIDE.md](./STEGO_TOOLS_GUIDE.md) when you need:
- Tool installation instructions and dependencies
- Detailed command reference for each stego tool
- Workflow patterns for specific file types

---

## 1. IMAGE STEGANOGRAPHY

### LSB (Least Significant Bit)

LSB embeds data in the least significant bits of pixel color channels.

```bash
# zsteg — LSB analysis for PNG/BMP
zsteg image.png                       # auto-detect all LSB patterns
zsteg image.png -a                    # try all known methods
zsteg image.png -b 1                  # extract bit plane 1
zsteg image.png -E "b1,rgb,lsb,xy"   # specific extraction pattern

# StegSolve (Java GUI)
java -jar StegSolve.jar
# Navigate color planes: Red 0, Green 0, Blue 0 → look for hidden image/text
# Data Extractor: specify bit planes + byte order

# stegoveritas — comprehensive automated analysis
stegoveritas image.png
# Runs: exiftool, binwalk, zsteg, foremost, color plane extraction
```

### PNG Specific

```bash
# pngcheck — validate structure, find hidden chunks
pngcheck -v image.png

# Hidden chunks: tEXt, zTXt (compressed text), iTXt (international text)
# Custom/private chunks may contain hidden data

# CRC vs dimensions trick
# If CRC doesn't match declared dimensions → image was cropped
# Fix: brute-force correct width/height → reveals hidden rows/columns
python3 -c "
import struct, zlib
with open('image.png','rb') as f:
    data = f.read()
# Check IHDR CRC at offset 29
ihdr = data[12:29]
for h in range(1,2000):
    for w in range(1,2000):
        new_ihdr = struct.pack('>II',w,h) + ihdr[8:]
        if zlib.crc32(b'IHDR'+new_ihdr) & 0xffffffff == struct.unpack('>I',data[29:33])[0]:
            print(f'Width: {w}, Height: {h}')
"

# APNG (animated PNG) — hidden frames
# Use apngdis to extract all frames: apngdis image.png
```

### JPEG Specific

```bash
# steghide — embed/extract from JPEG (DCT coefficient modification)
steghide extract -sf image.jpg                 # extract (no passphrase)
steghide extract -sf image.jpg -p PASSWORD     # extract with passphrase
steghide info image.jpg                        # check if data is embedded

# stegcracker — brute force steghide passphrase
stegcracker image.jpg wordlist.txt

# jsteg — JPEG LSB steganography
jsteg reveal image.jpg output.txt

# JPEG structure analysis
exiftool -v3 image.jpg       # verbose metadata + structure
jpegdump image.jpg           # raw JPEG marker analysis
```

### EXIF Metadata

```bash
# exiftool — comprehensive metadata extraction
exiftool image.jpg
exiftool -b -ThumbnailImage image.jpg > thumb.jpg   # extract thumbnail
exiftool -all= image.jpg                             # strip all metadata

# Hidden data in EXIF fields (comment, artist, copyright, etc.)
exiftool -Comment image.jpg
exiftool -UserComment image.jpg
strings image.jpg | grep -i "flag\|key\|secret"
```

### Palette-Based (GIF)

```bash
# GIF color table manipulation — data in color palette order
gifsicle -I image.gif                    # info
gifsicle --color-info image.gif          # palette details
# Check for animation frames: convert -coalesce image.gif frame_%d.png
```

---

## 2. AUDIO STEGANOGRAPHY

### Spectrogram Analysis

```bash
# Sonic Visualiser — best for spectrogram viewing
# Layer → Add Spectrogram → look for visual patterns (text/images)

# Audacity
# Analyze → Plot Spectrum
# Select audio → change view to Spectrogram

# sox for command-line spectrogram generation
sox audio.wav -n spectrogram -o spectro.png
```

### Audio LSB

```bash
# DeepSound — hide/extract files in audio (Windows)
# GUI tool: open audio file → extract hidden files

# WavSteg — LSB in WAV files
python3 WavSteg.py -r -i audio.wav -o output.txt -n 1   # extract 1 LSB
python3 WavSteg.py -r -i audio.wav -o output.txt -n 2   # extract 2 LSBs
```

### DTMF / Morse Code

```bash
# DTMF decoder (phone tones)
multimon-ng -t wav -a DTMF audio.wav

# Morse code
# Audacity → visual inspection of on/off pattern
# Online decoder or manual: .- = A, -... = B, etc.

# SSTV (Slow-Scan Television) — image in audio
qsstv                    # GUI decoder
# Or: RX-SSTV (Windows)
```

### WAV Header Manipulation

```bash
# Check for data appended after WAV audio data
# WAV data chunk size vs actual file size
python3 -c "
import wave
w = wave.open('audio.wav','rb')
print(f'Frames: {w.getnframes()}, Channels: {w.getnchannels()}, Width: {w.getsampwidth()}')
expected = w.getnframes() * w.getnchannels() * w.getsampwidth() + 44  # 44 = WAV header
import os
actual = os.path.getsize('audio.wav')
if actual > expected:
    print(f'Extra data: {actual - expected} bytes appended')
"
```

---

## 3. FILE STEGANOGRAPHY

### Polyglot Files

A single file that is valid in two or more formats simultaneously.

```bash
# Detection: check file with multiple tools
file suspicious_file
xxd suspicious_file | head          # check magic bytes
binwalk suspicious_file             # find embedded files

# Common polyglots: PDF+ZIP, JPEG+ZIP, JPEG+RAR, PNG+ZIP
# Try unzip on image files:
unzip image.jpg -d extracted/
7z x image.jpg -oextracted/
```

### Appended / Embedded Data

```bash
# binwalk — scan for embedded files and data
binwalk image.png                   # scan
binwalk -e image.png                # extract embedded files
binwalk --dd='.*' image.png         # extract everything

# foremost — file carving
foremost -i suspicious_file -o output_dir/

# dd — manual extraction
# If binwalk shows embedded ZIP at offset 0x1234:
dd if=suspicious_file bs=1 skip=$((0x1234)) of=extracted.zip
```

### NTFS Alternate Data Streams (ADS)

```cmd
:: List ADS (Windows)
dir /r file.txt
Get-Item file.txt -Stream *

:: Read hidden stream
more < file.txt:hidden_stream
Get-Content file.txt -Stream hidden_stream

:: Create ADS (for testing)
echo "hidden data" > file.txt:secret
```

### Steghide Brute Force

```bash
# stegcracker — wordlist attack on steghide passphrase
stegcracker image.jpg /usr/share/wordlists/rockyou.txt

# stegseek — faster alternative
stegseek image.jpg /usr/share/wordlists/rockyou.txt
# stegseek is ~10000x faster than stegcracker
```

---

## 4. TEXT STEGANOGRAPHY

### Whitespace Encoding

```bash
# Tabs and spaces encode binary (tab=1, space=0 or vice versa)
# stegsnow — whitespace steganography
stegsnow -C message.txt                # extract hidden message
stegsnow -C -p PASSWORD message.txt    # extract with password

# Manual detection:
cat -A file.txt | head     # show tabs (^I) and line endings ($)
xxd file.txt | grep "09 20\|20 09"    # look for tab/space patterns
```

### Zero-Width Characters

```bash
# Unicode invisible characters used for encoding:
# U+200B (Zero-Width Space), U+200C (ZWNJ), U+200D (ZWJ), U+FEFF (BOM)

# Detection:
python3 -c "
text = open('message.txt','r').read()
hidden = [c for c in text if ord(c) in [0x200b, 0x200c, 0x200d, 0xfeff]]
print(f'Found {len(hidden)} zero-width characters')
binary = ''.join('0' if ord(c)==0x200b else '1' for c in hidden)
# Convert binary to ASCII
"

# Online tools: holloway.nz/steg, Unicode Steganography decoders
```

### Homoglyph Substitution

```bash
# Visually identical characters from different Unicode blocks
# e.g., Latin 'a' (U+0061) vs Cyrillic 'а' (U+0430)

# Detection:
python3 -c "
text = open('message.txt','r').read()
for i, c in enumerate(text):
    if ord(c) > 127:
        print(f'Position {i}: char={c} ord={ord(c)} name={__import__(\"unicodedata\").name(c,\"?\")}')
"
```

---

## 5. DECISION TREE

```
Suspect hidden data — what file type?
│
├── Image (PNG/BMP)?
│   ├── Check metadata: exiftool (§1 EXIF)
│   ├── Check structure: pngcheck, binwalk (§1 PNG)
│   ├── LSB analysis: zsteg, StegSolve (§1 LSB)
│   ├── Check dimensions vs CRC: height/width brute force (§1 PNG)
│   ├── Check for appended data: binwalk -e (§3)
│   └── Try as polyglot: unzip/7z (§3)
│
├── Image (JPEG)?
│   ├── Check metadata: exiftool (§1 EXIF)
│   ├── Try steghide: steghide extract (§1 JPEG)
│   │   └── Password protected? → stegseek brute force (§3)
│   ├── Try jsteg: jsteg reveal (§1 JPEG)
│   ├── Check for appended data: binwalk -e (§3)
│   └── Check thumbnail: exiftool -b -ThumbnailImage (§1 EXIF)
│
├── Image (GIF)?
│   ├── Check frames: extract all animation frames (§1 Palette)
│   ├── Check palette: gifsicle --color-info (§1 Palette)
│   └── Check for appended data: binwalk -e (§3)
│
├── Audio (WAV/MP3/FLAC)?
│   ├── Spectrogram: Sonic Visualiser / Audacity (§2)
│   ├── LSB: WavSteg (§2)
│   ├── DTMF tones: multimon-ng (§2)
│   ├── Morse code: manual or decoder (§2)
│   ├── SSTV: qsstv (§2)
│   └── Check file size vs expected: header analysis (§2)
│
├── Text file?
│   ├── Check whitespace: cat -A, stegsnow (§4)
│   ├── Check zero-width chars: Unicode analysis (§4)
│   ├── Check homoglyphs: non-ASCII detection (§4)
│   └── Check encoding: multiple base decodings
│
├── Any file type?
│   ├── strings: strings -n 8 file | grep -i "flag\|key\|pass"
│   ├── binwalk: binwalk -e file (embedded files) (§3)
│   ├── file: file suspicious_file (true type)
│   ├── xxd: check magic bytes, compare headers
│   └── NTFS? → check ADS: dir /r (§3)
│
└── Password/passphrase needed?
    ├── steghide → stegseek / stegcracker (§3)
    ├── Check challenge description for hints
    └── Try common passwords: password, file name, challenge name
```

---

## 6. CONFIRMING THE FINDING

Steganography's failure mode is **seeing a payload in noise**, because any sufficiently large file yields
patterns when you look hard enough. This table is the discipline that separates a carrier from an artefact.

| Step | Question | What it proves |
|---|---|---|
| 1 | Is the **carrier's baseline** known: the original file, or the same file untreated? | without it, "the LSBs look odd" is meaningless |
| 2 | Was the extraction **verifiable**: does the payload have a structure, a hash, or a known header? | a plausible blob is not a payload |
| 3 | Is the difference **larger than the format's own tolerance** (compression, quantisation)? | JPEG/MP3 lossy formats create real LSB noise |
| 4 | Was the extraction **reproduced** by a second method or tool? | a carve's boundaries decide the result |
| 5 | Is there a **negative control**: the same analysis on a clean file of the same type? | the essential control in this domain |
| 6 | Is the payload's **presence in the channel** consistent with the delivery story? | the carrier must reach the target |
| 7 | Does the claim distinguish **steganography from watermarking/embedding by the format itself**? | legitimate metadata is not a payload |

**A known baseline, a structurally verifiable extraction, and a clean-file negative control.** Any large file
yields patterns under sufficient scrutiny, and the control is what separates a payload from a coincidence.

---

## 7. EXECUTION PRIMITIVES

The central rule: **a steganographic finding is a DIFFERENCE from a baseline, and both the extraction's
structure and a clean-file control are required.** Noise, alone, is never a finding.

### 6.1 The baseline, which is not optional

```bash
# WITHOUT A BASELINE THERE IS NO FINDING. Establish what "normal" is for THIS carrier.
CARRIER="${CARRIER:?the suspect file}"
echo "=== 1. the carrier's own facts, before any steg analysis ==="
file "$CARRIER"
sha256sum "$CARRIER" | tee /tmp/carrier.sha256
exiftool "$CARRIER" 2>/dev/null | head -40
cat <<'EXIF'
  READ THE METADATA FIRST, AND TREAT IT AS A LEAD, NOT AS PROOF:
    - a metadata field containing a LONG BASE64-LOOKING STRING is a candidate. It is ALSO
      what many legitimately tools write (a thumbnail, a preview, an XMP block, a comment).
    - THE DIFFERENCE BETWEEN A LEAD AND A FINDING IS THIS: for a legitimate field, you can
      DECODE it and show it is what the tool documents (a thumbnail decodes to an image; an XMP
      block parses as XMP). For a payload, you show the decoded bytes have a STRUCTURE the context
      does not explain.
    - AND: APPENDED DATA AFTER THE FORMAT'S END MARKER (after a JPEG's EOI, after a PNG's IEND,
      after a zip's central directory) is a STRONG candidate, because a format's own readers
      IGNORE it while a carver finds it. THAT is the commonest simple carrier.
EXIF
echo
echo "=== 2. the appended-data test, which is the highest-value quick check ==="
echo "  for a PNG:  the IEND chunk's position vs the file's end"
echo "  for a JPEG: the EOI (FFD9) marker's LAST occurrence vs the file's end"
echo "  for a ZIP:  the end-of-central-directory record's position, and what follows it"
python3 - "$CARRIER" <<'PY'
import sys
d = open(sys.argv[1], 'rb').read()
print(f"  file size: {len(d)}")
for name, sig in [("JPEG EOI (FFD9)", b'\xff\xd9'), ("PNG IEND", b'IEND'), ("ZIP EOCD", b'PK\x05\x06')]:
    i = d.rfind(sig)
    if i >= 0:
        tail = len(d) - (i + len(sig))
        print(f"  {name:20} last at offset {i:9}  ->  {tail} bytes follow the marker"
              + ("   <-- CANDIDATE: data after the format's end" if tail > 64 else ""))
print()
print("  THE TRAILING BYTES ARE A CANDIDATE, NOT A FINDING: extract them, and show their STRUCTURE")
print("  (a header, a magic, a container, a decodable payload) or say they are unstructured bytes.")
PY
echo
echo "=== 3. THE NEGATIVE CONTROL: the same analysis on a CLEAN file of the same type ==="
cat <<'CONTROL'
  THIS IS THE CONTROL THAT MAKES EVERY LSB CLAIM VALID:
    1. take a CLEAN file of the SAME FORMAT, ideally produced by the SAME TOOL, at a similar size
    2. run THE IDENTICAL analysis on it
    3. RECORD THE RESULT

  WHY IT IS ESSENTIAL: a LOSSLESS format's LSB planes carry real low-order structure, and a LOSSY
  format (JPEG, MP3, AAC) creates LSB NOISE BY DESIGN through quantisation. So:
    - a histogram of the LSBs is NOT flat in a clean file, in general
    - a chi-square or RS test's PASS/FAIL THRESHOLD is format- and tool-dependent
    - therefore 'the test flagged it' WITHOUT the clean-file's own value is UNINTERPRETABLE.
  A FINDING SAYS: 'the test's statistic on the suspect file is X; on a clean file of the same
  format and tool, it is Y; and the EXTRACTED PAYLOAD has structure Z.' ALL THREE PARTS.
CONTROL
```

**A trailing-data candidate is not a finding — it needs structure.** And the clean-file control is essential
because lossy formats create LSB noise by design, making the test's statistic uninterpretable alone.

### 6.2 The extraction, structurally verifiable

```bash
echo "=== THE EXTRACTION MUST PRODUCE SOMETHING WITH STRUCTURE ==="
cat > /tmp/steg_extract.md <<'MD'
### THE EXTRACTION'S THREE ACCEPTANCE LEVELS
1. LEVEL A - UNSTRUCTURED BYTES: a blob with no recognisable structure.
   -> NOT a finding on its own. It is a lead, and it must be labelled one.
2. LEVEL B - A RECOGNISED STRUCTURE: the bytes begin with a known magic (a file type, a container,
   a compressed stream, an encrypted blob's header) or decode as valid UTF-8 text with meaning.
   -> A FINDING, and it must be shown: the magic, the length, and what it parses as.
3. LEVEL C - AN AUTHENTICATED OR VERIFIED ARTEFACT: the structure validates (a zip extracts, a
   PNG renders, a text is coherent, a hash matches a reference).
   -> THE STRONGEST FINDING, and it is the one to aim for.

### AND THE CARVE'S OWN DISCIPLINE
- RECORD the parameters: the bit plane, the channel, the order, the offset, the stride, the length.
  A carve is PARAMETERISED, and a different parameter set produces different bytes - so the report
  must let a reader REPRODUCE the exact carve.
- RE-CARVE WITH A SECOND TOOL and compare hashes. Agreement is confirmation; disagreement means the
  parameters were not what you thought.
- WHERE THE CARRIER IS LOSSY: re-encoding DESTROYS the payload. Record that the analysis was on the
  ORIGINAL bytes, and never re-save the file before extracting.
MD
cat /tmp/steg_extract.md
echo
echo "=== THE CAPACITY SANITY CHECK, which rules out the impossible ==="
python3 - <<'PY'
print("  a carrier can hold only so much. An extraction claiming MORE than the capacity is WRONG:")
for fmt, bits, note in [("PNG/bitmap, 1 bit per channel per pixel", "W*H*C bits", "the classic"),
                        ("PNG, 1 bit in only one channel",           "W*H bits",     "C=1"),
                        ("JPEG (lossy)",                             "~0 SAFE bits", "quantisation destroys LSBs; a claimed LSB payload in a re-compressed JPEG is suspicious"),
                        ("MP3 (lossy)",                             "~0 SAFE bits", "the same, per frame"),
                        ("WAV PCM 16-bit, 1 LSB per sample",         "samples bits", "reliable in a LOSSLESS container"),
                        ("Text, trailing whitespace",                "chars bits",   "the carrier is the FORMAT's tolerance, not noise"),
                        ("Text, zero-width characters",              "chars * ~2",   "invisible, and survives copy-paste")]:
    print("    %-46s %-14s %s" % (fmt, bits, note))
print()
print("  THE CHECK: estimate the capacity, compare with the extracted payload's size, and STATE IT.")
print("  A payload larger than the carrier's capacity means the extraction's parameters are wrong.")
PY
```

**The carve is parameterised and must be reproducible, and a lossy carrier's re-encoding destroys the
payload.** A payload larger than the carrier's computed capacity means the extraction's parameters are wrong.

### 6.3 The channel, and the end-to-end harness

```bash
echo "=== THE CHANNEL: THE CARRIER MUST REACH THE TARGET, AND THE DELIVERY STORY MUST HOLD ==="
cat <<'CHANNEL'
  THE DELIVERY CHAIN, EACH LINK REQUIRING EVIDENCE:
    the CREATOR      : who produced the carrier, and with what tool (a tool-specific artefact, if any)
    the CHANNEL      : how it was delivered (an upload, an email attachment, a social post, a CDN)
    the CARRIER      : the file as it ARRIVED - and CRITICALLY, whether it SURVIVED the channel
                       (a social platform RE-ENCODES images; an email may repack; a CDN may minify)
    the EXTRACTOR    : the recipient's tool, and the same parameter set

  THE KILLER QUESTION: DID THE PAYLOAD SURVIVE THE CHANNEL AS OBSERVED?
    If the platform re-encoded the image, an LSB payload SPECIFICALLY would be DESTROYED, and the
    payload as observed could NOT have arrived that way. THAT CONTRADICTION IS A FINDING ABOUT THE
    ANALYSIS, and the extraction's parameters or the carrier's provenance must be re-examined.
  AND THE OBSERVED CARRIER IS THE EVIDENCE, NOT THE ORIGINAL: acquire the file AS DELIVERED, hash
  it, and analyse THOSE bytes. Analysing a re-saved copy is a common and fatal error.
CHANNEL
echo
echo "=== THE DISTINCTION: STEGANOGRAPHY vs THE FORMAT'S OWN EMBEDDING ==="
python3 - <<'PY'
D = [("a JPEG's EXIF thumbnail",        "the format documents it",            "NOT steganography"),
     ("an ID3 APIC frame in MP3",       "the format documents it",            "NOT steganography"),
     ("a Word doc's revision history",  "the application documents it",       "NOT steganography"),
     ("a PDF's incremental update",     "the format documents it",            "NOT steganography - but may hide DELETED content, which is a DIFFERENT finding"),
     ("an appended archive after EOI",  "the format IGNORES it",              "STEGANOGRAPHY (the reader and the carver disagree)"),
     ("LSB planes in a LOSSLESS image", "the format uses them meaningfully",  "STEGANOGRAPHY if the planes are perturbed vs the baseline"),
     ("zero-width characters in text",  "the format renders them invisibly",  "STEGANOGRAPHY (the renderer and the bytes disagree)"),
     ("metadata with a long blob",      "the format permits free text",       "AMBIGUOUS: decode it and show what it IS")]
print("%-34s %-38s %s" % ("observation","why it is not automatically steganography","classification"))
for a,b,c in D: print("%-34s %-38s %s" % (a,b,c))
print()
print("  THE PRINCIPLE: STEGANOGRAPHY IS A DISAGREEMENT BETWEEN WHAT THE RENDERER SHOWS AND WHAT THE")
print("  BYTES CONTAIN. A DOCUMENTED FIELD THE TOOL ITSELF WROTE IS NOT A DISAGREEMENT.")
PY
echo
echo "=== the end-to-end harness ==="
python3 - <<'PY'
print("=== STEGANOGRAPHY ACCEPTANCE CHECKLIST ===")
CHECKS = [
 ("the carrier as DELIVERED was acquired and hashed, and the analysis used those bytes",
  "analysing a re-saved copy is fatal, and re-encoding destroys lossy carriers"),
 ("metadata was read FIRST and treated as a lead, with any decoded field shown to be what the tool documents",
  "a long blob is equally likely to be a legitimate preview"),
 ("appended data after the format's end marker was tested, and its structure established",
  "trailing bytes are a candidate, not a finding"),
 ("the CLEAN-FILE negative control was run: the same analysis on a clean file of the same format and tool",
  "the control that makes every test statistic interpretable"),
 ("the test's statistic on the suspect file AND on the clean file are both reported",
  "a single value is uninterpretable, especially for lossy formats"),
 ("the extraction reached LEVEL B or C: a recognised structure, or a validated artefact",
  "unstructured bytes are a lead, not a finding"),
 ("the carve's PARAMETERS are recorded: bit plane, channel, order, offset, stride, length",
  "a carve is parameterised, and different parameters give different bytes"),
 ("the extraction was RE-CARVED with a second tool and the hashes compared",
  "agreement confirms; disagreement means the parameters were wrong"),
 ("the CAPACITY was computed and compared with the payload's size",
  "a payload larger than capacity means the parameters are wrong"),
 ("the payload's survival through the CHANNEL is consistent with the delivery story",
  "a re-encoding platform would destroy an LSB payload, which contradicts the observation"),
 ("a documented format field is NOT reported as steganography",
  "steganography is a disagreement between the renderer and the bytes"),
 ("the finding names the channel and the tool where possible",
  "'hidden data was found' names neither who hid it nor how it travelled"),
]
for n, how in CHECKS: print("  [ ] %-74s -> %s" % (n, how))
print()
print("=== THE REPORT SHAPE ===")
print("  carrier  : the file as delivered, its hash, its format and metadata")
print("  baseline : the clean-file control and its test statistic")
print("  carve    : the parameters, the second tool's agreement, the capacity check")
print("  payload  : the structure level reached, and what it validates as")
print("  channel  : the delivery path, and whether the payload could have survived it")
print("  class    : steganography, or the format's own documented embedding")
PY
```

---

## 8. EVIDENCE STANDARD
| Item | Why |
|---|---|
| The **carrier and its baseline**: the original file, or the same file untreated | without a baseline there is no difference, and without a difference there is no finding |
| The **control file's** statistics for the same format | lossy formats create LSB noise by design, so the comparator is mandatory |
| The **extraction method** and its parameters | an extraction is a procedure, and it must be reproducible |
| The **extracted payload's structure**: a magic, a container, a valid decode | random bytes are not a payload |
| The **capacity arithmetic**: the payload's size against what the carrier can hold | a payload larger than the capacity means the parameters are wrong |
| The rendered-versus-stored difference, where the finding is a renderer's behaviour | that difference is what steganography is |
| The **format's documentation** for any field claimed as hidden | a documented field is not hidden |

### Finding failures — how they mislead

| Failure | How it misleads |
|---|---|
| **No clean-file control** | lossy compression's own noise is reported as a payload |
| **Chi-square or entropy alone** | those statistics flag ordinary images, and they need a comparator |
| **Trailing data** treated as a payload without structure | every format permits padding; structure is what makes it a payload |
| A **documented field** reported as covert | the format defines it; it is not a channel |
| An **extraction that needed guessed parameters** | the parameters were fitted until something appeared |
| **Capacity ignored** | a 10-byte carrier cannot hold a 1 MB payload, so the extraction is wrong |
| **LSB noise** in a JPEG/MP3 reported as a payload | lossy formats create it by design |

| Item | Why |
|---|---|
| The carrier, its hash, and its **baseline** (the original or an untreated copy) | the difference is the finding and the baseline is half of it |
| The **clean-file control** for the same format, with its statistics | lossy noise is not a payload |
| The **extraction method**, its parameters, and its exact output | a fitted parameter is not an extraction |
| The extracted payload's **structure** and a successful **decode** | structure, not entropy, makes a payload |
| The **capacity arithmetic** against the carrier | a payload exceeding the capacity invalidates the extraction |
| The **renderer-versus-stored** difference where that is the finding | steganography is exactly that difference |
| The format's **documentation** for any field claimed as covert | a defined field is not hidden |

**A clean file's statistics are not optional** — lossy formats create LSB noise by design, so a chi-square
result without a comparator is uninterpretable, and structure is what turns trailing bytes into a payload.

---

## 9. REMEDIATION REFERENCE

1. **Re-encode rather than strip.** Metadata removal and a lossy re-encode destroy most LSB channels;
   "scan and delete" leaves the carrier structure intact.
2. **Fix the ingestion point.** A covert channel that arrives via an upload means the control belongs at
   the upload: normalise the media, re-encode it, and re-derive the metadata.
3. **State the detection you can actually run.** Statistical tests without a baseline have a high
   false-positive rate; a detection rule needs the comparator it will use.
4. **Note what the fix does not cover.** Re-encoding removes LSB channels and does not address a payload
   appended after the format's terminator, nor one in a permissive container.
5. **Distinguish a carrier from an artefact.** The fix for a hidden payload and the fix for an ordinary
   file with trailing bytes are different, and conflating them wastes the defender's time.

---

## 10. RELATED SIBLINGS - LOAD TOGETHER
- [traffic-analysis-pcap](../traffic-analysis-pcap/SKILL.md) - the channel a carrier travels through
- [data-breach-correlation-workflows](../data-breach-correlation-workflows/SKILL.md) - the provenance discipline the same evidence needs
- [memory-forensics-volatility](../memory-forensics-volatility/SKILL.md) - where an extracted payload may be found in use
- [malware-development-workflow](../malware-development-workflow/SKILL.md) - the payload an embedded carrier delivers
- [cloudflare-waf-recon-survival](../cloudflare-waf-recon-survival/SKILL.md) - the edge that may re-encode a delivered carrier
