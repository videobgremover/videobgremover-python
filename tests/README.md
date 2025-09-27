# VideoBGRemover SDK Tests

Quick guide to running tests for the VideoBGRemover Python SDK.

## Test Structure

```
tests/
├── README.md                           # 📖 This file
├── test_client.py                      # 🌐 API client tests (mock HTTP)
├── test_media.py                       # 🎬 Media component tests (no mocking)
├── test_videobgremover_workflow.py     # 🔄 Complete workflow tests (mock API + real FFmpeg)
└── test_integration.py                 # 🚀 Real API tests (costs credits)
```

## Quick Start

```bash
# Install dependencies
uv sync

# Run all unit tests (fast, no API calls)
uv run pytest tests/test_client.py tests/test_media.py -v

# Run workflow tests (mock API + real FFmpeg)
uv run pytest tests/test_videobgremover_workflow.py -v

# Run integration tests (real API - costs credits!)
uv run pytest tests/test_integration.py -v
```

## Test Categories

### 🏃‍♂️ **Fast Tests (< 10 seconds)**
```bash
# Unit tests - no FFmpeg execution
uv run pytest tests/test_client.py -v                    # API client tests
uv run pytest tests/test_media.py::TestVideo -v         # Video loading tests
uv run pytest tests/test_media.py::TestBackground -v    # Background tests

# FFmpeg command validation (no execution)
uv run pytest tests/test_media.py::TestComposition::test_dry_run_with_real_assets -v
```

### ⚡ **Medium Tests (10-30 seconds)**
```bash
# Workflow tests - mock API + real FFmpeg
uv run pytest tests/test_videobgremover_workflow.py::TestVideoBGRemoverWorkflow::test_webm_vp9_workflow_with_image_background -v
uv run pytest tests/test_videobgremover_workflow.py::TestVideoBGRemoverWorkflow::test_all_formats_comprehensive_workflow -v
```

### 🐌 **Slow Tests (30+ seconds, costs credits)**
```bash
# Integration tests - real API calls
uv run pytest tests/test_integration.py -v
```

## Test Assets

All test assets are in `test_assets/`:
- `transparent_webm_vp9.webm` - WebM with alpha + Opus audio (4.2MB)
- `transparent_mov_prores.mov` - ProRes with alpha + PCM audio (158MB)
- `stacked_video_comparison.mp4` - Stacked format + AAC audio (7.8MB)
- `background_image.png` - Image background (467KB)
- `background_video.mp4` - Video background + audio (4.6MB)
- `pro_bundle_multiple_formats.zip` - Pro bundle (color + alpha + audio)

## Environment Setup

### For Unit/Workflow Tests (No API Key Needed)
```bash
# Just run - uses test assets only
uv run pytest tests/test_media.py tests/test_videobgremover_workflow.py -v
```

### For Integration Tests (API Key Required)
```bash
# Set up environment
export VIDEOBGREMOVER_ENV=local
export VIDEOBGREMOVER_LOCAL_API_KEY=your_api_key
export VIDEOBGREMOVER_LOCAL_BASE_URL=http://localhost:3000
export TEST_VIDEO_URL=https://your.test.video.url

# Run integration tests
uv run pytest tests/test_integration.py -v
```

## Debugging Failed Tests

### FFmpeg Issues
```bash
# Check FFmpeg installation
ffmpeg -version

# Check WebM VP9 decoder support
ffmpeg -decoders | grep libvpx-vp9

# Run with verbose FFmpeg output
# (modify test to use verbose=True in comp.to_file())
```

### Audio Issues
```bash
# Check if output has audio
ffprobe -v quiet -select_streams a test_outputs/workflow_tests/your_output.mp4

# Check input audio
ffprobe -v quiet -select_streams a test_assets/transparent_webm_vp9.webm
```

### Performance Issues
```bash
# Run single test
uv run pytest tests/test_videobgremover_workflow.py::TestVideoBGRemoverWorkflow::test_webm_vp9_workflow_with_image_background -v -s

# Check file sizes
ls -lh test_assets/
ls -lh test_outputs/workflow_tests/
```

## What Each Test Does

### `test_client.py` 
- ✅ API authentication
- ✅ HTTP request/response handling  
- ✅ Error handling (credits, timeouts, etc.)
- ✅ Pydantic model validation

### `test_media.py`
- ✅ Video/Background/Foreground creation
- ✅ FFmpeg command generation (dry_run)
- ✅ Encoder profiles
- ✅ Composition layer effects

### `test_videobgremover_workflow.py`
- ✅ WebM VP9 format (with libvpx-vp9 decoder)
- ✅ MOV ProRes format  
- ✅ Stacked video format (crop + alphamerge)
- ✅ Audio preservation (foreground audio by default)
- ✅ Multiple output formats
- ✅ Real FFmpeg composition

### `test_integration.py`
- ✅ Real API calls (costs credits)
- ✅ End-to-end workflows
- ✅ Credit checking
- ✅ All transparent formats

## Quick Test Commands

```bash
# Test everything (except integration)
uv run pytest tests/ -m "not integration" -v

# Test just FFmpeg composition
uv run pytest tests/test_media.py::TestComposition -v

# Test all formats workflow  
uv run pytest tests/test_videobgremover_workflow.py::TestVideoBGRemoverWorkflow::test_all_formats_comprehensive_workflow -v

# Test audio handling
uv run pytest tests/test_videobgremover_workflow.py::TestVideoBGRemoverWorkflow::test_audio_handling_comprehensive -v
```

## Expected Results

**All tests should complete in < 30 seconds total** (excluding integration tests).

If tests are hanging or taking too long:
1. Check FFmpeg installation
2. Verify test assets exist
3. Check available disk space
4. Run individual tests to isolate issues
