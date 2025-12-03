# Encoder Guide

This guide provides detailed information about all available video encoders in HDR Forge.

## Available Encoders

HDR Forge supports multiple encoders for different use cases:

### CPU Encoders (Software)

#### libx265 - H.265/HEVC Encoding
-   **Best for:** Maximum quality, archival purposes, smallest file sizes
-   **Performance:** Slower encoding (baseline)
-   **Quality:** Highest quality, best compression
-   **HDR Support:** Full (HDR10, Dolby Vision base layer)
-   **SDR Support:** Yes
-   **10-bit Support:** Yes
-   **Special Features:** Grain tuning, extensive parameter control

**When to use:**
-   Archival encoding where quality is paramount
-   When you need the smallest possible file size
-   Processing film with grain
-   No time constraints

#### libx264 - H.264/AVC Encoding
-   **Best for:** Maximum compatibility, SDR content
-   **Performance:** Slower encoding (similar to libx265)
-   **Quality:** High quality (but less efficient than H.265)
-   **HDR Support:** No (SDR only)
-   **SDR Support:** Yes
-   **10-bit Support:** No (8-bit only)
-   **Special Features:** Mature encoder with excellent quality

**When to use:**
-   Need maximum device compatibility
-   Targeting older devices without H.265 support
-   SDR content only

#### libsvtav1 - AV1 Encoding (Beta)
-   **Best for:** Long-term archival, streaming, future-proof encoding
-   **Performance:** Very slow encoding (2-5x slower than libx265)
-   **Quality:** Excellent, superior to HEVC
-   **HDR Support:** Full (HDR10, Dolby Vision base layer)
-   **SDR Support:** Yes
-   **10-bit Support:** Yes
-   **Special Features:** Next-generation codec, royalty-free, superior compression
-   **Status:** Beta feature

**When to use:**
-   Long-term archival with smallest possible file sizes (20-40% smaller than HEVC)
-   Streaming content (YouTube, Netflix support)
-   Future-proof encoding for modern platforms
-   When encoding time is not a constraint

**Advantages:**
-   20-40% smaller file sizes compared to HEVC at similar quality
-   Royalty-free open-source codec
-   Growing platform support (YouTube, Netflix, modern browsers)
-   Full HDR10 metadata preservation

**Limitations:**
-   Very slow encoding (slower than libx265)
-   Limited device compatibility (requires recent hardware/software)
-   Beta status - some features may be refined in future releases

### GPU Encoders (Hardware-Accelerated)

#### hevc_nvenc - NVIDIA H.265/HEVC Encoding
-   **Best for:** Fast encoding, batch processing, real-time workflows
-   **Performance:** 3-10x faster than CPU encoding
-   **Quality:** Good (slightly lower than libx265)
-   **HDR Support:** Full (HDR10, Dolby Vision base layer)
-   **SDR Support:** Yes
-   **10-bit Support:** Yes
-   **Requirements:** NVIDIA GPU (GTX 1050 or newer)
-   **Special Features:** Hardware acceleration, low power consumption

**When to use:**
-   Large batch processing
-   Time-sensitive workflows
-   Testing encoding settings (with `--sample`)
-   Real-time encoding needs

**Limitations:**
-   Dolby Vision metadata injection not yet fully supported
-   HDR→SDR metadata removal not yet supported
-   Slightly larger file sizes (10-20% more than libx265)

#### h264_nvenc - NVIDIA H.264/AVC Encoding
-   **Best for:** Fast encoding with maximum compatibility
-   **Performance:** 3-10x faster than CPU encoding
-   **Quality:** Good
-   **HDR Support:** No (SDR only)
-   **SDR Support:** Yes
-   **10-bit Support:** No
-   **Requirements:** NVIDIA GPU (GTX 1050 or newer)
-   **Special Features:** Hardware acceleration, low power consumption

**When to use:**
-   Fast encoding with maximum device compatibility
-   Batch processing SDR content
-   Real-time workflows with compatibility requirements

### Stream Copy Mode

#### copy - No Re-encoding
-   **Best for:** Format conversion without quality loss
-   **Performance:** Extremely fast (just container operations)
-   **Quality:** No quality loss (original stream)
-   **Use Cases:**
    -   Dolby Vision profile conversion (Profile 5/7 → Profile 8)
    -   Dolby Vision to HDR10 base layer extraction
    -   Container format conversion

**When to use:**
-   Converting Dolby Vision profiles without re-encoding
-   Extracting HDR10 base layer from Dolby Vision
-   Container format changes only

**Limitations:**
-   Cannot apply filters (crop, scale, tone mapping)
-   Cannot change quality or bitrate
-   Limited to container-level operations

## Encoder Selection

### Automatic Selection

HDR Forge automatically selects the best encoder based on:

1. **`--video-codec` parameter:**
   - `h265` → libx265 (default), hevc_nvenc
   - `h264` → libx264, h264_nvenc
   - `av1` → libsvtav1 (Beta)
   - `copy` → Stream copy mode

2. **`--hw-preset` parameter:**
   - `cpu:balanced` or `cpu:quality` → CPU encoder
   - `gpu:balanced` or `gpu:quality` → GPU encoder (if available)

3. **Available hardware:**
   - Checks for NVENC support
   - Falls back to CPU if GPU not available

### Manual Selection

Force a specific encoder with `--encoder`:

```bash
# Force libx265
hdr_forge convert -i input.mkv -o output.mkv --encoder libx265

# Force NVENC HEVC
hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc

# Force libx264
hdr_forge convert -i input.mkv -o output.mkv --encoder libx264

# Force NVENC H.264
hdr_forge convert -i input.mkv -o output.mkv --encoder h264_nvenc

# Force AV1 (Beta)
hdr_forge convert -i input.mkv -o output.mkv --encoder libsvtav1
```

## Performance Comparison

### Speed Benchmarks

**Typical encoding speeds (relative to real-time):**

| Encoder | 1080p | 4K | Notes |
|---------|-------|-----|-------|
| libx265 (medium) | 0.3-0.5x | 0.1-0.2x | Baseline |
| libx265 (fast) | 0.5-1.0x | 0.2-0.4x | Faster preset |
| libsvtav1 (preset 6) | 0.1-0.2x | 0.03-0.08x | Beta - Very slow |
| hevc_nvenc (default) | 3-5x | 1-2x | 3-10x faster |
| hevc_nvenc (hq) | 2-4x | 0.8-1.5x | Quality mode |
| libx264 (medium) | 0.4-0.6x | 0.15-0.25x | Similar to libx265 |
| h264_nvenc (default) | 4-6x | 1.5-3x | Very fast |

*Note: Actual speeds vary based on system hardware, content complexity, and encoding settings.*

### Quality Comparison

**At equivalent visual quality:**

| Encoder | File Size | Quality | Compression Efficiency |
|---------|-----------|---------|----------------------|
| libsvtav1 (Beta) | Smallest | Excellent | Best (120-140%) |
| libx265 | Small | Highest | Excellent (100%) |
| hevc_nvenc | +10-20% | Good | Good (85-90%) |
| libx264 | +30-50% | High | Moderate (70-80%) |
| h264_nvenc | +40-60% | Good | Moderate (65-75%) |

**Note:** AV1 achieves 20-40% smaller file sizes compared to HEVC at similar quality.

### Power Consumption

| Encoder Type | CPU Usage | GPU Usage | Total Power | Heat |
|--------------|-----------|-----------|-------------|------|
| CPU (libx265/libx264) | Very High | None | High | High |
| GPU (NVENC) | Low | Medium | Medium-Low | Low |

## Hardware Requirements

### CPU Encoding
-   **Processor:** Any modern CPU (more cores = faster)
-   **RAM:** 4GB minimum (8GB+ recommended for 4K)
-   **Optimal:** 8+ cores for parallel encoding

### GPU Encoding (NVENC)
-   **GPU:** NVIDIA GTX 1050 or newer
-   **Driver:** Linux 470+, Windows 472+
-   **VRAM:** 2GB minimum (4GB+ for 4K)
-   **Compute Capability:** 5.0 or higher

**NVENC Support by GPU Generation:**

| GPU Series | H.264 NVENC | HEVC NVENC | Max Streams |
|------------|-------------|------------|-------------|
| GTX 900 | ✓ | ✗ | 2 |
| GTX 1000 | ✓ | ✓ | 2 |
| GTX 1600 | ✓ | ✓ | 3 |
| RTX 2000+ | ✓ | ✓ | 3+ |
| RTX 4000+ | ✓ | ✓ (AV1) | 3+ |

### Checking GPU Support

```bash
# Check available NVENC encoders
ffmpeg -hide_banner -encoders | grep nvenc

# Check CUDA support
ffmpeg -hwaccels

# Expected output should include:
hevc_nvenc          # HEVC NVENC encoder
h264_nvenc          # H.264 NVENC encoder
cuda                # CUDA hardware acceleration
```

## Encoder Parameters

### Universal Parameters

Work with all encoders:

-   **`--quality VALUE`** - Quality setting (0-51, lower = better)
    -   Maps to CRF for libx265/libx264
    -   Maps to CQ for NVENC encoders
-   **`--hw-preset PRESET`** - Hardware preset (cpu:balanced, cpu:quality, gpu:balanced, gpu:quality)

### CPU-Specific Parameters

Only for libx265/libx264:

-   **`--speed PRESET`** - Encoding speed preset
    -   ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow
    -   Faster = quicker encoding, less compression
    -   Slower = better compression, longer encoding time

### Advanced: Encoder-Specific Parameters

Expert mode with `--encoder-params`:

#### libx265/libx264 Parameters

Format: `preset=<value>:crf=<value>:tune=<value>`

```bash
# High-quality film encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain"

# Fast encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=ultrafast:crf=20"

# Animation tuning
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --encoder-params "preset=medium:crf=16:tune=animation"
```

**Available Tunes:**
-   `grain` - Preserve film grain
-   `animation` - Optimize for animated content
-   `fastdecode` - Optimize for fast decoding
-   `zerolatency` - Optimize for streaming

#### NVENC Parameters

Format: `preset=<value>:cq=<value>:rc=<value>`

```bash
# High-quality NVENC encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"

# Fast NVENC encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=llhp:cq=22:rc=vbr"
```

**NVENC Presets:**
-   `default` - Balanced speed and quality
-   `slow` - Better quality, slower
-   `hq` - High quality mode
-   `llhq` - Low latency, high quality
-   `llhp` - Low latency, high performance

**NVENC Rate Control Modes:**
-   `vbr` - Variable bitrate
-   `vbr_hq` - Variable bitrate, high quality (recommended)
-   `cbr` - Constant bitrate (for streaming)
-   `cqp` - Constant quantization parameter

## Best Practices

### For Maximum Quality
```bash
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder libx265 \
  --hw-preset cpu:quality \
  --grain auto
```

### For Fast Batch Processing
```bash
hdr_forge convert -i ./input_folder -o ./output_folder \
  --encoder hevc_nvenc \
  --hw-preset gpu:balanced
```

### For Testing Settings
```bash
hdr_forge convert -i input.mkv -o sample.mkv \
  --sample auto \
  --encoder hevc_nvenc \
  --hw-preset gpu:quality
```

### For Archival (HEVC)
```bash
hdr_forge convert -i input.mkv -o archive.mkv \
  --encoder libx265 \
  --encoder-params "preset=veryslow:crf=12:tune=grain" \
  --crop auto
```

### For Archival (AV1 - Beta)
```bash
# Smallest file sizes with excellent quality
hdr_forge convert -i input.mkv -o archive_av1.mkv \
  --encoder libsvtav1 \
  --quality 18 \
  --crop auto
```

### For Streaming/Live
```bash
hdr_forge convert -i input.mkv -o stream.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=llhq:cq=20:rc=cbr"
```

## Troubleshooting

### AV1 Encoder Not Available

**Problem:** `libsvtav1 encoder not available` error

**Solutions:**
1. Check if SVT-AV1 is installed: `ffmpeg -hide_banner -encoders | grep svt_av1`
2. Install SVT-AV1 library:
   - **Arch Linux:** `sudo pacman -S svt-av1`
   - **Ubuntu/Debian:** `sudo apt install libsvtav1enc-dev`
   - **Windows:** Update FFmpeg to a version with SVT-AV1 support
3. Rebuild FFmpeg with `--enable-libsvtav1` flag if needed
4. Verify installation: `ffmpeg -hide_banner -encoders | grep svt_av1`

### NVENC Not Available

**Problem:** `NVENC encoder not available` error

**Solutions:**
1. Check GPU model (must be GTX 1050 or newer for HEVC NVENC)
2. Update GPU drivers (Linux: 470+, Windows: 472+)
3. Reinstall FFmpeg with NVENC support
4. Verify CUDA support: `ffmpeg -hwaccels`

### Low GPU Utilization

**Problem:** GPU encoding slower than expected

**Solutions:**
1. Use `--hw-preset gpu:quality` for better GPU utilization
2. Check for CPU bottlenecks (decoding, filtering)
3. Ensure source files are on fast storage (SSD)
4. Consider encoding multiple files in parallel

### Quality Issues with NVENC

**Problem:** Visible quality loss with GPU encoding

**Solutions:**
1. Lower CQ value: `--quality 16` or lower
2. Use high-quality preset: `--hw-preset gpu:quality`
3. Use encoder-specific params: `--encoder-params "preset=hq:cq=16:rc=vbr_hq"`
4. Consider CPU encoding for critical content

### Encoder Selection Errors

**Problem:** Encoder not matching expected hardware

**Solutions:**
1. Use explicit encoder selection: `--encoder hevc_nvenc`
2. Check available encoders: `ffmpeg -encoders | grep nvenc`
3. Verify hardware preset matches encoder (cpu: vs gpu:)

## See Also

-   [Technical Details](technical-details.md) - In-depth technical information
-   [Advanced Examples](advanced-examples.md) - Complex encoding scenarios
-   [Troubleshooting](troubleshooting.md) - Common issues and solutions
