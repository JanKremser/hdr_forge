# HDR Forge - SDR/HDR10/DolbyVision Video converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A powerful command-line tool for converting video files with hardware-accelerated encoding (NVIDIA NVENC), intelligent HDR metadata preservation, automatic quality optimization, grain analysis, flexible cropping, and advanced format conversion (H.264, H.265/HEVC, Dolby Vision).

## Features

-   **Multiple Encoder Support:** CPU (libx265, libx264) and GPU-accelerated encoding (NVIDIA NVENC)
-   **Hardware Acceleration:** NVIDIA NVENC support for H.265/HEVC and H.264 encoding
-   **Multiple Format Support:** Convert between Dolby Vision, HDR10, and SDR formats
-   **Format Conversion:** DV → HDR10 → SDR with tone mapping support
-   **Dolby Vision Profiles:** Support for Profile 5, 7 (with EL), and 8
-   **HDR Metadata Injection:** Add or update HDR10 metadata without re-encoding
-   **Advanced Cropping:** Automatic black bar detection, manual cropping, aspect ratio presets
-   **Flexible Scaling:** Height-based and adaptive scaling modes
-   **Grain Analysis:** Automatic grain detection with encoding optimization
-   **Content-Aware Presets:** Film, action, and animation-optimized encoding profiles
-   **Hardware Presets:** CPU/GPU-specific encoding presets (balanced, quality)
-   **Video Sampling:** Test encoding settings on short video samples
-   **Intelligent Quality Control:** Resolution and content-based auto-optimization
-   **Batch Processing:** Convert entire folders with one command
-   **HDR Metadata Preservation:** Maintains master display and content light level metadata
-   **Dolby Vision Re-encoding:** Base layer re-encoding with RPU injection
-   **Stream Copying:** Preserves all audio and subtitle tracks
-   **Real-time Progress:** Live encoding progress with ETA and statistics

All videos are converted to H.265 (HEVC) or H.264 with compression settings dynamically adjusted based on resolution, content type, and grain. Settings can be customized using various CLI parameters.

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

# Convert Dolby Vision to HDR10
hdr_forge convert -i dv.mkv -o output.mkv --hdr-sdr-format hdr10

# Inject HDR metadata without re-encoding
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"
```

## Version History

**Current: v0.6.0**

-   Master-display support for gpu encoded videos

**Current: v0.4.0** (Complete rewrite in Python)

-   Previous Rust version removed from main branch
-   Hardware acceleration support (NVIDIA NVENC)
-   Multiple encoder support (libx265, libx264, HEVC NVENC, H.264 NVENC)
-   Advanced cropping modes (auto, manual, aspect ratio)
-   Flexible scaling modes (height-based, adaptive)
-   Grain analysis and optimization
-   HDR metadata injection without re-encoding
-   Content-aware encoding presets (film, action, animation)
-   Video sampling for testing
-   Enhanced CLI with comprehensive parameter support

## Installation

### Requirements

#### Software Requirements (Mandatory)

-   **Python 3.7 or higher**
-   **[ffmpeg / ffprobe](https://ffmpeg.org/download.html)** with libx265 or libx264 support
-   **[x265 >=4.1](https://github.com/videolan/x265)** for libx265
    -   [Windows builds](http://msystem.waw.pl/x265/)
    -   **Linux:** Available in the repositories

#### Hardware Acceleration (Optional)

-   **NVIDIA GPU** with NVENC support (GTX 1050 or newer)
    -   FFmpeg compiled with NVENC support
    -   Recent NVIDIA drivers (recommended: 470+ for Linux, 472+ for Windows)

#### Optional Tools for Advanced Features

**For Dolby Vision:**

-   **[dovi_tool](https://github.com/quietvoid/dovi_tool)** - RPU/EL extraction and injection
    -   **for Arch Linux:** Available in the repositories
    -   **for others:** Download from releases and place in PATH or project root

**For HDR Metadata Injection:**

-   **[hevc_hdr_editor](https://github.com/quietvoid/hevc_hdr_editor)** - HDR metadata injection tool
    -   Download from releases and place in PATH or project root

**For Container Operations:**

-   **[mkvmerge](https://mkvtoolnix.download/)** (part of MKVToolNix) - MKV muxing/demuxing
    -   Usually available in system repositories

**For MaxCLL Calculation:**

-   **numpy** - For parallel MaxCLL/MaxFALL calculation
    -   Install via: `pip install numpy`

### Install HDR Forge

```bash
# Install from source
git clone https://github.com/JanKremser/hdr_forge.git
cd hdr_forge
pip install -e .

# Or install directly with pip (when published to PyPI)
pip install hdr_forge
```

### Verify Installation

```bash
hdr_forge --version
ffmpeg -version
ffprobe -version
x265 --version

