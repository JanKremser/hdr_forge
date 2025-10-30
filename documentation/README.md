# HDR Forge Documentation

Welcome to the HDR Forge documentation! This directory contains comprehensive guides for all features.

## Documentation Overview

### 📘 [Encoder Guide](encoders.md)
Complete information about all available video encoders:
- CPU encoders (libx265, libx264)
- GPU encoders (NVENC HEVC, NVENC H.264)
- Stream copy mode
- Performance comparisons
- Hardware requirements
- GPU setup instructions
- Best practices for each encoder

**Read this if you want to:**
- Choose the right encoder for your needs
- Set up GPU acceleration
- Understand encoder trade-offs
- Optimize encoding performance

### 🎯 [Advanced Examples](advanced-examples.md)
Comprehensive collection of encoding workflows:
- Hardware acceleration examples
- Encoding preset combinations
- Complex cropping scenarios
- Grain analysis workflows
- Scaling examples
- Video sampling strategies
- HDR metadata injection
- Dolby Vision processing
- Batch processing
- Quality optimization

**Read this if you want to:**
- See practical examples for complex scenarios
- Learn how to combine multiple features
- Find workflows for specific use cases
- Optimize your encoding pipeline

### 🔧 [Technical Details](technical-details.md)
In-depth technical information about HDR Forge internals:
- Encoder selection algorithm
- Parameter priority system
- Auto-CRF/CQ calculation
- Crop detection algorithm
- HDR metadata extraction
- Tone mapping process
- Resolution scaling logic
- Grain analysis system
- Dolby Vision processing workflows
- Progress tracking implementation

**Read this if you want to:**
- Understand how HDR Forge works internally
- Debug encoding issues
- Contribute to the codebase
- Fine-tune advanced parameters

### 🛠️ [Troubleshooting Guide](troubleshooting.md)
Solutions to common problems:
- Installation issues
- NVENC/GPU encoding problems
- Encoding failures and crashes
- Dolby Vision issues
- Quality problems
- Performance issues
- Crop/scale problems
- Error message explanations

**Read this if you:**
- Encounter errors or issues
- Need help with setup
- Experience quality problems
- Have performance issues

## Quick Reference

### Most Common Tasks

**Basic conversion:**
```bash
hdr_forge convert -i input.mkv -o output.mkv
```

**GPU-accelerated encoding:**
```bash
hdr_forge convert -i input.mkv -o output.mkv --hw-preset gpu:balanced
```

**High-quality encoding:**
```bash
hdr_forge convert -i input.mkv -o output.mkv --hw-preset cpu:quality
```

**Convert Dolby Vision to HDR10:**
```bash
hdr_forge convert -i dv.mkv -o hdr10.mkv --hdr-sdr-format hdr10
```

**Batch conversion:**
```bash
hdr_forge convert -i ./input_folder -o ./output_folder
```

### Most Useful Links

- **Installation help:** [Troubleshooting - Installation Issues](troubleshooting.md#installation-issues)
- **GPU setup:** [Encoder Guide - GPU Setup](encoders.md#checking-gpu-support)
- **Encoder comparison:** [Encoder Guide - Performance Comparison](encoders.md#performance-comparison)
- **Parameter priority:** [Technical Details - Parameter Priority](technical-details.md#parameter-priority-system)
- **Dolby Vision workflow:** [Technical Details - Dolby Vision Processing](technical-details.md#dolby-vision-processing)
- **Complex examples:** [Advanced Examples](advanced-examples.md)

## Getting Started

1. **Start with the main [README](../README.md)** for installation and basic usage
2. **Check [Encoder Guide](encoders.md)** to choose the right encoder
3. **Browse [Advanced Examples](advanced-examples.md)** for your specific use case
4. **Refer to [Technical Details](technical-details.md)** for advanced tuning
5. **Use [Troubleshooting](troubleshooting.md)** if you encounter issues

## Need Help?

1. Check the relevant documentation section above
2. Search for your specific issue in [Troubleshooting Guide](troubleshooting.md)
3. Look for similar examples in [Advanced Examples](advanced-examples.md)
4. Enable debug mode: `hdr_forge convert -i input.mkv -o output.mkv --debug`
5. Open an issue on GitHub with debug output

## Contributing to Documentation

If you find errors or want to improve the documentation:
1. Fork the repository
2. Make your changes
3. Submit a pull request

Documentation improvements are always welcome!
