#!/usr/bin/env python3
"""
Advanced composition example for VideoBGRemover SDK.

This example demonstrates:
1. Processing multiple videos
2. Creating complex compositions with multiple layers
3. Using different backgrounds and effects
4. Exporting in different formats
"""

import os
from videobgremover import (
    VideoBGRemoverClient,
    Video,
    Background,
    Composition,
    EncoderProfile,
    RemoveBGOptions,
    Anchor,
    SizeMode,
)


def main():
    """Run advanced composition example."""
    # Get API key from environment
    api_key = os.getenv("VIDEOBGREMOVER_API_KEY")
    if not api_key:
        print("Please set VIDEOBGREMOVER_API_KEY environment variable")
        return

    # Initialize client
    client = VideoBGRemoverClient(api_key)

    # Check credits
    credits = client.credits()
    print(f"Remaining credits: {credits.remaining_credits}")

    if credits.remaining_credits < 30:  # Need more credits for multiple videos
        print("Not enough credits for this advanced example")
        return

    # Process first video
    print("Processing first video...")
    video1 = Video.open(
        "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    )

    options = RemoveBGOptions(prefer="webm_vp9")

    foreground1 = video1.remove_background(client, options)
    print("✅ First video processed")

    # For demo purposes, we'll reuse the same foreground as if it were different videos
    # In practice, you'd process different videos
    foreground2 = foreground1  # Simulating a second processed video

    # Create background from image/video
    # You can use a local image or video file, or a URL
    background = Background.from_color(
        hex_color="#1a1a2e",  # Dark blue background
        width=1920,
        height=1080,
        fps=30.0,
    )

    # Create complex composition
    print("Creating advanced composition...")
    comp = Composition(background)

    # Add main video (large, centered)
    main_layer = comp.add(foreground1, name="main_video")
    main_layer.at(Anchor.CENTER).size(SizeMode.CONTAIN).opacity(0.9)

    # Add picture-in-picture video (small, top-right)
    pip_layer = comp.add(foreground2, name="pip_video")
    pip_layer.at(Anchor.TOP_RIGHT, dx=-50, dy=50).size(
        SizeMode.CANVAS_PERCENT, percent=25
    )
    pip_layer.opacity(0.8).start(2.0).end(8.0)  # Show only from 2s to 8s

    # Add another layer with effects
    effect_layer = comp.add(foreground1, name="effect_video")
    effect_layer.at(Anchor.BOTTOM_LEFT, dx=50, dy=-50).size(
        SizeMode.CANVAS_PERCENT, percent=20
    )
    effect_layer.opacity(0.6).rotate(15.0)

    # Export in different formats

    # 1. High-quality H.264
    print("Exporting H.264 version...")
    h264_encoder = EncoderProfile.h264(crf=18, preset="slow")
    comp.to_file("advanced_composition_hq.mp4", h264_encoder)

    # 2. Transparent WebM (if you want to overlay on other content later)
    print("Exporting transparent WebM version...")
    # For transparent output, we'd need to modify the composition to not have a solid background
    transparent_comp = Composition.canvas(1920, 1080, 30.0)  # Empty canvas
    transparent_comp.add(foreground1, name="transparent_main").at(Anchor.CENTER).size(
        SizeMode.CONTAIN
    )

    webm_encoder = EncoderProfile.transparent_webm(crf=25)
    transparent_comp.to_file("transparent_output.webm", webm_encoder)

    # 3. ProRes for professional editing
    print("Exporting ProRes version...")
    prores_encoder = EncoderProfile.prores_4444()
    comp.to_file("advanced_composition_prores.mov", prores_encoder)

    print("✅ All exports completed!")
    print("Generated files:")
    print("  - advanced_composition_hq.mp4 (High-quality H.264)")
    print("  - transparent_output.webm (Transparent WebM)")
    print("  - advanced_composition_prores.mov (ProRes 4444)")

    # Show dry run command for debugging
    print("\nFFmpeg command that would be executed:")
    print(comp.dry_run())


def create_multi_layer_composition():
    """Example of creating a composition with many layers and effects."""
    # This is a more complex example showing advanced features

    comp = Composition.canvas(1920, 1080, 30.0)

    # Simulate having multiple foreground videos
    # In practice, these would come from different API calls
    foregrounds = []  # Would be populated with real Foreground objects

    if not foregrounds:
        print("This function requires multiple processed foreground videos")
        return

    # Create a grid layout
    positions = [
        (Anchor.TOP_LEFT, 0, 0),
        (Anchor.TOP_RIGHT, 0, 0),
        (Anchor.BOTTOM_LEFT, 0, 0),
        (Anchor.BOTTOM_RIGHT, 0, 0),
        (Anchor.CENTER, 0, 0),
    ]

    for i, (fg, (anchor, dx, dy)) in enumerate(zip(foregrounds, positions)):
        layer = comp.add(fg, name=f"video_{i}")
        layer.at(anchor, dx, dy).size(SizeMode.CANVAS_PERCENT, percent=45)

        # Add some variety
        if i == 4:  # Center video
            layer.size(SizeMode.CANVAS_PERCENT, percent=30).z(10)  # Bring to front

        # Stagger timing
        start_time = i * 0.5
        layer.start(start_time)

    return comp


if __name__ == "__main__":
    main()
