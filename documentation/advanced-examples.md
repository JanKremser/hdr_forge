# Advanced Examples

This document provides comprehensive examples for complex encoding scenarios with HDR Forge.

## Table of Contents

- [Hardware Acceleration](#hardware-acceleration)
- [AV1 Encoding](#av1-encoding)
- [Audio Encoding](#audio-encoding)
- [Subtitle Management](#subtitle-management)
- [edit Subcommand](#edit-subcommand)
- [Encoding Presets](#encoding-presets)
- [Cropping Examples](#cropping-examples)
- [Grain Analysis](#grain-analysis)
- [Scaling Examples](#scaling-examples)
- [Video Sampling](#video-sampling)
- [HDR Metadata Injection](#hdr-metadata-injection)
- [Dolby Vision](#dolby-vision)
- [Combined Complex Workflows](#combined-complex-workflows)
- [Batch Processing](#batch-processing)
- [Quality Optimization](#quality-optimization)

## Hardware Acceleration

### Basic GPU Encoding

```bash
# Use NVIDIA NVENC HEVC encoder explicitly
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# GPU encoding with balanced preset
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# GPU encoding with quality focus
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality
```

### H.264 NVENC for Maximum Compatibility

```bash
# H.264 NVENC with default settings
hdr_forge convert -i input.mkv -o output.mkv --encoder h264_nvenc

# H.264 NVENC with high quality
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder h264_nvenc \
  --hw-preset gpu:quality
```

### CPU vs GPU Comparison

```bash
# CPU encoding (maximum quality)
hdr_forge convert -i input.mkv -o cpu_output.mkv \
  --hw-preset cpu:quality

# GPU encoding (fast)
hdr_forge convert -i input.mkv -o gpu_output.mkv \
  --hw-preset gpu:balanced

# Compare file sizes and quality
ls -lh *_output.mkv
```

## AV1 Encoding

### Basic AV1 Encoding

```bash
# Basic AV1 encoding with default settings
hdr_forge convert -i input.mkv -o output_av1.mkv --encoder libsvtav1

# AV1 with custom quality (lower = better quality)
hdr_forge convert -i input.mkv -o output_av1.mkv \
  --encoder libsvtav1 \
  --quality 23

# High-quality AV1 for archival
hdr_forge convert -i input.mkv -o archive_av1.mkv \
  --encoder libsvtav1 \
  --quality 18
```

### AV1 for Different Resolutions

```bash
# 4K AV1 encoding
hdr_forge convert -i 4k_video.mkv -o 4k_av1.mkv \
  --encoder libsvtav1 \
  --quality 25

# 1080p AV1 encoding
hdr_forge convert -i 1080p_video.mkv -o 1080p_av1.mkv \
  --encoder libsvtav1 \
  --quality 23

# 4K to 1080p with AV1
hdr_forge convert -i 4k_video.mkv -o 1080p_av1.mkv \
  --encoder libsvtav1 \
  --scale FHD \
  --quality 23
```

### AV1 with HDR Input

AV1 supports both HDR10 and SDR encoding:

```bash
# HDR10 to HDR10 with AV1 (stream metadata)
hdr_forge convert -i hdr10_video.mkv -o hdr10_av1.mkv \
  --encoder libsvtav1 \
  --quality 23

# Convert HDR10 to SDR with AV1 (tone mapping)
hdr_forge convert -i hdr10_video.mkv -o sdr_av1.mkv \
  --encoder libsvtav1 \
  --hdr-sdr-format sdr \
  --quality 23

# Dolby Vision to HDR10 with AV1
hdr_forge convert -i dolby_vision.mkv -o hdr10_av1.mkv \
  --encoder libsvtav1 \
  --hdr-sdr-format hdr10

# Dolby Vision to SDR with AV1
hdr_forge convert -i dolby_vision.mkv -o sdr_av1.mkv \
  --encoder libsvtav1 \
  --hdr-sdr-format sdr
```

**Note:** AV1 HDR10 support uses stream metadata flags (Site Data). Dolby Vision encoding not supported.

### AV1 Comparison with HEVC

```bash
# Encode with both codecs for comparison
hdr_forge convert -i input.mkv -o output_hevc.mkv --encoder libx265
hdr_forge convert -i input.mkv -o output_av1.mkv --encoder libsvtav1

# Compare file sizes (AV1 typically 20-40% smaller)
ls -lh output_hevc.mkv output_av1.mkv
```

### AV1 for Streaming

```bash
# AV1 optimized for YouTube/streaming platforms
hdr_forge convert -i input.mkv -o stream_av1.mkv \
  --encoder libsvtav1 \
  --quality 25 \
  --crop auto

# Batch convert for streaming platform
hdr_forge convert -i ./videos -o ./av1_streams \
  --encoder libsvtav1 \
  --quality 25 \
  --scale FHD
```

**Note:** AV1 encoding is significantly slower than HEVC but produces smaller files. Use AV1 when:
- File size is critical (storage/bandwidth constraints)
- Encoding time is not a constraint
- Targeting modern platforms (YouTube, Netflix, etc.)
- Creating long-term archival copies (SDR and HDR10)

**Current Limitations:** AV1 HDR10 support uses stream metadata flags only. Dolby Vision encoding not supported.

## Audio Encoding

Audio tracks can be selectively encoded, removed, or converted using per-track targeting.

### Per-Language Audio Encoding

```bash
# Convert German audio to AAC, keep English as-is
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "ger:aac;eng:copy"

# Convert all German tracks to FLAC, remove others
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "ger:flac;*:remove"

# Audio priority: German AAC, English AC3, fallback FLAC
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "ger:aac;eng:ac3;*:flac"
```

### Per-Track ID Audio Encoding

```bash
# Encode by track ID
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "1:aac;2:ac3;3:remove"

# Keep only tracks 1 and 2, remove the rest
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "1:copy;2:copy;*:remove"
```

### Format Conversion

```bash
# Convert DTS to AAC globally
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "dts>aac"

# Language-specific format conversion
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "eng:dts>aac;ger:copy;*:ac3"

# Remove DTS tracks specifically
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "dts:remove;*:copy"
```

### Setting Default Audio Track

```bash
# Set German as default
hdr_forge convert -i input.mkv -o output.mkv --audio-default ger

# Set English as default
hdr_forge convert -i input.mkv -o output.mkv --audio-default eng

# Set track 2 as default
hdr_forge convert -i input.mkv -o output.mkv --audio-default 2
```

**Supported Codecs:** `copy`, `remove`, `aac`, `ac3`, `eac3`, `flac`

## Subtitle Management

Intelligently manage subtitle tracks with auto-detection of special types.

### Auto-Detection Mode

```bash
# Auto-detect forced, SDH, and commentary tracks
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags auto

# Auto-detect with German preference
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags auto>ger

# Auto-detect with English preference
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags auto>eng
```

### Manual Subtitle Management

```bash
# Copy all subtitles (default behavior)
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags copy

# Remove all subtitles
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags remove
```

### Common Workflows

```bash
# Film with forced subtitles and English SDH
hdr_forge convert -i input.mkv -o output.mkv \
  --subtitle-flags auto>eng \
  --audio-codec "eng:copy"

# Anime with German and English subtitles
hdr_forge convert -i input.mkv -o output.mkv \
  --subtitle-flags auto \
  --audio-codec "ger:aac;eng:ac3"

# Remove Japanese audio, keep English subtitles only
hdr_forge convert -i input.mkv -o output.mkv \
  --audio-codec "jpn:remove;eng:copy;*:remove" \
  --subtitle-flags auto>eng
```

**Supported Modes:** `copy`, `remove`, `auto`, `auto>LANG` (e.g., `auto>ger`, `auto>eng`, `auto>jpn`)

**Note:** Some players (particularly VLC) may have rendering issues with FFmpeg-set subtitle titles.

## edit Subcommand

In-place MKV editing without re-encoding using `mkvpropedit`.

### Auto Subtitle Detection

Auto-detect subtitle track flags (forced, SDH, commentary) and set default track by language:

```bash
# Auto-detect and set default subtitle track
hdr_forge edit -i movie.mkv --subtitle-flags auto

# Auto-detect with German as preferred default language
hdr_forge edit -i movie.mkv --subtitle-flags auto>ger

# Auto-detect with English preference
hdr_forge edit -i movie.mkv --subtitle-flags auto>eng

# Auto-detect with multiple language priority
hdr_forge edit -i movie.mkv --subtitle-flags auto>ger,eng
```

### Per-Track ID and Language Overrides

```bash
# Force specific track IDs to default
hdr_forge edit -i movie.mkv --subtitle-flags "1:default"

# Set language-specific flags
hdr_forge edit -i movie.mkv --subtitle-flags "ger:default;eng:forced"

# Explicit copy (no changes to subtitle flags)
hdr_forge edit -i movie.mkv --subtitle-flags copy
```

### When to Use edit vs convert

```bash
# Use edit when you only need to fix subtitle/audio track flags — no quality loss, very fast
hdr_forge edit -i movie.mkv --subtitle-flags auto

# Use convert when you also need to re-encode or when track removal is required
# (edit cannot remove tracks — would require remux)
hdr_forge convert -i movie.mkv -o output.mkv --subtitle-flags remove

# Use convert for combined operations (re-encode + subtitle fixes)
hdr_forge convert -i movie.mkv -o output.mkv \
  --encoder libx265 \
  --subtitle-flags auto
```

**Requirements:** `mkvpropedit` (part of MKVToolNix) must be in system PATH or `lib/` directory

## Encoding Presets

### Content-Aware Presets

```bash
# Film content with high quality
hdr_forge convert -i film.mkv -o output.mkv \
  --preset film \
  --hw-preset cpu:quality

# Action content with fast motion
hdr_forge convert -i action_movie.mkv -o output.mkv \
  --preset action \
  --quality 16

# Animation with vibrant colors
hdr_forge convert -i anime.mkv -o output.mkv \
  --preset animation \
  --grain auto
```

### Preset Combinations

```bash
# Film + CPU quality + grain analysis
hdr_forge convert -i old_film.mkv -o output.mkv \
  --preset film \
  --hw-preset cpu:quality \
  --grain auto \
  --crop auto

# Action + GPU fast encoding
hdr_forge convert -i action.mkv -o output.mkv \
  --preset action \
  --hw-preset gpu:balanced \
  --scale FHD

# Animation + custom quality
hdr_forge convert -i animation.mkv -o output.mkv \
  --preset animation \
  --quality 15 \
  --crop off
```

## Cropping Examples

### Automatic Cropping

```bash
# Basic automatic black bar detection
hdr_forge convert -i input.mkv -o output.mkv --crop auto

# Auto crop with GPU encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --crop auto \
  --encoder hevc_nvenc

# Auto crop with scaling
hdr_forge convert -i 4k_video.mkv -o output.mkv \
  --crop auto \
  --scale FHD
```

### Manual Cropping

```bash
# Manual crop with specific dimensions
# Format: width:height:x:y (based on original video)
hdr_forge convert -i input.mkv -o output.mkv \
  --crop 1920:804:0:138

# Crop letterbox format (2.35:1)
hdr_forge convert -i input.mkv -o output.mkv \
  --crop 1920:817:0:131

# Crop for IMAX (1.43:1)
hdr_forge convert -i input.mkv -o output.mkv \
  --crop 1440:1080:240:0
```

### Aspect Ratio Cropping

```bash
# Crop to 16:9 (standard widescreen)
hdr_forge convert -i input.mkv -o output.mkv --crop 16:9

# Crop to 21:9 (ultra-wide)
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# Crop to 4:3 (classic)
hdr_forge convert -i input.mkv -o output.mkv --crop 4:3

# Crop to 2.39:1 (CinemaScope)
hdr_forge convert -i input.mkv -o output.mkv --crop 2.39:1
```

### CinemaScope Presets

```bash
# CinemaScope Classic (2.35:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema

# CinemaScope Modern (2.39:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema-modern

# With scaling
hdr_forge convert -i 4k_movie.mkv -o output.mkv \
  --crop cinema-modern \
  --scale FHD
```

### Combining Crop with Other Features

```bash
# Crop + scale + quality
hdr_forge convert -i input.mkv -o output.mkv \
  --crop auto \
  --scale FHD \
  --quality 16

# Crop + grain + film preset
hdr_forge convert -i old_film.mkv -o output.mkv \
  --crop auto \
  --grain cat2 \
  --preset film
```

## Grain Analysis

### Automatic Grain Detection

```bash
# Basic auto grain detection
hdr_forge convert -i old_film.mkv -o output.mkv --grain auto

# Auto grain with CPU quality
hdr_forge convert -i film.mkv -o output.mkv \
  --grain auto \
  --hw-preset cpu:quality

# Auto grain with film preset
hdr_forge convert -i film.mkv -o output.mkv \
  --grain auto \
  --preset film
```

### Manual Grain Categories

```bash
# Light grain (cat1)
hdr_forge convert -i input.mkv -o output.mkv \
  --grain cat1 \
  --quality 17

# Medium grain (cat2)
hdr_forge convert -i grainy_film.mkv -o output.mkv \
  --grain cat2 \
  --hw-preset cpu:quality

# Heavy grain (cat3)
hdr_forge convert -i very_grainy.mkv -o output.mkv \
  --grain cat3 \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"
```

### Grain with Different Content Types

```bash
# Old film restoration
hdr_forge convert -i old_film.mkv -o restored.mkv \
  --grain cat3 \
  --preset film \
  --crop auto \
  --quality 14

# Documentary with moderate grain
hdr_forge convert -i documentary.mkv -o output.mkv \
  --grain cat2 \
  --hw-preset cpu:balanced

# Modern film with slight grain
hdr_forge convert -i modern_film.mkv -o output.mkv \
  --grain cat1 \
  --preset film
```

## Scaling Examples

### Named Resolutions

```bash
# 4K to 1080p (Full HD)
hdr_forge convert -i 4k_video.mkv -o 1080p.mkv --scale FHD

# 4K to 720p (HD)
hdr_forge convert -i 4k_video.mkv -o 720p.mkv --scale HD

# 1080p to 720p
hdr_forge convert -i 1080p_video.mkv -o 720p.mkv --scale HD

# 8K to 4K
hdr_forge convert -i 8k_video.mkv -o 4k.mkv --scale UHD
```

### Numeric Height

```bash
# Scale to exact height (1080p)
hdr_forge convert -i input.mkv -o output.mkv --scale 1080

# Scale to 1440p
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale 1440

# Scale to custom height (900p)
hdr_forge convert -i input.mkv -o output.mkv --scale 900
```

### Height vs Adaptive Mode

```bash
# Height mode (default): Fixed height, width calculated
hdr_forge convert -i input.mkv -o output.mkv \
  --scale 1080 \
  --scale-mode height

# Adaptive mode: Fits within bounds, maintains aspect ratio
hdr_forge convert -i input.mkv -o output.mkv \
  --scale 1920 \
  --scale-mode adaptive

# Adaptive with named resolution
hdr_forge convert -i input.mkv -o output.mkv \
  --scale FHD \
  --scale-mode adaptive
```

### Scaling with Crop

```bash
# Crop then scale (order is important)
hdr_forge convert -i 4k_letterbox.mkv -o output.mkv \
  --crop auto \
  --scale FHD

# Manual crop with scale
hdr_forge convert -i input.mkv -o output.mkv \
  --crop 1920:800:0:140 \
  --scale 1080

# Aspect ratio crop with scale
hdr_forge convert -i input.mkv -o output.mkv \
  --crop 21:9 \
  --scale FHD \
  --scale-mode adaptive
```

## Video Sampling

### Automatic Samples

```bash
# Default sample (30s at 1:00)
hdr_forge convert -i large_file.mkv -o sample.mkv --sample auto

# Sample with GPU for speed
hdr_forge convert -i input.mkv -o sample.mkv \
  --sample auto \
  --encoder hevc_nvenc

# Sample with all settings
hdr_forge convert -i input.mkv -o sample.mkv \
  --sample auto \
  --crop auto \
  --scale FHD \
  --grain auto
```

### Custom Time Ranges

```bash
# Sample from 1:00 to 1:30 (60-90 seconds)
hdr_forge convert -i input.mkv -o sample.mkv --sample 60:90

# Sample from 2:00 to 2:30
hdr_forge convert -i input.mkv -o sample.mkv --sample 120:150

# Sample first 30 seconds
hdr_forge convert -i input.mkv -o sample.mkv --sample 0:30

# Sample last minute (if video is 3600s long)
hdr_forge convert -i input.mkv -o sample.mkv --sample 3540:3600
```

### Testing Workflows

```bash
# Test grain settings
hdr_forge convert -i film.mkv -o test_grain.mkv \
  --sample 60:90 \
  --grain cat2 \
  --encoder hevc_nvenc

# Test crop settings
hdr_forge convert -i input.mkv -o test_crop.mkv \
  --sample auto \
  --crop auto

# Test quality settings
hdr_forge convert -i input.mkv -o test_q14.mkv \
  --sample auto \
  --quality 14

hdr_forge convert -i input.mkv -o test_q18.mkv \
  --sample auto \
  --quality 18

# Compare results
ls -lh test_*.mkv
```

### Sample Multiple Scenes

```bash
# Sample opening scene (0-30s)
hdr_forge convert -i movie.mkv -o sample_opening.mkv --sample 0:30

# Sample action scene (around 30 minutes in)
hdr_forge convert -i movie.mkv -o sample_action.mkv --sample 1800:1830

# Sample ending scene
hdr_forge convert -i movie.mkv -o sample_ending.mkv --sample 7170:7200
```

## Metadata Management

### Extract Metadata

```bash
# Extract all metadata (Dolby Vision, HDR10, HDR10+)
hdr_forge extract-metadata -i video.mkv -o ./metadata_output

# Extract from Dolby Vision source
hdr_forge extract-metadata -i dolby_vision.mkv -o ./dv_metadata
```

### Inject HDR10 Metadata

```bash
# Inject HDR10 metadata JSON
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --hdr10 metadata_hdr10.json

# Inject HDR10+ metadata
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --hdr10plus metadata_hdr10plus.json
```

### Inject Dolby Vision Metadata

```bash
# Inject RPU only
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --rpu dolby_vision.rpu

# Inject RPU with Enhancement Layer (Profile 7)
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --rpu dolby_vision.rpu \
  --el enhancement_layer.hevc

# Inject multiple metadata types
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --rpu dolby_vision.rpu \
  --hdr10 metadata_hdr10.json
```

### Metadata During Encoding

**Note:** Use `--master-display` and `--max-cll` during encoding for CPU encoders only.

```bash
# Inject metadata while encoding (libx265/libx264 only)
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# With quality settings
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --quality 16 \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

### Workflow: Extract and Re-inject

```bash
# 1. Extract metadata from source
hdr_forge extract-metadata -i source_with_metadata.mkv -o ./metadata

# 2. Encode without metadata
hdr_forge convert -i source_with_metadata.mkv -o encoded.mkv

# 3. Re-inject extracted metadata
hdr_forge inject-metadata -i encoded.mkv -o final.mkv \
  --hdr10 ./metadata/hdr10_metadata.json
```

## Dolby Vision

### Profile Preservation

```bash
# Preserve Dolby Vision (re-encode base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop off

# With custom quality
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --crop off \
  --quality 14 \
  --hw-preset cpu:quality
```

### Profile Conversion

```bash
# Convert to Profile 8.1 with re-encoding
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --dv-profile 8 \
  --crop off \
  --quality 16

# Fast profile conversion without re-encoding
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --video-codec copy \
  --dv-profile 8
```

### DV to HDR10

```bash
# Extract HDR10 base layer with re-encoding
hdr_forge convert -i dolby_vision.mkv -o hdr10.mkv \
  --hdr-sdr-format hdr10

# With crop and scale (supported when converting to HDR10)
hdr_forge convert -i dolby_vision.mkv -o hdr10_1080p.mkv \
  --hdr-sdr-format hdr10 \
  --crop auto \
  --scale FHD

# Fast extraction without re-encoding
hdr_forge convert -i dolby_vision.mkv -o hdr10.mkv \
  --video-codec copy \
  --hdr-sdr-format hdr10
```

### DV to SDR

```bash
# Convert to SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o sdr.mkv \
  --hdr-sdr-format sdr

# With crop and scale
hdr_forge convert -i dolby_vision.mkv -o sdr_720p.mkv \
  --hdr-sdr-format sdr \
  --crop auto \
  --scale HD

# Fast GPU conversion
hdr_forge convert -i dolby_vision.mkv -o sdr.mkv \
  --hdr-sdr-format sdr \
  --encoder hevc_nvenc
```

### DV with Auto Crop (RPU L5 Offsets)

Auto crop reads L5 Active Area offsets from RPU metadata — no cropdetect scan required:

```bash
# Auto crop from RPU L5 offsets (default behavior)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop auto

# Verify crop detected with info command
hdr_forge info -i dolby_vision.mkv  # shows "RPU Crop" if offsets present

# Combine with quality settings
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --crop auto \
  --quality 14 \
  --hw-preset cpu:quality

# Note: Manual and ratio crop modes are NOT supported for DV
# hdr_forge convert -i dv.mkv -o output.mkv --crop 1920:800:0:140  ← ERROR
# hdr_forge convert -i dv.mkv -o output.mkv --crop 21:9             ← ERROR
```

**Workaround for manual crop with DV:** Convert to HDR10 first:
```bash
hdr_forge convert -i dolby_vision.mkv -o hdr10_temp.mkv --hdr-sdr-format hdr10
hdr_forge convert -i hdr10_temp.mkv -o final.mkv --crop 1920:800:0:140
```

### Profile 5 Conversion

Profile 5 (IPTPQc2) uses a non-standard color space and requires full re-encoding with libplacebo:

```bash
# Profile 5 → Profile 8.1 (requires Vulkan GPU driver and FFmpeg libplacebo)
hdr_forge convert -i profile5_dv.mkv -o output_p81.mkv --dv-profile 8

# Profile 5 → HDR10 (extract base layer with re-encode)
hdr_forge convert -i profile5_dv.mkv -o output_hdr10.mkv --hdr-sdr-format hdr10

# Profile 5 → SDR (full tone mapping)
hdr_forge convert -i profile5_dv.mkv -o output_sdr.mkv --hdr-sdr-format sdr

# With quality settings
hdr_forge convert -i profile5_dv.mkv -o output_p81_1080p.mkv \
  --dv-profile 8 \
  --quality 15
```

**Note:** Copy mode is not available for Profile 5 sources (requires re-encoding).
**Requirements:** FFmpeg compiled with `--enable-libplacebo`, Vulkan-capable GPU.

### Batch DV Processing

```bash
# Convert entire DV library to HDR10
hdr_forge convert -i ./dv_collection -o ./hdr10_collection \
  --hdr-sdr-format hdr10 \
  --scale FHD

# Convert DV library to SDR
hdr_forge convert -i ./dv_collection -o ./sdr_collection \
  --hdr-sdr-format sdr \
  --crop auto
```

## Combined Complex Workflows

### Maximum Quality Archival

```bash
# 4K to 1080p with maximum quality
hdr_forge convert -i 4k_film.mkv -o archive.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain" \
  --crop auto \
  --scale FHD \
  --grain cat2

# With custom metadata
hdr_forge convert -i 4k_film.mkv -o archive.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain" \
  --crop auto \
  --scale FHD \
  --grain cat2 \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

### Fast Batch Processing

```bash
# GPU batch conversion with auto settings
hdr_forge convert -i ./4k_videos -o ./1080p_encoded \
  --encoder hevc_nvenc \
  --hw-preset gpu:balanced \
  --crop auto \
  --scale FHD

# With grain optimization
hdr_forge convert -i ./videos -o ./encoded \
  --encoder hevc_nvenc \
  --hw-preset gpu:quality \
  --grain auto \
  --crop auto
```

### Film Restoration Workflow

```bash
# Old film with heavy grain
hdr_forge convert -i old_film.mkv -o restored.mkv \
  --preset film \
  --grain cat3 \
  --crop auto \
  --quality 13 \
  --hw-preset cpu:quality

# Test sample first
hdr_forge convert -i old_film.mkv -o test_sample.mkv \
  --sample 60:90 \
  --preset film \
  --grain cat3 \
  --quality 13 \
  --encoder hevc_nvenc
```

### Action Content Optimization

```bash
# Action movie with fast motion
hdr_forge convert -i action_movie.mkv -o output.mkv \
  --preset action \
  --quality 14 \
  --crop cinema-modern \
  --scale FHD

# With GPU acceleration
hdr_forge convert -i action_movie.mkv -o output.mkv \
  --preset action \
  --encoder hevc_nvenc \
  --hw-preset gpu:quality \
  --crop cinema-modern
```

### Animation Workflow

```bash
# Anime with vibrant colors
hdr_forge convert -i anime.mkv -o output.mkv \
  --preset animation \
  --quality 16 \
  --crop auto \
  --scale FHD

# With grain analysis
hdr_forge convert -i anime.mkv -o output.mkv \
  --preset animation \
  --grain auto \
  --hw-preset cpu:balanced
```

### Multi-Format Output

```bash
# Create multiple versions from one source

# 4K HDR10 archival
hdr_forge convert -i source.mkv -o 4k_hdr.mkv \
  --hw-preset cpu:quality \
  --crop auto

# 1080p HDR10 for streaming
hdr_forge convert -i source.mkv -o 1080p_hdr.mkv \
  --scale FHD \
  --hw-preset cpu:balanced \
  --crop auto

# 1080p SDR for compatibility
hdr_forge convert -i source.mkv -o 1080p_sdr.mkv \
  --hdr-sdr-format sdr \
  --scale FHD \
  --crop auto \
  --encoder hevc_nvenc

# 720p H.264 for maximum compatibility
hdr_forge convert -i source.mkv -o 720p_h264.mkv \
  --hdr-sdr-format sdr \
  --scale HD \
  --encoder h264_nvenc \
  --crop auto
```

## Batch Processing

### Basic Batch

```bash
# Convert all videos in folder
hdr_forge convert -i ./input_folder -o ./output_folder

# With specific settings
hdr_forge convert -i ./videos -o ./encoded \
  --hw-preset cpu:balanced \
  --crop auto
```

### Resolution-Specific Batches

```bash
# Batch 4K to 1080p
hdr_forge convert -i ./4k_videos -o ./1080p_videos \
  --scale FHD \
  --hw-preset gpu:balanced \
  --crop auto

# Batch HDR to SDR
hdr_forge convert -i ./hdr_videos -o ./sdr_videos \
  --hdr-sdr-format sdr \
  --crop auto
```

### Content-Type Batches

```bash
# Batch films
hdr_forge convert -i ./films -o ./encoded_films \
  --preset film \
  --grain auto \
  --crop auto

# Batch action content
hdr_forge convert -i ./action_movies -o ./encoded_action \
  --preset action \
  --hw-preset gpu:balanced

# Batch animation
hdr_forge convert -i ./anime -o ./encoded_anime \
  --preset animation \
  --quality 16
```

## Quality Optimization

### Testing Different Quality Settings

```bash
# Create samples with different CRF values
hdr_forge convert -i input.mkv -o sample_crf12.mkv --sample auto --quality 12
hdr_forge convert -i input.mkv -o sample_crf14.mkv --sample auto --quality 14
hdr_forge convert -i input.mkv -o sample_crf16.mkv --sample auto --quality 16
hdr_forge convert -i input.mkv -o sample_crf18.mkv --sample auto --quality 18
hdr_forge convert -i input.mkv -o sample_crf20.mkv --sample auto --quality 20

# Compare file sizes
ls -lh sample_*.mkv

# Find optimal quality
# View samples and choose best quality/size trade-off
```

### Preset Testing

```bash
# Test different speed presets (CPU)
hdr_forge convert -i input.mkv -o test_fast.mkv --sample auto --speed fast
hdr_forge convert -i input.mkv -o test_medium.mkv --sample auto --speed medium
hdr_forge convert -i input.mkv -o test_slow.mkv --sample auto --speed slow

# Test hardware presets
hdr_forge convert -i input.mkv -o test_cpu_bal.mkv --sample auto --hw-preset cpu:balanced
hdr_forge convert -i input.mkv -o test_cpu_qual.mkv --sample auto --hw-preset cpu:quality
hdr_forge convert -i input.mkv -o test_gpu_bal.mkv --sample auto --hw-preset gpu:balanced
hdr_forge convert -i input.mkv -o test_gpu_qual.mkv --sample auto --hw-preset gpu:quality
```

### Content-Type Optimization

```bash
# Film with grain optimization
hdr_forge convert -i film.mkv -o optimized_film.mkv \
  --preset film \
  --grain auto \
  --hw-preset cpu:quality \
  --crop auto

# Action with motion optimization
hdr_forge convert -i action.mkv -o optimized_action.mkv \
  --preset action \
  --quality 14 \
  --hw-preset gpu:quality

# Animation with color optimization
hdr_forge convert -i anime.mkv -o optimized_anime.mkv \
  --preset animation \
  --quality 16 \
  --crop off
```

## See Also

-   [Encoder Guide](encoders.md) - Detailed encoder information
-   [Technical Details](technical-details.md) - In-depth technical information
-   [Troubleshooting](troubleshooting.md) - Common issues and solutions
