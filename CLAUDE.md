# HDR Forge - Codebase Documentation

**IMPORTANT:** Keep this file compact and under 40,000 characters. Focus on essential information only. Move detailed explanations to `documentation/` directory.

## Project Overview

HDR Forge is a Python CLI tool for video conversion with HDR metadata preservation, hardware acceleration (NVIDIA NVENC), and advanced features like grain analysis, cropping, and Dolby Vision support.

**Version:** Python v0.7.11

## Documentation Structure

**When updating documentation:**
- Keep README.md user-friendly and concise (~600 lines max)
- Move technical details to `documentation/` directory:
  - `encoders.md` - Encoder support and hardware requirements
  - `advanced-examples.md` - CLI parameters and complex workflows
  - `technical-details.md` - Internal algorithms and processing
  - `troubleshooting.md` - Common issues and solutions

## Technology Stack

- **Language:** Python 3.7+
- **Video Processing:** ffmpeg, ffprobe
- **Hardware Acceleration:** NVIDIA NVENC (HEVC/H.264)
- **Video Codecs:** libx265 (HEVC), libx264 (H.264), libsvtav1 (AV1 - Beta), hevc_nvenc, h264_nvenc
- **Key Dependencies:** python-ffmpeg, dovi_tool, hevc_hdr_editor, mkvmerge, numpy

## Project Structure

```
src/hdr_forge/
├── main.py                        # CLI entry point (info, convert, calc_maxcll, inject-hdr-metadata)
├── video.py                       # Video metadata extraction (Video class)
├── encoder.py                     # Encoder orchestration (Encoder class)
├── hdr_metadata_injector.py       # HDR metadata injection without re-encoding
├── cli/                           # CLI output and argument parsing
├── typedefs/                      # Type definitions and enums
├── ffmpeg/video_codec/            # Codec implementations (libx265, libx264, libsvtav1, hevc_nvenc, h264_nvenc)
├── tools/                         # External tools (dovi_tool, hevc_hdr_editor, mkvmerge)
├── analyze/                       # MaxCLL/MaxFALL calculation
└── core/                          # Global configuration
```

## Key Modules

### encoder.py - Encoder Orchestration

**Core class for video encoding workflows**

Key methods:
- `convert()` - Universal conversion (routes to appropriate workflow)
- `convert_sdr_hdr10()` - Standard SDR/HDR10 conversion
- `convert_dolby_vision()` - Dolby Vision with re-encoding
- `convert_dolby_vision_to_hdr10_without_re_encoding()` - DV base layer extraction
- `convert_dolby_vision_to_other_profile_without_re_encoding()` - DV profile conversion

**Encoder Selection Priority:**
1. `--encoder` flag (explicit: libx265, libx264, libsvtav1, hevc_nvenc, h264_nvenc)
2. `--hw-preset` + hardware availability (gpu:* → NVENC, cpu:* → libx265/libx264/libsvtav1)
3. Default: libx265 CPU encoding

**Format Conversion Rules:**
- Only downgrades allowed: Dolby Vision → HDR10 → SDR
- HDR→SDR includes tone mapping (zscale + Hable algorithm)
- Format upgrades blocked with error

### ffmpeg/video_codec/ - Codec Implementations

**Base class pattern with codec-specific implementations**

**video_codec_base.py** - Abstract base class:
- HDR/SDR format validation
- Auto CRF/CQ/preset calculation based on resolution and content
- Filter chain building (crop, scale, tone mapping)
- HDR metadata handling

**Parameter Priority (CRF/CQ):**
1. `--encoder-params` (crf=X or cq=X)
2. `--quality` (universal 0-51)
3. Auto-detection (hw_preset + adjustments)

**Parameter Priority (Preset):**
1. `--encoder-params` (preset=X)
2. `--speed` (libx265/libx264 only)
3. Auto-detection (hw_preset)

**Auto-CRF Adjustments:**
- HDR10/DV: +1.0 CRF (10-bit allows higher compression)
- Action preset: -2.0 CRF (weighted, better for fast motion)
- Grain: -1/-2/-3 CRF (cat1/cat2/cat3)
- Weighting to avoid extreme values

