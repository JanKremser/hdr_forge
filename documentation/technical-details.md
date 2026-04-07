# Technical Details

This document provides in-depth technical information about HDR Forge's internal workings.

## Encoder Selection Algorithm

### Selection Priority

HDR Forge uses a multi-level priority system for encoder selection:

1. **Explicit Override:** `--encoder` flag
   - `libx265`, `libx264`, `hevc_nvenc`, `h264_nvenc`
   - Highest priority, bypasses all automatic detection

2. **Automatic Selection:** Based on `--hw-preset` and hardware availability
   - `gpu:*` presets → NVENC (if available, otherwise error)
   - `cpu:*` presets → libx265 or libx264
   - Prefix-free presets (`balanced`, `quality`) → Derived from `--video-codec`

3. **Default Fallback:** libx265 with CPU encoding

### Hardware Detection Process

```python
def get_available_hw_encoders():
    1. Query: ffmpeg -hide_banner -encoders
    2. Parse output for hardware encoders
    3. Check for: nvenc, qsv, vaapi, amf, v4l2
    4. Return list of available VideoEncoderLibrary enum members
    5. Error if GPU preset selected but hardware not available
```

### Encoder Instantiation

```python
def _get_video_codec_lib_instance():
    Priority 1: encoder_override (if not AUTO)
        → _get_codec_from_override()

    Priority 2: video_codec + enable_gpu_acceleration
        If video_codec == H265:
            If enable_gpu_acceleration:
                → HevcNvencCodec (if available)
            Else:
                → Libx265Codec

        If video_codec == X264:
            If enable_gpu_acceleration:
                → H264NvencCodec (if available)
            Else:
                → Libx264Codec
```

## Parameter Priority System

### Quality Parameters (CRF/CQ)

**Priority Chain:**

1. **`--encoder-params`** (Highest)
   - libx265: `crf=14` in `preset=slow:crf=14`
   - NVENC: `cq=16` in `preset=hq:cq=16:rc=vbr_hq`

2. **`--quality`** (Universal parameter)
   - Maps to CRF for libx265/libx264
   - Maps to CQ for NVENC encoders

3. **Auto-detection** (Lowest)
   - Base value from hardware preset
   - Adjustments for HDR/DV, action preset

### Speed Parameters (Preset)

**Priority Chain (libx265/libx264 only):**

1. **`--encoder-params`** (Highest)
   - `preset=slow` in `preset=slow:crf=14`

2. **`--speed`**
   - ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow

3. **Auto-detection** (Lowest)
   - Based on hardware preset and resolution

**Note:** NVENC uses different preset system via `--encoder-params`

### Tune Parameters (libx265/libx264 only)

**Priority Chain:**

1. **`--encoder-params`** (Highest)
   - `tune=grain` in `preset=slow:crf=14:tune=grain`

2. **Auto-detection** (Lowest)
   - Animation preset → `tune=animation`

## Auto-CRF/CQ Calculation

### Base CRF Calculation

```python
def _get_auto_crf(hw_preset):
    # Get base CRF from hardware preset
    base_crf = hw_preset.crf  # Resolution-based value

    # HDR adjustment
    if is_hdr_encoding():
        base_crf += 1.0  # 10-bit allows higher CRF

    # Action preset adjustment
    if hdr_forge_preset == ACTION:
        action_crf_delta = 2.0
        weight = _calculate_crf_adjustment_weight(base_crf, action_crf_delta)
        base_crf -= action_crf_delta * weight

    return round(base_crf)
```

### CRF Adjustment Weighting

Prevents extreme CRF values by reducing adjustment impact at already-low CRF:

```python
def _calculate_crf_adjustment_weight(current_crf, crf_delta):
    if crf_delta > 0:  # Lowering CRF (improving quality)
        if current_crf <= 14:
            return 0.3  # Minimal adjustment at very high quality
        elif current_crf <= 18:
            return 0.7  # Moderate adjustment
        else:
            return 1.0  # Full adjustment at lower quality
    return 1.0
```

### Hardware Preset CRF Values

**CPU Presets (libx265/libx264):**

| Resolution | Pixel Count | cpu:balanced | cpu:quality |
|------------|-------------|--------------|-------------|
| 8K | 33M+ | 12 | 10 |
| 4K+ | 6.1M+ | 13 | 11 |
| 2K-4K | 2.2M-6.1M | 14-18 | 12-16 |
| Full HD | 2.1M | 18 | 16 |
| HD | 1M-2.1M | 19 | 17 |
| Lower | <1M | 20 | 18 |