# For Dolby Vision support
dovi_tool --help

# For HDR metadata injection
hevc_hdr_editor --help

# Check available hardware encoders
ffmpeg -hide_banner -encoders | grep nvenc
```

### GPU Setup (Optional)

To enable NVIDIA NVENC hardware acceleration:

1. **Install NVIDIA Drivers:**
   - Linux: `nvidia-driver` (recommended version 470+)
   - Windows: Download from NVIDIA website (recommended version 472+)

2. **Verify FFmpeg NVENC Support:**
   ```bash
   ffmpeg -hide_banner -encoders | grep nvenc
   ```
   You should see encoders like `hevc_nvenc` and `h264_nvenc`

3. **Test GPU Encoding:**
   ```bash
   hdr_forge convert -i test.mkv -o output.mkv --encoder hevc_nvenc
   ```

4. **If NVENC Not Available:**
   - Check GPU model (must be GTX 1050 or newer for HEVC NVENC)
   - Update GPU drivers
   - Reinstall FFmpeg with NVENC support enabled
   - On Linux: `ffmpeg -hwaccels` should list `cuda`

## Usage

### Video Information

Display detailed video metadata without conversion:

```bash
hdr_forge info -i video.mkv
```

Shows resolution, frame rate, color information, HDR metadata, and Dolby Vision details if present.

### Encoder Selection

HDR Forge supports multiple encoders for different use cases:

**CPU Encoders (Software):**
-   **libx265** - H.265/HEVC encoding (default, best quality, slower)
-   **libx264** - H.264/AVC encoding (wider compatibility, SDR only)

**GPU Encoders (Hardware-Accelerated):**
-   **hevc_nvenc** - NVIDIA H.265/HEVC encoding (faster, requires NVIDIA GPU)
-   **h264_nvenc** - NVIDIA H.264/AVC encoding (faster, requires NVIDIA GPU)

**Stream Copy:**
-   **copy** - No re-encoding, copy video stream (fastest, limited operations)

**Automatic Selection:**

By default, HDR Forge selects the best encoder based on:
-   `--video-codec` (x265, x264, copy)
-   `--hw-preset` (cpu:balanced, cpu:quality, gpu:balanced, gpu:quality)
-   Available hardware

**Explicit Selection:**

```bash
# Force specific encoder
hdr_forge convert -i input.mkv -o output.mkv --encoder libx265
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc
hdr_forge convert -i input.mkv -o output.mkv --encoder h264_nvenc

# Copy mode (no re-encoding)
hdr_forge convert -i input.mkv -o output.mkv --video-codec copy
```

### Hardware Acceleration

**Using GPU Encoding (NVIDIA NVENC):**

```bash
# Balanced GPU encoding (default GPU mode)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# Quality-focused GPU encoding
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality

# Explicit NVENC encoder
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc
```

**GPU vs CPU Trade-offs:**

| Aspect | CPU (libx265) | GPU (NVENC) |
|--------|---------------|-------------|
| **Speed** | Slower | 3-10x faster |
| **Quality** | Higher | Good (slightly lower) |
| **File Size** | Smaller | Larger (10-20%) |
| **Power Usage** | Higher CPU | Lower overall |
| **Best For** | Archival, max quality | Real-time, fast encoding |

**When to Use GPU:**
-   Large batch processing
-   Time-sensitive workflows
-   Real-time preview generation
-   Testing encoding settings (with `--sample`)

**When to Use CPU:**
-   Maximum quality needed
-   Archival purposes
-   Smallest file size required
-   No NVIDIA GPU available

### Basic Conversion

Convert a single video file. Black bars are detected and cropped by default:

```bash
hdr_forge convert -i input.mkv -o output.mkv
```

Disable automatic cropping:

```bash
hdr_forge convert -i input.mkv -o output.mkv --crop off
```

### Encoding Presets

HDR Forge provides intelligent preset combinations for different content types and quality targets.

#### Content-Aware Presets

Optimize encoding for specific content types:

```bash
# Film content (moderate motion, focus on detail)
hdr_forge convert -i film.mkv -o output.mkv --preset film

# Action content (fast motion, adjusted CRF)
hdr_forge convert -i action.mkv -o output.mkv --preset action

# Animation content (vibrant colors, optimized for animated content)
hdr_forge convert -i anime.mkv -o output.mkv --preset animation

# Auto mode (automatic detection, default)
hdr_forge convert -i input.mkv -o output.mkv --preset auto
```

#### Hardware Presets

Select encoding quality and speed balance:

```bash
# CPU encoding presets
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality

# GPU encoding presets (requires NVIDIA GPU)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality

# Prefix-free presets (hardware derived from --encoder or --video-codec)
hdr_forge convert -i input.mkv -o output.mkv --hw-preset balanced
hdr_forge convert -i input.mkv -o output.mkv --hw-preset quality
```

#### Combining Presets

```bash
# Film content with high-quality CPU encoding
hdr_forge convert -i film.mkv -o output.mkv --preset film --hw-preset cpu:quality

# Action content with fast GPU encoding
hdr_forge convert -i action.mkv -o output.mkv --preset action --hw-preset gpu:balanced
```

### Cropping

HDR Forge supports multiple cropping modes for black bar removal and aspect ratio adjustment.

#### Automatic Cropping

```bash
# Automatic black bar detection (analyzes 10 positions)
hdr_forge convert -i input.mkv -o output.mkv --crop auto
```

#### Manual Cropping

```bash
# Format: width:height:x:y (based on original video dimensions)
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140
```

#### Aspect Ratio Cropping

```bash
# Crop to 16:9 aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --crop 16:9

# Crop to 21:9 ultra-wide
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# Crop to 2.39:1 aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --crop 2.39:1
```

#### CinemaScope Presets

```bash
# CinemaScope Classic (2.35:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema

# CinemaScope Modern (2.39:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema-modern
```

#### Disable Cropping

```bash
# No cropping (default for Dolby Vision preservation)
hdr_forge convert -i input.mkv -o output.mkv --crop off
```

**Important Notes:**
-   Automatic crop detection analyzes 10 evenly-distributed video positions
-   Dolby Vision encoding requires `--crop off` (RPU metadata is position-dependent)
-   Cropping is applied BEFORE scaling

### Resolution Scaling

Scale videos to specific resolutions with multiple scaling modes:

#### Height-Based Scaling (Default)

Fixed target height, width calculated from aspect ratio:

```bash
# Using named resolutions
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD    # 1920x1080
hdr_forge convert -i 2k_video.mkv -o output.mkv --scale HD     # 1280x720

# Using numeric height (width calculated automatically)
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale 1080
hdr_forge convert -i input.mkv -o output.mkv --scale 720
```

#### Adaptive Scaling

Scales to fit within target resolution without exceeding width or height:

```bash
# Adaptive mode (no upscaling, maintains aspect ratio)
hdr_forge convert -i input.mkv -o output.mkv --scale 1920 --scale-mode adaptive

# Fit within 4K bounds adaptively
hdr_forge convert -i input.mkv -o output.mkv --scale UHD --scale-mode adaptive
```

#### Available Named Resolutions

-   `8K` - 4320p (7680x4320)
-   `UHD` - 2160p (3840x2160)
-   `QHD` - 1440p (2560x1440)
-   `FHD` - 1080p (1920x1080)
-   `HD` - 720p (1280x720)
-   `SD` - 480p (640x480)

**Important Limitations:**

-   **Only downscaling is supported** - Videos cannot be upscaled to larger resolutions
-   **Not compatible with Dolby Vision** - Scaling modifies frame dimensions which breaks RPU metadata
-   Scaling preserves aspect ratio and is applied after cropping (if enabled)

### Grain Analysis

Detect and optimize encoding for film grain:

```bash
# Automatic grain detection and optimization
hdr_forge convert -i input.mkv -o output.mkv --grain auto

# Manual grain category (light grain)
hdr_forge convert -i input.mkv -o output.mkv --grain cat1

# Medium grain optimization
hdr_forge convert -i input.mkv -o output.mkv --grain cat2

# Heavy grain optimization
hdr_forge convert -i input.mkv -o output.mkv --grain cat3

# Disable grain analysis (default)
hdr_forge convert -i input.mkv -o output.mkv --grain off
```

**Grain Categories:**

-   **cat1** - Light grain (CRF adjustment: -1)
-   **cat2** - Medium grain (CRF adjustment: -2, tune=grain for libx265)
-   **cat3** - Strong grain (CRF adjustment: -3, tune=grain for libx265)

**Effects:**
-   Lowers CRF to preserve grain detail
-   Sets `tune=grain` for libx265/libx264 (cat2, cat3)
-   Prevents over-compression that destroys grain texture

### Dolby Vision

Dolby Vision videos are automatically detected based on RPU metadata flags.

**Supported Profiles:**
- Profile 5 (IPTPQc2, BL+RPU) → Preserves Profile 5 or converts to Profile 8.1
- Profile 7 (MEL, BL+EL+RPU) → Preserves Profile 7 or converts to Profile 8.1
- Profile 8 (BL+RPU) → Keeps Profile 8.1

**Preserve Dolby Vision (re-encode with DV):**
```bash
# Must disable cropping when preserving DV
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop off

# Force conversion to Profile 8.1
hdr_forge convert -i dolby_vision.mkv -o output.mkv --dv-profile 8 --crop off
```

**Convert to HDR10 (extract base layer only):**
```bash
# Cropping and scaling supported when converting to HDR10
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10 --scale FHD

