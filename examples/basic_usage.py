#!/usr/bin/env python3
"""
Basic usage example for VideoBGRemover SDK.

This example demonstrates:
1. Removing background from a video
2. Creating a composition with custom background
3. Exporting the final result
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
    """Run basic usage example."""
    # Get API key from environment
    api_key = os.getenv("VIDEOBGREMOVER_API_KEY")
    if not api_key:
        print("Please set VIDEOBGREMOVER_API_KEY environment variable")
        return

    # Initialize client
    client = VideoBGRemoverClient(api_key)

    # Check credits
    print("Checking credit balance...")
    credits = client.credits()
    print(f"Remaining credits: {credits.remaining_credits}")

    if credits.remaining_credits < 10:
        print("Not enough credits for this example")
        return

    # Load video (replace with your video path or URL)
    video_path = "https://sample-videos.com/zip/10/mp4/SampleVideo_1280x720_1mb.mp4"
    print(f"Loading video: {video_path}")

    video = Video.open(video_path)

    # Configure background removal options
    options = RemoveBGOptions(
        prefer="webm_vp9"  # Prefer WebM for small file size
    )

    # Remove background (this will consume credits!)
    print("Removing background... (this may take a few minutes)")

    def progress_callback(progress):
        print(f"Progress: {progress:.1f}%")

    foreground = video.remove_background(client, options, on_status=progress_callback)

    print("Background removal completed!")

    # Create a custom background
    background = Background.from_color(
        hex_color="#00FF00",  # Green screen
        width=1920,
        height=1080,
        fps=30.0,
    )

    # Create composition
    print("Creating composition...")
    composition = Composition(background)

    # Add the processed video
    composition.add(foreground, name="main_video").at(Anchor.CENTER).size(
        SizeMode.CONTAIN
    )

    # Export final video
    output_path = "output_with_green_background.mp4"
    encoder = EncoderProfile.h264(crf=20, preset="medium")

    print(f"Exporting to: {output_path}")
    composition.to_file(output_path, encoder)

    print("✅ Video processing completed!")
    print(f"Output saved to: {output_path}")


if __name__ == "__main__":
    main()