**GPU Presets (NVENC):**

Similar scaling but typically 2-3 points higher than CPU for equivalent quality:

| Resolution | Pixel Count | gpu:balanced | gpu:quality |
|------------|-------------|--------------|-------------|
| 4K+ | 6.1M+ | 15 | 13 |
| Full HD | 2.1M | 20 | 18 |

### Preset Calculation

**CPU Presets:**

| Resolution | Pixel Count | cpu:balanced | cpu:quality |
|------------|-------------|--------------|-------------|
| 4K+ | 8.8M+ | superfast | faster |
| 2K-4K | 2.1M-8.8M | faster | fast |
| Full HD | 2.1M | fast | medium |
| Lower | <2.1M | medium | slow |

**GPU Presets:**

| Resolution | gpu:balanced | gpu:quality |
|------------|--------------|-------------|
| All | default | hq |

## Crop Detection Algorithm

### Process

1. **Sample Selection:**
   - Divides video into 10 evenly-distributed positions
   - Calculates timestamps across video timeline

2. **Parallel Processing:**
   - Uses ThreadPoolExecutor with configurable thread count
   - Each thread processes one video position

3. **Crop Detection Per Sample:**
   ```bash
   ffmpeg -ss {timestamp} -i input.mkv -vf cropdetect -frames:v 1 -f null -
   ```

4. **Result Aggregation:**
   - Collects crop dimensions from all samples
   - Uses Counter to find most common dimensions
   - Returns most frequent crop value

5. **Progress Tracking:**
   - Real-time callback with position updates
   - Shows progress: `Crop Detection: [====>    ] 5/10`

### Crop Modes

#### Automatic Crop (`--crop auto`)
Detects black bars automatically using cropdetect filter.

#### Manual Crop (`--crop width:height:x:y`)
Format based on **original video dimensions**:
- width: Target width in pixels
- height: Target height in pixels
- x: Horizontal offset from left
- y: Vertical offset from top

Example: `--crop 1920:800:0:140`

#### Aspect Ratio Crop (`--crop 16:9`, `--crop 21:9`)
Calculates crop dimensions to achieve target aspect ratio while maximizing resolution.

Algorithm:
```python
def calculate_aspect_ratio_crop(video_width, video_height, target_ratio):
    target_aspect = parse_ratio(target_ratio)  # e.g., 16/9 = 1.777...
    current_aspect = video_width / video_height

    if current_aspect > target_aspect:
        # Video is wider, crop width
        new_width = int(video_height * target_aspect)
        new_height = video_height
        x_offset = (video_width - new_width) // 2
        y_offset = 0
    else:
        # Video is taller, crop height
        new_width = video_width
        new_height = int(video_width / target_aspect)
        x_offset = 0
        y_offset = (video_height - new_height) // 2

    return (new_width, new_height, x_offset, y_offset)
```

#### CinemaScope Presets
- `cinema`: 2.35:1 aspect ratio
- `cinema-modern`: 2.39:1 aspect ratio

### Limitations

-   **Dolby Vision (auto crop only):** When `--crop auto` and DV source: reads L5 Active Area offsets via `dovi_tool info`, produces `crop=W:H:X:Y` filter. Manual crop (`width:height:x:y`) and ratio crop modes (`16:9`, `21:9`, cinema, etc.) are blocked for DV encoding and will produce an error. Scale remains unsupported for DV.
-   **Non-auto crop modes:** Manual and ratio crop modes require `cropdetect` scanning (10 FFmpeg invocations); blocked for DV
-   **Variable Black Bars:** Uses most common dimensions; irregular bars may not be perfectly cropped
-   **Performance:** Non-DV auto crop requires 10 FFmpeg invocations; can be slow for large files

**Note:** The `hdr_forge info` display shows `RPU Crop` when L5 active area offsets are detected in DV metadata.

## HDR Metadata Extraction

### Method

Uses ffprobe with frame-level metadata extraction:

```bash
ffprobe -hide_banner \
        -show_frames \
        -read_intervals %+#1 \
        -select_streams v:0 \
        -print_format json \
        input.mkv
```

### Parsing Process

