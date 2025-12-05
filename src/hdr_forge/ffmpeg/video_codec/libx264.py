from typing import Optional, Tuple
from hdr_forge.ffmpeg.video_codec.service.presets import Hdr_Forge_X265_X264_Preset
from hdr_forge.ffmpeg.video_codec.video_codec_base import VideoCodecBase
from hdr_forge.typedefs.encoder_typing import EncoderSettings, HdrForgeEncodingTuningPresets, HdrForgeSpeedPreset, HdrSdrFormat, Libx264Params, X264Tune
from hdr_forge.typedefs.video_typing import HdrMetadata
from hdr_forge.typedefs.codec_typing import BT_709_FLAGS, PIXEL_FORMAT_YUV420_10_BIT, PIXEL_FORMAT_YUV420_8_BIT, CodecPreset, VideoEncoderLibrary
from hdr_forge.video import Video

class Libx264Codec(VideoCodecBase):

    HDR_SDR_SUPPORT: list[HdrSdrFormat] = [
        HdrSdrFormat.SDR,
    ]

    SDR_PROFILE = 'high'

    def __init__(self, encoder_settings: EncoderSettings, video: Video, scale: Tuple[int, int]):
        super().__init__(
            lib=VideoEncoderLibrary.LIBX264,
            encoder_settings=encoder_settings,
            video=video,
            scale=scale,
            supported_hdr_sdr_formats=self.HDR_SDR_SUPPORT,
        )
        hw_preset: Hdr_Forge_X265_X264_Preset = self.calc_hw_preset_settings(Hdr_Forge_X265_X264_Preset)
        self._crf: int = self._get_auto_crf(hw_preset)
        self._preset: CodecPreset = self._get_auto_preset(calc_preset=hw_preset.preset)
        self._tune: X264Tune | None = self._get_auto_tune()

    def get_ffmpeg_params(self, exist_params: dict) -> dict:
        output_options: dict = super().get_ffmpeg_params(exist_params=exist_params)
        output_options.update({
            "profile:v": self.SDR_PROFILE,
            "preset": self._preset.codec_preset,
            "crf": str(self._crf),
        })

        pix_fmt: str | None = self.get_pix_format_for_encoding()
        if pix_fmt is not None:
            output_options["pix_fmt"] = pix_fmt

        if self._tune is not None:
            output_options['tune'] = self._tune.value

        output_options['x264-params'] = self._build_x264_params()

        return output_options

    def _build_default_x264_params(self) -> list[str]:
        """Build default x264 parameters.
        Returns:
            list of x264 parameter strings
        """
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.VIDEO:
            return []  # use x264 defaults for video preset

        # default params
        params: dict[str, str | None] = {
            'aq-mode': None,
            # default is 1
            # x264: 1 = variance AQ (standard), 2 = auto-variance AQ (empfohlen für die meisten Fälle)
            'aq-strength': None,
            # - Default ist 1.0
            # - 0.8–1.2 → sehr stabil für die meisten Filme, guter Kompromiss
            #   1.0 → universal
            #   1.5+ → sehr aggressiv, manchmal für HDR oder stark texturierte Inhalte
            'psy-rd': None,
            # Psychovisual Rate-Distortion Optimization
            # - Default ist 1.0:0.0 (psy-rd:psy-trellis)
            # - Format: psy-rd=X.X:Y.Y
            # - Werte zwischen 0.8:0.0 und 1.2:0.15 sind üblich
            'ref': None,
            # Anzahl der Referenzbilder
            # - default ist 1 für veryfast, 3 für medium, 5 für slow
            # - 4-5 = optimaler Allround-Wert
            # - 6-8 = leichte Optimierung, aber langsamer
            # - >8 = kaum Mehrwert außer für Anime oder sehr saubere 4K-Master (max 16)
            'bframes': '4',
            # Anzahl der B-Frames
            # - default ist 3 für medium/slow
            # - 4-8 = optimaler Bereich
            'b-adapt': '2',
            # B-Frame-Adaptionsmodus
            # - default ist 1
            # - 0 = deaktiviert
            # - 1 = schnell (fast algorithm)
            # - 2 = optimal (optimal algorithm), langsamer aber bessere Entscheidungen
            'trellis': None,
            # Trellis-Quantisierung (ähnlich wie rdoq-level bei x265)
            # - 0 = deaktiviert (default bei fast/faster)
            # - 1 = nur am Ende der Codierung
            # - 2 = immer aktiv (default bei slow/slower), besser für dunkle Szenen
            'qcomp': '0.65',
            # Balanciert Kontrast und Bewegungsszenen gut
            # - 0.5-1.0 ist der übliche Bereich
            # - Default ist 0.6
            'rc-lookahead': '50',
            # Bessere Vorausschau für komplexe Szenen
            # - default ist 10 für veryfast, 40 für medium, 50 für slow
            # - 40-50 = optimaler Allround-Wert
            # - RAM-intensiv bei sehr hochauflösenden Videos (4K+)
            'me': None,
            # Motion Estimation Methode
            # - dia (diamond) = schnellste
            # - hex (hexagon) = guter Kompromiss (default bei fast/faster)
            # - umh (uneven multi-hexagon) = default bei slow/slower
            # - esa (exhaustive) = sehr langsam, kaum Mehrwert
            'subme': None,
            # Subpixel Motion Estimation Qualität
            # - 1-11 (1 = schnell, 11 = beste Qualität)
            # - default ist 6 für medium, 7 für slow, 9 für slower
            # - 7-9 = guter Bereich für Qualität
            'merange': None,
            # Motion Estimation Suchbereich
            # - default ist 16 für medium/slow
            # - 16-24 = guter Bereich
        }

        new_params= self._preset.ffmpeg_params.get('x264-params', {}) or {}
        if type(new_params) is dict:
            params.update(new_params)

        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            params.update({
                'aq-mode': '2',
                'aq-strength': '1.1',
                'psy-rd': '0.9:0.0',  # x264 format: psy-rd:psy-trellis
                'ref': '8',  # Anime profitiert von mehr Referenzbildern
                'bframes': '10',  # für Animation können mehr B-Frames helfen
                'b-adapt': '2',
                'trellis': '2',
                'deblock': None,  # default bei animation tune ist 1:1
            })
        elif (
            hdr_forge_preset in [
                HdrForgeEncodingTuningPresets.FILM,
                HdrForgeEncodingTuningPresets.ACTION,
            ]
        ):
            # optimize psy settings for more optical quality
            params.update({
                'aq-mode': '2',
                'psy-rd': '1.0:0.15',  # leichte psy-trellis Erhöhung für bessere Texturerhaltung
            })
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.BANDING:
            # reduce banding artifacts
            params.update({
                'aq-mode': '3',  # auto-variance AQ with bias to dark scenes
                'aq-strength': '1.2',
                'psy-rd': '1.2:0.20',
                'deblock': '-1:-1',
                'trellis': '2',
                'qcomp': '0.65',
            })

        return list(f"{key}={value}" for key, value in params.items() if value is not None)

    def _build_x264_params(self) -> str:
        """Build x264 parameters for SDR video encoding.

        Returns:
            list of x264 parameter strings
        """
        params: list[str] = self._build_default_x264_params()

        if self._video.get_color_primaries() == 'bt709':
            params.extend(BT_709_FLAGS.copy())

        x264_params_str: str = ':'.join(params)
        return x264_params_str

    def get_pix_format_for_encoding(self) -> str | None:
        bit_depth = self.get_bit_depth_for_encoding()
        if bit_depth == 10:
            return PIXEL_FORMAT_YUV420_10_BIT
        elif bit_depth == 8:
            return PIXEL_FORMAT_YUV420_8_BIT
        return super().get_pix_format_for_encoding()

    def get_bit_depth_for_encoding(self) -> int:
        return super().get_bit_depth_for_encoding()

    def get_custom_lib_parameters(self) -> dict:
        return {
            "crf": self._crf,
            "preset": self._preset.codec_preset,
            "tune": self._tune.value if self._tune else None,
        }

    def get_hdr_metadata_for_encoding(self) -> Optional[HdrMetadata]:
        return None

    def _get_auto_tune(self) -> Optional[X264Tune]:
        """Select optimal encoding tune based on parameter priority.

        Priority:
            1. libx264_params.tune (from --encoder-params)
            2. Auto-detection (preset or grain analysis)

        Returns:
            X264Tune enum or None if no tune is set
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.tune is not None:
            return libx264_params.tune

        # Priority 2: Auto-detection
        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        if hdr_forge_preset == HdrForgeEncodingTuningPresets.ANIMATION:
            return X264Tune.ANIMATION
        elif hdr_forge_preset == HdrForgeEncodingTuningPresets.FILM:
            return X264Tune.FILM

        if self._grain.get_category() >= 2:
            return X264Tune.GRAIN

        return None

    def _get_auto_preset(self, calc_preset: HdrForgeSpeedPreset) -> CodecPreset:
        """Select optimal encoding preset based on parameter priority.

        Priority:
            1. libx265_params.preset (from --encoder-params)
            2. universal_params.speed (from --speed)
            3. calc_preset (auto-detection)

        Returns:
            CodecPreset value
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.preset is not None:
            return CodecPreset(
                codec_libs=[self.lib],
                codec_preset=str(libx264_params.preset),
                ffmpeg_params={},
            )

        return super()._get_auto_preset(calc_preset=calc_preset)

    def _get_auto_crf(self, hw_preset: Hdr_Forge_X265_X264_Preset) -> int:
        """Calculate optimal CRF value based on parameter priority.

        Priority:
            1. libx264_params.crf (from --encoder-params)
            2. universal_params.quality (from --quality)
            3. hw_preset.crf (auto-detection)

        Returns:
            CRF value (lower = higher quality)
        """
        # Priority 1: libx264_params from --encoder-params
        libx264_params: Libx264Params = self._encoder_settings.libx264_params
        if libx264_params.crf is not None:
            return libx264_params.crf

        # Priority 2: universal_params from --quality
        universal_params = self._encoder_settings.universal_params
        if universal_params.quality is not None:
            return universal_params.quality

        # Priority 3: Auto-detection from hw_preset
        crf: float = hw_preset.crf

        hdr_forge_preset: HdrForgeEncodingTuningPresets = self._encoder_settings.hdr_forge_encoding_preset.preset
        action_crf: float = 2.0 if hdr_forge_preset == HdrForgeEncodingTuningPresets.ACTION else 0.0 # Action preset lowers CRF for better handling of fast motion

        action_w: float = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=action_crf,
        )
        crf -= action_crf * action_w

        grain_crf: float = self._grain.get_crf_x265_x264_adjustment()
        grain_w: float = self._calculate_crf_adjustment_weight(
            current_crf=crf,
            crf_delta=grain_crf,
        )
        crf -= grain_crf * grain_w

        return round(crf)
