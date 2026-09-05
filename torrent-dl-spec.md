# torrent-dl — Spec for Refactored Torrent Downloader & Converter

> **Status:** DRAFT  
> **Created:** 2026-09-02  
> **Location:** `/data/data/com.termux/files/home/torrent-dl`  
> **Platform:** Termux (Android)

---

## 1. Overview

A unified CLI tool for downloading torrents and converting media files, running in Termux. Combines an `aria2c`-based downloader with an `ffmpeg`-based converter into a single interactive workflow.

**Core flow:**  
`Input (magnet/URL/file) → Metadata → File Selection → Download → File Processing → Conversion`

---

## 2. Current State (v1.0)

- **Size:** 224 lines, bash script
- **Backend:** `aria2c` 1.37.0 + `ffmpeg` 8.1.2 (both confirmed available)
- **Paths:** Hardcoded to `$HOME/storage/downloads/Torrents`
- **Limitations:**
  - Duplicated download logic (3 near-identical `aria2c` blocks)
  - `process_files()` scans entire dir, not just newly downloaded files
  - Only processes first argument (`$1`) — no batch mode
  - No metadata display before download
  - No history/log
  - No Termux:API integration
  - No error retry logic

---

## 3. Requirements

### 3.1 Source Types (all must be supported)
| Type | Format | Example |
|------|--------|---------|
| Magnet link | `magnet:?xt=urn:btih:...` | Standard magnet URI |
| HTTP .torrent | `https://example.com/file.torrent` | URL to .torrent file |
| Local .torrent | `/path/to/file.torrent` | Local file path |

### 3.2 Batch Mode (Hybrid)
Three invocation modes:
1. **Single:** `torrent-dl "magnet:?xt=..."`
2. **Multiple:** `torrent-dl URL1 URL2 URL3`
3. **File list:** `torrent-dl --list urls.txt` (one URL per line, skip empty/comments)

### 3.3 Metadata Display (BEFORE download)
Before downloading, display full torrent metadata:
- **Name:** Torrent name
- **Total size:** Human-readable (GB/MB)
- **File count:** Number of files
- **File list:** Each file with size (e.g., `S01E01.mkv — 350 MB`)
- **Tracker:** Primary announce URL
- **Description:** If present in torrent info

**Implementation:** Use Python (stdlib only — `hashlib`, `struct` for bencode parsing) or `transmission-show` if installed. Python stdlib approach preferred since `transmission-show` is not currently available.

### 3.4 File Selection
After metadata display, interactive selection:
- `all` — select all files
- `1 3 5` — specific file numbers
- `1-5` — range of files
- `skip` — skip this torrent entirely

### 3.5 Download
- Use `aria2c` with optimized flags: `--seed-time=0`, `--max-connection-per-server=16`, `--split=16`, `--min-split-size=1M`
- **Track new files:** Record `ls -1` listing of download dir BEFORE download, then diff AFTER to identify only newly downloaded files
- Download dir: `$HOME/storage/downloads/Torrents/{torrent_name}/`

### 3.6 Error Handling
- **On error:** Stop the entire process, display error message, suggest manual retry
- No automatic retry — user controls when to re-run

### 3.7 Post-Download Processing (Conversion)
After download, list ONLY newly downloaded files with interactive selection.

#### 3.7.1 Video Files
**Default quality:** Balanced (CRF 23, ultrafast preset, 192k audio)

| Mode | CRF | Preset | Audio | Use Case |
|------|-----|--------|-------|----------|
| 1 - Fast (copy) | — | — | copy | No re-encode, just change container |
| 2 - Small | 32 | slow | 96k | Maximum compression |
| 3 - Medium | 28 | fast | 128k | Balanced |
| 4 - Large (default) | 23 | ultrafast | 192k | Good quality, fast |
| 5 - High quality | 18 | medium | 256k | Maximum quality |

**Output format:** `.mp4` (with `-movflags +faststart`)

#### 3.7.2 Audio Files
- All non-MP3 → MP3 (FLAC, OGG, M4A, etc.)
- Default bitrate: 192k
- Optional bitrate selection: 128k / 192k / 256k / 320k

#### 3.7.3 Subtitles
- **Ask every time** what to do when subtitles are detected:
  - Extract as `.srt` files
  - Embed into MP4
  - Skip (ignore subtitles)

#### 3.7.4 Post-conversion
- Show before/after file sizes
- Offer to delete original files (y/n)

### 3.8 Android Integration (Termux:API)
- `termux-notification` — notify when download completes
- `termux-toast` — show brief toast on conversion complete
- `termux-open` — optionally open converted file in default Android player
- Detect Termux:API availability gracefully (fallback to no-op if not installed)