# Fast extraction without re-encoding (copy mode)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --video-codec copy --hdr-sdr-format hdr10
```

**Convert to SDR (with tone mapping):**
```bash
# Converts DV → HDR10 base layer → SDR with tone mapping
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format sdr
```

**Convert Dolby Vision Profile (without re-encoding):**
```bash
# Fast profile conversion using copy mode
hdr_forge convert -i dolby_vision.mkv -o output.mkv --video-codec copy --dv-profile 8
```

**Important Notes:**
- Dolby Vision does NOT support cropping or scaling when preserving DV format (use `--crop off` and avoid `--scale`)
- Cropping and scaling ARE supported when converting DV → HDR10 or DV → SDR
- Profile 7 with Enhancement Layer is preserved only with `--dv-profile auto` (default)
- Video sampling NOT supported for Dolby Vision encoding

### Format Conversion

Convert between different HDR/SDR formats. Only downgrades are supported (DV → HDR10 → SDR):

```bash
# Convert HDR10 to SDR with tone mapping
hdr_forge convert -i hdr10_video.mkv -o output.mkv --hdr-sdr-format sdr

# Convert Dolby Vision to HDR10 (extracts base layer)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --hdr-sdr-format hdr10

# Keep source format (default behavior)
hdr_forge convert -i input.mkv -o output.mkv --hdr-sdr-format auto
```

**Tone Mapping:**
- HDR to SDR conversion uses zscale filter with Hable tone mapping algorithm
- Automatically removes HDR metadata for SDR output
- Adjusts color space to BT.709 for SDR

**Format Hierarchy:**
- Dolby Vision (highest)
- HDR10
- SDR (lowest)

Only downgrades are allowed. Attempting to upgrade (e.g., SDR → HDR10) will result in an error.

### Batch Processing

Convert all supported video files in a folder:

```bash
hdr_forge convert -i ./input_folder -o ./output_folder
```

Output files maintain original names with `.mkv` extension.

### Video Sampling

Test encoding settings on short video samples before full conversion:

```bash
# Automatic sample (30 seconds starting at 1 minute)
hdr_forge convert -i input.mkv -o sample.mkv --sample auto

# Custom sample from 1:30 to 2:00 (90-120 seconds)
hdr_forge convert -i input.mkv -o sample.mkv --sample 90:120

# Sample with GPU encoding for fast testing
hdr_forge convert -i input.mkv -o sample.mkv --sample auto --encoder hevc_nvenc
```

**Use Cases:**
-   Test encoding quality before processing large files
-   Quick preview of encoding settings
-   Fast grain analysis testing
-   Verify crop/scale results

**Limitations:**
-   Not supported for Dolby Vision encoding (RPU metadata requires full video)

### Custom Quality Settings

Override automatic quality settings:

#### Universal Quality Parameter

Works with all encoders, automatically maps to CRF (libx265/libx264) or CQ (NVENC):

```bash
# Higher quality (lower value = better quality, larger file)
hdr_forge convert -i input.mkv -o output.mkv --quality 14

# Standard quality
hdr_forge convert -i input.mkv -o output.mkv --quality 18

# Lower quality (smaller files)
hdr_forge convert -i input.mkv -o output.mkv --quality 22
```

#### Speed Preset (libx265/libx264 only)

```bash
# Faster encoding (lower compression)
hdr_forge convert -i input.mkv -o output.mkv --speed faster

# Balanced
hdr_forge convert -i input.mkv -o output.mkv --speed medium

# Slower encoding (higher compression)
hdr_forge convert -i input.mkv -o output.mkv --speed slow
```

**Available Speed Presets:** ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow

**Note:** `--speed` is NOT compatible with NVENC encoders. Use `--encoder-params` instead.

#### Advanced: Encoder-Specific Parameters

For expert users, directly set encoder-specific parameters:

**libx265/libx264:**
```bash
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=slow:crf=14:tune=grain"
```

**NVENC:**
```bash
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

**NVENC Parameters:**
-   Presets: default, slow, hq, llhq, llhp
-   RC Modes: vbr, vbr_hq, cbr, cqp

### HDR Metadata Injection

Inject or update HDR10 metadata without re-encoding (ultra-fast):

```bash
# Inject master display metadata
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

# With MaxCLL/MaxFALL values
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

**Use Cases:**
-   Add HDR10 metadata to SDR video
-   Update incorrect HDR metadata
-   Fix missing master display information
-   Quick metadata correction without re-encoding overhead

**Performance:**
-   Much faster than re-encoding (seconds vs. hours)
-   No quality loss
-   Requires `hevc_hdr_editor` tool

**Master Display Format:**
```
G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)
```

**MaxCLL/MaxFALL Format:**
```
MaxCLL,MaxFALL
```

### Supported Formats

**Input Formats:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output Format:** `.mkv` (H.265/HEVC or H.264 video + original audio/subtitle streams)

## Command Reference

### Global Options

```
hdr_forge --version              Show program version
hdr_forge --help                 Show help message
```

### Info Subcommand

```
hdr_forge info -i INPUT          Display video metadata

