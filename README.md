# HDR Forge - SDR/HDR10/HDR10+/DolbyVision Video Converter

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for converting video files with hardware-accelerated encoding (NVIDIA NVENC), intelligent HDR metadata preservation, automatic quality optimization, grain analysis, flexible cropping, and advanced format conversion (H.264, H.265/HEVC, AV1, Dolby Vision).

## Features

-   **Multiple Encoder Support:** CPU (libx265, libx264, libsvtav1) and GPU-accelerated encoding (NVIDIA NVENC)
-   **AV1 Encoding:** Next-generation codec with superior compression, HDR10 pass-through via stream metadata (SiteData)
-   **Hardware Acceleration:** NVIDIA NVENC support for H.265/HEVC and H.264 encoding
-   **Multiple Format Support:** Convert between Dolby Vision, HDR/HDR10, and SDR formats
-   **Format Conversion:** DV → HDR/HDR10 → SDR with tone mapping support
-   **Dolby Vision Profiles:** Support for Profiles 5, 7 (with EL), and 8.1 (Profile 5 re-encoding with libplacebo)
-   **DV Crop (Auto):** Reads RPU L5 Active Area offsets — no black bar scan needed
-   **HDR Metadata Injection:** Add or update HDR10/HDR10+/Dolby Vision metadata without re-encoding
-   **Advanced Cropping:** Automatic black bar detection, manual cropping, aspect ratio presets
-   **Flexible Scaling:** Height-based and adaptive scaling modes
-   **Grain Analysis:** Automatic grain detection with encoding optimization
-   **Content-Aware Presets:** Film, banding, video, action, and animation-optimized encoding profiles
-   **Logo Removal:** Automatic logo detection and removal with multiple algorithms (delogo, mask)
-   **Hardware Presets:** CPU/GPU-specific encoding presets (balanced, quality)
-   **Video Sampling:** Test encoding settings on short video samples
-   **Intelligent Quality Control:** Resolution and content-based auto-optimization
-   **Batch Processing:** Convert entire folders with one command
-   **Real-time Progress:** Live encoding progress with ETA and statistics

All videos are converted with compression settings dynamically adjusted based on resolution, content type, and grain. Settings can be customized using various CLI parameters.

## Quick Start

```bash
# Show video information
hdr_forge info -i video.mkv

# Basic conversion (auto settings)
hdr_forge convert -i input.mkv -o output.mkv

# GPU-accelerated conversion (NVIDIA NVENC)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# High-quality CPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# AV1 encoding (next-generation codec)
hdr_forge convert -i input.mkv -o output.mkv -v av1

# In-place subtitle editing (no re-encode)
hdr_forge edit -i video.mkv --subtitle-flags auto

# Launch GUI
hdr_forge_ui

# Convert Dolby Vision to HDR10
hdr_forge convert -i dv.mkv -o output.mkv --hdr-sdr-format hdr10

# Inject metadata without re-encoding
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --hdr10 metadata_hdr10.json
```

## Documentation

- **[Encoder Guide](documentation/encoders.md)** - Comprehensive encoder information (libx265, libx264, libsvtav1, NVENC)
- **[Advanced Examples](documentation/advanced-examples.md)** - Complex encoding workflows and examples
- **[Technical Details](documentation/technical-details.md)** - In-depth technical information
- **[Troubleshooting](documentation/troubleshooting.md)** - Solutions to common problems

## Version History

| Version | Highlights |
|---------|-----------|
| **1.1.0** | DV auto crop via L5 offsets, Profile 5→8.1 re-encoding with libplacebo, `edit` subcommand for in-place MKV editing, GTK4 Adwaita-themed GUI |
| **1.0.0** | AV1 encoding (libsvtav1), audio/subtitle management, logo removal, batch processing |
| **0.7.x** | HDR metadata injection, DV profile support, audio/subtitle management, logo detection |
| **0.4.0** | Python rewrite with NVENC, multiple encoders, advanced cropping/scaling, grain analysis |
-   Video sampling for testing
-   Enhanced CLI with comprehensive parameter support