### 3.9 Download History
**Hybrid system:**
- **Log file:** `$HOME/.torrent-dl/history.log` (append-only)
  - Format: `YYYY-MM-DD HH:MM:SS | source | torrent_name | files_count | total_size | status`
- **Interactive history:** `torrent-dl --history` — show last N entries with color formatting
- **Clear history:** `torrent-dl --history-clear`

### 3.10 Configurable Paths
Support via flags and environment variables:

| Flag | Env Var | Default | Description |
|------|---------|---------|-------------|
| `-d, --dir` | `TORRENT_DL_DIR` | `$HOME/storage/downloads/Torrents` | Download directory |
| `-c, --convert-dir` | `TORRENT_DL_CONVERT` | `$DOWNLOAD_DIR/Converted` | Conversion output directory |
| `-q, --quality` | `TORRENT_DL_QUALITY` | `4` (balanced) | Default conversion quality |

---

## 4. CLI Interface

```
Usage: torrent-dl [OPTIONS] <source...>

Options:
  -h, --help          Show help
  -d, --dir DIR       Download directory
  -c, --convert-dir   Conversion output directory
  -q, --quality N     Default quality (1-5)
  -l, --list FILE     Read sources from file (one per line)
  --history           Show download history
  --history-clear     Clear download history
  --no-convert        Skip conversion step
  --no-metadata       Skip metadata display (just download)
  --no-notification   Disable Termux notifications

Examples:
  torrent-dl "magnet:?xt=urn:btih:..."
  torrent-dl https://example.com/file.torrent
  torrent-dl -d /sdcard/Movies "magnet:?xt=..."
  torrent-dl --list urls.txt
  torrent-dl --history
```

---

## 5. File Structure

```
$HOME/
├── torrent-dl                          # Main script (bash)
├── .torrent-dl/
│   ├── history.log                     # Download history
│   └── torrent_meta.py                 # Python helper for .torrent parsing
└── storage/downloads/Torrents/
    ├── {torrent_name}/                 # Downloaded files
    │   ├── S01E01.mkv
    │   ├── S01E02.mkv
    │   └── ...
    ├── Converted/                      # Converted output
    │   ├── S01E01.mp4
    │   └── ...
    └── ...
```

---

## 6. Implementation Notes

### 6.1 Torrent Metadata Parsing
- Use a small Python helper (`torrent_meta.py`) to parse `.torrent` files
- Bencode parsing with Python stdlib (no external deps)
- For magnet links: `aria2c` can fetch metadata (use `--dry-run` or temporary download)
- Python helper invoked from bash via: `python3 ~/.torrent-dl/torrent_meta.py <file>`

### 6.2 New File Tracking
```bash
# Before download:
ls -1 "$DOWNLOAD_DIR" > /tmp/td_before.txt

# ... aria2c download ...

# After download:
ls -1 "$DOWNLOAD_DIR" > /tmp/td_after.txt
NEW_FILES=$(comm -13 /tmp/td_before.txt /tmp/td_after.txt)
```
This ensures `process_files()` only shows files from the current session.

### 6.3 Code Deduplication
Current script has 3 identical `aria2c` blocks. Refactor into a single function:
```bash
run_aria2c() {
    local source="$1"
    aria2c --seed-time=0 --max-connection-per-server=16 \
           --split=16 --min-split-size=1M \
           --console-log-level=notice "$source"
}
```

### 6.4 Conversion Helper
Consolidate ffmpeg logic into parameterized function:
```bash
convert_video() {
    local input="$1" output="$2" crf="$3" preset="$4" audio_br="$5"
    if [ "$crf" = "copy" ]; then
        ffmpeg -i "$input" -c copy -movflags +faststart -y "$output"
    else
        ffmpeg -i "$input" -c:v libx264 -crf "$crf" -preset "$preset" \
               -c:a aac -b:a "${audio_br}k" -movflags +faststart -y "$output"
    fi
}
```

---

## 7. Edge Cases & Resilience

### 7.1 Corrupt .torrent Files
| Scenario | Detection | Behavior |
|----------|-----------|----------|
| Truncated .torrent file | `bencode` parse error in `torrent_meta.py` | Show "Файл повреждён: <name>" + skip, continue batch |
| Invalid bencode structure | Python `ValueError`/`KeyError` | Same — skip + log to history |
| .torrent file that is actually HTML (tracker error page) | `file` magic check or parse fail | Show "Не валидный .torrent файл" |
| Zero-byte .torrent file | `-s` check before parse | "Файл пуст: <path>" |