1. **Extract First Frame:**
   - Uses `-read_intervals %+#1` to read only first frame
   - Parses JSON output

2. **Parse Side Data:**
   ```python
   for side_data in frame['side_data_list']:
       if side_data['side_data_type'] == 'Mastering display metadata':
           # Parse mastering display
       if side_data['side_data_type'] == 'Content light level metadata':
           # Parse MaxCLL/MaxFALL
   ```

3. **Fallback Values:**
   - If metadata missing, uses None
   - Encoder decides whether to use fallback defaults

### Metadata Formats

#### Master Display Metadata

Format: `G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)`

Example: `G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)`

Components:
- G(x,y): Green primary (BT.2020 chromaticity coordinates × 50000)
- B(x,y): Blue primary
- R(x,y): Red primary
- WP(x,y): White point
- L(max,min): Luminance (max in cd/m², min in cd/m² × 10000)

#### Content Light Level Metadata

Format: `MaxCLL,MaxFALL`

Example: `1000,400`

Components:
- MaxCLL: Maximum Content Light Level (cd/m²)
- MaxFALL: Maximum Frame-Average Light Level (cd/m²)

## HDR to SDR Tone Mapping

### Filter Chain

```
zscale=transfer=linear:npl=100,
format=gbrpf32le,
tonemap=hable:desat=0,
zscale=transfer=bt709:matrix=bt709:range=tv:primaries=bt709,
format=yuv420p
```

### Process Breakdown

1. **zscale (linear):**
   - Converts from PQ (ST.2084) to linear light
   - `npl=100`: Normalizes peak luminance to 100 cd/m²

2. **format (gbrpf32le):**
   - Converts to 32-bit float RGB
   - Required for tone mapping operations

3. **tonemap (hable):**
   - Applies Hable (Uncharted 2) tone mapping curve
   - `desat=0`: No desaturation

4. **zscale (bt709):**
   - Converts back to BT.709 color space
   - Sets SDR transfer function (gamma)
   - Sets BT.709 matrix and primaries
   - `range=tv`: Limited range (16-235)

5. **format (yuv420p):**
   - Converts to 8-bit 4:2:0 YUV
   - Standard SDR pixel format

### Hable Tone Mapping Curve

The Hable operator provides filmic tone mapping with good detail preservation:

```
f(x) = ((x*(A*x+C*B)+D*E)/(x*(A*x+B)+D*F))-E/F

Where:
A = 0.15 (Shoulder Strength)
B = 0.50 (Linear Strength)
C = 0.10 (Linear Angle)
D = 0.20 (Toe Strength)
E = 0.02 (Toe Numerator)
F = 0.30 (Toe Denominator)
```

## Resolution Scaling

### Height Mode (Default)

Fixed target height, width calculated from aspect ratio:

```python
def calculate_height_scale(video_width, video_height, target_height):
    if video_height <= target_height:
        return None  # No upscaling

    aspect_ratio = video_width / video_height
    new_height = target_height
    new_width = int(target_height * aspect_ratio)

    # Ensure even dimensions (required for chroma subsampling)
    new_width = new_width - (new_width % 2)

    return (new_width, new_height)
```

### Adaptive Mode

Scales to fit within bounds without exceeding width or height:

```python
def calculate_adaptive_scale(video_width, video_height, max_width, max_height):
    if video_width <= max_width and video_height <= max_height:
        return None  # Already within bounds

    width_scale = max_width / video_width
    height_scale = max_height / video_height
    scale_factor = min(width_scale, height_scale)

    new_width = int(video_width * scale_factor)
    new_height = int(video_height * scale_factor)

    # Ensure even dimensions
    new_width = new_width - (new_width % 2)
    new_height = new_height - (new_height % 2)

    return (new_width, new_height)
```

### FFmpeg Scale Filter

```bash
# Height mode
-vf scale=-2:1080

# Adaptive mode (fits within 1920x1080)
-vf scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease

# With crop applied first
-vf crop=1920:800:0:140,scale=-2:1080
```

### Scaling Considerations

-   **Order:** Crop → Scale (if both enabled)
-   **Aspect Ratio:** Always preserved
-   **Even Dimensions:** Required for 4:2:0 chroma subsampling
-   **Upscaling:** Blocked (no quality improvement)
-   **Dolby Vision:** Not supported (RPU metadata is resolution-dependent)

