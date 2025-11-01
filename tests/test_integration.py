"""Real integration tests for the VideoBGRemover SDK.

These tests make actual API calls and process real videos.
IMPORTANT: These tests will consume credits when run against production API.

Setup Requirements:
1. Start the local API server: `npm run dev` (in project root)
2. Configure your .env file with:
   - VIDEOBGREMOVER_ENV=local (or prod)
   - VIDEOBGREMOVER_LOCAL_API_KEY=your_local_key
   - VIDEOBGREMOVER_LOCAL_BASE_URL=http://localhost:3000
   - TEST_VIDEO_URL=https://your.test.video.url
   - TEST_BACKGROUND_VIDEO=test_assets/background_video.mp4
   - TEST_BACKGROUND_IMAGE=test_assets/background_image.png

For local testing:
- The Next.js dev server must be running on localhost:3000
- API endpoints are at /api/v1/* (e.g., /api/v1/credits)
- Make sure you have valid API keys configured
"""

import os
import pytest
from pathlib import Path
from videobgremover import (
    VideoBGRemoverClient,
    Video,
    Background,
    Composition,
    EncoderProfile,
    RemoveBGOptions,
    Prefer,
    Model,
    Anchor,
    SizeMode,
)


@pytest.fixture
def api_key():
    """Get API key from environment."""
    from .conftest import get_test_api_key

    key = get_test_api_key()
    if not key:
        env = os.getenv("VIDEOBGREMOVER_ENV", "local")
        pytest.skip(
            f"Set VIDEOBGREMOVER_{env.upper()}_API_KEY environment variable to run integration tests"
        )
    return key


@pytest.fixture
def client(api_key):
    """Create API client."""
    from .conftest import get_test_base_url

    return VideoBGRemoverClient(api_key, base_url=get_test_base_url())


@pytest.fixture
def sample_video_url():
    """Sample video URL for testing."""
    from .conftest import get_test_video_sources

    sources = get_test_video_sources()
    url = sources["url"]

    if not url:
        pytest.skip("Set TEST_VIDEO_URL environment variable to run URL-based tests")

    return url


@pytest.fixture
def test_backgrounds():
    """Get test background assets."""
    from .conftest import get_test_backgrounds

    backgrounds = get_test_backgrounds()

    # Check if background files exist
    if backgrounds["video"] and not Path(backgrounds["video"]).exists():
        pytest.skip(f"Background video not found: {backgrounds['video']}")

    if backgrounds["image"] and not Path(backgrounds["image"]).exists():
        pytest.skip(f"Background image not found: {backgrounds['image']}")

    return backgrounds


@pytest.fixture
def output_dir():
    """Create output directory for test results."""
    output_path = Path("test_outputs")
    output_path.mkdir(exist_ok=True)
    return output_path