Options:
  -i, --input INPUT         Input video file
  -d, --debug               Enable debug output
```

### Convert Subcommand

```
hdr_forge convert -i INPUT -o OUTPUT [OPTIONS]

Required Arguments:
  -i, --input INPUT         Input video file or folder
  -o, --output OUTPUT       Output video file or folder

Encoder Selection:
  -v, --video-codec CODEC   Video codec: x265, x264, copy (default: x265)
  --encoder CODEC           Force specific encoder: auto, libx265, libx264,
                            hevc_nvenc, h264_nvenc (default: auto)

Encoding Presets:
  -p, --preset PRESET       Content preset: auto, film, action, animation
                            (default: auto)
  --hw-preset PRESET        Hardware preset: cpu:balanced, cpu:quality,
                            gpu:balanced, gpu:quality, balanced, quality
                            (default: cpu:balanced)

Quality Settings:
  --quality VALUE           Universal quality (0-51, lower = better)
                            Maps to CRF for libx265/libx264, CQ for NVENC
  --speed PRESET            Speed preset (libx265/libx264 only):
                            ultrafast, superfast, veryfast, faster, fast,
                            medium, slow, slower, veryslow

Cropping & Scaling:
  --crop MODE               Crop mode:
                            [off]              : No cropping (default)
                            [auto]             : Automatic black bar detection
                            [width:height:x:y] : Manual crop dimensions
                            [16:9], [21:9]     : Aspect ratio crop
                            [cinema]           : CinemaScope 2.35:1
                            [cinema-modern]    : CinemaScope 2.39:1
  --scale RESOLUTION        Target resolution: 8K, UHD, QHD, FHD, HD, SD,
                            or numeric height (e.g., 1080)
  --scale-mode MODE         Scale mode: height, adaptive (default: height)

Content Analysis:
  --grain MODE              Grain analysis: off, auto, cat1, cat2, cat3
                            (default: off)
  --sample TIME             Process video sample: auto or start:end in seconds
                            (e.g., 60:90 for 1:00-1:30)

Format Conversion:
  --hdr-sdr-format FORMAT   Target format:
                            [auto]   : Keep source format (default)
                            [hdr10]  : Convert to HDR10
                            [sdr]    : Convert to SDR with tone mapping
  --dv-profile PROFILE      Dolby Vision profile:
                            [auto]   : Automatic detection (default)
                            [8]      : Force Profile 8.1 output

Expert Options:
  --encoder-params PARAMS   Encoder-specific parameters
                            libx265/libx264: preset=<val>:crf=<val>:tune=<val>
                            NVENC: preset=<val>:cq=<val>:rc=<val>
  --master-display STRING   Custom master display metadata
                            Format: G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)
  --max-cll STRING          Custom MaxCLL/MaxFALL values
                            Format: MaxCLL,MaxFALL (e.g., "1000,400")

Debug:
  -d, --debug               Enable debug output
```

### inject-hdr-metadata Subcommand

```
hdr_forge inject-hdr-metadata -i INPUT [OPTIONS]

Description:
  Inject HDR10 metadata into HEVC bitstream without re-encoding

Required Arguments:
  -i, --input INPUT                Input video file (MKV or HEVC)
  --master-display METADATA        Master display metadata
                                   Format: G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)

Optional Arguments:
  -o, --output OUTPUT              Output MKV file (default: input.mkv)
  --max-cll VALUES                 MaxCLL and MaxFALL values
                                   Format: MaxCLL,MaxFALL (e.g., "1000,400")
  -d, --debug                      Enable debug output
```

### calc_maxcll Subcommand

```
hdr_forge calc_maxcll -i INPUT   Calculate MaxCLL and MaxFALL (BETA)

Options:
  -i, --input INPUT         Input video file
  -d, --debug               Enable debug output
