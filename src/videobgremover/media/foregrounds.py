"""Foreground classes for transparent videos."""

from typing import Optional, Literal, Tuple, List, Dict
from pathlib import Path
from urllib.parse import urlparse
from .video_source import VideoSource
from .context import MediaContext, default_context


class Foreground(VideoSource):
    """Foreground video with transparency information."""

    format: Literal[
        "webm_vp9", "mov_prores", "png_sequence", "pro_bundle", "stacked_video"
    ]  # API format name
    primary_path: str  # Main video file path (always present)
    mask_path: Optional[str] = None  # Mask video path (only for pro_bundle)
    audio_path: Optional[str] = None  # Audio file path (only for pro_bundle with audio)
    source_trim: Optional[Tuple[float, Optional[float]]] = (
        None  # (start, end) for trimming
    )

    model_config = {"frozen": True}

    @staticmethod
    def from_webm_vp9(path: str, ctx: Optional[MediaContext] = None) -> "Foreground":
        """
        Create foreground from WebM VP9 video file with alpha channel.

        Args:
            path: Path to WebM VP9 video file with alpha channel or URL
            ctx: Media context for operations

        Returns:
            Foreground instance with probed format information
        """
        ctx = ctx or default_context()

        fg = Foreground(format="webm_vp9", primary_path=path)
        fg._probe_and_store(path, ctx)  # Probe format info once
        return fg

    @staticmethod
    def from_mov_prores(path: str, ctx: Optional[MediaContext] = None) -> "Foreground":
        """
        Create foreground from MOV ProRes video file with alpha channel.

        Args:
            path: Path to MOV ProRes video file with alpha channel or URL
            ctx: Media context for operations

        Returns:
            Foreground instance with probed format information
        """
        ctx = ctx or default_context()

        fg = Foreground(format="mov_prores", primary_path=path)
        fg._probe_and_store(path, ctx)  # Probe format info once
        return fg

    @staticmethod
    def from_png_sequence(
        path: str, ctx: Optional[MediaContext] = None
    ) -> "Foreground":
        """
        Create foreground from PNG sequence ZIP file.

        Args:
            path: Path to PNG sequence ZIP file or URL
            ctx: Media context for operations

        Returns:
            Foreground instance with probed format information
        """
        ctx = ctx or default_context()

        fg = Foreground(format="png_sequence", primary_path=path)
        # Note: PNG sequences don't need video probing since they're image sequences
        return fg

    @staticmethod
    def from_video_and_mask(
        video_path: str,
        mask_path: str,
        audio_path: Optional[str] = None,
        ctx: Optional[MediaContext] = None,
    ) -> "Foreground":
        """
        Create foreground from separate RGB video and mask files.

        Args:
            video_path: Path to RGB video file or URL
            mask_path: Path to mask video file (grayscale)
            audio_path: Path to separate audio file (optional)
            ctx: Media context for operations

        Returns:
            Foreground instance with probed format information
        """
        ctx = ctx or default_context()

        fg = Foreground(
            format="pro_bundle",
            primary_path=video_path,
            mask_path=mask_path,
            audio_path=audio_path,
        )
        fg._probe_and_store(video_path, ctx)  # Probe the RGB video
        return fg

    @staticmethod
    def from_stacked_video(
        path: str, ctx: Optional[MediaContext] = None
    ) -> "Foreground":
        """
        Create foreground from stacked video file.

        Stacked video contains:
        - Top half: Original video (RGB)
        - Bottom half: Grayscale mask

        Args:
            path: Path to stacked video file or URL
            ctx: Media context for operations

        Returns:
            Foreground instance with probed format information
        """
        ctx = ctx or default_context()

        fg = Foreground(format="stacked_video", primary_path=path)
        fg._probe_and_store(path, ctx)  # Probe format info once
        return fg

    @staticmethod
    def from_pro_bundle_zip(path: str) -> "Foreground":
        """
        Create foreground from pro bundle ZIP file (from API).

        ZIP should contain:
        - color.mp4 - RGB video
        - alpha.mp4 - Grayscale mask
        - audio.m4a - Audio (optional)
        - manifest.json - Metadata (optional)

        Args:
            path: Path to pro bundle ZIP file from API

        Returns:
            Foreground instance (will be processed as bundle format)
        """
        # Let the importer handle the ZIP extraction
        from ._importer_internal import Importer
        from .context import default_context

        ctx = default_context()
        importer = Importer(ctx)
        return importer._handle_zip_bundle(path)

    # Backward compatibility alias
    @staticmethod
    def from_zip(path: str) -> "Foreground":
        """DEPRECATED: Use from_pro_bundle_zip() instead."""
        import warnings

        warnings.warn(
            "from_zip() is deprecated. Use from_pro_bundle_zip() for clarity.",
            DeprecationWarning,
            stacklevel=2,
        )
        return Foreground.from_pro_bundle_zip(path)

    def subclip(self, start: float, end: Optional[float] = None) -> "Foreground":
        """
        Create a new Foreground with source trimming.

        Args:
            start: Start time in source video (seconds)
            end: End time in source video (seconds, None = use until end)

        Returns:
            New Foreground instance with trimming applied
        """
        # Create a new instance with the same properties but different trim
        new_fg = Foreground(
            format=self.format,
            primary_path=self.primary_path,
            mask_path=self.mask_path,
            audio_path=self.audio_path,
            source_trim=(start, end),
        )
        # Copy the probed video info
        if hasattr(self, "_video_info"):
            new_fg._video_info = self._video_info
        return new_fg

    @staticmethod
    def _get_file_extension(path: str) -> str:
        """
        Extract file extension from path or URL using proper parsing.

        Args:
            path: File path or URL

        Returns:
            File extension in lowercase (e.g., '.webm', '.mov', '.mp4', '.zip')
        """
        try:
            if path.startswith(("http://", "https://")):
                # It's a URL - extract path component
                parsed_url = urlparse(path)
                return Path(parsed_url.path).suffix.lower()
            else:
                # It's a file path
                return Path(path).suffix.lower()
        except Exception:
            # Fallback to basic string parsing
            path_lower = path.lower()
            if "." in path_lower:
                return "." + path_lower.split(".")[-1]
            return ""

    @staticmethod
    def from_file(path: str, ctx: Optional[MediaContext] = None) -> "Foreground":
        """
        Create foreground from any video file with automatic format detection.

        This method examines the file extension and chooses the appropriate format:
        - .webm -> WebM VP9 format
        - .mov -> MOV ProRes format
        - .zip -> Attempts to detect if it's PNG sequence or Pro Bundle
        - .mp4 -> Assumes stacked video format

        Supports both local file paths and URLs.

        Args:
            path: Path to video file or URL (e.g., "video.webm" or "https://example.com/video.mp4")
            ctx: Media context for operations

        Returns:
            Foreground instance with detected format
        """
        ctx = ctx or default_context()
        extension = Foreground._get_file_extension(path)

        if extension == ".webm":
            return Foreground.from_webm_vp9(path, ctx)
        elif extension == ".mov":
            return Foreground.from_mov_prores(path, ctx)
        elif extension == ".zip":
            # For ZIP files, use the pro bundle ZIP method which handles detection
            return Foreground.from_pro_bundle_zip(path)
        elif extension == ".mp4":
            # MP4 from API is stacked video format
            return Foreground.from_stacked_video(path, ctx)
        else:
            # Unknown extension - raise error with format guidance
            raise ValueError(
                f"Unknown video format for file: {path}\n"
                f"Detected extension: {extension or 'none'}\n"
                f"Supported formats:\n"
                f"  - .webm → use Foreground.from_webm_vp9()\n"
                f"  - .mov  → use Foreground.from_mov_prores()\n"
                f"  - .mp4  → use Foreground.from_stacked_video()\n"
                f"  - .zip  → use Foreground.from_pro_bundle_zip()\n"
                f"Or use specific format methods if you know the exact format."
            )

    def get_ffmpeg_inputs(
        self,
        input_idx: int,
        layer_idx: int,
        ctx: MediaContext,
        source_trim_args: List[str],
        composition_timing_args: List[str],
    ) -> Tuple[List[str], Dict[str, int], Optional[str]]:
        """
        Get FFmpeg input arguments for this foreground format.

        Args:
            input_idx: Starting input index
            layer_idx: Layer index for naming
            ctx: Media context
            source_trim_args: Source trimming arguments (from subclip)
            composition_timing_args: Composition timing arguments

        Returns:
            Tuple of (ffmpeg_args, input_map_updates, audio_input_key)
        """
        if self.format == "webm_vp9":
            return self._get_webm_inputs(
                input_idx, layer_idx, ctx, source_trim_args, composition_timing_args
            )
        elif self.format == "mov_prores":
            return self._get_mov_inputs(
                input_idx, layer_idx, ctx, source_trim_args, composition_timing_args
            )
        elif self.format == "pro_bundle":
            return self._get_bundle_inputs(
                input_idx, layer_idx, ctx, source_trim_args, composition_timing_args
            )
        elif self.format == "stacked_video":
            return self._get_stacked_inputs(
                input_idx, layer_idx, ctx, source_trim_args, composition_timing_args
            )
        else:
            raise ValueError(f"Unknown foreground format: {self.format}")

    def get_ffmpeg_filters(
        self, layer_label: str, input_map: Dict[str, int], alpha_enabled: bool = True
    ) -> List[str]:
        """
        Get FFmpeg filters to process this foreground into RGBA format.

        Args:
            layer_label: Unique label for this layer
            input_map: Mapping of input names to indices
            alpha_enabled: Whether to process alpha channel transparency

        Returns:
            List of FFmpeg filter strings
        """
        if self.format == "webm_vp9":
            return self._get_webm_filters(layer_label, input_map, alpha_enabled)
        elif self.format == "mov_prores":
            return self._get_mov_filters(layer_label, input_map, alpha_enabled)
        elif self.format == "pro_bundle":
            return self._get_bundle_filters(layer_label, input_map, alpha_enabled)
        elif self.format == "stacked_video":
            return self._get_stacked_filters(layer_label, input_map, alpha_enabled)
        else:
            raise ValueError(f"Unknown foreground format: {self.format}")

    def _get_webm_inputs(
        self,
        input_idx: int,
        layer_idx: int,
        ctx: MediaContext,
        source_trim_args: List[str],
        composition_timing_args: List[str],
    ) -> Tuple[List[str], Dict[str, int], Optional[str]]:
        """Handle WebM VP9 inputs with alpha channel."""
        args = []
        args.extend(composition_timing_args)

        # Use libvpx-vp9 decoder to preserve alpha channels if available
        if ctx.check_webm_support():
            args.extend(["-c:v", "libvpx-vp9"])
            args.extend(source_trim_args)
            args.extend(["-i", self.primary_path])
            ctx.logger.debug(f"Using libvpx-vp9 decoder for WebM: {self.primary_path}")
        else:
            # Use default decoder
            args.extend(source_trim_args)
            args.extend(["-i", self.primary_path])

        layer_key = f"layer_{layer_idx}"
        input_map_updates = {layer_key: input_idx}
        audio_input_key = layer_key  # Same input for both video and audio

        return args, input_map_updates, audio_input_key

    def _get_mov_inputs(
        self,
        input_idx: int,
        layer_idx: int,
        ctx: MediaContext,
        source_trim_args: List[str],
        composition_timing_args: List[str],
    ) -> Tuple[List[str], Dict[str, int], Optional[str]]:
        """Handle MOV ProRes inputs with alpha channel."""
        args = []
        args.extend(composition_timing_args)

        # MOV ProRes uses default decoder (no special decoder needed)
        args.extend(source_trim_args)
        args.extend(["-i", self.primary_path])

        layer_key = f"layer_{layer_idx}"
        input_map_updates = {layer_key: input_idx}
        audio_input_key = layer_key  # Same input for both video and audio

        return args, input_map_updates, audio_input_key

    def _get_bundle_inputs(
        self,
        input_idx: int,
        layer_idx: int,
        ctx: MediaContext,
        source_trim_args: List[str],
        composition_timing_args: List[str],
    ) -> Tuple[List[str], Dict[str, int], Optional[str]]:
        """Handle pro bundle (RGB + mask + optional audio) inputs."""
        if self.mask_path is None:
            raise ValueError("mask_path is required for pro_bundle format")

        rgb_args = []
        mask_args = []

        # Add composition timing to both RGB and mask
        rgb_args.extend(composition_timing_args)
        mask_args.extend(composition_timing_args)

        if (
            self.primary_path
            and Foreground._get_file_extension(self.primary_path) == ".webm"
            and ctx.check_webm_support()
        ):
            rgb_args.extend(["-c:v", "libvpx-vp9"])
            rgb_args.extend(source_trim_args)
            rgb_args.extend(["-i", self.primary_path])
            mask_args.extend(source_trim_args)
            mask_args.extend(["-i", self.mask_path])
            ctx.logger.debug(
                f"Using libvpx-vp9 decoder for WebM RGB: {self.primary_path}"
            )
        else:
            rgb_args.extend(source_trim_args)
            rgb_args.extend(["-i", self.primary_path])
            mask_args.extend(source_trim_args)
            mask_args.extend(["-i", self.mask_path])

        args = rgb_args + mask_args
        input_map_updates = {
            f"layer_{layer_idx}_rgb": input_idx,
            f"layer_{layer_idx}_mask": input_idx + 1,
        }

        # Add separate audio file if present
        if self.audio_path:
            audio_args = []
            audio_args.extend(composition_timing_args)
            audio_args.extend(source_trim_args)
            audio_args.extend(["-i", self.audio_path])
            args.extend(audio_args)
            audio_key = f"layer_{layer_idx}_audio"
            input_map_updates[audio_key] = input_idx + 2
            audio_input_key = audio_key  # Use separate audio file
        else:
            audio_input_key = f"layer_{layer_idx}_rgb"  # Fallback to RGB input

        return args, input_map_updates, audio_input_key

    def _get_stacked_inputs(
        self,
        input_idx: int,
        layer_idx: int,
        ctx: MediaContext,
        source_trim_args: List[str],
        composition_timing_args: List[str],
    ) -> Tuple[List[str], Dict[str, int], Optional[str]]:
        """Handle stacked video inputs."""
        args = []
        args.extend(composition_timing_args)
        args.extend(source_trim_args)
        args.extend(["-i", self.primary_path])

        layer_key = f"layer_{layer_idx}_stacked"
        input_map_updates = {layer_key: input_idx}
        audio_input_key = layer_key  # Same input for both video and audio

        return args, input_map_updates, audio_input_key

    def _get_webm_filters(
        self, layer_label: str, input_map: Dict[str, int], alpha_enabled: bool = True
    ) -> List[str]:
        """Get filters for WebM VP9 format."""
        if not alpha_enabled:
            # Convert RGBA to RGB to remove alpha channel
            input_key = (
                f"layer_{layer_label.split('_')[1]}"  # Extract layer index from label
            )
            return [f"[{input_map[input_key]}:v]format=rgb24[{layer_label}_merged]"]
        # WebM VP9 with alpha is already in the right format, no filters needed
        return []

    def _get_mov_filters(
        self, layer_label: str, input_map: Dict[str, int], alpha_enabled: bool = True
    ) -> List[str]:
        """Get filters for MOV ProRes format."""
        if not alpha_enabled:
            # Convert RGBA to RGB to remove alpha channel
            input_key = (
                f"layer_{layer_label.split('_')[1]}"  # Extract layer index from label
            )
            return [f"[{input_map[input_key]}:v]format=rgb24[{layer_label}_merged]"]
        # MOV ProRes with alpha is already in the right format, no filters needed
        return []

    def _get_bundle_filters(
        self, layer_label: str, input_map: Dict[str, int], alpha_enabled: bool = True
    ) -> List[str]:
        """Get filters for pro bundle format (RGB + mask files)."""
        filters = []
        rgb_input = f"[{input_map[f'{layer_label}_rgb']}:v]"

        if alpha_enabled:
            # Full alpha processing with mask
            mask_input = f"[{input_map[f'{layer_label}_mask']}:v]"

            # Create the alphamerge filter chain with proper labels and binary mask conversion
            filters.append(f"{rgb_input}format=rgba[{layer_label}_rgba]")
            filters.append(f"{mask_input}format=gray[{layer_label}_mask_gray]")
            # Convert mask to binary (0 or 255) - same as stacked processing
            filters.append(
                f"[{layer_label}_mask_gray]geq='if(gte(lum(X,Y),128),255,0)'[{layer_label}_binary_mask]"
            )
            filters.append(
                f"[{layer_label}_rgba][{layer_label}_binary_mask]alphamerge[{layer_label}_merged]"
            )
        else:
            # No alpha - just use RGB directly
            filters.append(f"{rgb_input}format=rgb24[{layer_label}_merged]")

        return filters

    def _get_stacked_filters(
        self, layer_label: str, input_map: Dict[str, int], alpha_enabled: bool = True
    ) -> List[str]:
        """Get filters for stacked video format."""
        filters = []
        stacked_input = f"[{input_map[f'{layer_label}_stacked']}:v]"

        # Always extract top half (original video)
        filters.append(f"{stacked_input}crop=iw:ih/2:0:0[{layer_label}_top]")

        if alpha_enabled:
            # Full alpha processing with mask
            filters.append(f"[{layer_label}_top]format=rgba[{layer_label}_top_rgba]")

            # Extract bottom half (mask), convert to grayscale, and make binary
            filters.append(f"{stacked_input}crop=iw:ih/2:0:ih/2[{layer_label}_bottom]")
            filters.append(
                f"[{layer_label}_bottom]format=gray[{layer_label}_mask_gray]"
            )
            filters.append(
                f"[{layer_label}_mask_gray]geq='if(gte(lum(X,Y),128),255,0)'[{layer_label}_binary_mask]"
            )

            # Apply mask as alpha channel using alphamerge
            filters.append(
                f"[{layer_label}_top_rgba][{layer_label}_binary_mask]alphamerge[{layer_label}_merged]"
            )
        else:
            # No alpha - just use RGB from top half directly
            filters.append(f"[{layer_label}_top]format=rgb24[{layer_label}_merged]")

        return filters

    def get_current_input_label(
        self, layer_label: str, alpha_enabled: bool = True
    ) -> str:
        """Get the current input label after all format-specific processing."""
        if self.format == "webm_vp9":
            if alpha_enabled:
                # WebM VP9 uses the direct input when alpha is enabled
                input_key = f"layer_{layer_label.split('_')[1]}"  # Extract layer index
                return f"[{input_key}:v]"
            else:
                # When alpha is disabled, use the merged output
                return f"[{layer_label}_merged]"
        elif self.format == "mov_prores":
            if alpha_enabled:
                # MOV ProRes uses the direct input when alpha is enabled
                input_key = f"layer_{layer_label.split('_')[1]}"  # Extract layer index
                return f"[{input_key}:v]"
            else:
                # When alpha is disabled, use the merged output
                return f"[{layer_label}_merged]"
        elif self.format in ("pro_bundle", "stacked_video"):
            # Bundle and stacked formats always use the merged output
            return f"[{layer_label}_merged]"
        else:
            raise ValueError(f"Unknown foreground format: {self.format}")
