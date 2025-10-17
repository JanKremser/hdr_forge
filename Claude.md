# EHDR - HDR Video Conversion CLI Tool

## Project Overview

**EHDR** (Easy HDR) is a command-line tool for converting video files to H.265/HEVC format with intelligent HDR metadata preservation. It specializes in handling HDR10, Dolby Vision, and SDR video content with automatic quality optimization and black bar detection.

**Current Version:** Python v0.4.0 (Complete rewrite)
**Legacy Version:** Rust v0.3.0 (available in `rust_legacy/` folder)

**Key Capabilities:**
- HDR10 and SDR video conversion to H.265/HEVC
- Dolby Vision Profile 8.1 support
- Automatic black bar detection and cropping (multi-threaded)
- Resolution-based quality auto-scaling
- Batch folder processing
- Metadata and stream preservation (audio, subtitles)

**License:** MIT

## Version Information

This project has been rewritten from Rust to Python:
- **Current (Python v0.4.0)**: Modern Python implementation with the same functionality
  - Location: `src/ehdr/`
  - Better maintainability and easier contributions
  - No Python dependencies beyond standard library

- **Legacy (Rust v0.3.0)**: Original Rust implementation
  - Location: `rust_legacy/`
  - Preserved for reference and compatibility

The documentation below covers **both versions** where applicable, with notes indicating version-specific details.

## Architecture

### Project Structure (Python v0.4.0)

```
ehdr/
├── src/
│   └── ehdr/
│       ├── __init__.py         # Package initialization
│       ├── main.py             # CLI entry point and conversion orchestration
│       ├── video.py            # Video metadata extraction and analysis
│       └── dolby_vision.py     # Dolby Vision RPU extraction
├── rust_legacy/                # Legacy Rust version (v0.3.0)
│   ├── src/
│   ├── Cargo.toml
│   └── Cargo.lock
├── pyproject.toml              # Python package configuration
├── setup.py                    # Setup script for pip install
├── requirements.txt            # Python dependencies (none - only external tools)
├── README.md                   # User documentation
├── Claude.md                   # Developer documentation
└── LICENSE                     # MIT License
```

### Project Structure (Rust Legacy v0.3.0)

```
rust_legacy/
├── src/
│   ├── main.rs                 # CLI entry point, argument parsing, conversion orchestration
│   ├── video/
│   │   └── mod.rs              # Video metadata extraction and analysis (333 lines)
│   └── dolpy_vision/
│       └── mod.rs              # Dolby Vision RPU extraction (37 lines)
├── Cargo.toml                  # Dependencies: serde_json, regex, clap
└── Cargo.lock                  # Dependency lock file
```

### Core Components (Python v0.4.0)

#### 1. **main.py**
The CLI entry point and orchestration layer:

- **CLI Interface**: Uses `argparse` for argument parsing
  - `-i/--input`: Input file or folder (required)
  - `-o/--output`: Output file or folder (required)
  - `--crf`: Constant Rate Factor for quality (auto-calculated by default)
  - `-p/--preset`: Encoding speed preset (auto-calculated by default)
  - `--ncrop`: Disable automatic cropping
  - `--dv`: Enable Dolby Vision mode

- **Two Conversion Functions**:
  - `convert_sdr_hdr10()`: Standard HDR10/SDR pipeline
  - `convert_dolby_vision()`: Dolby Vision specific pipeline

- **Batch Processing**: Detects if input is directory and processes all supported files

#### 2. **video.py**
The video analysis and metadata handling module:

**Key Class: `Video`**
```python
class Video:
    def __init__(self, filepath: str)
    # Attributes:
    filepath: Path
    metadata: Dict           # ffprobe metadata (JSON)
    width: int
    height: int
    crop_width: int
    crop_height: int
    crop_x: int
    crop_y: int
```

