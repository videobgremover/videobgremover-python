"""Video composition system with layer handling and canvas rules."""

import subprocess
from typing import List, Optional, Tuple, Literal, Dict, Any
from contextlib import contextmanager
from .backgrounds import Background, BaseBackground
from .foregrounds import Foreground
from .encoders import EncoderProfile
from .context import MediaContext, default_context
from ..core.types import Anchor, SizeMode, ProgressCb


class LayerHandle:
    """Handle for manipulating a layer in a composition."""

    def __init__(self, comp: "Composition", idx: int):
        """Initialize layer handle."""
        self._comp = comp
        self._idx = idx

    # Position/Size methods
    def at(
        self, anchor: Anchor = Anchor.CENTER, dx: int = 0, dy: int = 0
    ) -> "LayerHandle":
        """Set layer position using anchor and offset."""
        layer = self._comp._layers[self._idx]
        layer["anchor"] = anchor
        layer["dx"] = dx
        layer["dy"] = dy
        return self

    def xy(self, x_expr: str, y_expr: str) -> "LayerHandle":
        """Set layer position using custom expressions."""
        layer = self._comp._layers[self._idx]
        layer["x_expr"] = x_expr
        layer["y_expr"] = y_expr
        return self

    def size(
        self,
        mode: SizeMode,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        percent: Optional[float] = None,
        scale: Optional[float] = None,
    ) -> "LayerHandle":
        """Set layer size mode and parameters."""
        layer = self._comp._layers[self._idx]
        layer["size"] = (mode, width, height, percent, scale)
        return self

    # Visual effects
    def opacity(self, alpha: float) -> "LayerHandle":
        """Set layer opacity (0.0 to 1.0)."""
        layer = self._comp._layers[self._idx]
        layer["opacity"] = max(0.0, min(1.0, alpha))
        return self

    def rotate(self, degrees: float) -> "LayerHandle":
        """Set layer rotation in degrees."""
        layer = self._comp._layers[self._idx]
        layer["rotate"] = degrees
        return self

    def crop(self, x: int, y: int, w: int, h: int) -> "LayerHandle":
        """Set layer crop rectangle."""
        layer = self._comp._layers[self._idx]
        layer["crop"] = (x, y, w, h)
        return self

    # Timing methods - Composition timing (when to show in final video)
    def start(self, seconds: float) -> "LayerHandle":
        """Set when this layer starts appearing in the composition timeline."""
        layer = self._comp._layers[self._idx]
        layer["comp_start"] = seconds
        return self

    def end(self, seconds: float) -> "LayerHandle":
        """Set when this layer stops appearing in the composition timeline."""
        layer = self._comp._layers[self._idx]
        layer["comp_end"] = seconds
        return self

    def duration(self, seconds: float) -> "LayerHandle":
        """Set how long this layer appears in the composition (from its start time)."""
        layer = self._comp._layers[self._idx]
        layer["comp_duration"] = seconds
        return self

    # Source trimming (which part of source video to use)
    def subclip(self, start: float, end: Optional[float] = None) -> "LayerHandle":
        """
        Trim the source video to use only a specific time range.

        Args:
            start: Start time in source video (seconds)
            end: End time in source video (seconds, None = use until end)
        """
        layer = self._comp._layers[self._idx]
        layer["source_trim"] = (start, end)
        return self

    # Audio control
    def audio(self, enabled: bool = True, volume: float = 1.0) -> "LayerHandle":
        """
        Set audio properties for this layer.

        Args:
            enabled: Whether to include audio from this layer
            volume: Audio volume (0.0 to 1.0, where 1.0 is full volume)
        """
        layer = self._comp._layers[self._idx]
        layer["audio_enabled"] = enabled
        layer["audio_volume"] = max(0.0, min(1.0, volume))  # Clamp volume to 0.0-1.0
        return self

    # Z-order
    def z(self, index: int) -> "LayerHandle":
        """Set layer z-index (rendering order)."""
        layer = self._comp._layers[self._idx]
        layer["z"] = index
        return self

    def alpha(self, enabled: bool = True) -> "LayerHandle":
        """
        Control alpha channel transparency for this layer.

        Args:
            enabled: Whether to use alpha channel transparency (default: True)

        Returns:
            LayerHandle for method chaining
        """
        layer = self._comp._layers[self._idx]
        layer["alpha_enabled"] = enabled
        return self