```

## Automatic Quality Optimization

HDR Forge automatically adjusts encoding parameters based on video resolution for optimal quality and encoding speed:

### CRF/CQ (Quality) - Lower = Better Quality

**CPU Encoders (libx265/libx264):**

| Resolution Range | Pixel Count      | Base CRF   |
| ---------------- | ---------------- | ---------- |
| 4K+              | 6.1M+ pixels     | 13         |
| 2K-4K            | 2.2M-6.1M pixels | 14-18      |
| Full HD          | ~2.1M pixels     | 18         |
| HD               | 1M-2.1M pixels   | 19         |
| Lower            | <1M pixels       | 20         |

**GPU Encoders (NVENC):**

Similar scaling with CQ parameter, typically 2-3 points higher than CRF for equivalent quality.

**Adjustments:**

-   **HDR10/DV:** +1.0 CRF/CQ (10-bit encoding allows higher values without quality loss)
-   **Action Preset:** -2.0 CRF/CQ (weighted, better fast motion handling)
-   **Grain Analysis:**
    -   cat1: -1.0 CRF/CQ
    -   cat2: -2.0 CRF/CQ
    -   cat3: -3.0 CRF/CQ

### Preset (Speed) - Faster = Quicker Encoding

**CPU Encoders (libx265/libx264):**

| Resolution Range | Pixel Count      | Preset    |
| ---------------- | ---------------- | --------- |
| 4K+              | 8.8M+ pixels     | superfast |
| 2K-4K            | 2.1M-8.8M pixels | faster    |
| Full HD          | ~2.1M pixels     | fast      |
| Lower            | <2.1M pixels     | medium    |

**GPU Encoders (NVENC):**

| Hardware Preset | NVENC Preset | Description                      |
| --------------- | ------------ | -------------------------------- |
| gpu:balanced    | default      | Balanced speed and quality       |
| gpu:quality     | hq           | Higher quality, slower           |

These defaults can be overridden with `--quality`, `--speed`, `--hw-preset`, or `--encoder-params` parameters.

## Advanced Examples

### Hardware Acceleration Examples

```bash
# Use NVIDIA NVENC HEVC encoder explicitly
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# GPU encoding with quality focus
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality

# CPU encoding with balanced settings
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced

# H.264 NVENC for maximum compatibility
hdr_forge convert -i input.mkv -o output.mkv --encoder h264_nvenc
```

### Encoding Preset Combinations

```bash
# Film content with high-quality CPU encoding
hdr_forge convert -i film.mkv -o output.mkv --preset film --hw-preset cpu:quality

# Action content with fast GPU encoding
hdr_forge convert -i action.mkv -o output.mkv --preset action --hw-preset gpu:balanced

# Animation with grain optimization
hdr_forge convert -i anime.mkv -o output.mkv --preset animation --grain auto
```

### Complex Cropping Examples

```bash
# Automatic black bar detection
hdr_forge convert -i input.mkv -o output.mkv --crop auto

# Manual crop with custom dimensions
hdr_forge convert -i input.mkv -o output.mkv --crop 1920:804:0:138

# Crop to 16:9 aspect ratio
hdr_forge convert -i input.mkv -o output.mkv --crop 16:9

# Crop to 21:9 ultra-wide
hdr_forge convert -i input.mkv -o output.mkv --crop 21:9

# CinemaScope format (2.35:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema

# CinemaScope modern (2.39:1)
hdr_forge convert -i input.mkv -o output.mkv --crop cinema-modern
```

### Grain Analysis Examples

```bash
# Automatic grain detection and optimization
hdr_forge convert -i old_film.mkv -o output.mkv --grain auto

# Manual grain category (light)
hdr_forge convert -i input.mkv -o output.mkv --grain cat1 --hw-preset cpu:quality

# Heavy grain optimization with film preset
hdr_forge convert -i grainy_film.mkv -o output.mkv --grain cat3 --preset film
```

### Scaling Examples

```bash
# Adaptive scaling (fits within 1920 bounds, no upscaling)
hdr_forge convert -i input.mkv -o output.mkv --scale 1920 --scale-mode adaptive

# Fixed height scaling to 1080p
hdr_forge convert -i 4k_video.mkv -o output.mkv --scale FHD --scale-mode height

# Scale to 720p with adaptive mode
hdr_forge convert -i input.mkv -o output.mkv --scale HD --scale-mode adaptive
```

### Video Sampling Examples

```bash
# Test encoding with automatic 30-second sample (at 1:00)
hdr_forge convert -i large_file.mkv -o sample.mkv --sample auto

# Custom sample from 2:00 to 2:30
hdr_forge convert -i input.mkv -o sample.mkv --sample 120:150

# Fast GPU sample for testing settings
hdr_forge convert -i input.mkv -o sample.mkv --sample auto --encoder hevc_nvenc

# Test grain settings on sample
hdr_forge convert -i input.mkv -o sample.mkv --sample auto --grain auto
```

### HDR Metadata Injection Examples

```bash
# Inject HDR10 metadata without re-encoding
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

# With MaxCLL/MaxFALL values
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# Update metadata during encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

### Combined Complex Examples