**Important Methods:**
- `_extract_metadata()`: Executes `ffprobe -v quiet -print_format json -show_format -show_streams`
- `get_pix_fmt()`: Returns pixel format (e.g., "yuv420p10le" for 10-bit HDR)
- `get_color_primaries()`, `get_color_space()`, `get_color_transfer()`: Color metadata
- `get_master_display()`: Extracts HDR mastering display metadata
- `get_auto_crf()`: Resolution-based CRF calculation
- `get_auto_preset()`: Resolution-based preset selection
- `crop_video()`: Multi-threaded black bar detection (10 threads using ThreadPoolExecutor)
- `is_hdr_video()`: Detects HDR by checking for 10-bit pixel format

#### 3. **dolby_vision.py**
Handles Dolby Vision specific processing:

- **Function: `extract_rpu()`**
  - Extracts RPU (Reference Processing Unit) metadata using `dovi_tool`
  - Pipeline: Video → ffmpeg (HEVC bitstream) → dovi_tool → RPU file
  - Caches RPU file to avoid re-extraction on subsequent runs

- **Function: `build_dolby_vision_params()`**
  - Builds x265 parameter list for Dolby Vision encoding
  - Applies Profile 8.1 settings and master display metadata

### Core Components (Rust Legacy)

#### 1. **main.rs** (222 lines)
The orchestration layer that handles:

- **CLI Interface**: Uses `clap` for argument parsing
  - `-i/--input`: Input file or folder (required)
  - `-o/--output`: Output file or folder (required)
  - `--crf`: Constant Rate Factor for quality (auto-calculated by default)
  - `-p/--preset`: Encoding speed preset (auto-calculated by default)
  - `--ncrop`: Disable automatic cropping
  - `--dv`: Enable Dolby Vision mode

- **Two Conversion Pipelines**:
  - `convert_sdr_hdr10()`: Standard HDR10/SDR pipeline
  - `convert_dolpy_vision()`: Dolby Vision specific pipeline

- **Batch Processing**: Detects if input is directory and processes all supported files

#### 2. **video/mod.rs** (333 lines)
The video analysis and metadata handling module:

**Key Struct: `Video`**
```rust
pub struct Video {
    filepath: String,
    json: Value,           // ffprobe metadata
    width: u32,
    height: u32,
    crop_width: u32,
    crop_height: u32,
    crop_x: u32,
    crop_y: u32,
}
```

**Important Methods:**
- `new()`: Initializes video by executing `ffprobe -v quiet -print_format json -show_format -show_streams`
- `get_pix_fmt()`: Returns pixel format (e.g., "yuv420p10le" for 10-bit HDR)
- `get_color_primaries()`, `get_color_space()`, `get_color_transfer()`: Color metadata
- `get_master_display()`: Extracts HDR mastering display metadata
- `get_auto_crf()`: Resolution-based CRF calculation
- `get_auto_preset()`: Resolution-based preset selection
- `crop_video()`: Multi-threaded black bar detection (10 threads)
- `is_hdr_video()`: Detects HDR by checking for 10-bit pixel format

**Auto-Scaling Logic:**

Resolution-based **CRF** (quality):
- UHD 4K (6,144,000+ pixels): CRF 13
- 2K range (2,211,841-6,143,999 pixels): CRF 14-18 (scaled linearly)
- Full HD (2,073,600-2,211,840 pixels): CRF 18
- Lower resolutions: CRF 19-20

Resolution-based **Preset** (speed):
- 4K+ (8,847,361+ pixels): superfast
- 2K-4K (2,073,601-8,847,360 pixels): faster
- Full HD (2,073,600 pixels): faster/fast
- Lower: medium

#### 3. **dolpy_vision/mod.rs** (37 lines)
Handles Dolby Vision specific processing:

- **Function: `extract_rpu()`**
  - Extracts RPU (Reference Processing Unit) metadata using `dovi_tool`
  - Pipeline: Video → ffmpeg (HEVC bitstream) → dovi_tool → RPU file
  - Caches RPU file to avoid re-extraction on subsequent runs

### Conversion Flow

#### Standard HDR10/SDR Flow:
1. Parse CLI arguments
2. Check input type (file vs. directory)
3. For each video:
   - Create `Video` instance (runs `ffprobe` to read metadata)
   - Optionally run `crop_video()` (10-threaded black bar detection)
   - Determine auto CRF/preset based on resolution
   - Build `ffmpeg` command with libx265 encoder
   - Apply HDR metadata parameters if HDR detected
   - Execute ffmpeg with real-time progress output