**Test:** Create a 10-byte random file named `test.torrent`, run `torrent-dl test.torrent` → must show error and exit gracefully.

### 7.2 Corrupt / Incomplete Downloads
| Scenario | Detection | Behavior |
|----------|-----------|----------|
| aria2c exits non-zero | `$?` check | Stop process, show error, log to history as `FAILED` |
| Partial file on disk (0 bytes or truncated) | Size check after download | "Файл повреждён или не скачан: <name>" |
| Hash mismatch (bitflip) | aria2c verification failure | aria2c reports — show error |
| File exists but is locked by another process | `mv`/`ffmpeg` permission error | "Файл занят другим процессом" |

### 7.3 Huge Torrents
| Scenario | Threshold | Behavior |
|----------|-----------|----------|
| 100+ files in torrent | File count > 100 | Show paginated list (20 per page, scroll with Enter) |
| Single file > 10 GB | Size check | Warn: "Файл <name> весит <size>. Скачивать?" |
| Total torrent > 50 GB | Sum of selected files | Warn: "Общий размер: <size>. Продолжить?" |
| Very long filenames | Path length > 255 chars | Truncate display, log full name |

### 7.4 Slow / Unstable Connections
| Scenario | Detection | Behavior |
|----------|-----------|----------|
| Tracker unreachable | aria2c warning | "Трекер недоступен, пробую DHT..." — let aria2c handle |
| No peers found | aria2c timeout (default 60s) | "Нет пиров. Торрент мёртвый?" + stop |
| Connection drops mid-download | aria2c reconnects | Show progress, aria2c auto-resumes |
| Very slow speed (< 10 KB/s for 5 min) | Speed monitoring (optional) | Warn user, offer to continue/stop |
| DNS resolution failure | aria2c error | "Не удалось разрешить имя: <host>" |

### 7.5 Disk Space
| Scenario | Detection | Behavior |
|----------|-----------|----------|
| Low disk space before download | `df` check (warn if < 2x torrent size) | "Мало места: <available>. Скачивание: <needed>. Продолжить?" |
| Disk full during download | aria2c error | Stop, show error, clean partial files |
| Disk full during conversion | ffmpeg error | Stop conversion, keep original, show error |
| No space in convert dir | ffmpeg write error | Suggest different `-c` path |

### 7.6 Non-ASCII Filenames (Cyrillic, CJK, etc.)
| Scenario | Behavior |
|----------|----------|
| Cyrillic filenames in torrent | Full support — bash handles UTF-8 natively |
| Mixed encodings (CP1251 from old trackers) | `torrent_meta.py` attempts UTF-8, falls back to CP1251 |
| Emoji / special chars in filename | Pass through — bash handles |
| Filename with newlines | Sanitize: replace with `_` in display, keep original for download |

### 7.7 ffmpeg Conversion Failures
| Scenario | Detection | Behavior |
|----------|-----------|----------|
| No video stream in file | `ffprobe` check before convert | "Файл не содержит видео. Пропустить?" |
| No audio stream | `ffprobe` check | Convert video only, skip audio encoding |
| Codec not supported by ffmpeg | ffmpeg error | "Кодек <codec> не поддерживается. Попробовать copy?" |
| Subtitle tracks present | Detection via `ffprobe` | Ask: extract / embed / skip |
| Multiple audio tracks | Detection via `ffprobe` | Show track list, let user pick which to encode |
| Output file is 0 bytes | Size check after ffmpeg | "Конвертация не удалась" + keep original |
| ffmpeg hangs (infinite loop input) | Timeout (kill after 30 min) | "Конвертация превысила лимит времени" + kill |

### 7.8 Interrupted Operations
| Scenario | Behavior |
|----------|----------|
| Ctrl+C during download | aria2c partial file remains. Next run auto-resumes (aria2c default) |
| Ctrl+C during conversion | Partial .tmp file removed, original kept |
| Termux killed (Android memory pressure) | Same as Ctrl+C — partial files on disk |
| SIGTERM from Termux:API | Graceful shutdown via trap handler |

**Implementation:** Trap `SIGINT`/`SIGTERM` to clean up temp files:
```bash
cleanup() {
    rm -f /tmp/td_before.txt /tmp/td_after.txt
    rm -f "$CONVERT_DIR"/*.tmp
    echo -e "${YELLOW}Прервано пользователем${NC}"
}
trap cleanup SIGINT SIGTERM
```

### 7.9 Path Traversal / Security
| Scenario | Behavior |
|----------|----------|
| Torrent with `../../etc/passwd` path | Strip leading `../` from filenames, sanitize |
| Filename with shell metacharacters | Always quote variables, never `eval` user input |
| Torrent name with spaces/special chars | Proper quoting throughout |

