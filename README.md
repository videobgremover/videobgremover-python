# VideoBGRemover Python SDK

![PyPI version](https://badge.fury.io/py/videobgremover.svg)
![Python versions](https://img.shields.io/pypi/pyversions/videobgremover.svg)
![License](https://img.shields.io/pypi/l/videobgremover.svg)

The official Python SDK for [VideoBGRemover](https://videobgremover.com) - Remove video backgrounds with AI and compose videos with FFmpeg.

📖 **[Full Documentation](https://docs.videobgremover.com/)** | 🐙 **[GitHub Repository](https://github.com/videobgremover/videobgremover-python)**

## Goal

This SDK simplifies using the VideoBGRemover API and abstracts the complexity of transparent video formats. It handles all the difficult parts of video composition, format conversion, and FFmpeg integration so you can focus on your application.

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

- **Python 3.9+**
- **FFmpeg** - Required binary for video processing operations
- **VideoBGRemover API key**

**Note:** FFmpeg must be available in your system PATH. The SDK automatically detects and uses your FFmpeg installation for video composition, format conversion, and metadata extraction.

## Quick Start

```python
import os
from videobgremover import VideoBGRemoverClient, Video, Background, Composition, EncoderProfile, Anchor, SizeMode

# Initialize client
client = VideoBGRemoverClient(os.getenv("VIDEOBGREMOVER_API_KEY"))

# Remove background from video
video = Video.open("https://example.com/video.mp4")

try:
    foreground = video.remove_background(client)
except Exception as e:
    if "credits" in str(e).lower():
        print("Not enough credits. Please top up your account.")
        exit(1)

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

## Cost & Credits

- Each video processing consumes credits based on video length
- Check your balance: `client.credits().remaining_credits`
- Processing typically takes 1-3 minutes depending on video length
- Failed jobs don't consume credits

## Usage Examples

### Basic Background Removal

```python
from videobgremover import VideoBGRemoverClient, Video, RemoveBGOptions, Prefer

client = VideoBGRemoverClient("your_api_key")

# Load video from file or URL
video = Video.open("path/to/video.mp4")

# Configure processing options
options = RemoveBGOptions(
    prefer=Prefer.WEBM_VP9  # Output format preference
)

# Remove background
foreground = video.remove_background(client, options)
```

### Complete Workflow Example

```python
from videobgremover import (
    VideoBGRemoverClient, Video, Background, Composition, 
    EncoderProfile, Anchor, SizeMode, RemoveBGOptions, Prefer
)

# Initialize client
client = VideoBGRemoverClient("your_api_key")

# Check credits first
credits = client.credits()
print(f"Remaining credits: {credits.remaining_credits}")

# Process video
video = Video.open("input.mp4")
options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)

def progress_callback(status):
    print(f"Status: {status}")

foreground = video.remove_background(client, options, on_status=progress_callback)

# Create composition
background = Background.from_image("background.jpg", fps=30.0)
comp = Composition(background)

# Add main video
layer = comp.add(foreground, name="main_video")
layer.at(Anchor.CENTER).size(SizeMode.CONTAIN).opacity(0.9)

# Export
comp.to_file("final_output.mp4", EncoderProfile.h264(crf=20))
```

### Video-on-Video Composition

```python
# Process foreground video
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
comp.to_file("output.webm", EncoderProfile.transparent_webm(crf=25))

# ProRes for professional editing  
comp.to_file("output.mov", EncoderProfile.prores_4444())

# PNG sequence for frame-by-frame work
comp.to_file("frames/frame_%04d.png", EncoderProfile.png_sequence())
```

### Layer Positioning & Effects

```python
# Add a layer with positioning
layer = comp.add(foreground, name="main")

# Positioning options
layer.at(Anchor.CENTER)                    # Center
layer.at(Anchor.TOP_LEFT, dx=100, dy=50)   # Top-left with offset

# Sizing options
layer.size(SizeMode.CONTAIN)                           # Fit within canvas
layer.size(SizeMode.PX, width=800, height=600)        # Exact pixels
layer.size(SizeMode.CANVAS_PERCENT, percent=50)       # 50% of canvas size

# Visual effects
layer.opacity(0.8)                         # 80% opacity
layer.rotate(15.0)                         # Rotate 15 degrees
layer.crop(10, 20, 100, 200)              # Crop rectangle

# Timing control
layer.start(2.0)                           # Start at 2 seconds
layer.end(10.0)                            # End at 10 seconds
layer.duration(5.0)                        # Show for 5 seconds

# Audio control
layer.audio(enabled=True, volume=0.8)      # Enable audio at 80% volume
```

## Transparent Video Formats

The SDK supports multiple transparent video formats:

| Format | File Size | Quality | Compatibility | Best For |
|--------|-----------|---------|---------------|----------|
| **WebM VP9** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | Web applications, small files |
| **Stacked Video** | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | Universal compatibility |
| **ProRes 4444** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐ | Professional video editing |
| **PNG Sequence** | ⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | Frame-by-frame work, GIFs |

**WebM VP9** is excellent for video composition workflows due to its small file sizes and native alpha channel support. The SDK automatically chooses WebM VP9 as the default format when you don't specify a preference, making it ideal for most use cases including web applications and API integrations.

**Recommendation**: Use WebM VP9 for most applications. Fall back to stacked video for maximum compatibility.

```python
# Choose format when processing
options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)      # Small files
options = RemoveBGOptions(prefer=Prefer.STACKED_VIDEO) # Universal
options = RemoveBGOptions(prefer=Prefer.MOV_PRORES)    # Professional
```

## Canvas and Sizing

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

## Error Handling

```python
from videobgremover.client.models import InsufficientCreditsError, ProcessingError

try:
    foreground = video.remove_background(client)
except InsufficientCreditsError:
    print("Not enough credits. Please top up your account.")
except ProcessingError as e:
    print(f"Video processing failed: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Troubleshooting

### FFmpeg Issues
- **WebM transparency not working**: Ensure FFmpeg has `libvpx-vp9` support
- **Large file sizes**: Use WebM format instead of ProRes for smaller files

### API Issues
- **401 Unauthorized**: Check your API key
- **402 Payment Required**: Top up your credits
- **Processing timeout**: Increase timeout or check video file size limits

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
- **`Prefer`**: Output format preferences (WEBM_VP9, STACKED_VIDEO, etc.)

### Layout & Effects

- **`Anchor`**: Positioning anchors (CENTER, TOP_LEFT, etc.)
- **`SizeMode`**: Sizing modes (CONTAIN, COVER, PX, CANVAS_PERCENT)
- **`LayerHandle`**: Layer manipulation methods

## Development

### Running Tests

```bash
# Unit tests (no API calls)
pytest tests/ -m "not integration"

# Integration tests (requires API key and consumes credits)
export VIDEOBGREMOVER_API_KEY="your_key"
pytest tests/ -m integration
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- 📖 [Full Documentation](https://docs.videobgremover.com/)
- 🐙 [GitHub Repository](https://github.com/videobgremover/videobgremover-python)

- 📧 [Email Support](mailto:paul@videobgremover.com)
- 🐛 [Issue Tracker](https://github.com/videobgremover/videobgremover-python/issues)
