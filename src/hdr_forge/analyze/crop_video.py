import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Counter, Optional, Tuple
from dataclasses import dataclass
from hdr_forge.cli.cli_output import ProgressBarSpinner, print_err, print_warn
from hdr_forge.typedefs.encoder_typing import CropMode, CropSettings, HdrSdrFormat
from hdr_forge.video import Video

@dataclass
class CropResult:
    width: int = 0
    height: int = 0
    x: int = 0
    y: int = 0
    is_valid: bool = False

class VideoCropper:
    def __init__(self, video: Video, crop_settings: CropSettings, encoding_hdr_sdr_format: HdrSdrFormat):
        self._video: Video = video
        self._crop_settings: CropSettings = crop_settings
        self._encoding_hdr_sdr_format: HdrSdrFormat = encoding_hdr_sdr_format

        self._crop_result = CropResult(
            width=video.width,
            height=video.height,
            x=0,
            y=0,
            is_valid=False
        )

    def _detect_crop_at_position(self, position_seconds: int) -> Optional[Tuple[int, int, int, int]]:
        hdr_cropdetect_filter: str = ""
        if self._video.is_hdr_video():
            hdr_cropdetect_filter = "zscale=transfer=bt709,format=yuv420p,hqdn3d=1.5:1.5:6:6,"

        cmd: list[str] = [
            'ffmpeg',
            '-ss', str(position_seconds),
            '-i', str(self._video._filepath),
            '-vf', f'{hdr_cropdetect_filter}cropdetect=24:16:0',
            '-frames:v', '30',
            '-f', 'null',
            '-'
        ]

        try:
            result: subprocess.CompletedProcess[str] = subprocess.run(
                cmd, capture_output=True, text=True, timeout=30
            )

            import re
            crop_pattern = re.compile(r'crop=(\d+):(\d+):(\d+):(\d+)')

            for line in result.stderr.split('\n'):
                match = crop_pattern.search(line)
                if match:
                    w, h, x, y = map(int, match.groups())
                    return (w, h, x, y)
        except (subprocess.TimeoutExpired, Exception):
            pass

        return None

    def _detect_crop_auto(
        self,
        check_samples: int = 10,
        max_workers: int = 16,
    ) -> Optional[Tuple[int, int, int, int]]:
        progressbar = ProgressBarSpinner(description="Detecting crop")
        progressbar.start()

        duration: float = self._video.get_duration_seconds()
        if duration <= 0:
            return None

        interval: float = duration / (check_samples + 1)
        positions: list[int] = [int(interval * (i + 1)) for i in range(check_samples)]

        crop_results: list = []
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self._detect_crop_at_position, pos): pos
                for pos in positions
            }

            for future in as_completed(futures):
                result = future.result()
                if result:
                    crop_results.append(result)
                completed += 1

                progressbar.update(percent=(completed / check_samples * 100))

        if not crop_results:
            return None

        crop_counter = Counter(crop_results)

        crop: Tuple[int, int, int, int] = crop_counter.most_common(1)[0][0]

        progressbar.stop(
            text="Crop detection completed",
            long_info_text=f"Detected crop: width={crop[0]}, height={crop[1]}, x={crop[2]}, y={crop[3]}"
        )
        return crop

    def detect_crop(
        self,
    ) -> None:
        if self._crop_settings.mode == CropMode.OFF:
            return

        if self._encoding_hdr_sdr_format == HdrSdrFormat.DOLBY_VISION:
            print_err(msg="Crop detection is not supported for Dolby Vision encoding.")
            sys.exit(1)

        if self._crop_settings.mode == CropMode.AUTO:
            cpu_kerne: int = min(self._crop_settings.check_samples, os.cpu_count() or 4)
            crop_result = self._detect_crop_auto(
                check_samples=self._crop_settings.check_samples,
                max_workers=cpu_kerne,
            )
            if crop_result is None:
                print_warn("Auto crop detection failed or no crop needed.")
                return
            self._crop_result = CropResult(
                width=crop_result[0],
                height=crop_result[1],
                x=crop_result[2],
                y=crop_result[3],
                is_valid=True
            )

        elif self._crop_settings.mode == CropMode.MANUAL:
            if self._crop_settings.manual_crop is not None:
                x, y, w, h = self._crop_settings.manual_crop
                self._crop_result = CropResult(
                    width=w,
                    height=h,
                    x=x,
                    y=y,
                    is_valid=True
                )

        elif self._crop_settings.mode == CropMode.RATIO:
            if self._crop_settings.ratio is not None:
                ar_w, ar_h = self._crop_settings.ratio
                target_aspect_ratio: float = ar_w / ar_h
                current_aspect_ratio: float = self._video.width / self._video.height

                if current_aspect_ratio > target_aspect_ratio:
                    new_width: int = int(self._video.height * target_aspect_ratio)
                    self._crop_result = CropResult(
                        width=new_width,
                        height=self._video.height,
                        x=(self._video.width - new_width) // 2,
                        y=0,
                        is_valid=True
                    )
                elif current_aspect_ratio < target_aspect_ratio:
                    new_height: int = int(self._video.width / target_aspect_ratio)
                    self._crop_result = CropResult(
                        width=self._video.width,
                        height=new_height,
                        x=0,
                        y=(self._video.height - new_height) // 2,
                        is_valid=True
                    )

    def get_crop_result(self) -> CropResult:
        return self._crop_result

    def is_cropped(self) -> bool:
        return self._crop_result.is_valid
