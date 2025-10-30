# Advanced Examples

This document provides comprehensive examples for complex encoding scenarios with HDR Forge.

## Table of Contents

- [Hardware Acceleration](#hardware-acceleration)
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

## HDR Metadata Injection

### Basic Injection

```bash
# Inject master display metadata
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)"

# With MaxCLL/MaxFALL
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

### Common Display Metadata Presets

```bash
# Standard BT.2020 / DCI-P3 D65
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# LG OLED C9 Display
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(850,0.0001)" \
  --max-cll "800,400"

# Sony X900H Display
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,3000)R(34000,16000)WP(15635,16450)L(1100,0.01)" \
  --max-cll "1100,450"
```

### Injection During Encoding

```bash
# Inject metadata while encoding
hdr_forge convert -i input.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# With quality settings
hdr_forge convert -i input.mkv -o output.mkv \
  --quality 16 \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"
```

### Updating Existing Metadata

```bash
# Replace incorrect metadata (no re-encoding)
hdr_forge inject-hdr-metadata -i wrong_metadata.mkv -o fixed.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1000,400"

# Update only MaxCLL values
hdr_forge inject-hdr-metadata -i video.mkv -o output.mkv \
  --master-display "G(13250,34500)B(7500,30000)R(34000,16000)WP(15635,16450)L(1000,0.05)" \
  --max-cll "1200,500"
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