#### Dolby Vision Flow:
1. Extract RPU metadata using `dovi_tool`
2. Build conversion pipeline:
   - ffmpeg extracts raw video → piped to x265
   - Apply Dolby Vision Profile 8.1 parameters
   - Inject RPU metadata
   - Set VBV buffer (20000 kbps)
3. Execute with real-time progress

### Multi-Threading Strategy

**Crop Detection** (video/mod.rs:crop_video()):
- Spawns 10 concurrent threads
- Each thread analyzes a different 5-second segment of the video
- Uses Rust's `mpsc` (multi-producer, single-consumer) channel
- Collects results and selects most common crop dimensions
- Falls back to original dimensions if analysis fails

## Dependencies

### Rust Dependencies (Cargo.toml)
```toml
serde_json = "1.0"    # JSON parsing for ffprobe output
regex = "1.4"         # Metadata parsing (color primaries, master display)
clap = "2.33"         # CLI argument parsing
```

### External Runtime Dependencies

**Required:**
- `ffmpeg` - Video encoding and format conversion
- `ffprobe` - Video metadata extraction

**Dolby Vision Only:**
- `x265` (10-bit version) - H.265 encoder with Dolby Vision support
- `dovi_tool` - Dolby Vision metadata extraction/injection

## Working with the Codebase

### Python Version (v0.4.0)

#### Installation

```bash
# Install from source (development mode)
cd /path/to/ehdr
pip install -e .

# Or install as package
pip install .

# Verify installation
ehdr --version
```

#### Running the Tool

```bash
# Direct execution
ehdr -i input.mkv -o output.mkv

# Run as module (without installing)
python -m ehdr.main -i input.mkv -o output.mkv
```

#### Development

```bash
# No external Python dependencies!
# All functionality relies on external tools (ffmpeg, ffprobe, etc.)

# Test the package structure
python -c "import ehdr; print(ehdr.__version__)"

# Format code (if using black)
black src/ehdr/

# Type checking (if using mypy)
mypy src/ehdr/
```

### Rust Version (Legacy)

#### Building the Project

```bash
# Navigate to rust_legacy folder
cd rust_legacy/

# Debug build
cargo build

# Release build (optimized)
cargo build --release

# Run directly
cargo run -- -i input.mkv -o output.mkv

# Install system-wide
cargo install --path .
```

### Running Tests

Currently no test suite exists. Consider adding:
- Unit tests for metadata parsing
- Integration tests with sample video files
- Crop detection accuracy tests

### Key Code Patterns

#### 1. Metadata Extraction Pattern
```rust
// All metadata comes from ffprobe JSON output
let video = Video::new(input_path);
if video.is_hdr_video() {
    // Apply HDR-specific parameters
}
```

#### 2. Process Spawning Pattern
```rust
// All external tools executed via Command::new()
let output = Command::new("ffprobe")
    .args(&["-v", "quiet", "-print_format", "json"])
    .output()
    .expect("Failed to execute ffprobe");
```

#### 3. Platform-Specific Constants
```rust
#[cfg(target_os = "windows")]
const LINE_ENDING: &'static str = "\r\n";

#[cfg(not(target_os = "windows"))]
const LINE_ENDING: &'static str = "\n";
```

### Important Implementation Details

#### HDR Detection Logic
HDR is detected by checking pixel format:
```rust
pub fn is_hdr_video(&self) -> bool {
    self.get_pix_fmt().contains("10le") // 10-bit = HDR
}
```

#### Master Display Metadata Parsing
Uses regex to extract luminance and color primaries:
```rust
let re_display = Regex::new(r"mastering display data: (.*)").unwrap();
// Format: "G(x,y)B(x,y)R(x,y)WP(x,y)L(max,min)"
```

#### FFmpeg Command Construction
All encoding uses piped input/output:
```rust
ffmpeg -y -i input.mkv \
  -c:v libx265 -preset <preset> -crf <crf> \
  -x265-params "hdr-opt=1:..." \
  -c:a copy -c:s copy \
  output.mkv
```