class Composition:
    """Video composition with layers and effects."""

    def __init__(
        self,
        background: Optional[BaseBackground] = None,
        ctx: Optional[MediaContext] = None,
    ):
        """
        Initialize composition.

        Args:
            background: Optional background
            ctx: Media context for operations
        """
        self.ctx = ctx or default_context()
        self._background: Optional[BaseBackground] = background
        self._layers: List[Dict[str, Any]] = []
        self._canvas_hint: Optional[Tuple[int, int, float]] = None
        self._explicit_duration: Optional[float] = None  # For rule 3: explicit override

    # Background/Canvas setup
    def background(self, bg: BaseBackground) -> "Composition":
        """Set composition background."""
        self._background = bg
        return self

    @staticmethod
    def canvas(
        width: int, height: int, fps: float, ctx: Optional[MediaContext] = None
    ) -> "Composition":
        """Create composition with explicit canvas size."""
        return Composition(Background.empty(width, height, fps), ctx=ctx)

    def set_canvas(self, width: int, height: int, fps: float) -> "Composition":
        """Set explicit canvas dimensions."""
        self._canvas_hint = (width, height, fps)
        return self

    def set_duration(self, seconds: float) -> "Composition":
        """Set explicit composition duration (Rule 3: Override)."""
        self._explicit_duration = seconds
        return self

    # Layer management
    def add(self, fg: Foreground, name: Optional[str] = None) -> LayerHandle:
        """
        Add a foreground layer to the composition.

        Args:
            fg: Foreground to add
            name: Optional layer name

        Returns:
            LayerHandle for further configuration
        """
        layer_name = name or f"layer{len(self._layers)}"

        layer = {
            "name": layer_name,
            "fg": fg,
            "anchor": Anchor.CENTER,
            "dx": 0,
            "dy": 0,
            "x_expr": None,
            "y_expr": None,
            "size": (SizeMode.CONTAIN, None, None, None, None),
            "opacity": 1.0,
            "rotate": 0.0,
            "crop": None,
            # Timing system
            "comp_start": None,  # When to start in composition timeline
            "comp_end": None,  # When to end in composition timeline
            "comp_duration": None,  # How long to show (alternative to comp_end)
            "source_trim": None,  # (start, end) - which part of source to use
            # Audio system (enabled by default for foregrounds)
            "audio_enabled": True,  # Foreground audio enabled by default
            "audio_volume": 1.0,  # Full volume by default
            # Alpha transparency system
            "alpha_enabled": True,  # Alpha channel transparency enabled by default
            "z": len(self._layers),
        }

        self._layers.append(layer)
        return LayerHandle(self, len(self._layers) - 1)

    # Export methods
    def to_file(
        self,
        out_path: str,
        encoder: EncoderProfile,
        on_progress: ProgressCb = None,
        verbose: bool = False,
    ) -> None:
        """
        Export composition to file.

        Args:
            out_path: Output file path
            encoder: Encoder profile to use
            on_progress: Progress callback
            verbose: Show FFmpeg output in real-time
        """
        argv = self._build_ffmpeg_argv(out_path, encoder, to_pipe=False)
        self._run(argv, on_progress, verbose=verbose)

    def to_stream(
        self,
        format: Literal["y4m", "webm", "matroska", "mp4_fragmented"],
        video: Optional[EncoderProfile] = None,
        audio: Optional[str] = None,
        on_progress: ProgressCb = None,
    ):
        """
        Export composition to stream.

        Args:
            format: Stream format
            video: Video encoder profile
            audio: Audio codec
            on_progress: Progress callback

        Returns:
            Stream context manager
        """
        encoder = video or EncoderProfile.vp9()
        argv = self._build_ffmpeg_argv("-", encoder, to_pipe=True, stream_format=format)
        return self._pipe_context(argv, on_progress)

    def dry_run(self) -> str:
        """
        Generate FFmpeg command without executing.

        Returns:
            FFmpeg command string
        """
        argv = self._build_ffmpeg_argv("OUT.mp4", EncoderProfile.h264(), to_pipe=False)
        return " ".join(map(str, argv))

    # Internal methods
    def _get_canvas_size(self) -> Tuple[int, int, float]:
        """Determine canvas size from background, hint, or layers."""
        # Priority 1: Background dimensions (all background types have these)
        if (
            self._background
            and self._background.width
            and self._background.height
            and self._background.fps
        ):
            return self._background.width, self._background.height, self._background.fps

        # Priority 2: Explicit canvas hint
        if self._canvas_hint:
            return self._canvas_hint

        # Priority 3: Error - cannot determine canvas size
        raise RuntimeError(
            "Cannot determine canvas size. Please provide a background "
            "(Background.from_image/from_video/from_color) or set explicit canvas dimensions "
            "using Composition.canvas() or .set_canvas()."
        )

    def _get_composition_duration(self) -> Optional[float]:
        """Get composition duration using simple 3-rule logic."""
        # Rule 3: Explicit override wins
        if self._explicit_duration is not None:
            return self._explicit_duration

        # Rule 1: Video background controls duration
        if self._background and self._background.controls_duration():
            if hasattr(self._background, "get_duration"):
                bg_duration = self._background.get_duration()
                if bg_duration and bg_duration > 0:
                    return bg_duration

        # Rule 2: Longest foreground controls duration
        return self._get_longest_foreground_duration()

    def _get_longest_foreground_duration(self) -> Optional[float]:
        """Get duration of longest foreground layer."""
        max_duration = 0.0
        for layer in self._layers:
            fg_duration = self._get_foreground_duration(layer["fg"])
            if fg_duration and fg_duration > max_duration:
                max_duration = fg_duration
        return max_duration if max_duration > 0 else None

    def _get_foreground_duration(self, fg: Foreground) -> Optional[float]:
        """Get duration of a foreground using already-probed video info."""
        # Use the video info from VideoSource (should already be probed during creation)
        if hasattr(fg, "_video_info") and fg._video_info:
            duration = fg._video_info.get("duration")
            if duration:
                return float(duration)

        # If no video info available, return None
        # This should not happen if foreground was created properly via factory methods
        return None

    def _log_duration_info(self, duration: float) -> None:
        """Log friendly duration information."""
        if self._explicit_duration is not None:
            self.ctx.logger.info(f"🎬 Using explicit duration: {duration:.1f}s")
        elif self._background and self._background.controls_duration():
            self.ctx.logger.info(f"🎬 Using video background duration: {duration:.1f}s")
        else:
            self.ctx.logger.info(
                f"🎬 Using longest foreground duration: {duration:.1f}s"
            )

    def _build_ffmpeg_argv(
        self,
        out_path: str,
        encoder: EncoderProfile,
        to_pipe: bool,
        stream_format: Optional[str] = None,
    ) -> List[str]:
        """Build complete FFmpeg argument list."""
        canvas_width, canvas_height, canvas_fps = self._get_canvas_size()

        argv = [self.ctx.ffmpeg, "-y"]  # Force overwrite existing files

        # Input sources
        input_map = {}  # Map input labels to indices
        input_idx = 0

        # Add background (clean approach with separate classes)
        if self._background:
            # Each background class handles its own FFmpeg arguments
            bg_args = self._background.get_ffmpeg_input_args(
                canvas_width, canvas_height, canvas_fps, self.ctx
            )
            argv.extend(bg_args)
            input_map["background"] = input_idx
            input_idx += 1
        else:
            # No background - create transparent
            argv.extend(
                [
                    "-f",
                    "lavfi",
                    "-i",
                    f"color=c=black@0.0:size={canvas_width}x{canvas_height}:rate={canvas_fps}",
                ]
            )
            input_map["background"] = input_idx
            input_idx += 1

        # Add layer inputs with timing and collect audio info simultaneously
        audio_inputs = []

        for i, layer in enumerate(self._layers):
            fg = layer["fg"]

            # Helper functions for timing arguments
            def get_source_trim_args():
                if fg.source_trim:
                    start, end = fg.source_trim
                    args = ["-ss", str(start)]
                    if end is not None:
                        args.extend(["-t", str(end - start)])
                    return args
                return []

            def get_composition_timing_args():
                # Composition timing is now handled in filter graph, not input level
                return []

            # Use Foreground's clean method to get inputs
            source_trim_args = get_source_trim_args()
            composition_timing_args = get_composition_timing_args()

            ffmpeg_args, input_map_updates, audio_input_key = fg.get_ffmpeg_inputs(
                input_idx, i, self.ctx, source_trim_args, composition_timing_args
            )

            # Add the FFmpeg arguments
            argv.extend(ffmpeg_args)

            # Update input map
            input_map.update(input_map_updates)
            input_idx = (
                max(input_map.values()) + 1
            )  # Update input_idx based on what was actually added

            # Collect audio info immediately while we know the input key
            if (
                layer["audio_enabled"]
                and audio_input_key
                and audio_input_key in input_map
            ):
                audio_inputs.append(
                    {
                        "input": f"{input_map[audio_input_key]}:a",
                        "volume": layer["audio_volume"],
                        "type": "foreground",
                        "layer_index": i,
                    }
                )

        # Build filter graph
        filter_parts = []
        current_output = f"[{input_map['background']}:v]"

        # Sort layers by z-index
        sorted_layers = sorted(enumerate(self._layers), key=lambda x: x[1]["z"])

        for layer_idx, (original_idx, layer) in enumerate(sorted_layers):
            fg = layer["fg"]

            # Use Foreground's clean method to get filters
            layer_label = f"layer_{original_idx}"
            alpha_enabled = layer.get(
                "alpha_enabled", True
            )  # Get alpha setting from layer
            format_filters = fg.get_ffmpeg_filters(
                layer_label, input_map, alpha_enabled
            )

            # Add format-specific filters
            filter_parts.extend(format_filters)

            # Get the current input after format processing
            if format_filters:
                # Format produced filters, use the merged output
                layer_output = fg.get_current_input_label(layer_label, alpha_enabled)
            else:
                # No format filters, use direct input
                layer_output = f"[{input_map[f'layer_{original_idx}']}:v]"

            # Apply layer transformations (positioning, sizing, effects, timing)
            transformation_filters = self._get_layer_transformation_filters(
                layer, original_idx, layer_output, canvas_width, canvas_height
            )
            filter_parts.extend(transformation_filters)

            # Get final layer output after transformations
            if transformation_filters:
                layer_output = f"[layer_{original_idx}_final]"
            # else layer_output remains unchanged

            # Overlay current layer
            # Configure overlay behavior based on duration policy
            # Always use eof_action=pass to let the duration policy (-t flag) control final duration
            # This ensures foregrounds disappear when they end instead of freezing on last frame

            # Calculate position from anchor and offsets
            position_params = self._calculate_overlay_position(
                layer, canvas_width, canvas_height
            )

            # Overlay parameters - timing now handled by setpts in layer filters
            overlay_params = f"={position_params}:eof_action=pass"

            if layer_idx == len(sorted_layers) - 1:
                # Last layer - output to final
                filter_parts.append(
                    f"{current_output}{layer_output}overlay{overlay_params}[out]"
                )
            else:
                # Intermediate layer
                temp_output = f"[tmp{layer_idx}]"
                filter_parts.append(
                    f"{current_output}{layer_output}overlay{overlay_params}{temp_output}"
                )
                current_output = temp_output

        # Store video filter parts for later combination with audio filters
        video_filter_parts = filter_parts.copy() if filter_parts else []
        video_map_args = []

        if filter_parts:
            video_map_args = ["-map", "[out]"]
        else:
            # No layers, just use background
            video_map_args = ["-map", f"{input_map['background']}:v"]

        # Add background audio if enabled (audio_inputs already contains foreground audio)
        if (
            self._background
            and hasattr(self._background, "audio_enabled")
            and self._background.audio_enabled
            and hasattr(self._background, "has_audio")
            and self._background.has_audio()
        ):
            audio_inputs.append(
                {
                    "input": f"{input_map['background']}:a",
                    "volume": self._background.audio_volume,
                    "type": "background",
                }
            )

        # Handle audio with proper timing in filter graph (not input-level timing)
        audio_filter_parts = []
        audio_map_args = []

        if len(audio_inputs) == 0:
            # No audio
            audio_map_args = ["-an"]
        elif len(audio_inputs) == 1:
            # Single audio source - but still needs timing if comp_start > 0
            audio_input = audio_inputs[0]

            # Check if this audio needs timing delay
            needs_delay = False
            comp_start = 0

            # Only apply timing delay for foreground audio, not background audio
            if audio_input["type"] == "foreground":
                layer_idx = audio_input.get("layer_index", 0)
                if layer_idx < len(self._layers):
                    layer = self._layers[layer_idx]
                    comp_start = layer.get("comp_start", 0)
                    needs_delay = comp_start and comp_start > 0
            # Background audio should never be delayed - it plays from the beginning

            if needs_delay or audio_input["volume"] != 1.0:
                # Use filter graph for timing and/or volume
                current_label = f"[{audio_input['input']}]"

                # Apply timing delay if needed
                if needs_delay:
                    delay_ms = int(comp_start * 1000)
                    delayed_label = "[audio_delayed]"
                    audio_filter_parts.append(
                        f"{current_label}adelay={delay_ms}|{delay_ms}{delayed_label}"
                    )
                    current_label = delayed_label

                # Apply volume if needed
                if audio_input["volume"] != 1.0:
                    volume_label = "[audio_out]"
                    audio_filter_parts.append(
                        f"{current_label}volume={audio_input['volume']}{volume_label}"
                    )
                    current_label = volume_label
                else:
                    # Rename to standard output
                    if current_label != "[audio_out]":
                        audio_filter_parts.append(f"{current_label}anull[audio_out]")

                audio_map_args = ["-map", "[audio_out]"]
            else:
                # No timing or volume changes needed
                audio_map_args = ["-map", f"{audio_input['input']}?"]
        else:
            # Multiple audio sources - handle timing in audio filters
            processed_audio = []

            for i, audio_input in enumerate(audio_inputs):
                # Get timing info for this layer
                layer_idx = audio_input.get("layer_index", i)
                if layer_idx < len(self._layers):
                    layer = self._layers[layer_idx]
                    comp_start = layer.get("comp_start", 0)
                    comp_duration = layer.get("comp_duration")
                    # comp_end = layer.get("comp_end")  # Not used currently

                    # Start with the raw input
                    current_label = f"[{audio_input['input']}]"

                    # Apply adelay for timing (no asetpts normalization needed for trimmed sources)
                    # Use adelay to position audio in the timeline based on comp_start
                    if comp_start and comp_start > 0:
                        delay_ms = int(comp_start * 1000)
                        delayed_label = f"[audio_delayed_{i}]"
                        audio_filter_parts.append(
                            f"{current_label}adelay={delay_ms}|{delay_ms}{delayed_label}"
                        )
                        current_label = delayed_label

                    # Apply volume if needed
                    if audio_input["volume"] != 1.0:
                        volume_label = f"[audio_vol_{i}]"
                        audio_filter_parts.append(
                            f"{current_label}volume={audio_input['volume']}{volume_label}"
                        )
                        current_label = volume_label

                    processed_audio.append(current_label)
                else:
                    # Fallback for missing layer info
                    if audio_input["volume"] != 1.0:
                        volume_label = f"[audio_vol_{i}]"
                        audio_filter_parts.append(
                            f"[{audio_input['input']}]volume={audio_input['volume']}{volume_label}"
                        )
                        processed_audio.append(volume_label)
                    else:
                        processed_audio.append(f"[{audio_input['input']}]")

            # Mix all processed audio streams
            amix_filter = f"{''.join(processed_audio)}amix=inputs={len(processed_audio)}:duration=longest[audio_out]"
            audio_filter_parts.append(amix_filter)
            audio_map_args = ["-map", "[audio_out]"]

        # Combine video and audio filters
        all_filter_parts = video_filter_parts + audio_filter_parts

        if all_filter_parts:
            argv.extend(["-filter_complex", ";".join(all_filter_parts)])

        # Add video and audio mapping
        argv.extend(video_map_args)
        argv.extend(audio_map_args)

        # Add duration control using simple 3-rule logic
        comp_duration = self._get_composition_duration()
        if comp_duration:
            argv.extend(["-t", str(comp_duration)])
            self._log_duration_info(comp_duration)

        # Add encoder arguments
        encoder_args = encoder.args(out_path if not to_pipe else "-")
        argv.extend(encoder_args[:-1])  # All except output path

        # Handle streaming format
        if to_pipe and stream_format:
            if stream_format == "y4m":
                argv.extend(["-f", "yuv4mpegpipe"])
            elif stream_format == "webm":
                argv.extend(["-f", "webm"])
            elif stream_format == "matroska":
                argv.extend(["-f", "matroska"])
            elif stream_format == "mp4_fragmented":
                argv.extend(["-f", "mp4", "-movflags", "frag_keyframe+empty_moov"])

        # Add output
        argv.append(encoder_args[-1])  # Output path

        return argv

    def _get_layer_transformation_filters(
        self,
        layer: Dict[str, Any],
        layer_idx: int,
        current_input: str,
        canvas_width: int,
        canvas_height: int,
    ) -> List[str]:
        """
        Get FFmpeg filters for layer transformations (positioning, sizing, effects, timing).

        Args:
            layer: Layer configuration dict
            layer_idx: Layer index for labeling
            current_input: Current input label (e.g., "[layer_0_merged]")
            canvas_width: Canvas width
            canvas_height: Canvas height

        Returns:
            List of FFmpeg filter strings
        """
        filters = []
        layer_label = f"layer_{layer_idx}"
        current_output = current_input

        # Apply timeline shifting for composition timing (before other transformations)
        comp_start = layer.get("comp_start")

        if comp_start and comp_start > 0:
            next_label = f"[{layer_label}_timed]"
            # Shift video timeline: reset to 0, then shift by comp_start seconds
            filters.append(
                f"{current_output}setpts=PTS-STARTPTS,setpts=PTS+{comp_start}/TB{next_label}"
            )
            current_output = next_label

        # Apply layer transformations with proper chaining

        # Note: Source trimming is now handled at FFmpeg input level, not in filters

        # Crop
        if layer["crop"]:
            x, y, w, h = layer["crop"]
            next_label = f"[{layer_label}_crop]"
            filters.append(f"{current_output}crop={w}:{h}:{x}:{y}{next_label}")
            current_output = next_label

        # Scale/Size
        size_mode, width, height, percent, scale = layer["size"]
        # Apply scaling based on size mode
        scale_applied = False
        aspect_constraint = self._get_aspect_ratio_constraint(size_mode)

        if size_mode == SizeMode.PX and width and height:
            target_w, target_h = width, height
            scale_applied = True
        elif size_mode == SizeMode.CANVAS_PERCENT:
            target_w, target_h = self._calculate_target_dimensions(
                layer["size"], canvas_width, canvas_height
            )
            scale_applied = True
        elif size_mode in [SizeMode.CONTAIN, SizeMode.COVER]:
            target_w, target_h = canvas_width, canvas_height
            scale_applied = True
        elif size_mode == SizeMode.FIT_WIDTH:
            target_w, target_h = canvas_width, -1
            scale_applied = True
        elif size_mode == SizeMode.FIT_HEIGHT:
            target_w, target_h = -1, canvas_height
            scale_applied = True
        elif size_mode == SizeMode.SCALE:
            # Scale relative to original video dimensions using scale factors
            if width is not None and height is not None:
                # Non-uniform scaling with separate width and height scale factors
                target_w, target_h = f"iw*{width}", f"ih*{height}"
            elif scale is not None:
                # Uniform scaling with single scale factor
                target_w, target_h = f"iw*{scale}", f"ih*{scale}"
            elif width is not None:
                # Width scale factor only, maintain aspect ratio
                target_w, target_h = f"iw*{width}", f"ih*{width}"
            elif height is not None:
                # Height scale factor only, maintain aspect ratio
                target_w, target_h = f"iw*{height}", f"ih*{height}"
            else:
                # No scale specified, use original size (scale=1.0)
                target_w, target_h = "iw", "ih"
            scale_applied = True

        if scale_applied:
            next_label = f"[{layer_label}_scale]"
            scale_params = f"{target_w}:{target_h}"
            if aspect_constraint:
                scale_params += f":force_original_aspect_ratio={aspect_constraint}"
            filters.append(f"{current_output}scale={scale_params}{next_label}")
            current_output = next_label

        # Rotation
        if layer["rotate"] != 0:
            next_label = f"[{layer_label}_rotate]"
            filters.append(
                f"{current_output}rotate={layer['rotate']}*PI/180{next_label}"
            )
            current_output = next_label

        # Opacity
        if layer["opacity"] != 1.0:
            next_label = f"[{layer_label}_opacity]"
            filters.append(
                f"{current_output}colorchannelmixer=aa={layer['opacity']}{next_label}"
            )
            current_output = next_label

        # Update the final output label if we applied any transformations
        if filters:
            # The last filter already has the correct output label
            # Just ensure it ends with the final label
            if not current_output.endswith(f"[layer_{layer_idx}_final]"):
                # Add a null operation to create the final label
                filters.append(f"{current_output}null[layer_{layer_idx}_final]")

        return filters

    def _build_layer_filter(
        self,
        layer: Dict[str, Any],
        layer_idx: int,
        input_map: Dict[str, int],
        canvas_width: int,
        canvas_height: int,
    ) -> str:
        """Build filter string for a single layer."""
        fg = layer["fg"]
        filters = []

        # Generate unique labels for this layer
        layer_label = f"layer_{layer_idx}"

        if fg.format in ("webm_vp9", "mov_prores"):
            # RGBA input - start with the input
            current_input = f"[{input_map[f'layer_{layer_idx}']}:v]"
        elif fg.format == "pro_bundle":
            # Pro bundle (RGB + mask files) - combine them first
            rgb_input = f"[{input_map[f'layer_{layer_idx}_rgb']}:v]"
            mask_input = f"[{input_map[f'layer_{layer_idx}_mask']}:v]"

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
            current_input = f"[{layer_label}_merged]"
        else:  # stacked_video
            # Stacked video - split and process in one command (like overlay tool)
            stacked_input = f"[{input_map[f'layer_{layer_idx}_stacked']}:v]"

            # Extract top half (original video) and convert to RGBA
            filters.append(f"{stacked_input}crop=iw:ih/2:0:0[{layer_label}_top]")
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
            current_input = f"[{layer_label}_merged]"

        # Apply timeline shifting for composition timing (before other transformations)
        comp_start = layer.get("comp_start")
        current_output = current_input  # Initialize current_output from current_input
        filter_index = 0  # Initialize filter index

        if comp_start and comp_start > 0:
            next_label = f"[{layer_label}_timed]"
            # Shift video timeline: reset to 0, then shift by comp_start seconds
            filters.append(
                f"{current_output}setpts=PTS-STARTPTS,setpts=PTS+{comp_start}/TB{next_label}"
            )
            current_output = next_label
            filter_index += 1

        # Apply layer transformations with proper chaining

        # Note: Source trimming is now handled at FFmpeg input level, not in filters

        # Crop
        if layer["crop"]:
            x, y, w, h = layer["crop"]
            next_label = f"[{layer_label}_crop]"
            filters.append(f"{current_output}crop={w}:{h}:{x}:{y}{next_label}")
            current_output = next_label
            filter_index += 1

        # Scale/Size
        size_mode, width, height, percent, scale = layer["size"]
        # Apply scaling based on size mode
        scale_applied = False
        aspect_constraint = self._get_aspect_ratio_constraint(size_mode)

        if size_mode == SizeMode.PX and width and height:
            target_w, target_h = width, height
            scale_applied = True
        elif size_mode == SizeMode.CANVAS_PERCENT:
            target_w, target_h = self._calculate_target_dimensions(
                layer["size"], canvas_width, canvas_height
            )
            scale_applied = True
        elif size_mode in [SizeMode.CONTAIN, SizeMode.COVER]:
            target_w, target_h = canvas_width, canvas_height
            scale_applied = True
        elif size_mode == SizeMode.FIT_WIDTH:
            target_w, target_h = canvas_width, -1
            scale_applied = True
        elif size_mode == SizeMode.FIT_HEIGHT:
            target_w, target_h = -1, canvas_height
            scale_applied = True
        elif size_mode == SizeMode.SCALE:
            # Scale relative to original video dimensions using scale factors
            if width is not None and height is not None:
                # Non-uniform scaling with separate width and height scale factors
                target_w, target_h = f"iw*{width}", f"ih*{height}"
            elif scale is not None:
                # Uniform scaling with single scale factor
                target_w, target_h = f"iw*{scale}", f"ih*{scale}"
            elif width is not None:
                # Width scale factor only, maintain aspect ratio
                target_w, target_h = f"iw*{width}", f"ih*{width}"
            elif height is not None:
                # Height scale factor only, maintain aspect ratio
                target_w, target_h = f"iw*{height}", f"ih*{height}"
            else:
                # No scale specified, use original size (scale=1.0)
                target_w, target_h = "iw", "ih"
            scale_applied = True

        if scale_applied:
            next_label = f"[{layer_label}_scale]"
            scale_params = f"{target_w}:{target_h}"
            if aspect_constraint:
                scale_params += f":force_original_aspect_ratio={aspect_constraint}"
            filters.append(f"{current_output}scale={scale_params}{next_label}")
            current_output = next_label
            filter_index += 1

        # Rotation
        if layer["rotate"] != 0:
            next_label = f"[{layer_label}_rotate]"
            filters.append(
                f"{current_output}rotate={layer['rotate']}*PI/180{next_label}"
            )
            current_output = next_label
            filter_index += 1

        # Opacity
        if layer["opacity"] != 1.0:
            next_label = f"[{layer_label}_opacity]"
            filters.append(
                f"{current_output}colorchannelmixer=aa={layer['opacity']}{next_label}"
            )
            current_output = next_label
            filter_index += 1

        # Note: Composition timing is now handled at overlay level, not in layer filters

        # Return the final output label or the original input if no filters were applied
        if filters:
            # Join all filters with semicolons for proper FFmpeg syntax
            filter_chain = ";".join(filters)
            return f"{filter_chain};{current_output}"
        else:
            # No filters applied, return the input directly
            return current_input

    def _get_overlay_timing_enable(self, layer: Dict[str, Any]) -> str:
        """Get enable parameter for overlay filter timing."""
        comp_start = layer.get("comp_start")
        comp_end = layer.get("comp_end")
        comp_duration = layer.get("comp_duration")

        # Calculate effective start and end times
        start_time = comp_start if comp_start is not None else 0
        end_time = None

        if comp_end is not None:
            end_time = comp_end
        elif comp_duration is not None:
            end_time = start_time + comp_duration

        # Build enable parameter for overlay filter
        # Use between(t,START,END) for precise timing windows
        if end_time is not None:
            # Show between start and end
            return f":enable='between(t,{start_time},{end_time})'"
        elif start_time > 0:
            # Show from start onwards
            return f":enable='gte(t,{start_time})'"

        return ""  # No timing needed (show always)

    def _get_aspect_ratio_constraint(self, size_mode: SizeMode) -> Optional[str]:
        """Get the appropriate aspect ratio constraint for each size mode."""
        if size_mode in [
            SizeMode.CANVAS_PERCENT,
            SizeMode.PX,
            SizeMode.CONTAIN,
            SizeMode.FIT_WIDTH,
            SizeMode.FIT_HEIGHT,
        ]:
            return "decrease"  # Fit within bounds, preserve aspect ratio
        elif size_mode == SizeMode.COVER:
            return "increase"  # Fill bounds, preserve aspect ratio, may crop
        elif size_mode == SizeMode.SCALE:
            return None  # SCALE mode uses explicit scale factors, no automatic aspect ratio constraint
        else:
            return None  # No constraint (stretch to exact dimensions)

    def _calculate_target_dimensions(
        self, size_params: Tuple[Any, ...], canvas_width: int, canvas_height: int
    ) -> Tuple[int, int]:
        """Calculate target dimensions for CANVAS_PERCENT mode sizing."""
        size_mode, width, height, percent, scale = size_params

        if size_mode != SizeMode.CANVAS_PERCENT:
            return canvas_width, canvas_height  # Not used for non-CANVAS_PERCENT modes

        # Same logic as in _build_layer_filter
        if width is not None and height is not None:
            target_width = int(canvas_width * width / 100)
            target_height = int(canvas_height * height / 100)
        elif width is not None:
            target_width = int(canvas_width * width / 100)
            target_height = int(canvas_height * (percent or 100) / 100)
        elif height is not None:
            target_width = int(canvas_width * (percent or 100) / 100)
            target_height = int(canvas_height * height / 100)
        elif percent:
            target_width = int(canvas_width * percent / 100)
            target_height = int(canvas_height * percent / 100)
        else:
            target_width = canvas_width
            target_height = canvas_height

        return target_width, target_height

    def _calculate_overlay_position(
        self, layer: Dict[str, Any], canvas_width: int, canvas_height: int
    ) -> str:
        """Calculate overlay position from anchor and offsets using FFmpeg expressions."""
        anchor = layer["anchor"]
        dx = layer["dx"]
        dy = layer["dy"]

        # Use custom expressions if provided
        if layer["x_expr"] and layer["y_expr"]:
            return f"x='{layer['x_expr']}':y='{layer['y_expr']}'"

        # Check if this is CANVAS_PERCENT mode - if so, use target box dimensions for positioning
        size_mode = layer["size"][0]
        use_target_box = size_mode == SizeMode.CANVAS_PERCENT

        if use_target_box:
            target_width, target_height = self._calculate_target_dimensions(
                layer["size"], canvas_width, canvas_height
            )

        # Calculate position based on anchor
        # For CANVAS_PERCENT mode: use target box dimensions for positioning
        # For other modes: use actual video dimensions (w, h variables in FFmpeg)
        if use_target_box:
            # CANVAS_PERCENT mode: position the target box, then center video within it
            if anchor == Anchor.TOP_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.TOP_CENTER:
                x_expr = (
                    f"(W-{target_width})/2{dx:+d}"
                    if dx != 0
                    else f"(W-{target_width})/2"
                )
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.TOP_RIGHT:
                x_expr = f"W-{target_width}{dx:+d}" if dx != 0 else f"W-{target_width}"
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.CENTER_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = (
                    f"(H-{target_height})/2{dy:+d}"
                    if dy != 0
                    else f"(H-{target_height})/2"
                )
            elif anchor == Anchor.CENTER:
                x_expr = (
                    f"(W-{target_width})/2{dx:+d}"
                    if dx != 0
                    else f"(W-{target_width})/2"
                )
                y_expr = (
                    f"(H-{target_height})/2{dy:+d}"
                    if dy != 0
                    else f"(H-{target_height})/2"
                )
            elif anchor == Anchor.CENTER_RIGHT:
                x_expr = f"W-{target_width}{dx:+d}" if dx != 0 else f"W-{target_width}"
                y_expr = (
                    f"(H-{target_height})/2{dy:+d}"
                    if dy != 0
                    else f"(H-{target_height})/2"
                )
            elif anchor == Anchor.BOTTOM_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = (
                    f"H-{target_height}{dy:+d}" if dy != 0 else f"H-{target_height}"
                )
            elif anchor == Anchor.BOTTOM_CENTER:
                x_expr = (
                    f"(W-{target_width})/2{dx:+d}"
                    if dx != 0
                    else f"(W-{target_width})/2"
                )
                y_expr = (
                    f"H-{target_height}{dy:+d}" if dy != 0 else f"H-{target_height}"
                )
            elif anchor == Anchor.BOTTOM_RIGHT:
                x_expr = f"W-{target_width}{dx:+d}" if dx != 0 else f"W-{target_width}"
                y_expr = (
                    f"H-{target_height}{dy:+d}" if dy != 0 else f"H-{target_height}"
                )
            else:
                # Default to center
                x_expr = (
                    f"(W-{target_width})/2{dx:+d}"
                    if dx != 0
                    else f"(W-{target_width})/2"
                )
                y_expr = (
                    f"(H-{target_height})/2{dy:+d}"
                    if dy != 0
                    else f"(H-{target_height})/2"
                )

            # Align video to anchor within the target box
            if anchor in [Anchor.TOP_RIGHT, Anchor.CENTER_RIGHT, Anchor.BOTTOM_RIGHT]:
                # Right-aligned: position video at right edge of target box
                x_expr = f"({x_expr})+({target_width}-w)"
            elif anchor in [Anchor.TOP_CENTER, Anchor.CENTER, Anchor.BOTTOM_CENTER]:
                # Center-aligned: center video within target box
                x_expr = f"({x_expr})+({target_width}-w)/2"
            # Left-aligned anchors: video stays at left edge of target box (no adjustment needed)

            if anchor in [
                Anchor.BOTTOM_LEFT,
                Anchor.BOTTOM_CENTER,
                Anchor.BOTTOM_RIGHT,
            ]:
                # Bottom-aligned: position video at bottom edge of target box
                y_expr = f"({y_expr})+({target_height}-h)"
            elif anchor in [Anchor.CENTER_LEFT, Anchor.CENTER, Anchor.CENTER_RIGHT]:
                # Center-aligned: center video within target box
                y_expr = f"({y_expr})+({target_height}-h)/2"
            # Top-aligned anchors: video stays at top edge of target box (no adjustment needed)
        else:
            # Other modes: use actual video dimensions (w, h variables in FFmpeg)
            if anchor == Anchor.TOP_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.TOP_CENTER:
                x_expr = f"(W-w)/2{dx:+d}" if dx != 0 else "(W-w)/2"
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.TOP_RIGHT:
                x_expr = f"W-w{dx:+d}" if dx != 0 else "W-w"
                y_expr = f"0{dy:+d}" if dy != 0 else "0"
            elif anchor == Anchor.CENTER_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = f"(H-h)/2{dy:+d}" if dy != 0 else "(H-h)/2"
            elif anchor == Anchor.CENTER:
                x_expr = f"(W-w)/2{dx:+d}" if dx != 0 else "(W-w)/2"
                y_expr = f"(H-h)/2{dy:+d}" if dy != 0 else "(H-h)/2"
            elif anchor == Anchor.CENTER_RIGHT:
                x_expr = f"W-w{dx:+d}" if dx != 0 else "W-w"
                y_expr = f"(H-h)/2{dy:+d}" if dy != 0 else "(H-h)/2"
            elif anchor == Anchor.BOTTOM_LEFT:
                x_expr = f"0{dx:+d}" if dx != 0 else "0"
                y_expr = f"H-h{dy:+d}" if dy != 0 else "H-h"
            elif anchor == Anchor.BOTTOM_CENTER:
                x_expr = f"(W-w)/2{dx:+d}" if dx != 0 else "(W-w)/2"
                y_expr = f"H-h{dy:+d}" if dy != 0 else "H-h"
            elif anchor == Anchor.BOTTOM_RIGHT:
                x_expr = f"W-w{dx:+d}" if dx != 0 else "W-w"
                y_expr = f"H-h{dy:+d}" if dy != 0 else "H-h"
            else:
                # Default to center
                x_expr = f"(W-w)/2{dx:+d}" if dx != 0 else "(W-w)/2"
                y_expr = f"(H-h)/2{dy:+d}" if dy != 0 else "(H-h)/2"

        return f"x='{x_expr}':y='{y_expr}'"

    def _run(
        self, argv: List[str], on_progress: ProgressCb = None, verbose: bool = False
    ) -> None:
        """Execute FFmpeg command with progress tracking."""
        self.ctx.logger.info(f"Running FFmpeg: {' '.join(argv)}")

        try:
            if verbose:
                # Verbose mode - show FFmpeg output in real-time
                print(f"🔧 FFmpeg command: {' '.join(argv)}")
                process = subprocess.Popen(argv, text=True, stdin=subprocess.DEVNULL)
                process.wait()

                if process.returncode != 0:
                    raise RuntimeError(
                        f"FFmpeg failed with return code: {process.returncode}"
                    )
            else:
                # Normal mode - capture output
                process = subprocess.Popen(
                    argv,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    stdin=subprocess.DEVNULL,
                )

                # Simple progress tracking (could be enhanced)
                if on_progress:
                    on_progress("processing")

                stdout, stderr = process.communicate()

                if process.returncode != 0:
                    raise RuntimeError(f"FFmpeg failed: {stderr}")

            if on_progress:
                on_progress("completed")

            self.ctx.logger.info("FFmpeg completed successfully")

        except Exception as e:
            raise RuntimeError(f"FFmpeg execution failed: {e}")

    @contextmanager
    def _pipe_context(self, argv: List[str], on_progress: ProgressCb = None):
        """Context manager for streaming output."""
        self.ctx.logger.info(f"Starting FFmpeg stream: {' '.join(argv)}")

        process = subprocess.Popen(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.DEVNULL,
        )

        try:
            yield process.stdout
        finally:
            process.terminate()
            process.wait()