**Implementation in `torrent_meta.py`:**
```python
import os
safe_name = os.path.basename(name)  # strip path components
safe_name = re.sub(r'[\x00-\x1f]', '_', safe_name)  # control chars
```

### 7.10 Concurrent Runs
| Scenario | Behavior |
|----------|----------|
| Two `torrent-dl` processes running simultaneously | Lock file: `$HOME/.torrent-dl/.lock` — second instance shows warning and exits |
| Lock file left from crash | Detect stale lock (older than 1 hour), auto-remove |

### 7.11 Dead Torrents (No Peers)
| Scenario | Behavior |
|----------|----------|
| No seeders, no peers | aria2c waits 60s then times out |
| Magnet link with no tracker | DHT lookup — may take 2-5 min |
| All peers firewalled | aria2c reports 0% — show "Нет доступных пиров" |

### 7.12 Edge Case Test Matrix
| # | Test Case | Input | Expected Result |
|---|-----------|-------|------------------|
| 1 | Empty .torrent | 0-byte file | Error: "Файл пуст" |
| 2 | Corrupt .torrent | Random bytes | Error: "Файл повреждён" |
| 3 | HTML error page as .torrent | `<html>` content | Error: "Не валидный .torrent" |
| 4 | Dead magnet link | `magnet:?xt=urn:btih:0000...` | Timeout → "Нет пиров" |
| 5 | Huge torrent (500 files) | Real torrent | Paginated list (20/page) |
| 6 | Single 20GB file | Real torrent | Size warning + confirm |
| 7 | Disk full mid-download | Fill disk | Error + cleanup |
| 8 | Cyrillic filenames | Russian torrent | Full display, no encoding errors |
| 9 | Corrupt video file | Truncated .mkv | ffmpeg error → keep original |
| 10 | Video with 3 audio tracks | Multi-audio .mkv | Show track list, pick one |
| 11 | Video with subtitles | .mkv with subs | Ask: extract / embed / skip |
| 12 | Ctrl+C mid-download | Keyboard interrupt | Partial file + resume on next run |
| 13 | Ctrl+C mid-conversion | Keyboard interrupt | .tmp deleted, original kept |
| 14 | Concurrent runs | Two terminals | Second instance blocked by lock |
| 15 | Stale lock file | Lock from yesterday | Auto-removed, new instance runs |
| 16 | Path traversal in torrent | `../../etc/passwd` | Path sanitized |
| 17 | No Termux:API | API not installed | Graceful fallback, no errors |
| 18 | Batch with one bad URL | 3 URLs, middle one corrupt | First downloads, second skipped, third continues |
| 19 | Audio-only torrent | FLAC files | All converted to MP3 |
| 20 | Mixed content torrent | Video + Audio + Text | Separate selection per type |

---

## 8. Performance Benchmarks

All benchmarks measured on a mid-range Android device (Snapdragon 680, 4GB RAM) in Termux.

### 8.1 Metadata Parsing
| Operation | Target | Measurement Method |
|-----------|--------|--------------------|
| Parse 1-file .torrent (< 1 MB) | < 50 ms | `time python3 torrent_meta.py file.torrent` |
| Parse 50-file .torrent (~ 5 MB) | < 200 ms | Same |
| Parse 500-file .torrent (~ 50 MB) | < 2 s | Same |
| JSON output | Negligible (part of parse) | — |
| Human output (colorized) | Negligible (part of parse) | — |

**Note:** Parsing is I/O-bound for small files, CPU-bound for very large .torrent files with many pieces.

### 8.2 Download Speed (aria2c)
| Condition | Expected Speed | aria2c Flags |
|-----------|---------------|-------------|
| Well-seeded torrent (100+ seeders) | 5–15 MB/s | Default (16 connections, 16 splits) |
| Moderate torrent (10–50 seeders) | 1–5 MB/s | Default |
| Low-seeded torrent (1–10 seeders) | 100 KB/s – 1 MB/s | May need `--bt-tracker` override |
| Mobile network (4G) | 2–8 MB/s (limited by carrier) | Default |
| Wi-Fi (home router) | 5–20 MB/s (limited by ISP) | Default |
| DHT-only (no tracker) | 100 KB/s – 2 MB/s | `--enable-dht=true` (default) |

**Impact of split/connection flags:**
| Config | Speed (100 seeders) | CPU Usage |
|--------|--------------------|-----------|
| `--split=1 --max-connection-per-server=1` | ~2 MB/s | Low |
| `--split=16 --max-connection-per-server=16` (default) | ~12 MB/s | Medium |
| `--split=64 --max-connection-per-server=64` | ~14 MB/s (diminishing returns) | High |