### Common Gotchas

1. **Dolby Vision Cropping**: Dolby Vision mode does NOT support automatic cropping. Always use `--dv --ncrop` together.

2. **10-bit x265 Required**: Standard x265 builds may not support Dolby Vision. Ensure you have a 10-bit capable build.

3. **Crop Detection Memory**: 10 concurrent ffmpeg processes can use significant memory (2-3GB per process on 4K video).

4. **RPU Caching**: Dolby Vision RPU files are cached. Delete `.rpu` files to re-extract if source changes.

5. **Line Ending Handling**: ffmpeg progress output parsing is platform-specific (Windows vs. Unix).

## Supported Formats

**Input Formats:**
- `.mkv` (Matroska)
- `.m2ts`, `.ts` (MPEG Transport Stream)
- `.mp4` (MP4)

**Output Format:**
- `.mkv` only (H.265/HEVC video, original audio/subtitle streams)

## Usage Examples

### Basic Conversion
```bash
ehdr -i movie.mkv -o movie_converted.mkv
```

### Dolby Vision Conversion
```bash
ehdr -i dolby_vision_movie.mkv -o output.mkv --dv --ncrop
```

### Batch Processing
```bash
ehdr -i ./input_folder -o ./output_folder
```

### Custom Quality Settings
```bash
# Lower CRF = higher quality, larger file
ehdr -i input.mkv -o output.mkv --crf 12 --preset slow
```

### Disable Auto-Cropping
```bash
ehdr -i input.mkv -o output.mkv --ncrop
```

## Future Improvement Ideas

1. **Testing**: Add unit and integration tests
2. **Audio Re-encoding**: Option to convert audio codecs
3. **Subtitle Handling**: Better subtitle format conversion
4. **Progress Bar**: Replace raw ffmpeg output with clean progress bar
5. **Resume Support**: Resume interrupted conversions
6. **Hardware Acceleration**: Support for NVENC, QSV, VideoToolbox
7. **Dolby Vision Auto-Detection**: Detect DV without `--dv` flag
8. **Configuration File**: Support for .ehdrrc config file
9. **Parallel Batch Processing**: Convert multiple files simultaneously
10. **Format Support**: Add AV1 output option

## Debugging Tips

### Check Video Metadata
```bash
ffprobe -v quiet -print_format json -show_streams input.mkv | jq .
```

### Test Crop Detection Manually
```bash
ffmpeg -i input.mkv -vf cropdetect -f null - 2>&1 | grep crop
```

### Verify HDR Metadata
```bash
ffprobe input.mkv 2>&1 | grep -E "(pix_fmt|color_|master)"
```

### Check Dolby Vision Profile
```bash
dovi_tool info input.mkv
```

## Contributing Guidelines

When contributing to this project:

1. **Code Style**: Follow standard Rust formatting (`cargo fmt`)
2. **Error Handling**: Use `expect()` with descriptive messages for external commands
3. **Documentation**: Add doc comments for new public functions
4. **Testing**: Add tests for new features (once test framework established)
5. **Compatibility**: Ensure Windows and Unix support for file operations

## Troubleshooting

### "Failed to execute ffmpeg"
- Ensure ffmpeg and ffprobe are installed and in PATH
- Verify: `ffmpeg -version` and `ffprobe -version`

### "Failed to execute x265"
- Dolby Vision requires standalone x265 binary (10-bit)
- Verify: `x265 --version` shows 10-bit support

### Crop Detection Hangs
- Very long videos may take time (10 segments analyzed)
- Use `--ncrop` to skip if needed
- Check system resources (10 ffmpeg processes)

### Output File is Larger
- Increase `--crf` value (lower quality, smaller file)
- Use slower preset for better compression: `--preset slow`

## License

MIT License - See LICENSE file for details

## Author

Jan Kremser <git@nerdbrief.de>

---

**Note**: This documentation was generated based on code analysis as of commit 3c00bc2. For the most up-to-date information, refer to the source code and README.md.