```bash
# 4K to 1080p: film preset, auto crop, grain analysis, high quality
hdr_forge convert -i 4k_film.mkv -o 1080p_output.mkv \
  --preset film \
  --scale FHD \
  --crop auto \
  --grain auto \
  --hw-preset cpu:quality

# Fast GPU batch conversion with automatic settings
hdr_forge convert -i ./4k_videos -o ./1080p_encoded \
  --scale FHD \
  --hw-preset gpu:balanced \
  --crop auto

# High-quality archival encoding with custom parameters
hdr_forge convert -i source.mkv -o archive.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain" \
  --crop auto

# Fast sample test before full encode
hdr_forge convert -i large_video.mkv -o test_sample.mkv \
  --sample 60:90 \
  --encoder hevc_nvenc \
  --hw-preset gpu:quality

# Convert entire Dolby Vision library to HDR10 with scaling
hdr_forge convert -i ./dv_collection -o ./hdr10_collection \
  --hdr-sdr-format hdr10 \
  --scale FHD \
  --hw-preset gpu:balanced

# Dolby Vision to SDR with tone mapping, crop, and scale
hdr_forge convert -i dolby_vision.mkv -o sdr_output.mkv \
  --hdr-sdr-format sdr \
  --crop auto \
  --scale FHD

# Action content with fast motion optimization
hdr_forge convert -i action_movie.mkv -o output.mkv \
  --preset action \
  --quality 16 \
  --crop cinema-modern
```

## Technical Details

### Encoder Selection Logic

HDR Forge selects the optimal encoder based on multiple factors:

**Priority:**

1. **Explicit Override:** `--encoder` flag (libx265, libx264, hevc_nvenc, h264_nvenc)
2. **Automatic Selection:** Based on `--hw-preset` and available hardware
   - `gpu:*` presets → NVENC (if available, otherwise error)
   - `cpu:*` presets → libx265 or libx264
   - Prefix-free presets → Derived from `--video-codec`
3. **Default:** libx265 with CPU encoding

**Hardware Detection:**

-   Queries `ffmpeg -encoders` for available encoders
-   Checks for NVENC support (nvenc, qsv, vaapi, amf, v4l2)
-   Errors if GPU preset selected but hardware not available

### Crop Detection

-   Analyzes 10 evenly-distributed samples across video timeline
-   Uses ThreadPoolExecutor for parallel processing
-   Selects most common crop dimensions using Counter
-   Progress callback for real-time updates
-   Not supported for Dolby Vision when preserving DV format

### HDR Metadata Extraction

-   Uses `ffprobe -show_frames -read_intervals %+#1` to extract first frame metadata
-   Parses mastering display and content light level side data
-   Handles multiple metadata formats (JSON parsing)
-   Fallback to default values if metadata missing

### HDR to SDR Tone Mapping

Tone mapping filter chain (zscale + Hable algorithm):

```
zscale=transfer=linear:npl=100,
format=gbrpf32le,
tonemap=hable:desat=0,
zscale=transfer=bt709:matrix=bt709:range=tv:primaries=bt709,
format=yuv420p
```

### Progress Tracking

-   **FFmpeg:** Parses progress callback from python-ffmpeg library
-   **Real-time ETA:** Calculation based on FPS and remaining frames
-   **Multi-line display:** ANSI escape codes for line clearing
-   **Subprocess monitoring:** Spinner animation for dovi_tool, hevc_hdr_editor, mkvmerge

### Resolution Scaling

**Scaling Modes:**

-   **height:** Fixed target height, width calculated from aspect ratio (default)
-   **adaptive:** Scales to fit within target resolution without exceeding width or height

**Process:**

-   Preserves aspect ratio when scaling
-   Applies scaling AFTER cropping if both enabled
-   Recalculates pixel count for auto-CRF/preset after scaling
-   Only downscaling supported (no upscaling)

### Grain Analysis

**Purpose:** Detect film grain and optimize encoding settings to preserve detail

**Categories:**

-   **cat1** - Light grain: CRF -1
-   **cat2** - Medium grain: CRF -2, tune=grain
-   **cat3** - Strong grain: CRF -3, tune=grain

**Integration:**

-   Lowers CRF to preserve grain detail
-   Sets `tune=grain` for libx265/libx264
-   Prevents over-compression

### Dolby Vision Processing

**Multi-Stage Workflow:**

1. **Base Layer Extraction:** Removes RPU to get HDR10 base layer using `dovi_tool remove`
2. **Temporary MKV Creation:** Muxes base layer with audio/subs for FFmpeg processing
3. **Re-encoding:** Applies encoder, CRF/CQ, and quality settings
4. **RPU Extraction:** Extracts RPU with profile-specific mode conversion
5. **Enhancement Layer (Profile 7 only):** Extracts and multiplexes EL
6. **RPU Injection:** Re-injects RPU into encoded base layer
7. **Final Muxing:** Creates final MKV with video, audio, subtitles