## Dolby Vision Processing

### Three Processing Workflows

#### Workflow 1: DV → HDR10/SDR (Copy Mode)

Fast extraction without re-encoding:

```
1. Extract base layer (dovi_tool remove)
2. Mux BL + audio/subs → output.mkv
3. Cleanup temp directory
```

#### Workflow 2: DV → DV (Copy Mode, Profile Conversion)

Profile conversion without re-encoding:

```
1. Extract base layer (dovi_tool remove)
2. Extract RPU with profile conversion
3. If Profile 7 → Profile 7:
   a. Extract Enhancement Layer
   b. Multiplex BL + EL
4. Inject RPU into BL (or BL+EL)
5. Mux HEVC + audio/subs → output.mkv
6. Cleanup temp directory
```

#### Workflow 3: DV → Any Format (With Re-encoding)

Full re-encoding workflow:

```
1. Extract base layer (dovi_tool remove)
2. Mux BL + audio/subs → temp_BL.mkv
3. Re-encode temp_BL.mkv → encoded.mkv (FFmpeg)
4. Delete temp_BL.mkv

If target is HDR10/SDR:
   5. Move encoded.mkv to target output
   6. Cleanup temp directory
   → DONE

If target is Dolby Vision:
   5. Extract encoded HEVC from encoded.mkv
   6. Extract RPU with profile conversion
   7. If Profile 7 → Profile 7:
      a. Extract Enhancement Layer
      b. Multiplex encoded BL + EL
   8. Inject RPU into encoded HEVC
   9. Mux final HEVC + audio/subs → output.mkv
   10. Cleanup temp directory
```

### Profile Conversion Matrix

| Source | Target | Copy | Re-encode |
|--------|--------|------|-----------|
| Profile 5 | 5 (preserved) | Supported | Not applicable |
| Profile 5 | 8.1 | Not supported | Supported (Vulkan req.) |
| Profile 7 (EL) | 7 (with EL, preserved) | Supported | Not supported |
| Profile 7 (EL) | 8.1 | Supported (EL discarded) | Supported |
| Profile 8 | 8.1 | Supported | Supported |

**dovi_tool mode mapping:**
| Source | Mode | Process |
|--------|------|---------|
| Profile 5 | 3 | IPTPQc2 → MEL conversion (requires Vulkan/libplacebo) |
| Profile 7 | 2 | MEL preservation (copy) or MEL conversion (re-encode) |
| Profile 8 | 2 | MEL → MEL conversion |

### Profile 5 Re-encoding Workflow

Profile 5 (IPTPQc2) uses a non-standard color space and cannot be converted via copy mode. Full re-encoding is required:

```
1. Extract base layer (dovi_tool remove)
2. Mux BL + audio/subs → temp_BL.mkv
3. Re-encode with libplacebo color space conversion filter:
   - For HDR/DV output: libplacebo=colorspace=bt2020nc:color_primaries=bt2020:color_trc=smpte2084:format=yuv420p10le
   - For SDR output: libplacebo=colorspace=bt709:color_primaries=bt709:color_trc=bt709:format=yuv420p10le|yuv420p
4. Delete temp_BL.mkv

If target is HDR10/SDR:
   5. Output encoded.mkv
   → DONE

If target is Dolby Vision Profile 8.1:
   5. Extract encoded HEVC from encoded.mkv
   6. Extract RPU with dovi_tool mode 3 (Profile 5 → 8.1 mapping)
   7. Inject RPU into encoded HEVC
   8. Mux final HEVC + audio/subs → output.mkv
   9. Cleanup temp directory
```

**Requirements:**
- FFmpeg compiled with `--enable-libplacebo` support
- Vulkan GPU driver
- `-init_hw_device vulkan` prepended to ffmpeg command

**Important:** Profile 5 sources cannot use `--video-codec copy` for profile conversion. Full re-encode with `--dv-profile 8` or format conversion (`--hdr-sdr-format hdr10`/`sdr`) is required.

### RPU Extraction Pipeline

```bash
# Extract RPU with mode conversion
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | \
dovi_tool -m {MODE} extract-rpu - -o output.rpu
```

### Base Layer Extraction Pipeline

```bash
# Remove RPU to get HDR10 base layer
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | \
dovi_tool remove - -o output_BL.hevc
```

### RPU Injection Pipeline

