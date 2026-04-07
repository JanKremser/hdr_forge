# Troubleshooting Guide

This guide helps you resolve common issues with HDR Forge.

## Table of Contents

- [Installation Issues](#installation-issues)
- [NVENC / GPU Encoding Issues](#nvenc--gpu-encoding-issues)
- [Encoding Issues](#encoding-issues)
- [Dolby Vision Issues](#dolby-vision-issues)
- [Quality Issues](#quality-issues)
- [Performance Issues](#performance-issues)
- [Crop/Scale Issues](#cropscale-issues)
- [Error Messages](#error-messages)

## Installation Issues

### "Command not found: hdr_forge"

**Problem:** HDR Forge not found in PATH after installation

**Solutions:**
```bash
# Verify installation
pip list | grep hdr-forge

# If not installed, install again
pip install -e .

# Or install from source
git clone https://github.com/JanKremser/hdr_forge.git
cd hdr_forge
pip install -e .

# Check if script is in PATH
which hdr_forge

# If not, add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
```

### "Command not found: ffmpeg"

**Problem:** FFmpeg not installed or not in PATH

**Solutions:**
```bash
# Install FFmpeg
# Ubuntu/Debian
sudo apt update
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Windows (Chocolatey)
choco install ffmpeg

# Verify installation
ffmpeg -version
ffprobe -version
```

### "Command not found: x265"

**Problem:** x265 encoder not available

**Solutions:**
```bash
# Check if FFmpeg has libx265 support
ffmpeg -hide_banner -encoders | grep libx265

# If not found, reinstall FFmpeg with x265 support
# Ubuntu/Debian
sudo apt install ffmpeg libx265-dev

# Or compile FFmpeg from source with --enable-libx265

# Arch Linux (usually included)
sudo pacman -S x265

# Verify
x265 --version
```

## NVENC / GPU Encoding Issues

### "NVENC encoder not available"

**Problem:** NVENC encoder not found when using GPU encoding

**Diagnosis:**
```bash
# Check available encoders
ffmpeg -hide_banner -encoders | grep nvenc

# Check CUDA support
ffmpeg -hwaccels

# Check GPU
nvidia-smi  # Should show your GPU

# Check NVIDIA driver version
nvidia-smi | grep "Driver Version"
```

**Solutions:**

1. **Verify GPU Model:**
   - HEVC NVENC requires GTX 1050 or newer
   - H.264 NVENC requires GTX 900 or newer
   - Check: https://developer.nvidia.com/video-encode-and-decode-gpu-support-matrix

2. **Update GPU Drivers:**
   ```bash
   # Linux (Ubuntu)
   sudo ubuntu-drivers autoinstall
   # Or manually install driver >= 470

   # Windows
   # Download latest driver from NVIDIA website (>= 472)
   ```

3. **Reinstall FFmpeg with NVENC Support:**
   ```bash
   # Check current FFmpeg configuration
   ffmpeg -buildconf | grep nvenc

   # If not included, install FFmpeg with NVENC
   # Ubuntu (PPA with NVENC)
   sudo add-apt-repository ppa:savoury1/ffmpeg4
   sudo apt update
   sudo apt install ffmpeg

   # Or compile from source:
   # ./configure --enable-nvenc --enable-cuda-nvcc --enable-libnpp
   ```

4. **Fallback to CPU Encoding:**
   ```bash
   # Use CPU encoding instead
   hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced
   ```

### Low GPU Utilization

**Problem:** GPU encoding slower than expected, low GPU usage

**Diagnosis:**
```bash
# Monitor GPU usage during encoding
nvidia-smi -l 1

# Check for CPU bottlenecks
htop  # or top
```

**Solutions:**

1. **Use Quality Preset:**
   ```bash
   # Better GPU utilization with quality preset
   hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:quality
   ```

2. **Check Source File Location:**
   - Ensure source files are on fast storage (SSD)
   - Slow HDD read speeds can bottleneck GPU encoding

3. **Parallel Encoding:**
   ```bash
   # Encode multiple files simultaneously to maximize GPU usage
   hdr_forge convert -i file1.mkv -o output1.mkv --encoder hevc_nvenc &
   hdr_forge convert -i file2.mkv -o output2.mkv --encoder hevc_nvenc &
   wait
   ```

4. **Reduce Decode Overhead:**
   - Complex filters (crop, scale) run on CPU and can bottleneck
   - Consider pre-processing or using simpler settings

### NVENC Quality Issues

**Problem:** Visible quality loss with GPU encoding

**Solutions:**

1. **Lower CQ Value:**
   ```bash
   # Use lower CQ (higher quality)
   hdr_forge convert -i input.mkv -o output.mkv \
     --encoder hevc_nvenc \
     --quality 16  # or lower
   ```

2. **Use High-Quality Preset:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv \
     --hw-preset gpu:quality
   ```

3. **Advanced NVENC Parameters:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv \
     --encoder hevc_nvenc \
     --encoder-params "preset=hq:cq=16:rc=vbr_hq"
   ```

4. **Consider CPU Encoding:**
   ```bash
   # For archival/critical content, use CPU
   hdr_forge convert -i input.mkv -o output.mkv \
     --hw-preset cpu:quality
   ```

## Encoding Issues

### Encoding Very Slow

**Problem:** Encoding taking much longer than expected

**Diagnosis:**
```bash
# Check CPU usage
htop  # Should show high CPU usage during CPU encoding

# Check for disk I/O issues
iotop  # Check if disk is bottleneck

# Check encoding speed in output
# Look for "Speed: 0.5x" or similar in progress
```

**Solutions:**

1. **Use Faster Preset:**
   ```bash
   # CPU encoding
   hdr_forge convert -i input.mkv -o output.mkv --speed faster

   # Or use balanced hardware preset
   hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:balanced
   ```

2. **Use GPU Encoding:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv --encoder hevc_nvenc
   ```

3. **Disable Heavy Features:**
   ```bash
   # Disable crop detection
   hdr_forge convert -i input.mkv -o output.mkv --crop off
   ```

4. **Use Lower Resolution:**
   ```bash
   # Scale to lower resolution
   hdr_forge convert -i 4k_input.mkv -o output.mkv --scale FHD
   ```

### Encoding Crashes or Fails

**Problem:** Encoding stops with error or crashes

**Diagnosis:**
```bash
# Enable debug mode for detailed output
hdr_forge convert -i input.mkv -o output.mkv --debug

# Check system resources
free -h  # Check RAM
df -h    # Check disk space

# Check system logs
dmesg | tail
journalctl -xe
```

**Solutions:**

1. **Check Disk Space:**
   ```bash
   # Ensure enough space for output + temp files
   df -h

   # Dolby Vision needs up to 2x source file size temporarily
   ```

2. **Check RAM:**
   ```bash
   # 4K encoding needs significant RAM
   free -h

   # Reduce parallel operations if low on RAM
   ```

3. **Check Input File:**
   ```bash
   # Verify input file is not corrupted
   ffmpeg -v error -i input.mkv -f null -

   # Try with different input file
   ```

4. **Update FFmpeg:**
   ```bash
   # Ensure latest FFmpeg version
   ffmpeg -version

   # Update if needed
   sudo apt update && sudo apt upgrade ffmpeg
   ```

### "Encoder not found" Error

**Problem:** Selected encoder not available

**Solutions:**

1. **Check Available Encoders:**
   ```bash
   # List all video encoders
   ffmpeg -hide_banner -encoders | grep -E "h264|h265|hevc"
   ```

2. **Use Different Encoder:**
   ```bash
   # Try libx265 instead
   hdr_forge convert -i input.mkv -o output.mkv --encoder libx265

   # Or let HDR Forge auto-select
   hdr_forge convert -i input.mkv -o output.mkv --encoder auto
   ```

3. **Install Missing Encoder:**
   ```bash
   # Install x265 libraries
   sudo apt install libx265-dev

   # Reinstall/rebuild FFmpeg
   ```

## Dolby Vision Issues

### "dovi_tool not found"

**Problem:** Dolby Vision operations fail due to missing dovi_tool

**Solutions:**

1. **Install dovi_tool:**
   ```bash
   # Arch Linux
   sudo pacman -S dovi_tool

   # Others: Download from GitHub
   # https://github.com/quietvoid/dovi_tool/releases

   # Place in PATH or project root
   mv dovi_tool ~/.local/bin/
   chmod +x ~/.local/bin/dovi_tool
   ```

2. **Verify Installation:**
   ```bash
   dovi_tool --help
   which dovi_tool
   ```

### Cropping and Scaling with Dolby Vision

**Auto crop is now supported for Dolby Vision** via RPU L5 Active Area offsets.  
**Manual crop, ratio crop, and scale remain unsupported** when preserving DV format.

#### Supported: Auto Crop (reads RPU L5 offsets)

```bash
# --crop auto uses RPU L5 Active Area offsets (default behavior)
hdr_forge convert -i dolby_vision.mkv -o output.mkv --crop auto

# Verify crop detected with info command
hdr_forge info -i dolby_vision.mkv  # shows "RPU Crop" when offsets are detected
```

No cropdetect scan is run. The crop is embedded in the RPU metadata itself.

#### Not Supported: Manual Crop / Ratio Crop / Scale

```bash
# These will produce an error when preserving DV:
hdr_forge convert -i dv.mkv -o output.mkv --crop 1920:800:0:140  ← ERROR
hdr_forge convert -i dv.mkv -o output.mkv --crop 21:9             ← ERROR
hdr_forge convert -i dv.mkv -o output.mkv --scale FHD             ← ERROR
```

**Workaround for manual crop/scale:** Convert to HDR10 first.

```bash
# Step 1: Extract HDR10 base layer (removes DV RPU)
hdr_forge convert -i dolby_vision.mkv -o hdr10.mkv --hdr-sdr-format hdr10

# Step 2: Apply manual crop or scale to HDR10 video
hdr_forge convert -i hdr10.mkv -o final.mkv --crop 1920:800:0:140 --scale FHD
```

### Dolby Vision Conversion Takes Very Long

**Problem:** Dolby Vision encoding much slower than regular HDR10

**Explanation:**
Dolby Vision workflow involves multiple steps (base layer extraction, RPU extraction, encoding, RPU injection) which increases processing time.

**Solutions:**

1. **Use Copy Mode:**
   ```bash
   # Profile conversion without re-encoding (fast)
   hdr_forge convert -i dolby_vision.mkv -o output.mkv \
     --video-codec copy \
     --dv-profile 8
   ```

2. **Convert to HDR10:**
   ```bash
   # If Dolby Vision not needed, convert to HDR10
   hdr_forge convert -i dolby_vision.mkv -o output.mkv \
     --hdr-sdr-format hdr10
   ```

3. **Use GPU Encoding:**
   ```bash
   # GPU encoding speeds up the re-encoding step
   hdr_forge convert -i dolby_vision.mkv -o output.mkv \
     --encoder hevc_nvenc \
     --crop off
   ```

### High Disk Usage During DV Conversion

**Problem:** Temporary disk usage up to 2x source file size

**Explanation:**
Dolby Vision workflow creates multiple intermediate files (base layer, RPU, encoded base layer) before final muxing.

**Solutions:**

1. **Ensure Sufficient Disk Space:**
   ```bash
   # Check available space
   df -h

   # Need approximately 2x source file size free
   ```

2. **Use Different Output Location:**
   ```bash
   # Output to drive with more space
   hdr_forge convert -i input.mkv -o /mnt/large_drive/output.mkv --crop off
   ```

3. **Clean Temp Files Manually:**
   ```bash
   # If conversion fails, temp files may remain
   # Remove manually: .hdr_forge_temp_* directories
   rm -rf .hdr_forge_temp_*
   ```

### Profile 5 Dolby Vision: "copy mode not supported"

**Problem:** Using `--video-codec copy` with a Profile 5 source fails with an error

**Explanation:**
Profile 5 (IPTPQc2) uses a non-standard color space which cannot be stream-copied for profile conversion. Full re-encoding is required.

**Solutions:**

1. **Use Re-encoding with `--dv-profile 8`:**
   ```bash
   # Profile 5 → Profile 8.1 via re-encode (requires Vulkan GPU driver)
   hdr_forge convert -i profile5_dv.mkv -o output.mkv --dv-profile 8 --quality 15
   ```

2. **Convert to HDR10 (faster alternative):**
   ```bash
   # Extracts HDR10 base layer without RPU
   hdr_forge convert -i profile5_dv.mkv -o output_hdr10.mkv --hdr-sdr-format hdr10
   ```

3. **Convert to SDR:**
   ```bash
   # Profile 5 → SDR with tone mapping
   hdr_forge convert -i profile5_dv.mkv -o output_sdr.mkv --hdr-sdr-format sdr
   ```

**Requirements for Profile 5 → 8.1:**
- FFmpeg compiled with `--enable-libplacebo` support
- Vulkan-capable GPU with drivers installed
- Significantly slower than other DV conversions (uses libplacebo color space conversion)

## Quality Issues

### Output Quality Lower Than Expected

**Problem:** Encoded video has visible quality loss

**Solutions:**

1. **Lower CRF/CQ Value:**
   ```bash
   # Use lower value (higher quality)
   hdr_forge convert -i input.mkv -o output.mkv --quality 14
   ```

2. **Use Quality Preset:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
   ```

3. **Use Slower Speed Preset:**
   ```bash
   # CPU encoding only
   hdr_forge convert -i input.mkv -o output.mkv --speed slow
   ```

4. **Switch to CPU Encoding:**
   ```bash
   # CPU encoding has better quality than GPU
   hdr_forge convert -i input.mkv -o output.mkv \
     --encoder libx265 \
     --hw-preset cpu:quality
   ```

### File Size Too Large

**Problem:** Output file larger than expected

**Solutions:**

1. **Increase CRF/CQ Value:**
   ```bash
   # Higher value = smaller file (lower quality)
   hdr_forge convert -i input.mkv -o output.mkv --quality 20
   ```

2. **Use Faster Speed Preset:**
   ```bash
   # Less compression efficiency but smaller file than very slow presets
   hdr_forge convert -i input.mkv -o output.mkv --speed faster
   ```

3. **Scale Down Resolution:**
   ```bash
   # 4K to 1080p significantly reduces file size
   hdr_forge convert -i 4k_input.mkv -o output.mkv --scale FHD
   ```

4. **Use CPU Encoding:**
   ```bash
   # CPU encoding has better compression than GPU
   hdr_forge convert -i input.mkv -o output.mkv --encoder libx265
   ```

### Grain Looks Blotchy or Compressed

**Problem:** Film grain not preserved properly

**Solutions:**

1. **Lower CRF:**
   ```bash
   hdr_forge convert -i film.mkv -o output.mkv \
     --quality 14
   ```

2. **Use Grain Tune:**
   ```bash
   hdr_forge convert -i film.mkv -o output.mkv \
     --encoder libx265 \
     --encoder-params "preset=slow:crf=14:tune=grain"
   ```

3. **Use CPU Encoding:**
   ```bash
   # CPU encoding better at preserving grain
   hdr_forge convert -i film.mkv -o output.mkv \
     --hw-preset cpu:quality
   ```

## Performance Issues

### Crop Detection Too Slow

**Problem:** Crop detection taking very long time

**Explanation:**
Automatic crop detection analyzes 10 video positions, requiring 10 FFmpeg invocations.

**Solutions:**

1. **Use Manual Crop:**
   ```bash
   # If you know dimensions, use manual crop
   hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140
   ```

2. **Use Aspect Ratio Crop:**
   ```bash
   # Faster than auto detection
   hdr_forge convert -i input.mkv -o output.mkv --crop 21:9
   ```

3. **Disable Cropping:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv --crop off
   ```

4. **Pre-analyze with Sample:**
   ```bash
   # Analyze crop on sample, then apply to full video
   hdr_forge convert -i input.mkv -o sample.mkv \
     --sample auto \
     --crop auto

   # View output to determine crop dimensions
   ffprobe sample.mkv

   # Apply crop manually to full video
   hdr_forge convert -i input.mkv -o output.mkv --crop 1920:800:0:140
   ```

### Batch Processing Too Slow

**Problem:** Batch encoding taking very long

**Solutions:**

1. **Use GPU Encoding:**
   ```bash
   hdr_forge convert -i ./videos -o ./encoded --encoder hevc_nvenc
   ```

2. **Parallel Processing:**
   ```bash
   # Process multiple files in parallel (manual)
   for file in ./videos/*.mkv; do
     hdr_forge convert -i "$file" -o "./encoded/$(basename "$file")" \
       --encoder hevc_nvenc &
   done
   wait
   ```

3. **Use Faster Preset:**
   ```bash
   hdr_forge convert -i ./videos -o ./encoded --speed faster
   ```

4. **Disable Heavy Features:**
   ```bash
   hdr_forge convert -i ./videos -o ./encoded \
     --crop off
   ```

## Crop/Scale Issues

### Black Bars Still Visible After Auto-Crop

**Problem:** Automatic crop didn't remove all black bars

**Explanation:**
Some videos have irregular black bars that vary throughout. Crop detection uses most common dimensions.

**Solutions:**

1. **Use Manual Crop:**
   ```bash
   # Determine exact crop needed
   ffmpeg -i input.mkv -vf cropdetect -f null - 2>&1 | grep crop=

   # Apply manual crop
   hdr_forge convert -i input.mkv -o output.mkv --crop 1920:804:0:138
   ```

2. **Try Different Crop Approach:**
   ```bash
   # Use aspect ratio crop instead
   hdr_forge convert -i input.mkv -o output.mkv --crop 21:9
   ```

### Scaling Not Working as Expected

**Problem:** Output resolution different than expected

**Solutions:**

1. **Check Scale Mode:**
   ```bash
   # Height mode (default) - sets exact height
   hdr_forge convert -i input.mkv -o output.mkv \
     --scale 1080 \
     --scale-mode height

   # Adaptive mode - fits within bounds
   hdr_forge convert -i input.mkv -o output.mkv \
     --scale 1920 \
     --scale-mode adaptive
   ```

2. **Check Source Resolution:**
   ```bash
   # Cannot upscale - only downscale supported
   ffprobe -v error -select_streams v:0 \
     -show_entries stream=width,height \
     -of csv=p=0 input.mkv
   ```

3. **Consider Crop First:**
   ```bash
   # Crop affects final dimensions
   hdr_forge convert -i input.mkv -o output.mkv \
     --crop auto \
     --scale FHD
   ```

### "Cannot scale Dolby Vision" Warning

**Problem:** Trying to scale while preserving Dolby Vision

**Solution:**
Convert to HDR10 first (see "Cannot crop/scale Dolby Vision" section above)

## Error Messages

### "Format upgrade not supported"

**Problem:** Attempting to upgrade video format (e.g., SDR → HDR10)

**Explanation:**
HDR Forge only supports format downgrades (DV → HDR10 → SDR), not upgrades.

**Solution:**
```bash
# Cannot do: SDR → HDR10 or HDR10 → DV
# Can only do: DV → HDR10, HDR10 → SDR, DV → SDR

# Keep original format or downgrade
hdr_forge convert -i hdr10.mkv -o output.mkv --hdr-sdr-format auto
hdr_forge convert -i hdr10.mkv -o output.mkv --hdr-sdr-format sdr
```

### "Speed preset not compatible with NVENC"

**Problem:** Using `--speed` parameter with NVENC encoder

**Explanation:**
The `--speed` parameter only works with libx265/libx264 encoders.

**Solution:**
```bash
# Don't use --speed with NVENC
# Instead use --encoder-params
hdr_forge convert -i input.mkv -o output.mkv \
  --encoder hevc_nvenc \
  --encoder-params "preset=hq:cq=16:rc=vbr_hq"
```

### "Video sampling not supported for Dolby Vision"

**Problem:** Trying to use `--sample` with Dolby Vision encoding

**Explanation:**
Dolby Vision RPU metadata requires the complete video stream.

**Solution:**
```bash
# Cannot sample when preserving Dolby Vision
# Either remove --sample or convert to HDR10
hdr_forge convert -i dolby_vision.mkv -o output.mkv \
  --hdr-sdr-format hdr10 \
  --sample auto
```

### "hevc_hdr_editor not found"

**Problem:** HDR metadata injection command fails

**Solution:**
```bash
# Install hevc_hdr_editor
# Download from: https://github.com/quietvoid/hevc_hdr_editor/releases

# Place in PATH or project root
mv hevc_hdr_editor ~/.local/bin/
chmod +x ~/.local/bin/hevc_hdr_editor

# Verify
hevc_hdr_editor --help
```

## Getting Help

If you continue to experience issues:

1. **Enable Debug Mode:**
   ```bash
   hdr_forge convert -i input.mkv -o output.mkv --debug
   ```

2. **Check System Information:**
   ```bash
   # FFmpeg version and configuration
   ffmpeg -version
   ffmpeg -buildconf

   # GPU information (if using NVENC)
   nvidia-smi

   # System resources
   free -h
   df -h
   ```

3. **Create Issue on GitHub:**
   - Include debug output
   - Include FFmpeg version and configuration
   - Include command used
   - Include error message
   - Include system information

4. **Check Documentation:**
   - [Encoder Guide](encoders.md)
   - [Technical Details](technical-details.md)
   - [Advanced Examples](advanced-examples.md)

## See Also

-   [Encoder Guide](encoders.md) - Detailed encoder information
-   [Technical Details](technical-details.md) - In-depth technical information
-   [Advanced Examples](advanced-examples.md) - Complex encoding scenarios