**Profile Handling:**

-   Profile 5 (IPTPQc2) → Profile 8.1 via mode 3
-   Profile 7 (MEL+EL) → Profile 7 (with EL) or Profile 8.1 via mode 2
-   Profile 8 → Profile 8.1 via mode 2

**Copy Mode (No Re-encoding):**

-   DV → HDR10: Extract base layer only
-   DV → DV: Extract base layer, convert RPU profile, inject RPU

**Temporary File Management:**

-   Creates `.hdr_forge_temp_{filename}/` directory in output location
-   Incremental deletion of intermediate files during workflow
-   Final cleanup removes entire temp directory

## Troubleshooting

### "Command not found: ffmpeg"

Install ffmpeg from [ffmpeg.org](https://ffmpeg.org/download.html) and ensure it's in your PATH.

### "dovi_tool not found" (Dolby Vision only)

Install dovi_tool from [GitHub releases](https://github.com/quietvoid/dovi_tool/releases) or place the binary in the project root directory.

### "hevc_hdr_editor not found"

Install hevc_hdr_editor from [GitHub releases](https://github.com/JanKremser/hevc-hdr-editor/releases) or place the binary in the project root directory. Required for `inject-hdr-metadata` command.

### "NVENC encoder not available"

**Check GPU Support:**
```bash
# List available hardware encoders
ffmpeg -hide_banner -encoders | grep nvenc

# Check for CUDA support
ffmpeg -hwaccels
```

**Solutions:**
-   Verify GPU model (GTX 1050 or newer for HEVC NVENC)
-   Update GPU drivers (Linux: 470+, Windows: 472+)
-   Reinstall FFmpeg with NVENC support
-   Use CPU encoding instead: `--hw-preset cpu:balanced`

### Slow crop detection

Crop detection analyzes 10 video samples. For very large files, consider using `--crop off` or manual crop: `--crop width:height:x:y`.

### Black bars still visible after conversion

Some videos have irregular black bars that vary throughout the video. Crop detection uses the most common dimensions found. Use manual crop with `--crop width:height:x:y` for precise control.

### "Cannot crop/scale Dolby Vision" warning

When preserving Dolby Vision format, cropping and scaling are not supported because RPU metadata is frame-position dependent.

**Options:**
- Use `--crop off` to disable cropping for DV preservation
- Convert to HDR10 or SDR to enable cropping/scaling: `--hdr-sdr-format hdr10`

### High disk usage during Dolby Vision conversion

Dolby Vision conversion creates temporary files that can use up to 2x the source file size. These are automatically cleaned up after conversion. Ensure sufficient disk space in the output directory.

### "Speed preset not compatible with NVENC"

The `--speed` parameter only works with libx265/libx264 encoders. For NVENC encoders, use `--encoder-params` instead:

```bash
# Correct NVENC usage
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

## Performance Comparison

### CPU vs. GPU Encoding

**Speed:**
-   **GPU (NVENC):** 3-10x faster than CPU
-   **CPU (libx265):** Slower but more configurable

**Quality (at same bitrate):**
-   **CPU (libx265):** Higher quality, better compression
-   **GPU (NVENC):** Slightly lower quality, larger files (10-20%)

**File Size (at target quality):**
-   **CPU (libx265):** Smaller files for same visual quality
-   **GPU (NVENC):** Larger files (typically 10-20% more)

**Power Consumption:**
-   **CPU:** Higher CPU usage, more heat
-   **GPU:** Lower overall system power, offloads work to GPU

**Best Use Cases:**

| Scenario | Recommended | Reason |
|----------|------------|--------|
| Archival/Maximum Quality | CPU (libx265) | Best compression, smallest files |
| Fast Batch Processing | GPU (NVENC) | Much faster, good quality |
| Testing Settings | GPU (NVENC) + `--sample` | Extremely fast preview |
| Live Streaming/Real-time | GPU (NVENC) | Low latency, hardware-accelerated |
| Film with Grain | CPU (libx265) + grain | Best grain preservation |
| 4K/8K Content | CPU or GPU | Depends on speed vs. quality needs |

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## License

MIT License - See LICENSE file for details

## Acknowledgments

-   [FFmpeg](https://ffmpeg.org/) - Video processing
-   [x265](https://www.videolan.org/developers/x265.html) - HEVC encoding
-   [NVIDIA NVENC](https://developer.nvidia.com/nvidia-video-codec-sdk) - Hardware-accelerated encoding
-   [dovi_tool](https://github.com/quietvoid/dovi_tool) - Dolby Vision metadata handling
-   [hevc_hdr_editor](https://github.com/JanKremser/hevc-hdr-editor) - HDR metadata injection
-   [MKVToolNix](https://mkvtoolnix.download/) - MKV container operations