```bash
# Inject RPU back into encoded HEVC
dovi_tool inject-rpu -i encoded.hevc --rpu-in RPU.rpu -o final.hevc
```

### Enhancement Layer Operations (Profile 7)

```bash
# Extract Enhancement Layer
ffmpeg -i input.mkv -c:v copy -bsf:v hevc_mp4toannexb -f hevc - | \
dovi_tool demux - --el-only -o EL.hevc

# Multiplex BL + EL
dovi_tool mux -i BL.hevc --el EL.hevc -o BL_EL.hevc
```

### Temporary File Management

```python
temp_dir = target_file.parent / f".hdr_forge_temp_{target_file.stem}"

# Created files (example for DV re-encoding workflow):
temp_dir/
├── video_BL.hevc           # Base layer (deleted after temp_BL.mkv)
├── video_BL.mkv            # BL + audio/subs (deleted after encoding)
├── video_BL_Encoded.mkv    # Encoded BL (deleted after HEVC extraction)
├── video_encoded_BL.hevc   # Encoded BL HEVC (deleted after RPU injection)
├── RPU.rpu                 # RPU metadata (deleted after injection)
├── video_EL.hevc           # Enhancement Layer (if Profile 7)
├── video_encoded_BL_EL.hevc # BL+EL multiplexed (if Profile 7)
└── video_encoded_BL_RPU.hevc # Final with RPU (moved to output)

# Cleanup process:
# - Files deleted incrementally as soon as no longer needed
# - Final cleanup: shutil.rmtree(temp_dir)
```

## Video Sampling

### Sample Time Calculation

```python
def _determine_video_sample(sample_settings):
    if not sample_settings.enabled:
        return None

    video_duration = video.get_duration_seconds()

    # Custom sample
    if sample_settings.start_time and sample_settings.end_time:
        start = max(0, min(sample_settings.start_time, video_duration))
        end = max(start, min(sample_settings.end_time, video_duration))
        return (start, end)

    # Auto sample: 30 seconds starting at 1 minute
    start = min(video_duration, 60)
    end = min(video_duration, 60 + 30)

    # Fallback if video shorter than 60s
    if start == video_duration:
        start = 0
        end = min(video_duration, 30)

    return (start, end)
```

### FFmpeg Sample Parameters

```python
output_options = {
    'ss': str(start_time),  # Seek to start
    't': str(end_time - start_time)  # Duration
}
```

## Command Reference

Complete parameter reference for all HDR Forge subcommands.

### Global Options

```
hdr_forge --version              Show program version
hdr_forge --help                 Show help message
```

### info Subcommand

```
hdr_forge info -i INPUT          Display video metadata

Options:
  -i, --input INPUT         Input video file
  -d, --debug               Enable debug output
```

### detect-logo Subcommand

```
hdr_forge detect-logo -i INPUT   Detect logos in video

Options:
  -i, --input INPUT         Input video file
  -e, --export PATH         Export detected logo mask as PNG image
  -d, --debug               Enable debug output
```

### extract-metadata Subcommand

```
hdr_forge extract-metadata -i INPUT   Extract DV/HDR10/HDR10+ metadata

Options:
  -i, --input INPUT         Input video file
  -o, --output FOLDER       Output folder for metadata files
  --to-dv-8                 Convert extracted DV metadata to Profile 8.1
  --crop                    Crop RPU active area offsets (passes --crop to dovi_tool)
  -d, --debug               Enable debug output
```

### inject-metadata Subcommand

```
hdr_forge inject-metadata -i INPUT -o OUTPUT   Inject DV/HDR10/HDR10+ metadata

Description:
  Inject Dolby Vision/HDR10/HDR10+ metadata into HEVC stream without re-encoding

Required Arguments:
  -i, --input INPUT         Input video file
  -o, --output OUTPUT       Output video file

Optional Arguments:
  --rpu PATH                RPU file (Dolby Vision metadata)
  --el PATH                 Enhancement Layer file (DV)
  --hdr10 PATH              HDR10 metadata JSON file
  --hdr10plus PATH          HDR10+ metadata JSON file
  -d, --debug               Enable debug output
```

### edit Subcommand