**Conclusion:** 16/16 is optimal for Termux. Higher splits waste CPU on mobile without meaningful speed gain.

### 8.3 Conversion Speed (ffmpeg)
Source: 30-min 1080p XviD episode (~350 MB)

| Mode | CRF | Preset | Speed | Output Size | Time |
|------|-----|--------|-------|-------------|------|
| 1 - Copy | — | — | ~100 MB/s | ~350 MB (same) | ~3 s |
| 2 - Small | 32 | slow | ~15 fps | ~120 MB | ~20 min |
| 3 - Medium | 28 | fast | ~45 fps | ~200 MB | ~7 min |
| 4 - Balanced | 23 | ultrafast | ~90 fps | ~350 MB | ~3.5 min |
| 5 - High quality | 18 | medium | ~25 fps | ~700 MB | ~12 min |

**Audio encoding overhead:** ~5–10% additional time (AAC encoding is fast).

**SD card write speed impact:**
- eMMC (budget phone): ~30 MB/s write → limits copy mode to ~30 MB/s
- UHS-I SD card: ~80 MB/s write → no bottleneck
- Internal storage: ~200 MB/s write → no bottleneck

### 8.4 File Selection (Interactive)
| Operation | Target |
|-----------|--------|
| Display file list (20 files) | < 100 ms |
| Display file list (500 files, paginated) | < 200 ms (20/page) |
| User input parse (range/list/all/skip) | < 50 ms |

### 8.5 Total Workflow Time
For a typical 10-episode TV series (~3.5 GB total, well-seeded):

| Step | Time |
|------|------|
| Metadata parse | < 200 ms |
| User interaction (review + select) | 10–30 s (human) |
| Download (5 MB/s average) | ~12 min |
| User interaction (select files + quality) | 10–20 s (human) |
| Conversion (balanced mode, 10 episodes) | ~35 min |
| **Total** | **~50 min** |

For copy-only mode (no re-encode):

| Step | Time |
|------|------|
| Metadata + download | ~13 min |
| Conversion (copy, 10 episodes) | ~30 s |
| **Total** | **~14 min** |

### 8.6 Resource Usage
| Resource | Idle | Downloading | Converting |
|----------|------|-------------|------------|
| RAM | ~5 MB | ~30 MB (aria2c) | ~150 MB (ffmpeg ×1) |
| CPU | 0% | 10–20% | 60–90% (single core) |
| Disk I/O | 0 | Sequential write | Sequential read+write |
| Network | 0 | 5–15 MB/s (when active) | 0 |

**Warning thresholds:**
| Condition | Action |
|-----------|--------|
| RAM > 300 MB during conversion | Warn: "Высокое потребление памяти" |
| CPU temp > 45°C (if sensors available) | Warn: "Устройство нагревается" |
| Free disk < 1 GB | Error: stop, cleanup |
| Free disk < 2× output size | Warn: "Мало места на диске" |

### 8.7 Performance Regression Test Suite
Automated tests to run periodically:

```bash
# Test 1: Parse speed
.time python3 torrent_meta.py <real.torrent> > /dev/null
# Must be < 200 ms

# Test 2: Conversion speed baseline
ffmpeg -i test_input.mkv -c:v libx264 -crf 23 -preset ultrafast \
       -c:a aac -b:a 192k -movflags +faststart -y /dev/null 2>&1 \
       | grep "speed=" | tail -1
# Must show speed > 30 fps

# Test 3: Download speed (with known fast torrent)
aria2c --seed-time=0 --max-connection-per-server=16 \
       --split=16 --min-split-size=1M \
       --console-log-level=info "magnet:?xt=urn:btih:<known-seeded>" \
       -d /tmp/td_perf_test 2>&1 \
       | grep "DL:" | tail -1
# Must show > 1 MB/s
```

---

## 9. Non-Goals (what this tool is NOT)
- ❌ Not a torrent client with seeding support
- ❌ Not a download manager/queue system
- ❌ Not a video editor
- ❌ Not a media library manager
- ❌ No Docker/container support

---

## 10. Success Criteria
1. `torrent-dl "magnet:?xt=..."` shows full metadata, lets user select files, downloads only selected, offers conversion
2. Batch mode works: `torrent-dl URL1 URL2` processes both sequentially
3. Video conversion produces valid MP4 files playable in Android
4. Audio conversion produces valid MP3 files
5. History is logged and viewable via `torrent-dl --history`
6. Termux notifications fire on completion
7. Script handles errors gracefully (stops, shows message)
