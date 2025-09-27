"""Encoder profiles for video output with FFmpeg argument generation."""

from pydantic import BaseModel
from typing import List, Optional, Literal


class EncoderProfile(BaseModel):
    """Encoder profile that generates FFmpeg arguments."""

    kind: Literal[
        "h264",
        "vp9",
        "transparent_webm",
        "prores_4444",
        "png_sequence",
        "stacked_video",
    ]
    crf: Optional[int] = None
    preset: Optional[str] = None
    layout: Optional[Literal["vertical", "horizontal"]] = None
    fps: Optional[float] = None

    @staticmethod
    def h264(crf: int = 18, preset: str = "medium") -> "EncoderProfile":
        """
        H.264 encoder profile for standard video output.

        Args:
            crf: Constant Rate Factor (lower = higher quality)
            preset: Encoding preset (ultrafast, superfast, veryfast, faster, fast, medium, slow, slower, veryslow)

        Returns:
            H.264 encoder profile
        """
        return EncoderProfile(kind="h264", crf=crf, preset=preset)

    @staticmethod
    def vp9(crf: int = 32) -> "EncoderProfile":
        """
        VP9 encoder profile for web-optimized video.

        Args:
            crf: Constant Rate Factor

        Returns:
            VP9 encoder profile
        """
        return EncoderProfile(kind="vp9", crf=crf)

    @staticmethod
    def transparent_webm(crf: int = 28) -> "EncoderProfile":
        """
        Transparent WebM encoder profile with alpha channel.

        Args:
            crf: Constant Rate Factor

        Returns:
            Transparent WebM encoder profile
        """
        return EncoderProfile(kind="transparent_webm", crf=crf)

    @staticmethod
    def prores_4444() -> "EncoderProfile":
        """
        ProRes 4444 encoder profile for high-quality transparent video.

        Returns:
            ProRes 4444 encoder profile
        """
        return EncoderProfile(kind="prores_4444")

    @staticmethod
    def png_sequence(fps: Optional[float] = None) -> "EncoderProfile":
        """
        PNG sequence encoder profile for frame-by-frame output.

        Args:
            fps: Frame rate for sequence

        Returns:
            PNG sequence encoder profile
        """
        return EncoderProfile(kind="png_sequence", fps=fps)

    @staticmethod
    def stacked_video(
        layout: Literal["vertical", "horizontal"] = "vertical",
    ) -> "EncoderProfile":
        """
        Stacked video encoder profile (RGB + mask).

        Args:
            layout: Stacking layout (vertical or horizontal)

        Returns:
            Stacked video encoder profile
        """
        return EncoderProfile(kind="stacked_video", layout=layout)

    def args(self, out_path: str) -> List[str]:
        """
        Generate FFmpeg arguments for this encoder profile.

        Args:
            out_path: Output file path

        Returns:
            List of FFmpeg arguments
        """
        if self.kind == "h264":
            args = [
                "-c:v",
                "libx264",
                "-crf",
                str(self.crf or 18),
                "-preset",
                self.preset or "medium",
                "-pix_fmt",
                "yuv420p",
            ]

        elif self.kind == "vp9":
            args = [
                "-c:v",
                "libvpx-vp9",
                "-crf",
                str(self.crf or 32),
                "-b:v",
                "0",  # Use CRF mode
            ]

        elif self.kind == "transparent_webm":
            args = [
                "-c:v",
                "libvpx-vp9",
                "-crf",
                str(self.crf or 28),
                "-b:v",
                "0",
                "-pix_fmt",
                "yuva420p",  # Enable alpha channel
                "-auto-alt-ref",
                "0",  # Disable alt-ref frames for better compatibility
            ]

        elif self.kind == "prores_4444":
            args = [
                "-c:v",
                "prores_ks",
                "-profile:v",
                "4",  # ProRes 4444
                "-pix_fmt",
                "yuva444p10le",
            ]

        elif self.kind == "png_sequence":
            args = ["-c:v", "png", "-pix_fmt", "rgba"]
            if self.fps:
                args.extend(["-r", str(self.fps)])

        elif self.kind == "stacked_video":
            # Stacked video uses standard H.264 encoding
            # The stacking is handled in the composition phase
            args = [
                "-c:v",
                "libx264",
                "-crf",
                str(self.crf or 18),
                "-preset",
                self.preset or "medium",
                "-pix_fmt",
                "yuv420p",
            ]

        else:
            raise ValueError(f"Unknown encoder kind: {self.kind}")

        # Add output path
        args.append(out_path)

        return args