```
hdr_forge edit -i INPUT [OPTIONS]   Edit MKV files in-place (no re-encoding)

Required Arguments:
  -i, --input INPUT         Input MKV file or directory

Optional Arguments:
  -s, --subtitle-flags MODE Subtitle handling: copy, auto, auto>LANG, per-track overrides
                            Note: remove mode requires convert (remux needed)
  -d, --debug               Enable debug output

Requirements:
  mkvpropedit (part of MKVToolNix) must be in PATH or lib/ directory
```

### convert Subcommand

```
hdr_forge convert -i INPUT -o OUTPUT [OPTIONS]

Required Arguments:
  -i, --input INPUT         Input video file or folder
  -o, --output OUTPUT       Output video file or folder

Encoder Selection:
  -v, --video-codec CODEC   Video codec: h265, h264, av1, copy (default: h265)
  --encoder CODEC           Force specific encoder: auto, libx265, libx264,
                            libsvtav1, hevc_nvenc, h264_nvenc (default: auto)

Audio Options:
  -a, --audio-codec CODEC   Audio codec per track: copy, remove, aac, ac3,
                            eac3, flac. Use language/ID targeting:
                            ger:aac, eng:ac3, 1:remove, dts>aac (default: copy)
  --audio-default LANG_ID   Set default audio track by language (ger, eng)
                            or track ID (1, 2, etc.)

Subtitle Options:
  -s, --subtitle-flags MODE Subtitle management: copy, remove, auto,
                            auto>LANG (e.g., auto>ger) (default: copy)

Encoding Presets:
  -p, --preset PRESET       Content preset: auto, film, film4k, film4k:fast,
                            grain, grain:ffmpeg, banding, video, action,
                            animation (default: auto)
  --hw-preset PRESET        Hardware preset: cpu, cpu:balanced, cpu:quality,
                            gpu, gpu:balanced, gpu:quality, balanced, quality
                            (default: cpu:balanced)

Quality Settings:
  --quality VALUE           Universal quality (0-51, lower = better)
  --speed PRESET            Speed preset (libx265/libx264 only):
                            ultrafast, superfast, veryfast, faster, fast,
                            medium, medium:plus, slow, slow:plus, slower, veryslow

Cropping & Scaling:
  --crop MODE               Crop mode: off, auto, width:height:x:y,
                            16:9, 21:9, european, us-widescreen,
                            cinema, cinema-modern (default: off)
                            Note: For DV only --crop auto is supported (uses RPU L5 offsets)
  --scale RESOLUTION        Target resolution: FUHD, UHD, QHD+, WQHD, FHD, HD,
                            QHD, SD, or numeric height
  --scale-mode MODE         Scale mode: height, adaptive (default: height)

Content Analysis & Filtering:
  --grain MODE              Grain analysis: off, auto, cat1, cat2, cat3 (default: off)
  --remove-logo MODE        Logo removal: off, auto, delogo:auto, delogo:top-left,
                            mask:auto, mask:top-left (default: off)
  --sample TIME             Process sample: auto or start:end in seconds
  --dar-ratio RATIO         Custom display aspect ratio (e.g., 16:9, cinema)
  --vfilter FILTERS         Custom FFmpeg video filters

Format Conversion:
  --hdr-sdr-format FORMAT   Target format: auto, hdr, hdr10, sdr (default: auto)
  --dv-profile PROFILE      Dolby Vision profile: auto, 8 (default: auto)
                            Note: Profile 5 and Profile 7 → 7 preserve format via copy mode
                            Profile 5 → 8.1 and Profile 7 → 8.1 require re-encoding

Expert Options:
  --encoder-params PARAMS   Encoder-specific parameters
  --master-display STRING   Custom master display metadata
  --max-cll STRING          Custom MaxCLL/MaxFALL values
  --bit-depth DEPTH         Bit depth override for SDR: auto, 8, 10
  --color-primaries-flag PRIM  Color primaries (libx265/libx264 only):
                            bt470bg, smpte170m, bt709, bt2020
  --try-fix                 Ignore non-fatal errors during video import
  --threads COUNT           Number of threads for encoding
  --shutdown                Shutdown system after conversion completes

Debug:
  -d, --debug               Enable debug output
```

**For detailed parameter explanations, see earlier sections of this document.**

## See Also

-   [Encoder Guide](encoders.md) - Detailed encoder information
-   [Advanced Examples](advanced-examples.md) - Complex encoding scenarios
-   [Troubleshooting](troubleshooting.md) - Common issues and solutions
