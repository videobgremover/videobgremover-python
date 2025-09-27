# VideoBGRemover Python SDK

![PyPI version](https://badge.fury.io/py/videobgremover.svg)
![Python versions](https://img.shields.io/pypi/pyversions/videobgremover.svg)
![License](https://img.shields.io/pypi/l/videobgremover.svg)

The official Python SDK for [VideoBGRemover](https://videobgremover.com) - Remove video backgrounds with AI and compose videos with FFmpeg.

📖 **[Full Documentation](https://docs.videobgremover.com/)** | 🐙 **[GitHub Repository](https://github.com/videobgremover/videobgremover-python)**

## Features

🎥 **Video Background Removal**: Remove backgrounds from videos using state-of-the-art AI models  
🎨 **Video Composition**: Layer videos with custom backgrounds, effects, and positioning  
⚡ **Multiple Formats**: Support for WebM (with alpha), ProRes, stacked videos, and more  
🛠️ **FFmpeg Integration**: Professional video processing and encoding capabilities  
📱 **Easy to Use**: Simple, Pythonic API with type hints and validation  
🔧 **Flexible**: From simple background replacement to complex multi-layer compositions

## Installation

```bash
pip install videobgremover
```

### Requirements

- Python 3.9+
- FFmpeg (for video composition)
- VideoBGRemover API key

### FFmpeg Installation

The SDK requires FFmpeg for video processing:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian  
sudo apt update && sudo apt install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Quick Start

```python
import os
from videobgremover import VideoBGRemoverClient, Video, Background, Composition, EncoderProfile, Anchor, SizeMode

# Initialize client
client = VideoBGRemoverClient(os.getenv("VIDEOBGREMOVER_API_KEY"))

# Remove background from video
video = Video.open("https://example.com/video.mp4")
foreground = video.remove_background(client)

# Create composition with custom background
background = Background.from_color("#00FF00", 1920, 1080, 30.0)
composition = Composition(background)
composition.add(foreground).at(Anchor.CENTER).size(SizeMode.CONTAIN)

# Export final video
composition.to_file("output.mp4", EncoderProfile.h264())
```

## API Key Setup

Get your API key from [VideoBGRemover Dashboard](https://videobgremover.com/dashboard) and set it as an environment variable:

```bash
export VIDEOBGREMOVER_API_KEY="vbr_your_api_key_here"
```

Or pass it directly to the client:

```python
client = VideoBGRemoverClient("vbr_your_api_key_here")
```

## Usage Examples

### Basic Background Removal

```python
from videobgremover import VideoBGRemoverClient, Video, RemoveBGOptions, ModelSize

client = VideoBGRemoverClient("your_api_key")

# Load video from file or URL
video = Video.open("path/to/video.mp4")

# Configure processing options
options = RemoveBGOptions(
    prefer="webm_vp9",  # Output format preference
    model_size=ModelSize.LARGE,  # AI model size
    use_tensorrt=True  # GPU acceleration
)

# Remove background
foreground = video.remove_background(client, options)
```

### Video Composition

```python
from videobgremover import Background, Composition, Anchor, SizeMode

# Create background
bg = Background.from_image("background.jpg", fps=30.0)

# Create composition
comp = Composition(bg)

# Add video with positioning and effects
layer = comp.add(foreground, name="main_video")
layer.at(Anchor.CENTER).size(SizeMode.CONTAIN).opacity(0.9)

# Add picture-in-picture
pip_layer = comp.add(another_foreground, name="pip")
pip_layer.at(Anchor.TOP_RIGHT, dx=-50, dy=50).size(SizeMode.CANVAS_PERCENT, percent=25)

# Export
comp.to_file("composition.mp4", EncoderProfile.h264(crf=20))
```

### Video-on-Video Composition

```python
from videobgremover import VideoBGRemoverClient, Video, Background, Composition, Anchor, SizeMode, EncoderProfile

# Initialize client
client = VideoBGRemoverClient("your_api_key")

# Remove background from foreground video
foreground_video = Video.open("person_talking.mp4")
foreground = foreground_video.remove_background(client)

# Create composition with video background
background_video = Background.from_video("nature_scene.mp4")
comp = Composition(background_video)

# Add foreground video on top
comp.add(foreground, name="person").at(Anchor.CENTER).size(SizeMode.CONTAIN)

# Export final video
comp.to_file("person_on_nature.mp4", EncoderProfile.h264(crf=20))
```

### Multiple Output Formats

```python
# High-quality H.264
comp.to_file("output_hq.mp4", EncoderProfile.h264(crf=18, preset="slow"))

# Transparent WebM for web use
comp.to_file("output.webm", EncoderProfile.vp9(crf=25))

# ProRes for professional editing  
comp.to_file("output.mov", EncoderProfile.prores_4444())

# PNG sequence for frame-by-frame work
comp.to_file("frames/frame_%04d.png", EncoderProfile.png_sequence())
```

### Advanced Layer Effects

```python
layer = comp.add(foreground)

# Positioning
layer.at(Anchor.TOP_LEFT, dx=100, dy=50)  # Anchor with offset
layer.xy("W/2-w/2", "H/2-h/2")  # Custom expressions

# Sizing
layer.size(SizeMode.PX, width=800, height=600)  # Exact pixels
layer.size(SizeMode.CANVAS_PERCENT, percent=50)  # Percentage of canvas
layer.size(SizeMode.CONTAIN)  # Fit within canvas

# Visual effects
layer.opacity(0.8).rotate(15.0).crop(10, 20, 100, 200)

# Timing
layer.start(2.0).end(10.0)  # Show only between 2s-10s
layer.start(1.5)  # Start 1.5s later
layer.start(2.0).duration(5.0)  # Show for 5 seconds starting at 2s
```

### Progress Tracking

```python
def status_callback(status):
    print(f"Status: {status}")

foreground = video.remove_background(
    client, 
    options, 
    on_status=status_callback
)
```

### Error Handling

```python
try:
    foreground = video.remove_background(client)
except Exception as e:
    if "credits" in str(e).lower():
        print("Not enough credits. Please top up your account.")
    else:
        print(f"Video processing failed: {e}")
```

## Transparent Video Formats

The SDK supports multiple transparent video formats:

| Format | File Size | Quality | Compatibility | Best For |
|--------|-----------|---------|---------------|----------|
| **WebM VP9** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Web, APIs |
| **Stacked Video** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Universal |
| **ProRes 4444** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Professional editing |
| **PNG Sequence** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Frame-by-frame work |

**Recommendation**: Use WebM VP9 for most applications. Fall back to stacked video for maximum compatibility.

## Canvas and Sizing Rules

The composition system automatically determines canvas size:

1. **Background dimensions** (if background is set)
2. **Explicit canvas size** (if `.canvas()` or `.set_canvas()` called)  
3. **Auto-computed from layers** (with warning)

```python
# Explicit canvas
comp = Composition.canvas(1920, 1080, 30.0)

# Or set later
comp.set_canvas(3840, 2160, 60.0)  # 4K 60fps

# Or use empty background
comp = Composition(Background.empty(1920, 1080, 30.0))
```


## Development

### Setup Development Environment

```bash
git clone https://github.com/videobgremover/videobgremover-python.git
cd videobgremover-python

# Install with development dependencies
pip install -e ".[dev]"

# Or using uv
uv sync
```

### Running Tests

```bash
# Unit tests (no API calls)
pytest tests/ -m "not integration"

# Integration tests (requires API key and consumes credits)
export VIDEOBGREMOVER_API_KEY="your_key"
pytest tests/ -m integration

# All tests
pytest
```

### Code Quality

```bash
# Format code
ruff format

# Lint code  
ruff check

# Type checking
mypy src/
```

## API Reference

### Core Classes

- **`VideoBGRemoverClient`**: API client for background removal
- **`Video`**: Video loader (file or URL)
- **`Background`**: Background sources (color, image, video)
- **`Foreground`**: Transparent video representation
- **`Composition`**: Multi-layer video composition
- **`EncoderProfile`**: Video encoding settings

### Processing Options

- **`RemoveBGOptions`**: Background removal configuration
- **`ModelSize`**: AI model size (tiny, small, base, large)
- **`TransparentFormat`**: Output format preferences

### Layout & Effects

- **`Anchor`**: Positioning anchors (center, top-left, etc.)
- **`SizeMode`**: Sizing modes (contain, cover, px, percent)
- **`LayerHandle`**: Layer manipulation methods

## Examples

Check the `examples/` directory for complete working examples:

- [`basic_usage.py`](examples/basic_usage.py) - Simple background removal and replacement
- [`advanced_composition.py`](examples/advanced_composition.py) - Complex multi-layer compositions

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Full Documentation](https://docs.videobgremover.com/)
- 🐙 [GitHub Repository](https://github.com/videobgremover/videobgremover-python)
- 💬 [Discord Community](https://discord.gg/videobgremover)  
- 📧 [Email Support](mailto:support@videobgremover.com)
- 🐛 [Issue Tracker](https://github.com/videobgremover/videobgremover-python/issues)

## Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and updates.