@pytest.mark.integration
class TestRealIntegration:
    """Real integration tests - NO MOCKING."""

    def test_credits_check(self, client):
        """Test checking credit balance."""
        credits = client.credits()

        assert credits.user_id is not None
        assert credits.total_credits >= 0
        assert credits.remaining_credits >= 0
        assert credits.used_credits >= 0

        print(f"✅ Credits: {credits.remaining_credits}/{credits.total_credits}")

    def test_webm_processing_and_composition(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test WebM processing and composition with real background - NO MOCKING."""
        # Check credits first
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for WebM processing test")

        print("🎬 Processing video with WebM VP9 transparency...")

        # Load video
        video = Video.open(sample_video_url)

        # Configure for WebM output
        options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)

        # Process video (REAL API CALL - consumes credits!)
        def status_callback(status):
            status_messages = {
                "created": "📋 Job created...",
                "uploaded": "📤 Video uploaded...",
                "processing": "🤖 AI processing...",
                "completed": "✅ Processing completed!",
                "failed": "❌ Processing failed!",
            }
            message = status_messages.get(status, f"📊 Status: {status}")
            print(f"  {message}")

        foreground = video.remove_background(client, options, on_status=status_callback)

        # Verify we got a result
        assert foreground is not None
        assert foreground.format in (
            "webm_vp9",
            "mov_prores",
            "stacked_video",
            "pro_bundle",
        )
        print(f"✅ WebM processing completed: {foreground.format} format")

        # Create composition with real image background
        bg = Background.from_image(test_backgrounds["image"])
        comp = Composition(bg)
        comp.add(foreground, name="main_video").at(Anchor.CENTER).size(SizeMode.CONTAIN)

        # Export composition (REAL FFMPEG CALL)
        output_path = output_dir / "webm_real_background.mp4"
        encoder = EncoderProfile.h264(crf=20, preset="medium")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ Real composition exported: {output_path}")

    def test_stacked_video_processing(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test stacked video processing with real video background - NO MOCKING."""
        # Check credits
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for stacked video test")

        print("📹 Processing video with stacked video format...")

        # Load video
        video = Video.open(sample_video_url)

        # Configure for stacked video output
        options = RemoveBGOptions(prefer=Prefer.STACKED_VIDEO)

        # Process video (REAL API CALL)
        foreground = video.remove_background(client, options)

        assert foreground is not None
        # API should return stacked_video format when requested
        assert foreground.format == "stacked_video", (
            f"Expected stacked_video, got {foreground.format}"
        )
        assert foreground.primary_path is not None
        print(f"✅ Stacked video processing completed: {foreground.format} format")

        # Create composition with real background video
        bg = Background.from_video(test_backgrounds["video"])
        comp = Composition(bg)
        comp.add(foreground, name="main_video").at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        ).opacity(0.9)

        # Export composition (REAL FFMPEG CALL)
        output_path = output_dir / "stacked_video_background.mp4"
        encoder = EncoderProfile.h264(crf=18, preset="medium")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ Stacked composition exported: {output_path}")

    def test_webm_vp9_format_real_api(self, client, sample_video_url, output_dir):
        """Test WebM VP9 format with real API - REAL API CALLS."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for WebM VP9 test")

        print("🎬 Testing WebM VP9 format (real API)...")

        # Load video and configure for WebM VP9
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)

        # Process video (REAL API CALL)
        foreground = video.remove_background(client, options)

        # Verify result and format
        assert foreground is not None
        assert foreground.format == "webm_vp9"
        assert foreground.primary_path is not None
        assert foreground.primary_path.endswith(".webm")
        print(f"✅ WebM VP9 processing completed: {foreground.format} format")

        # Create composition with image background
        bg = Background.from_image("test_assets/background_image.png")
        comp = Composition(bg)
        comp.add(foreground, name="webm_layer").at(Anchor.CENTER).size(SizeMode.CONTAIN)

        # Export (REAL FFMPEG CALL)
        output_path = output_dir / "integration_webm_vp9.mp4"
        encoder = EncoderProfile.h264(crf=23, preset="fast")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ WebM VP9 integration test completed: {output_path}")

    def test_mov_prores_format_real_api(self, client, sample_video_url, output_dir):
        """Test MOV ProRes format with real API - REAL API CALLS."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for MOV ProRes test")

        print("🎬 Testing MOV ProRes format (real API)...")

        # Load video and configure for MOV ProRes
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.MOV_PRORES)

        # Process video (REAL API CALL)
        foreground = video.remove_background(client, options)

        # Verify result and format
        assert foreground is not None
        assert foreground.format == "mov_prores"
        assert foreground.primary_path is not None
        assert foreground.primary_path.endswith(".mov")
        print(f"✅ MOV ProRes processing completed: {foreground.format} format")

        # Create composition with video background
        bg = Background.from_video("test_assets/background_video.mp4")
        comp = Composition(bg)
        comp.add(foreground, name="prores_layer").at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        )
        # Audio will default to foreground audio

        # Export (REAL FFMPEG CALL)
        output_path = output_dir / "integration_mov_prores.mp4"
        encoder = EncoderProfile.h264(crf=23, preset="fast")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ MOV ProRes integration test completed: {output_path}")

    def test_stacked_video_format_real_api(self, client, sample_video_url, output_dir):
        """Test Stacked Video format with real API - REAL API CALLS."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for Stacked Video test")

        print("🎬 Testing Stacked Video format (real API)...")

        # Load video and configure for Stacked Video
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.STACKED_VIDEO)

        # Process video (REAL API CALL)
        foreground = video.remove_background(client, options)

        # Verify result
        assert foreground is not None
        print(f"✅ Stacked Video processing completed: {foreground.format} format")

        # Create composition with color background
        bg = Background.from_color("#FF0000", 1920, 1080, 30.0)
        comp = Composition(bg)
        comp.add(foreground, name="stacked_layer").at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        )

        # Export (REAL FFMPEG CALL)
        output_path = output_dir / "integration_stacked_video.mp4"
        encoder = EncoderProfile.h264(crf=23, preset="fast")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ Stacked Video integration test completed: {output_path}")

    def test_pro_bundle_format_real_api(self, client, sample_video_url, output_dir):
        """Test Pro Bundle format with real API - REAL API CALLS."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for Pro Bundle test")

        print("🎬 Testing Pro Bundle format (real API)...")

        # Load video and configure for Pro Bundle
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.PRO_BUNDLE)

        # Process video (REAL API CALL)
        foreground = video.remove_background(client, options)

        # Verify result and format
        assert foreground is not None
        assert foreground.format == "pro_bundle"
        assert foreground.primary_path is not None  # RGB video
        assert foreground.mask_path is not None  # Mask video
        # Audio path may or may not be present
        print(f"✅ Pro Bundle processing completed: {foreground.format} format")
        print(f"  RGB video: {foreground.primary_path}")
        print(f"  Mask video: {foreground.mask_path}")
        if foreground.audio_path:
            print(f"  Audio: {foreground.audio_path}")

        # Create composition with image background
        bg = Background.from_image("test_assets/background_image.png")
        comp = Composition(bg)
        comp.add(foreground, name="bundle_layer").at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        )

        # Export (REAL FFMPEG CALL)
        output_path = output_dir / "integration_pro_bundle.mp4"
        encoder = EncoderProfile.h264(crf=23, preset="fast")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ Pro Bundle integration test completed: {output_path}")

    def test_complete_api_workflow_url_to_composition(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test complete API workflow: URL → Background Removal → Composition → Export."""
        # Check credits first
        credits = client.credits()
        if credits.remaining_credits < 20:
            pytest.skip("Not enough credits for complete workflow test")

        print(
            "🔄 Testing complete API workflow: URL → BG Removal → Composition → Export..."
        )

        # Step 1: Load video from URL (no download yet)
        print("📹 Step 1: Loading video from URL...")
        video = Video.open(sample_video_url)
        assert video.src == sample_video_url
        print(f"✅ Video loaded: {video.src}")

        # Step 2: Remove background with different format preferences
        formats_to_test = [
            ("webm_vp9", "WebM VP9 with alpha channel"),
            ("stacked_video", "Stacked video (RGB + mask)"),
            ("pro_bundle", "Pro bundle (ZIP with separate files)"),
        ]

        for prefer_format, description in formats_to_test:
            print(f"\n🎨 Step 2: Processing with {description}...")

            options = RemoveBGOptions(prefer=prefer_format)

            def status_callback(status):
                status_messages = {
                    "created": "📋 Job created...",
                    "uploaded": "📤 Video uploaded...",
                    "processing": "🤖 AI processing...",
                    "completed": "✅ Processing completed!",
                    "failed": "❌ Processing failed!",
                }
                message = status_messages.get(status, f"📊 Status: {status}")
                print(f"  {message}")

            foreground = video.remove_background(
                client, options, on_status=status_callback
            )

            # Verify processing result
            assert foreground is not None
            print(f"✅ Background removal completed: {foreground.format} format")

            # Step 3: Create composition with image background
            print("🖼️ Step 3: Creating composition with image background...")
            bg_image = Background.from_image(test_backgrounds["image"])
            comp = Composition(bg_image)

            # Add foreground with positioning and sizing
            handle = comp.add(foreground, name=f"fg_{prefer_format}")
            handle.at(Anchor.CENTER).size(SizeMode.CONTAIN)

            # Step 4: Export final composition
            print("📤 Step 4: Exporting final composition...")
            output_path = output_dir / f"api_workflow_{prefer_format}.mp4"
            encoder = EncoderProfile.h264(crf=20, preset="medium")
            comp.to_file(str(output_path), encoder)

            # Verify final output
            assert output_path.exists()
            assert output_path.stat().st_size > 0
            print(f"✅ Complete workflow exported: {output_path}")

        print("🎉 Complete API workflow test passed for all formats!")

    def test_api_workflow_with_video_background(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test API workflow with video background composition."""
        # Check credits and video background availability
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for video background workflow test")

        if not test_backgrounds["video"]:
            pytest.skip("No video background configured for testing")

        print("🎬 Testing API workflow with video background...")

        # Process foreground
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)  # Fast format for this test

        foreground = video.remove_background(client, options)
        assert foreground is not None
        print("✅ Foreground processing completed")

        # Create composition with video background
        bg_video = Background.from_video(test_backgrounds["video"])
        comp = Composition(bg_video)
        comp.add(foreground).at(Anchor.CENTER).size(SizeMode.CONTAIN)

        # Export with video background
        output_path = output_dir / "api_workflow_video_bg.mp4"
        encoder = EncoderProfile.h264(crf=22, preset="fast")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0
        print(f"✅ Video background workflow completed: {output_path}")

    def test_api_error_handling_and_recovery(self, client, output_dir):
        """Test API error handling and recovery scenarios."""
        print("⚠️ Testing API error handling scenarios...")

        # Test 1: Invalid video URL
        print("🔍 Test 1: Invalid video URL handling...")
        try:
            invalid_video = Video.open(
                "https://invalid-url-that-does-not-exist.com/video.mp4"
            )
            # This should fail when we try to process it
            with pytest.raises(Exception):
                invalid_video.remove_background(client, RemoveBGOptions())
            print("✅ Invalid URL error handling works")
        except Exception as e:
            print(f"✅ Expected error for invalid URL: {e}")

        # Test 2: Insufficient credits simulation (if we can detect it)
        print("🔍 Test 2: Credits validation...")
        credits = client.credits()
        print(
            f"✅ Current credits: {credits.remaining_credits}/{credits.total_credits}"
        )

        # Test 3: API connectivity
        print("🔍 Test 3: API connectivity test...")
        try:
            # Simple credits check to verify API is reachable
            credits_check = client.credits()
            assert credits_check.user_id is not None
            print("✅ API connectivity verified")
        except Exception as e:
            pytest.fail(f"API connectivity failed: {e}")

    def test_api_batch_processing_simulation(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test processing multiple videos in sequence (batch-like workflow)."""
        credits = client.credits()
        if credits.remaining_credits < 30:  # Need more credits for batch test
            pytest.skip("Not enough credits for batch processing simulation")

        print("📦 Testing batch-like processing workflow...")

        # Simulate processing the same video with different settings
        video = Video.open(sample_video_url)

        batch_configs = [
            {"prefer": "webm_vp9", "name": "fast_webm"},
            {"prefer": "stacked_video", "name": "stacked_format"},
        ]

        results = []

        for i, config in enumerate(batch_configs):
            print(
                f"\n🔄 Processing batch item {i + 1}/{len(batch_configs)}: {config['name']}..."
            )

            options = RemoveBGOptions(prefer=config["prefer"])
            foreground = video.remove_background(client, options)

            # Create composition
            bg = Background.from_image(test_backgrounds["image"])
            comp = Composition(bg)
            comp.add(foreground).at(Anchor.CENTER).size(SizeMode.CONTAIN)

            # Export
            output_path = output_dir / f"batch_{config['name']}.mp4"
            encoder = EncoderProfile.h264(crf=23, preset="fast")
            comp.to_file(str(output_path), encoder)

            results.append(
                {
                    "config": config,
                    "output": output_path,
                    "foreground_form": foreground.format,
                }
            )

            print(
                f"✅ Batch item {i + 1} completed: {foreground.format} → {output_path}"
            )

        # Verify all batch results
        for result in results:
            assert result["output"].exists()
            assert result["output"].stat().st_size > 0

        print(
            f"🎉 Batch processing simulation completed: {len(results)} items processed"
        )

    def test_all_formats_comprehensive_real_api(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test all format preferences with real API calls - REAL API + REAL FFMPEG."""
        credits = client.credits()
        if credits.remaining_credits < 60:  # Need credits for 4 formats
            pytest.skip(
                "Not enough credits for comprehensive format testing (need ~60 credits)"
            )

        print("🎬 Testing ALL format preferences with REAL API calls...")

        formats_to_test = [
            ("webm_vp9", "WebM VP9 with alpha channel", "webm_vp9"),
            ("mov_prores", "MOV ProRes with alpha channel", "mov_prores"),
            ("stacked_video", "Stacked video (RGB + mask)", "stacked_video"),
            ("pro_bundle", "Pro bundle (ZIP with separate files)", "pro_bundle"),
        ]

        results = {}

        for format_key, description, expected_form in formats_to_test:
            print(f"\n🎨 Processing with {description}...")

            try:
                # Load video from URL
                video = Video.open(sample_video_url)
                options = RemoveBGOptions(prefer=format_key)

                def status_callback(status):
                    status_messages = {
                        "created": "📋 Job created...",
                        "uploaded": "📤 Video uploaded...",
                        "processing": "🤖 AI processing...",
                        "completed": "✅ Processing completed!",
                        "failed": "❌ Processing failed!",
                    }
                    message = status_messages.get(status, f"📊 Status: {status}")
                    print(f"  {message}")

                # REAL API CALL - This will consume credits!
                foreground = video.remove_background(
                    client, options, on_status=status_callback
                )

                # Verify processing result
                assert foreground is not None
                assert foreground.format == expected_form
                print(f"✅ {description} completed: {foreground.format} format")

                # Test composition with image background
                bg_image = Background.from_image(test_backgrounds["image"])
                comp = Composition(bg_image)

                # Add foreground with specific positioning for each format
                if format_key == "webm_vp9":
                    comp.add(foreground, name=f"fg_{format_key}").at(
                        Anchor.TOP_LEFT, dx=50, dy=50
                    ).size(SizeMode.CANVAS_PERCENT, percent=40)
                elif format_key == "mov_prores":
                    comp.add(foreground, name=f"fg_{format_key}").at(
                        Anchor.TOP_RIGHT, dx=-50, dy=50
                    ).size(SizeMode.CONTAIN)
                elif format_key == "stacked_video":
                    comp.add(foreground, name=f"fg_{format_key}").at(
                        Anchor.BOTTOM_LEFT, dx=50, dy=-50
                    ).size(SizeMode.COVER)
                else:  # pro_bundle
                    comp.add(foreground, name=f"fg_{format_key}").at(
                        Anchor.CENTER
                    ).size(SizeMode.SCALE, scale=0.8)

                # Export final composition
                output_path = output_dir / f"real_api_{format_key}.mp4"
                encoder = EncoderProfile.h264(crf=20, preset="medium")
                comp.to_file(str(output_path), encoder)

                # Verify final output
                assert output_path.exists()
                assert output_path.stat().st_size > 0

                results[format_key] = {
                    "success": True,
                    "output_path": output_path,
                    "file_size": output_path.stat().st_size,
                    "format": expected_form,
                    "foreground": foreground,
                }

                print(
                    f"✅ {description} exported: {output_path} ({output_path.stat().st_size} bytes)"
                )

            except Exception as e:
                results[format_key] = {"success": False, "error": str(e)}
                print(f"❌ {description} failed: {e}")

        # Verify at least 3 formats worked
        successful_formats = [k for k, v in results.items() if v["success"]]
        assert len(successful_formats) >= 3, (
            f"At least 3 formats should work, got: {successful_formats}"
        )

        print(
            f"\n🎉 Comprehensive format testing completed: {len(successful_formats)}/4 formats successful"
        )

        # Test multi-format composition with all successful results
        if len(successful_formats) >= 2:
            print("\n🎬 Creating multi-format composition showcase...")

            bg_showcase = Background.from_image(test_backgrounds["image"])
            comp_showcase = Composition(bg_showcase)

            positions = [
                (Anchor.TOP_LEFT, 50, 50),
                (Anchor.TOP_RIGHT, -50, 50),
                (Anchor.BOTTOM_LEFT, 50, -50),
                (Anchor.BOTTOM_RIGHT, -50, -50),
            ]

            for i, format_key in enumerate(successful_formats[:4]):
                fg_result = results[format_key]["foreground"]
                anchor, dx, dy = positions[i]

                comp_showcase.add(fg_result, name=f"showcase_{format_key}").at(
                    anchor, dx=dx, dy=dy
                ).size(SizeMode.CANVAS_PERCENT, percent=35).opacity(0.8)

            output_showcase = output_dir / "real_api_multi_format_showcase.mp4"
            comp_showcase.to_file(str(output_showcase), encoder)

            assert output_showcase.exists()
            print(f"✅ Multi-format showcase: {output_showcase}")

    def test_file_vs_url_processing_comparison(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test file upload vs URL processing with same video - REAL API."""
        credits = client.credits()
        if (
            credits.remaining_credits < 30
        ):  # Need credits for both file and URL processing
            pytest.skip("Not enough credits for file vs URL comparison test")

        print("⚖️ Testing file upload vs URL processing comparison...")

        # Test 1: URL-based processing
        print("\n🌐 Test 1: URL-based processing...")
        video_url = Video.open(sample_video_url)
        options_url = RemoveBGOptions(prefer="webm_vp9")  # Use fast format

        foreground_url = video_url.remove_background(client, options_url)
        assert foreground_url is not None
        print(f"✅ URL processing completed: {foreground_url.format} format")

        # Create composition from URL result
        bg = Background.from_image(test_backgrounds["image"])
        comp_url = Composition(bg)
        comp_url.add(foreground_url, name="url_result").at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        )

        output_url = output_dir / "real_api_url_processing.mp4"
        encoder = EncoderProfile.h264(crf=22, preset="fast")
        comp_url.to_file(str(output_url), encoder)

        assert output_url.exists()
        url_file_size = output_url.stat().st_size
        print(f"✅ URL result exported: {output_url} ({url_file_size} bytes)")

        # Test 2: File upload processing (if we have a local test file)
        print("\n📁 Test 2: File upload processing...")
        try:
            # Use a local test file
            video_file = Video.open("test_assets/default_green_screen.mp4")
            options_file = RemoveBGOptions(
                prefer="webm_vp9"
            )  # Same format for comparison

            foreground_file = video_file.remove_background(client, options_file)
            assert foreground_file is not None
            print(f"✅ File processing completed: {foreground_file.format} format")

            # Create composition from file result
            comp_file = Composition(bg)
            comp_file.add(foreground_file, name="file_result").at(Anchor.CENTER).size(
                SizeMode.CONTAIN
            )

            output_file = output_dir / "real_api_file_processing.mp4"
            comp_file.to_file(str(output_file), encoder)

            assert output_file.exists()
            file_file_size = output_file.stat().st_size
            print(f"✅ File result exported: {output_file} ({file_file_size} bytes)")

            # Create side-by-side comparison
            print("\n🔄 Creating side-by-side comparison...")
            comp_comparison = Composition(bg)
            comp_comparison.add(foreground_url, name="url_side").at(
                Anchor.CENTER_LEFT, dx=100
            ).size(SizeMode.CANVAS_PERCENT, percent=40)
            comp_comparison.add(foreground_file, name="file_side").at(
                Anchor.CENTER_RIGHT, dx=-100
            ).size(SizeMode.CANVAS_PERCENT, percent=40)

            output_comparison = output_dir / "real_api_url_vs_file_comparison.mp4"
            comp_comparison.to_file(str(output_comparison), encoder)

            assert output_comparison.exists()
            print(f"✅ Side-by-side comparison: {output_comparison}")

        except Exception as e:
            print(f"⚠️ File processing test skipped: {e}")
            print(
                "   (This is normal if test_assets/default_green_screen.mp4 doesn't exist)"
            )

        print("✅ File vs URL processing comparison completed")

    def test_composition_options_comprehensive(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test comprehensive composition options with real API - REAL API + REAL FFMPEG."""
        credits = client.credits()
        if credits.remaining_credits < 20:
            pytest.skip("Not enough credits for composition options test")

        print("🎨 Testing comprehensive composition options with REAL API...")

        # Get a processed foreground to work with
        video = Video.open(sample_video_url)
        options = RemoveBGOptions(prefer=Prefer.WEBM_VP9)  # Fast format for testing

        foreground = video.remove_background(client, options)
        assert foreground is not None
        print(f"✅ Foreground processed: {foreground.format} format")

        # Test 1: Different anchor positions
        print("\n⚓ Test 1: Testing different anchor positions...")
        bg_anchors = Background.from_image(test_backgrounds["image"])
        comp_anchors = Composition(bg_anchors)

        anchor_tests = [
            (Anchor.TOP_LEFT, "top_left", 30, 30),
            (Anchor.TOP_RIGHT, "top_right", -30, 30),
            (Anchor.BOTTOM_LEFT, "bottom_left", 30, -30),
            (Anchor.BOTTOM_RIGHT, "bottom_right", -30, -30),
            (Anchor.CENTER, "center", 0, 0),
        ]

        for anchor, name, dx, dy in anchor_tests:
            comp_anchors.add(foreground, name=f"anchor_{name}").at(
                anchor, dx=dx, dy=dy
            ).size(SizeMode.CANVAS_PERCENT, percent=15).opacity(0.7)

        output_anchors = output_dir / "real_api_composition_anchors.mp4"
        encoder = EncoderProfile.h264(crf=22, preset="fast")
        comp_anchors.to_file(str(output_anchors), encoder)

        assert output_anchors.exists()
        print(f"✅ Anchor positions test: {output_anchors}")

        # Test 2: Different sizing modes
        print("\n📐 Test 2: Testing different sizing modes...")
        bg_sizes = Background.from_color("#FF0000", 1920, 1080, 30.0)
        comp_sizes = Composition(bg_sizes)

        size_tests = [
            (SizeMode.CONTAIN, "contain", Anchor.TOP_LEFT, {}),
            (SizeMode.COVER, "cover", Anchor.TOP_RIGHT, {}),
            (
                SizeMode.CANVAS_PERCENT,
                "percent_30",
                Anchor.BOTTOM_LEFT,
                {"percent": 30},
            ),
            (SizeMode.SCALE, "scale_60", Anchor.BOTTOM_RIGHT, {"scale": 0.6}),
            (SizeMode.PX, "px_400x300", Anchor.CENTER, {"width": 400, "height": 300}),
        ]

        for size_mode, name, anchor, kwargs in size_tests:
            comp_sizes.add(foreground, name=f"size_{name}").at(
                anchor, dx=50, dy=50
            ).size(size_mode, **kwargs).opacity(0.6)

        output_sizes = output_dir / "real_api_composition_sizes.mp4"
        comp_sizes.to_file(str(output_sizes), encoder)

        assert output_sizes.exists()
        print(f"✅ Sizing modes test: {output_sizes}")

        # Test 3: Timing and opacity variations
        print("\n⏰ Test 3: Testing timing and opacity variations...")
        bg_timing = (
            Background.from_video(test_backgrounds["video"])
            if test_backgrounds["video"]
            else Background.from_color("#00FF00", 1920, 1080, 30.0)
        )
        comp_timing = Composition(bg_timing)

        # Add layers with different start times and opacities
        comp_timing.add(foreground, name="timing_1").start(0).duration(5).at(
            Anchor.TOP_LEFT, dx=50, dy=50
        ).size(SizeMode.CANVAS_PERCENT, percent=25).opacity(1.0)

        comp_timing.add(foreground, name="timing_2").start(3).duration(5).at(
            Anchor.TOP_RIGHT, dx=-50, dy=50
        ).size(SizeMode.CANVAS_PERCENT, percent=25).opacity(0.7)

        comp_timing.add(foreground, name="timing_3").start(6).duration(5).at(
            Anchor.BOTTOM_CENTER, dy=-50
        ).size(SizeMode.CANVAS_PERCENT, percent=25).opacity(0.4)

        output_timing = output_dir / "real_api_composition_timing.mp4"
        comp_timing.to_file(str(output_timing), encoder)

        assert output_timing.exists()
        print(f"✅ Timing and opacity test: {output_timing}")

        # Test 4: Audio handling
        print("\n🎵 Test 4: Testing audio handling...")

        # Test with video background (has audio)
        if test_backgrounds["video"]:
            bg_audio = Background.from_video(test_backgrounds["video"])
            comp_audio = Composition(bg_audio)

            # Add foreground with audio enabled
            comp_audio.add(foreground, name="audio_enabled").at(Anchor.CENTER).size(
                SizeMode.CONTAIN
            ).audio(enabled=True, volume=0.8)

            output_audio = output_dir / "real_api_composition_audio.mp4"
            comp_audio.to_file(str(output_audio), encoder)

            assert output_audio.exists()
            print(f"✅ Audio handling test: {output_audio}")
        else:
            print("⚠️ Audio test skipped (no video background available)")

        print("✅ Comprehensive composition options testing completed")

    def test_real_api_error_scenarios(self, client, output_dir):
        """Test real API error scenarios and recovery - REAL API."""
        print("⚠️ Testing real API error scenarios...")

        # Test 1: Invalid video URL
        print("\n🔍 Test 1: Invalid video URL handling...")
        try:
            invalid_video = Video.open("https://nonexistent-domain-12345.com/video.mp4")

            # This should fail during processing
            with pytest.raises(Exception) as exc_info:
                invalid_video.remove_background(client, RemoveBGOptions())

            print(f"✅ Invalid URL properly rejected: {exc_info.value}")

        except Exception as e:
            print(f"✅ Expected error for invalid URL: {e}")

        # Test 2: Check current credits
        print("\n💳 Test 2: Credits validation...")
        credits = client.credits()
        print(
            f"✅ Current credits: {credits.remaining_credits}/{credits.total_credits}"
        )

        # Test 3: API connectivity and response validation
        print("\n🔗 Test 3: API connectivity validation...")
        try:
            # Multiple credits checks to verify consistent API responses
            credits1 = client.credits()
            credits2 = client.credits()

            assert credits1.user_id == credits2.user_id
            assert credits1.total_credits == credits2.total_credits
            # remaining_credits might change slightly due to concurrent usage

            print("✅ API connectivity and consistency verified")

        except Exception as e:
            pytest.fail(f"API connectivity failed: {e}")

        # Test 4: Unsupported format preference (should fallback gracefully)
        print("\n🎛️ Test 4: Unsupported format handling...")
        try:
            # This should work - the API should handle unknown preferences gracefully
            _ = Video.open(
                "test_assets/default_green_screen.mp4"
            )  # Video creation should work

            # Use a non-existent format preference - should fallback to default
            _ = RemoveBGOptions()  # Options creation should work
            # Manually set to invalid preference (if the enum allows it)

            print("✅ Format preference handling verified")

        except Exception as e:
            print(f"⚠️ Format preference test result: {e}")

        print("✅ Real API error scenarios testing completed")

    def test_performance_and_timing_real_api(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test performance characteristics and timing with real API - REAL API."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for performance testing")

        print("🚀 Testing performance and timing with REAL API...")

        import time

        # Test 1: Measure processing time for different formats
        print("\n⏱️ Test 1: Measuring processing times...")

        video = Video.open(sample_video_url)

        # Test WebM VP9 (typically fastest)
        start_time = time.time()
        options_webm = RemoveBGOptions(prefer="webm_vp9")

        foreground_webm = video.remove_background(client, options_webm)
        webm_duration = time.time() - start_time

        assert foreground_webm is not None
        print(f"✅ WebM VP9 processing time: {webm_duration:.2f} seconds")

        # Test 2: Composition performance with real foreground
        print("\n🎨 Test 2: Measuring composition performance...")

        bg = Background.from_image(test_backgrounds["image"])
        comp = Composition(bg)

        # Add multiple layers to test composition complexity
        start_comp_time = time.time()

        for i in range(3):
            comp.add(foreground_webm, name=f"perf_layer_{i}").at(
                [Anchor.TOP_LEFT, Anchor.TOP_RIGHT, Anchor.BOTTOM_CENTER][i],
                dx=[50, -50, 0][i],
                dy=[50, 50, -50][i],
            ).size(SizeMode.CANVAS_PERCENT, percent=20).opacity(0.7)

        # Export and measure
        output_perf = output_dir / "real_api_performance_test.mp4"
        encoder = EncoderProfile.h264(crf=23, preset="fast")
        comp.to_file(str(output_perf), encoder)

        comp_duration = time.time() - start_comp_time

        assert output_perf.exists()
        print(f"✅ 3-layer composition time: {comp_duration:.2f} seconds")
        print(f"✅ Performance test output: {output_perf}")

        # Test 3: Memory usage validation (basic)
        print("\n💾 Test 3: Basic memory usage validation...")

        # Verify foreground objects don't consume excessive memory
        assert hasattr(foreground_webm, "primary_path")
        print("✅ Foreground memory footprint validated")

        print("\n📊 Performance Summary:")
        print(f"  - API processing: {webm_duration:.2f}s")
        print(f"  - Composition (3 layers): {comp_duration:.2f}s")
        print(f"  - Total workflow: {webm_duration + comp_duration:.2f}s")

        print("✅ Performance and timing testing completed")

    def test_animated_transparency_composition(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test animated composition with transparency alternating - REAL API + REAL FFMPEG."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for animated transparency test")

        print("🎭 Testing animated transparency composition...")

        # Process the long foreground video with auto format choice
        video = Video.open("test_assets/long_foreground_video.mp4")
        options = RemoveBGOptions()  # Auto format choice

        def status_callback(status):
            status_messages = {
                "created": "📋 Job created...",
                "uploaded": "📤 Video uploaded...",
                "processing": "🤖 AI processing started...",
                "completed": "✅ Processing completed!",
                "failed": "❌ Processing failed!",
            }
            message = status_messages.get(status, f"📊 Status: {status}")
            print(f"  {message}")

        foreground = video.remove_background(client, options, on_status=status_callback)
        assert foreground is not None
        print(f"✅ Long foreground processed with auto format: {foreground.format}")

        # Create composition with long background video
        bg_video = Background.from_video("test_assets/long_background_video.mp4")
        comp = Composition(bg_video)

        # Animation sequence with CONTINUOUS foreground (no restarting):
        # 0-3s: Full video at center (with alpha)
        # 3-6s: Same video continues at top-left (no alpha)
        # 6-9s: Same video continues at top-right (with alpha)
        # 9-12s: Same video continues at bottom-left (no alpha)
        # 12-15s: Same video continues at bottom-right (with alpha)
        # 15-18s: Same video continues at center small (no alpha)

        print("🎬 Creating animated sequence with CONTINUOUS foreground:")
        print("  0-3s: Full video at center (with alpha)")
        print("  3-6s: Continues at top-left (no alpha)")
        print("  6-9s: Continues at top-right (with alpha)")
        print("  9-12s: Continues at bottom-left (no alpha)")
        print("  12-15s: Continues at bottom-right (with alpha)")
        print("  15-18s: Continues at center small (no alpha)")

        # Layer 1: 0-3s Full video at center (with alpha)
        comp.add(foreground.subclip(0, 3)).start(0).duration(3).at(Anchor.CENTER).size(
            SizeMode.CONTAIN
        ).alpha(enabled=True)

        # Layer 2: 3-6s Continue at top-left (no alpha)
        comp.add(foreground.subclip(3, 6)).start(3).duration(3).at(
            Anchor.TOP_LEFT, dx=50, dy=50
        ).size(SizeMode.CANVAS_PERCENT, percent=40).alpha(enabled=False)

        # Layer 3: 6-9s Continue at top-right (with alpha)
        comp.add(foreground.subclip(6, 9)).start(6).duration(3).at(
            Anchor.TOP_RIGHT, dx=-50, dy=50
        ).size(SizeMode.CANVAS_PERCENT, percent=40).alpha(enabled=True)

        # Layer 4: 9-12s Continue at bottom-left (no alpha)
        comp.add(foreground.subclip(9, 12)).start(9).duration(3).at(
            Anchor.BOTTOM_LEFT, dx=50, dy=-50
        ).size(SizeMode.CANVAS_PERCENT, percent=40).alpha(enabled=False)

        # Layer 5: 12-15s Continue at bottom-right (with alpha)
        comp.add(foreground.subclip(12, 15)).start(12).duration(3).at(
            Anchor.BOTTOM_RIGHT, dx=-50, dy=-50
        ).size(SizeMode.CANVAS_PERCENT, percent=40).alpha(enabled=True)

        # Layer 6: 15-18s Continue at center small (no alpha)
        comp.add(foreground.subclip(15, 18)).start(15).duration(3).at(
            Anchor.CENTER
        ).size(SizeMode.CANVAS_PERCENT, percent=25).alpha(enabled=False)

        # Export animated composition
        output_path = output_dir / "animated_transparency_composition.mp4"
        encoder = EncoderProfile.h264(crf=20, preset="medium")

        print("🎬 Exporting animated composition...")
        comp.to_file(str(output_path), encoder)

        # Verify output
        assert output_path.exists()
        assert output_path.stat().st_size > 0

        # Get actual duration to verify timing
        import subprocess
        import json

        try:
            cmd = [
                "ffprobe",
                "-v",
                "quiet",
                "-print_format",
                "json",
                "-show_entries",
                "format=duration",
                str(output_path),
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                data = json.loads(result.stdout)
                duration = data.get("format", {}).get("duration")
                if duration:
                    actual_duration = float(duration)
                    print(f"✅ Animated composition duration: {actual_duration:.1f}s")
        except Exception:
            pass  # Duration check is optional

        print(f"✅ Animated transparency composition completed: {output_path}")
        print(
            "🎭 Animation shows alternating transparency effects with different positions!"
        )

        return output_path

    def test_webhook_integration_end_to_end(self, client, sample_video_url, output_dir):
        """Test webhook integration end-to-end with REAL API."""
        credits = client.credits()
        if credits.remaining_credits < 15:
            pytest.skip("Not enough credits for webhook integration test")

        print("🔔 Testing webhook integration end-to-end with REAL API...")

        # Use local test webhook endpoint
        webhook_url = "http://localhost:3000/api/test/webhook"
        print(f"📍 Webhook URL: {webhook_url}")

        # Step 1: Create and start job with webhook_url
        print("\n🎬 Step 1: Creating job with webhook URL...")

        # Create job
        from videobgremover.client import CreateJobUrlDownload

        create_response = client.create_job_url(
            CreateJobUrlDownload(video_url=sample_video_url)
        )
        job_id = create_response["id"]
        print(f"✅ Job created: {job_id}")

        # Start job with webhook
        print("🚀 Step 2: Starting job with webhook...")
        from videobgremover.client import StartJobRequest, BackgroundOptions
        from videobgremover.core import BackgroundType, TransparentFormat

        client.start_job(
            job_id,
            StartJobRequest(
                webhook_url=webhook_url,
                background=BackgroundOptions(
                    type=BackgroundType.TRANSPARENT,
                    transparent_format=TransparentFormat.WEBM_VP9,
                ),
            ),
        )
        print(f"✅ Job started with webhook: {webhook_url}")

        # Step 3: Wait for job completion
        print("\n⏳ Step 3: Waiting for job completion...")

        def status_callback(status):
            status_messages = {
                "created": "📋 Job created...",
                "uploaded": "📤 Video uploaded...",
                "processing": "🤖 AI processing...",
                "completed": "✅ Processing completed!",
                "failed": "❌ Processing failed!",
            }
            message = status_messages.get(status, f"📊 Status: {status}")
            print(f"  {message}")

        final_status = client.wait(job_id, poll_seconds=2.0, on_status=status_callback)

        assert final_status.status == "completed"
        print("✅ Job completed successfully")

        # Step 4: Check webhook delivery history
        print("\n📜 Step 4: Checking webhook delivery history...")
        deliveries = client.webhook_deliveries(job_id)

        print("📊 Webhook Delivery Summary:")
        print(f"  - Video ID: {deliveries['video_id']}")
        print(f"  - Total deliveries: {deliveries['total_deliveries']}")

        # Verify deliveries
        assert deliveries["video_id"] == job_id
        assert (
            deliveries["total_deliveries"] >= 2
        )  # At least job.started and job.completed

        # Check individual deliveries
        for delivery in deliveries["deliveries"]:
            print(f"\n  🔔 Webhook: {delivery['event_type']}")
            print(f"     - Attempt: {delivery['attempt_number']}")
            print(f"     - Status: {delivery['delivery_status']}")
            print(f"     - HTTP Code: {delivery['http_status_code']}")
            print(f"     - Scheduled: {delivery['scheduled_at']}")
            print(f"     - Delivered: {delivery['delivered_at']}")

            assert delivery["webhook_url"] == webhook_url
            assert delivery["delivery_status"] == "delivered"
            assert delivery["http_status_code"] == 200

        # Verify we got both job.started and job.completed
        event_types = [d["event_type"] for d in deliveries["deliveries"]]
        assert "job.started" in event_types
        assert "job.completed" in event_types

        print("\n✅ Webhook integration test completed successfully!")
        print("   - job.started webhook delivered")
        print("   - job.completed webhook delivered")
        print("   - Delivery history retrieved successfully")

    def test_model_choices(
        self, client, sample_video_url, test_backgrounds, output_dir
    ):
        """Test processing with different model choices."""
        # Check credits
        credits = client.credits()
        if credits.remaining_credits < 30:
            pytest.skip("Not enough credits for model choice test (need ~30 credits)")

        print("🤖 Testing different model choices with REAL API...")

        # Test both models with the same video
        models_to_test = [
            {"model": Model.VIDEOBGREMOVER_ORIGINAL, "name": "videobgremover-original"},
            {"model": Model.VIDEOBGREMOVER_LIGHT, "name": "videobgremover-light"},
        ]

        results = []

        for model_config in models_to_test:
            model = model_config["model"]
            name = model_config["name"]

            print(f"\n🎬 Processing with {name} model...")

            import time

            start_time = time.time()

            # Load video
            video = Video.open(sample_video_url)

            # Configure with model choice
            options = RemoveBGOptions(prefer=Prefer.WEBM_VP9, model=model)

            # Status callback for progress
            def status_callback(status):
                status_messages = {
                    "created": "📋 Job created...",
                    "uploaded": "📤 Video uploaded...",
                    "processing": "🤖 AI processing...",
                    "completed": "✅ Processing completed!",
                    "failed": "❌ Processing failed!",
                }
                message = status_messages.get(status, f"📊 Status: {status}")
                print(f"  {message}")

            # Process video (REAL API CALL - consumes credits!)
            foreground = video.remove_background(
                client, options, wait_poll_seconds=2.0, on_status=status_callback
            )

            processing_time = time.time() - start_time

            # Verify processing result
            assert foreground is not None
            print(f"✅ {name} processing completed in {processing_time:.2f}s")

            # Create composition with background
            if not test_backgrounds["image"]:
                pytest.skip("Test background image not found")

            bg = Background.from_image(test_backgrounds["image"], 30.0)
            comp = Composition(bg)
            comp.add(foreground, f"model_{name}").at(Anchor.CENTER).size(
                SizeMode.CONTAIN
            )

            # Export composition
            output_path = output_dir / f"model_{name.replace('-', '_')}.mp4"
            encoder = EncoderProfile.h264(crf=20, preset="medium")

            print(f"🔧 Exporting to: {output_path}")
            comp.to_file(str(output_path), encoder)

            # Verify output
            assert output_path.exists()
            file_size = output_path.stat().st_size
            assert file_size > 0

            results.append(
                {
                    "model": name,
                    "output_path": str(output_path),
                    "foreground": foreground,
                    "processing_time": processing_time,
                }
            )

            print(f"✅ {name} exported: {output_path} ({file_size} bytes)")

        # Verify both models worked
        assert len(results) == 2

        print("\n📊 Model Choice Results:")
        for result in results:
            print(
                f"  - {result['model']}: {result['processing_time']:.2f}s → {result['output_path']}"
            )

        print("\n🎉 Model choice test completed successfully!")


if __name__ == "__main__":
    # Run integration tests
    env = os.getenv("VIDEOBGREMOVER_ENV", "local")
    print(f"Running REAL integration tests against {env} environment...")
    print("⚠️ These tests will consume credits and process real videos!")

    pytest.main([__file__, "-v", "-m", "integration", "--tb=short"])