## Installation

### Requirements

#### Software Requirements (Mandatory)

-   **Python 3.13 or higher**
-   **[ffmpeg / ffprobe](https://ffmpeg.org/download.html)** with libx265, libx264, or libsvtav1 support

#### Hardware Acceleration (Optional)

-   **NVIDIA GPU** with NVENC support (GTX 1050 or newer)
    -   FFmpeg compiled with NVENC support
    -   Recent NVIDIA drivers (recommended: 470+ for Linux, 472+ for Windows)

**See [Encoder Guide](documentation/encoders.md) for detailed hardware requirements and setup.**

#### Optional Tools for Advanced Features

**Important:** All external tools must be either:
1. Available globally in system PATH, OR
2. Located in the `lib/` directory next to the HDR Forge executable/project

**For Dolby Vision:**

-   **[dovi_tool](https://github.com/quietvoid/dovi_tool)** - RPU/EL extraction and injection
    -   **Arch Linux:** `sudo pacman -S dovi-tool`
    -   **Others:** Download from releases and place in:
        -   System PATH (recommended), OR
        -   `lib/` directory in project root

**For HDR10 Metadata:**

-   **[hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor)** - HDR10 metadata injection tool
    -   Download from releases and place in:
        -   System PATH (recommended), OR
        -   `lib/` directory in project root

**For HDR10+ Metadata:**

-   **[hdr10plus_tool](https://github.com/quietvoid/hdr10plus_tool)** - HDR10+ metadata extraction and injection
    -   **Arch Linux:** `sudo pacman -S hdr10plus-tool`
    -   **Others:** Download from releases and place in:
        -   System PATH (recommended), OR
        -   `lib/` directory in project root

**For Container Operations:**

-   **[mkvmerge](https://mkvtoolnix.download/)** (part of MKVToolNix) - MKV muxing/demuxing
    -   **Linux:** `sudo pacman -S mkvtoolnix` or `sudo apt install mkvtoolnix`
    -   **Windows/macOS:** Download installer from website
-   **[mkvpropedit](https://mkvtoolnix.download/)** (part of MKVToolNix) - In-place MKV property editing (required for `hdr_forge edit`)
    -   Included in MKVToolNix installation above

### Install HDR Forge

```bash
# Install from source
git clone https://github.com/JanKremser/hdr_forge.git
cd hdr_forge
pip install -r requirements.txt

./build.sh

chmod +x ./dist/main
mv ./dist/main ./hdr_forge
```

### Verify Installation

```bash
hdr_forge --version
ffmpeg -version
ffprobe -version

# For AV1 support
ffmpeg -hide_banner -encoders | grep svt_av1

# For Dolby Vision support
dovi_tool --help

# For HDR10 metadata injection
hevc_hdr_editor --help

# For HDR10+ metadata
hdr10plus_tool --help

# For container operations
mkvmerge --version
mkvpropedit --version

# Check available hardware encoders
ffmpeg -hide_banner -encoders | grep nvenc
```

**For GPU setup instructions, see [Encoder Guide - GPU Setup](documentation/encoders.md#checking-gpu-support).**

## Quick Examples

### GUI Mode
```bash
# Launch interactive GUI
hdr_forge_ui
```

### In-Place MKV Editing (No Re-encode)
```bash
# Auto-detect subtitle tracks and set default
hdr_forge edit -i video.mkv --subtitle-flags auto

# Auto-detect with language preference
hdr_forge edit -i video.mkv --subtitle-flags auto>ger
```

### DV Auto Crop via L5 Offsets
```bash
# Crop from RPU metadata (no cropdetect scan)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop auto

# Verify crop detected
hdr_forge info -i dolby_vision.mkv  # shows "RPU Crop" if detected
```

### Profile 5 Dolby Vision
```bash
# Profile 5 → 8.1 (requires Vulkan GPU driver)
hdr_forge convert -i profile5_dv.mkv -o output.mkv --dv-profile 8

# Profile 5 → HDR10 (fast format conversion)
hdr_forge convert -i profile5_dv.mkv -o output.mkv --hdr-sdr-format hdr10
```

## Usage

### Video Information

Display detailed video metadata:

```bash
hdr_forge info -i video.mkv
```

Shows resolution, frame rate, color information, HDR metadata, and Dolby Vision details if present.

### Basic Conversion

Convert a video with automatic settings:

```bash
# Auto settings (keeps source format, no cropping by default)
hdr_forge convert -i input.mkv -o output.mkv

# Enable automatic cropping
hdr_forge convert -i input.mkv -o output.mkv --crop auto
```

### Encoder Selection

HDR Forge supports multiple encoders:

```bash
# CPU encoding (libx265) - highest quality
hdr_forge convert -i input.mkv -o output.mkv --video-codec h265

# GPU encoding (NVENC) - 3-10x faster
hdr_forge convert -i input.mkv -o output.mkv --video-codec h265 --hw-preset "gpu:balanced"

# H.264 for maximum compatibility
hdr_forge convert -i input.mkv -o output.mkv --video-codec h264

# GPU encoding (NVENC) - 3-10x faster
hdr_forge convert -i input.mkv -o output.mkv --video-codec h264 --hw-preset "gpu:balanced"

# AV1 for best compression
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1

# Stream copy (no re-encoding)
hdr_forge convert -i input.mkv -o output.mkv --video-codec copy
```

**See [Encoder Guide](documentation/encoders.md) for detailed encoder information and comparisons.**

### Hardware Acceleration

```bash
# Balanced GPU encoding (default GPU mode)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# Quality-focused GPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality

# CPU encoding presets
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
```

**See [Encoder Guide](documentation/encoders.md) for detailed encoder comparisons and benchmarks.**

### Encoding Presets

```bash
# Content-aware presets

# This is not the same as the preset from the video codec. Use the video preset for this.
hdr_forge convert -i film.mkv -o output.mkv --preset film

# Film at high resolution (4K optimized)
hdr_forge convert -i film4k.mkv -o output.mkv --preset film4k

# Film4K with faster encoding
hdr_forge convert -i film4k.mkv -o output.mkv --preset film4k:fast

hdr_forge convert -i action.mkv -o output.mkv --preset action

hdr_forge convert -i anime.mkv -o output.mkv --preset animation

# Grain preservation presets
hdr_forge convert -i grainy_film.mkv -o output.mkv --preset grain

# Grain with FFmpeg grain analysis
hdr_forge convert -i grainy_film.mkv -o output.mkv --preset grain:ffmpeg

# Banding reduction (and 8-bit to 10-bit for SDR)
hdr_forge convert -i input.mkv -o output.mkv --preset banding

# Neutral preset for mixed content (default preset from codec)
hdr_forge convert -i input.mkv -o output.mkv --preset video

# Combine with hardware presets
hdr_forge convert -i film.mkv -o output.mkv \
  --preset film \
  --hw-preset cpu:quality
```

### Cropping

```bash
# Automatic black bar detection
hdr_forge convert -i input.mkv -o output.mkv --crop auto

# Manual crop (width:height:x:y)
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140

# Aspect ratio crop
hdr_forge convert -i input.mkv -o output.mkv --crop 16:9
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# Disable cropping
hdr_forge convert -i input.mkv -o output.mkv --crop off

# DV auto crop (reads RPU L5 offsets)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop auto
```

### Resolution Scaling

```bash
# Named resolutions
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD   # 1920x1080
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale HD    # 1280x720
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale QHD+  # 1800p

# Numeric height
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale 1080

# Scaling modes
hdr_forge convert -i input.mkv -o output.mkv --scale 1080 --scale-mode height    # Fixed height
hdr_forge convert -i input.mkv -o output.mkv --scale 1920 --scale-mode adaptive  # Fit within bounds
```

**Available resolutions:** FUHD (8K), UHD (4K), QHD+ (1800p), WQHD (1440p), FHD (1080p), HD (720p), QHD (540p), SD (480p)

**Note:** Only downscaling is supported. Not compatible with Dolby Vision preservation.

### Grain Analysis

```bash
# Automatic grain detection
hdr_forge convert -i old_film.mkv -o output.mkv --grain auto

# Manual grain categories
hdr_forge convert -i input.mkv -o output.mkv --grain cat1  # Light grain
hdr_forge convert -i input.mkv -o output.mkv --grain cat2  # Medium grain
hdr_forge convert -i input.mkv -o output.mkv --grain cat3  # Heavy grain
```

### Logo Removal

```bash
# Automatic logo detection
hdr_forge convert -i input.mkv -o output.mkv --remove-logo auto

# Delogo filter or mask-based removal
hdr_forge convert -i input.mkv -o output.mkv --remove-logo delogo:auto
hdr_forge convert -i input.mkv -o output.mkv --remove-logo mask:auto
```

**See [Advanced Examples - Logo Removal](documentation/advanced-examples.md) for more options and techniques.**

### Dolby Vision

```bash
# Preserve Dolby Vision (re-encode with DV)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop off

# Force Profile 8.1
hdr_forge convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --crop off

# Convert to HDR10 (extract base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10

# Fast conversion without re-encoding
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --video-codec copy \
  --hdr-sdr-format hdr10

# Convert to SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format sdr
```

**Crop:** Auto crop (with `--crop auto`) reads RPU L5 offsets. Manual and ratio crop modes are blocked. Scale not supported.  
**See [Troubleshooting - Cropping with Dolby Vision](documentation/troubleshooting.md#cropping-and-scaling-with-dolby-vision) and [Advanced Examples - Profile 5](documentation/advanced-examples.md#profile-5-conversion).**

### Format Conversion

```bash
# Convert HDR10 to SDR with tone mapping
hdr_forge convert -i hdr10_video.mkv -o output.mkv --hdr-sdr-format sdr

# Preserve HDR without metadata (metadata flags only)
hdr_forge convert -i hdr10_video.mkv -o output.mkv --hdr-sdr-format hdr

# Keep source format (default)
hdr_forge convert -i input.mkv -o output.mkv --hdr-sdr-format auto
```

**Format hierarchy:** Dolby Vision → HDR10 → HDR (metadata only) → SDR (only downgrades supported)

### Video Sampling

Test encoding settings on short samples:

```bash
# Automatic sample (30s at 1:00)
hdr_forge convert -i large_file.mkv -o sample.mkv --sample auto

# Custom sample (1:30 to 2:00)
hdr_forge convert -i input.mkv -o sample.mkv --sample 90:120

# Fast GPU sample for testing
hdr_forge convert -i input.mkv -o sample.mkv \
  --sample auto \
  --encoder hevc_nvenc

# AV1 sample for quality comparison
hdr_forge convert -i input.mkv -o sample_av1.mkv \
  --sample auto \
  --encoder libsvtav1
```

### Audio & Subtitle Management

```bash
# Per-language audio encoding
hdr_forge convert -i input.mkv -o output.mkv --audio-codec "ger:aac;eng:ac3"

# Set default audio track
hdr_forge convert -i input.mkv -o output.mkv --audio-default ger

# Auto-detect subtitles
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags auto

# Auto-detect with language preference
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags auto>ger

# Remove all subtitles
hdr_forge convert -i input.mkv -o output.mkv --subtitle-flags remove
```

**See [Advanced Examples](documentation/advanced-examples.md#audio-encoding) for complete audio/subtitle workflows.**

### Custom Quality Settings

```bash
# Universal quality parameter (all encoders)
hdr_forge convert -i input.mkv -o output.mkv --quality 16

# Speed presets (libx265/libx264 only)
hdr_forge convert -i input.mkv -o output.mkv --speed slow
hdr_forge convert -i input.mkv -o output.mkv --speed slow:plus      # Better than slow
hdr_forge convert -i input.mkv -o output.mkv --speed medium:plus    # Better than medium

# Advanced: encoder-specific parameters
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"

hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

### Advanced Options

```bash
# Custom display aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --dar-ratio 16:9
hdr_forge convert -i input.mkv -o output.mkv --dar-ratio cinema

# Custom FFmpeg video filters
hdr_forge convert -i input.mkv -o output.mkv \
  --vfilter "eq=contrast=1.2:brightness=0.05,unsharp=5:5:1.0"
```

### Metadata Management

Extract and inject HDR/Dolby Vision metadata without re-encoding (ultra-fast):

```bash
# Extract metadata from video
hdr_forge extract-metadata -i video.mkv -o ./metadata_folder

# Inject HDR10 metadata
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --hdr10 metadata_hdr10.json

# Inject Dolby Vision RPU
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --rpu dolby_vision.rpu

# Inject Dolby Vision with Enhancement Layer
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --rpu dolby_vision.rpu \
  --el dolby_vision.hevc

# Inject HDR10+ metadata
hdr_forge inject-metadata -i video.mkv -o output.mkv \
  --hdr10plus metadata_hdr10plus.json
```

**See [Advanced Examples - Metadata Injection](documentation/advanced-examples.md#metadata-injection) for detailed workflows.**

### Batch Processing

```bash
# Convert all videos in folder
hdr_forge convert -i ./input_folder -o ./output_folder

# With specific settings
hdr_forge convert -i ./videos -o ./encoded \
  --hw-preset gpu:balanced \
  --crop auto \
  --scale FHD

# Batch convert to AV1
hdr_forge convert -i ./videos -o ./av1_encoded \
  --encoder libsvtav1 \
  --quality 23
```

### Supported Formats

**Input:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output:** `.mkv` (H.265/HEVC, H.264, or AV1 video + original audio/subtitle streams)

## Command Reference

For the complete list of CLI parameters and subcommands, see [Technical Details - Command Reference](documentation/technical-details.md#command-reference).

See the **[complete CLI parameter reference](documentation/technical-details.md#command-reference)** in Technical Details for all subcommands and options.

### Common Subcommands

```bash
hdr_forge --version                                    # Show version
hdr_forge info -i video.mkv                            # Display metadata
hdr_forge convert -i input.mkv -o output.mkv           # Convert video
hdr_forge edit -i video.mkv --subtitle-flags auto      # Edit in-place
hdr_forge extract-metadata -i video.mkv -o ./meta      # Extract metadata
hdr_forge inject-metadata -i video.mkv -o out.mkv --rpu file.rpu   # Inject metadata
hdr_forge detect-logo -i video.mkv --export mask.png   # Detect logos
```

### Automatic Quality Optimization

HDR Forge adjusts encoding quality based on resolution. For details, see:
- **[Technical Details - Auto-CRF Calculation](documentation/technical-details.md#auto-crfcq-calculation)** - Quality tables and formulas

## More Examples

Basic and complex workflows are covered in the documentation:
- **[Advanced Examples](documentation/advanced-examples.md)** - Complete workflow examples for all features
- **[Troubleshooting Guide](documentation/troubleshooting.md)** - Solutions to common issues

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

-   [FFmpeg](https://ffmpeg.org/) - Video processing
-   [x265](https://www.videolan.org/developers/x265.html) - HEVC encoding
-   [SVT-AV1](https://gitlab.com/AOMediaCodec/SVT-AV1) - AV1 encoding
-   [NVIDIA NVENC](https://developer.nvidia.com/nvidia-video-codec-sdk) - Hardware-accelerated encoding
-   [dovi_tool](https://github.com/quietvoid/dovi_tool) - Dolby Vision metadata handling
-   [hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor) - HDR metadata injection
-   [MKVToolNix](https://mkvtoolnix.download/) - MKV container operations
