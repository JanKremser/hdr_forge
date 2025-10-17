# EHDR - Easy HDR Video Converter

[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Easy HDR10, Dolby Vision, and SDR video converter**

A command-line tool for converting video files to H.265/HEVC format with intelligent HDR metadata preservation, automatic quality optimization, and black bar detection.

---

## Features

- Convert HDR10, Dolby Vision, and SDR videos to H.265/HEVC
- Automatic black bar detection and cropping (multi-threaded)
- Resolution-based quality auto-scaling (CRF and preset)
- Batch folder processing
- HDR metadata preservation
- Audio and subtitle stream copying

All videos are converted to H.265 (HEVC). The compression settings are set dynamically based on the resolution. These can be influenced with the parameters `--crf` and `--preset`. Read the [ffmpeg H.265 documentation](https://trac.ffmpeg.org/wiki/Encode/H.265) for more details.

## Version History

**Current: Python v0.4.0** (Complete rewrite in Python)
- Previous Rust version available in `rust_legacy/` folder

## Installation

### Requirements

- Python 3.7 or higher
- [ffmpeg / ffprobe](https://ffmpeg.org/download.html)

**Only for Dolby Vision:**
- [x265](https://github.com/videolan/x265) (10-bit version) - [Windows builds](http://msystem.waw.pl/x265/)
- [dovi_tool](https://github.com/quietvoid/dovi_tool)

### Install EHDR

```bash
# Install from source
git clone https://github.com/yourusername/ehdr.git
cd ehdr
pip install -e .

# Or install directly with pip (when published)
pip install ehdr
```

### Verify Installation

```bash
ehdr --version
ffmpeg -version
ffprobe -version
```

## Usage

### Basic Conversion

Videos with black bars are automatically cropped. If you don't want this, use `--ncrop`.

**Convert HDR10 or SDR video:**
```bash
ehdr -i input.mkv -o output.mkv
```

### Dolby Vision

Dolby Vision is not yet automatically detected. Use the `--dv` parameter for Dolby Vision videos.
**Note:** Dolby Vision does not support cropping, so always use `--ncrop` with `--dv`.

```bash
ehdr -i input.mkv -o output.mkv --dv --ncrop
```

### Batch Processing

Convert multiple files in a folder:
```bash
ehdr -i ./input_folder -o ./output_folder
```

### Custom Quality Settings

```bash
# Higher quality (lower CRF = better quality, larger file)
ehdr -i input.mkv -o output.mkv --crf 12 --preset slow

# Faster encoding (faster preset = quicker encoding)
ehdr -i input.mkv -o output.mkv --preset faster
```

### Supported Formats

**Input:** `.mkv`, `.m2ts`, `.ts`, `.mp4`
**Output:** `.mkv` (H.265/HEVC video, original audio/subtitle streams)

## Command-Line Options

```
usage: ehdr [-h] -i INPUT -o OUTPUT [--crf CRF] [-p PRESET] [--ncrop] [--dv] [--version]

options:
  -h, --help            Show this help message
  -i, --input INPUT     Input video file or folder
  -o, --output OUTPUT   Output video file or folder
  --crf CRF             Constant Rate Factor (lower = higher quality)
  -p, --preset PRESET   Encoding preset (ultrafast to veryslow)
  --ncrop               Disable automatic black bar cropping
  --dv                  Enable Dolby Vision mode
  --version             Show program version
```

## Auto-Scaling

EHDR automatically optimizes encoding parameters based on video resolution:

**CRF (Quality):**
- 4K (6.1M+ pixels): CRF 13
- 2K-4K (2.2M-6.1M pixels): CRF 14-18 (scaled)
- Full HD (2.1M pixels): CRF 18
- Lower: CRF 19-20

**Preset (Speed):**
- 4K+ (8.8M+ pixels): superfast
- 2K-4K: faster
- Full HD: fast
- Lower: medium