**Codec Implementations:**
- `libx265.py` - Software HEVC (HDR10, SDR, DV base layer)
- `libx264.py` - Software H.264 (SDR only)
- `libsvtav1.py` - Software AV1 (SDR only) - **Beta** (HDR10/DV not yet implemented)
- `hevc_nvenc.py` - Hardware HEVC (HDR10, SDR, DV base layer)
- `h264_nvenc.py` - Hardware H.264 (SDR only)

### tools/dovi_tool.py - Dolby Vision Operations

**Dolby Vision RPU/EL handling**

Key functions:
- `extract_base_layer()` - Extract HDR10 base layer without RPU
- `extract_rpu()` - Extract RPU with profile conversion
- `inject_rpu()` - Inject RPU into HEVC
- `extract_enhancement_layer()` - Extract EL for Profile 7
- `inject_dolby_vision_layers()` - Multiplex BL+EL

**Supported Profiles:**
- Profile 5 (IPTPQc2) → Profile 8.1 (mode 3)
- Profile 7 (MEL+EL) → Profile 7 (with EL) or Profile 8.1 (mode 2)
- Profile 8 → Profile 8.1 (mode 2)

## Conversion Workflows

### SDR/HDR10 Conversion

1. Select codec (encoder selection priority)
2. Validate format (no upgrades)
3. Build filter chain (crop, scale, tone mapping)
4. Build encoder parameters (CRF/CQ, preset, x265-params)
5. Execute FFmpeg with progress tracking
6. Copy audio/subtitle streams

### Dolby Vision Conversion

**Workflow 1: DV → HDR10/SDR (Copy Mode)**
- Command: `--video-codec copy --hdr-sdr-format hdr10`
- Extract base layer (dovi_tool remove)
- Mux with audio/subs

**Workflow 2: DV → DV (Copy Mode, Profile Conversion)**
- Command: `--video-codec copy --dv-profile 8`
- Extract base layer and RPU
- Convert RPU profile
- Extract/multiplex EL if Profile 7
- Inject RPU, mux final file

**Workflow 3: DV → Any Format (With Re-encoding)**
- Command: `--video-codec x265` (default)
1. Extract and mux base layer
2. Re-encode with FFmpeg (filters, CRF/CQ)
3. For DV output: Extract RPU, inject into encoded video
4. Mux final file with audio/subs

**Important:** DV format does NOT support cropping/scaling (RPU is frame-position dependent). Only supported when converting DV → HDR10/SDR.

### HDR Metadata Injection

**Command:** `inject-hdr-metadata -i input.mkv --master-display "..." --max-cll "..."`
1. Create JSON config
2. Extract HEVC stream
3. Inject metadata (hevc_hdr_editor)
4. Mux back with audio/subs

## CLI Quick Reference

```bash
# Basic conversion
hdr_forge convert -i input.mkv -o output.mkv

# GPU acceleration
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced

# Explicit encoder (HEVC)
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# AV1 encoding (Beta)
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1

# Custom quality
hdr_forge convert -i input.mkv -o output.mkv --quality 16

# HDR Forge presets
hdr_forge convert -i input.mkv -o output.mkv --preset film|action|animation

# Cropping
hdr_forge convert -i input.mkv -o output.mkv --crop auto|off|21:9|1920:800:0:140

# Scaling
hdr_forge convert -i input.mkv -o output.mkv --scale FHD|UHD --scale-mode height|adaptive

# Grain analysis
hdr_forge convert -i input.mkv -o output.mkv --grain auto

# Format conversion
hdr_forge convert -i dv.mkv -o output.mkv --hdr-sdr-format hdr10|sdr

# DV profile conversion (copy mode)
hdr_forge convert -i dv.mkv -o output.mkv --video-codec copy --dv-profile 8

# Video sampling
hdr_forge convert -i input.mkv -o sample.mkv --sample auto|90:120

# Expert mode
hdr_forge convert -i input.mkv -o output.mkv --encoder libx265 --encoder-params "preset=slow:crf=14:tune=grain"

# Other commands
hdr_forge info -i input.mkv
hdr_forge calc_maxcll -i input.mkv
hdr_forge inject-hdr-metadata -i input.mkv -o output.mkv --master-display "..." --max-cll "..."
```

## Key Technical Details

### Encoder Selection Algorithm
1. Explicit `--encoder` flag
2. Automatic based on `--hw-preset`:
   - `gpu:*` → NVENC (if available)
   - `cpu:*` → libx265/libx264
3. Hardware detection via `ffmpeg -encoders`

### Parameter Priority
**Universal Parameters:**
- `--quality` (0-51) → CRF or CQ
- `--speed` → libx265/libx264 presets only

**Encoder-Specific:**
- `--encoder-params` → Highest priority, overrides auto-detection
- Format: `preset=X:crf=X:tune=X` (CPU) or `preset=X:cq=X:rc=X` (GPU)

### Auto-CRF Calculation
- Base from hw_preset (resolution-based)
- HDR10/DV: +1.0 CRF
- Action: -2.0 CRF (weighted)
- Grain: -1/-2/-3 CRF (cat1/2/3)
- Weighting function prevents extreme values

### Crop Detection
- Analyzes 10 positions across timeline
- Parallel processing (ThreadPoolExecutor)
- Modes: off, auto, manual (W:H:X:Y), aspect ratio (16:9, 21:9, cinema)

### Dolby Vision Processing
**Temporary files:** `.hdr_forge_temp_{filename}/`
**Profile handling:**
- Profile 5 → 8.1 (mode 3)
- Profile 7 → 7 (with EL) or 8.1 (mode 2)
- Profile 8 → 8.1 (mode 2)

## Common Development Tasks

### Adding a New Video Codec
1. Create class in `ffmpeg/video_codec/` inheriting `VideoCodecBase`
2. Implement: `get_ffmpeg_params()`, `get_custom_lib_parameters()`, `get_hdr_metadata_for_encoding()`
3. Define `HDR_SDR_SUPPORT`
4. Add to `encoder.py` in `_get_video_codec_lib_instance()`
5. Add enum to `typedefs/encoder_typing.py`
6. Update CLI arguments
7. Add preset configuration in `ffmpeg/video_codec/service/presets.py` if needed

### Modifying Auto-CRF Logic
1. Edit `calc_hw_preset_settings()` in `ffmpeg/video_codec/service/presets.py`
2. Adjust resolution thresholds and CRF mappings
3. Modify `_get_auto_crf()` in codec classes

### Adding CLI Parameters
1. Add argument in `cli/args/pars_args.py`
2. Parse in `cli/args/pars_encoder_settings.py`
3. Add to `EncoderSettings` in `typedefs/encoder_typing.py`
4. Update `main.py`
5. Update documentation

### Debugging
```bash
hdr_forge convert -i input.mkv -o output.mkv --debug
```
Shows: FFmpeg commands, encoder parameter selection, format detection, filter chains

## Known Limitations

1. **DV Cropping/Scaling:** Not supported when preserving DV format (only DV → HDR10/SDR)
2. **DV Sampling:** Not supported for DV encoding
3. **NVENC HDR:** Limited DV metadata injection support, HDR→SDR metadata removal not supported
4. **Upscaling:** Not supported (only downscaling)
5. **Format Upgrades:** Not possible (SDR → HDR10, HDR10 → DV)
6. **Hardware:** Only NVIDIA NVENC supported (no Intel QSV, AMD VCE, Apple VideoToolbox)
7. **AV1 Beta:** AV1 encoding is in beta status - currently SDR only, HDR10/Dolby Vision not yet implemented

## External Dependencies

**Required:** ffmpeg, ffprobe
**Optional:**
- dovi_tool (Dolby Vision processing)
- hevc_hdr_editor (HDR metadata injection)
- mkvmerge (MKVToolNix - container operations)
- SVT-AV1 library (for AV1 encoding - Beta)
**Hardware:** NVIDIA GPU with NVENC for hardware encoding
