import os
import librosa
import numpy as np
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import logging
from fastapi.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Audio processing utilities"""
    
    @staticmethod
    def _extract_metadata_sync(file_path: str) -> Dict[str, Any]:
        """Synchronous part of extract_metadata"""
        info = sf.info(file_path)
        y, sr = librosa.load(file_path, sr=None)

        duration = len(y) / sr
        rms = librosa.feature.rms(y=y)[0]
        loudness_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
        peak_db = 20 * np.log10(np.max(np.abs(y))) if np.max(np.abs(y)) > 0 else -np.inf
        dynamic_range = AudioProcessor._calculate_dynamic_range(y)
        spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
        zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))

        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        chroma = librosa.feature.chroma_stft(y=y, sr=sr)
        key = AudioProcessor._estimate_key(chroma)
            
        return {
            "duration": duration, "sample_rate": info.samplerate, "channels": info.channels,
            "format": info.format, "codec": info.subtype, "bit_rate": None,
            "loudness_lufs": loudness_lufs, "peak_db": peak_db, "dynamic_range": dynamic_range,
            "spectral_centroid": spectral_centroid, "zero_crossing_rate": zero_crossing_rate,
            "tempo": tempo, "key": key, "rms_energy": np.mean(rms)
        }

    @staticmethod
    async def extract_metadata_async(file_path: str) -> Dict[str, Any]:
        """Extract comprehensive audio metadata asynchronously"""
        try:
            return await run_in_threadpool(AudioProcessor._extract_metadata_sync, file_path)
        except Exception as e:
            logger.error(f"Error extracting audio metadata: {e}")
            return {
                "duration": None, "sample_rate": None, "channels": None, "format": None,
                "codec": None, "bit_rate": None, "loudness_lufs": None, "peak_db": None,
                "dynamic_range": None, "spectral_centroid": None, "zero_crossing_rate": None,
                "tempo": None, "key": None, "rms_energy": None
            }
    
    @staticmethod
    def _calculate_loudness_lufs(y: np.ndarray, sr: int) -> float:
        """Calculate LUFS loudness (simplified implementation)"""
        try:
            if y.size == 0: return -np.inf # Handle empty audio array
            rms = np.sqrt(np.mean(y**2))
            if rms == 0: return -np.inf # Avoid log(0)
            lufs = 20 * np.log10(rms) - 0.691 # This is a very rough approximation
            return float(lufs)
        except Exception as e:
            logger.warning(f"Could not calculate LUFS: {e}")
            return -23.0
    
    @staticmethod
    def _calculate_dynamic_range(y: np.ndarray) -> float:
        """Calculate dynamic range"""
        try:
            if y.size == 0: return 0.0
            peak_val = np.max(np.abs(y))
            if peak_val == 0: return 0.0
            peak_db = 20 * np.log10(peak_val)

            rms_val = np.sqrt(np.mean(y**2))
            if rms_val == 0: return 0.0 # or peak_db if preferred for silent audio
            rms_db = 20 * np.log10(rms_val)

            return float(peak_db - rms_db)
        except Exception as e:
            logger.warning(f"Could not calculate dynamic range: {e}")
            return 0.0
    
    @staticmethod
    def _estimate_key(chroma: np.ndarray) -> str:
        """Estimate musical key from chroma features"""
        try:
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            if chroma.size == 0: return "Unknown"
            chroma_mean = np.mean(chroma, axis=1)
            key_idx = np.argmax(chroma_mean)
            return key_names[key_idx]
        except Exception as e:
            logger.warning(f"Could not estimate key: {e}")
            return "Unknown"

    @staticmethod
    def _load_audio_sync(file_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Synchronously loads audio file."""
        try:
            y, sr = librosa.load(file_path, sr=None)
            return y, sr
        except Exception as e:
            logger.error(f"Error loading audio file {file_path}: {e}")
            return None, None

    @staticmethod
    async def load_audio_async(file_path: str) -> Tuple[Optional[np.ndarray], Optional[int]]:
        """Asynchronously loads audio file."""
        return await run_in_threadpool(AudioProcessor._load_audio_sync, file_path)

    @staticmethod
    def _normalize_audio_sync(input_path: str, output_path: str, target_lufs: float) -> bool:
        y, sr = librosa.load(input_path, sr=None)
        if y is None: return False # Check if loading failed
        current_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
        gain_db = target_lufs - current_lufs
        gain_linear = 10 ** (gain_db / 20)
        y_normalized = y * gain_linear
        if np.max(np.abs(y_normalized)) > 1.0:
            y_normalized = y_normalized / np.max(np.abs(y_normalized)) * 0.99
        sf.write(output_path, y_normalized, sr)
        return True

    @staticmethod
    async def normalize_audio_async(input_path: str, output_path: str, target_lufs: float = -23.0) -> bool:
        """Normalize audio to target LUFS asynchronously"""
        try:
            return await run_in_threadpool(AudioProcessor._normalize_audio_sync, input_path, output_path, target_lufs)
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            return False

    @staticmethod
    def _apply_eq_sync(input_path: str, output_path: str, eq_settings: Dict[str, float]) -> bool:
        y, sr = librosa.load(input_path, sr=None)
        if eq_settings.get("bass_gain", 0) != 0:
            bass_gain = eq_settings["bass_gain"]
            y = y * (1 + bass_gain * 0.1) # Simplified
        if eq_settings.get("treble_gain", 0) != 0:
            treble_gain = eq_settings["treble_gain"]
            y = y * (1 + treble_gain * 0.1) # Simplified
        if np.max(np.abs(y)) > 1.0:
            y = y / np.max(np.abs(y)) * 0.99
        sf.write(output_path, y, sr)
        return True

    @staticmethod
    async def apply_eq_async(input_path: str, output_path: str, eq_settings: Dict[str, float]) -> bool:
        """Apply EQ to audio file asynchronously"""
        try:
            return await run_in_threadpool(AudioProcessor._apply_eq_sync, input_path, output_path, eq_settings)
        except Exception as e:
            logger.error(f"Error applying EQ: {e}")
            return False

    @staticmethod
    def _apply_compression_sync(input_path: str, output_path: str, ratio: float, threshold: float) -> bool:
        y, sr = librosa.load(input_path, sr=None)
        threshold_linear = 10 ** (threshold / 20)
        above_threshold = np.abs(y) > threshold_linear
        y_compressed = y.copy()
        y_compressed[above_threshold] = (
            np.sign(y[above_threshold]) *
            (threshold_linear + (np.abs(y[above_threshold]) - threshold_linear) / ratio)
        )
        sf.write(output_path, y_compressed, sr)
        return True

    @staticmethod
    async def apply_compression_async(input_path: str, output_path: str, ratio: float = 4.0, threshold: float = -20.0) -> bool:
        """Apply compression to audio file asynchronously"""
        try:
            return await run_in_threadpool(AudioProcessor._apply_compression_sync, input_path, output_path, ratio, threshold)
        except Exception as e:
            logger.error(f"Error applying compression: {e}")
            return False

    @staticmethod
    def _convert_format_sync(input_path: str, output_path: str, target_format: str) -> bool:
        y, sr = librosa.load(input_path, sr=None)
        if target_format.lower() == "mp3":
            logger.warning("MP3 conversion requires additional libraries like pydub")
            return False # Or raise NotImplementedError
        sf.write(output_path, y, sr, format=target_format.upper())
        return True

    @staticmethod
    async def convert_format_async(input_path: str, output_path: str, target_format: str = "wav") -> bool:
        """Convert audio to different format asynchronously"""
        try:
            return await run_in_threadpool(AudioProcessor._convert_format_sync, input_path, output_path, target_format)
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return False

class MasteringProcessor:
    """Advanced mastering processing"""
    
    @staticmethod
    def _master_audio_sync(
        input_path: str, output_path: str, preset: str,
        target_loudness: float, enhance_bass: bool, enhance_treble: bool, stereo_width: float
    ) -> Dict[str, Any]:
        y, sr = librosa.load(input_path, sr=None)

        if preset == "loud":
            target_loudness = -9.0; compression_ratio = 6.0; compression_threshold = -18.0
        elif preset == "dynamic":
            target_loudness = -18.0; compression_ratio = 2.0; compression_threshold = -24.0
        else: # balanced
            target_loudness = -14.0; compression_ratio = 4.0; compression_threshold = -20.0

        if enhance_bass: y = y * 1.2 # Simplified
        if enhance_treble: y = y * 1.15 # Simplified

        threshold_linear = 10 ** (compression_threshold / 20)
        above_threshold = np.abs(y) > threshold_linear
        y[above_threshold] = (np.sign(y[above_threshold]) * (threshold_linear + (np.abs(y[above_threshold]) - threshold_linear) / compression_ratio))

        if len(y.shape) > 1 and stereo_width != 1.0 and y.shape[1] == 2: # Ensure stereo
            mid = (y[:, 0] + y[:, 1]) / 2
            side = (y[:, 0] - y[:, 1]) / 2
            side = side * stereo_width
            y_stereo = np.empty_like(y)
            y_stereo[:, 0] = mid + side
            y_stereo[:, 1] = mid - side
            y = y_stereo

        current_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
        gain_db = target_loudness - current_lufs
        if current_lufs > -np.inf : # Avoid issues if current_lufs is -inf
             gain_linear = 10 ** (gain_db / 20)
             y = y * gain_linear

        if np.max(np.abs(y)) > 0.99: y = y / np.max(np.abs(y)) * 0.99

        sf.write(output_path, y, sr)

        final_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
        final_peak = 20 * np.log10(np.max(np.abs(y))) if np.max(np.abs(y)) > 0 else -np.inf
        final_dynamic_range = AudioProcessor._calculate_dynamic_range(y)

        return {
            "success": True, "final_loudness_lufs": final_lufs, "final_peak_db": final_peak,
            "final_dynamic_range": final_dynamic_range,
            "processing_applied": {
                "preset": preset, "compression": True, "eq": enhance_bass or enhance_treble,
                "stereo_width": stereo_width, "limiting": True
            }
        }

    @staticmethod
    async def master_audio_async(
        input_path: str, 
        output_path: str, 
        preset: str = "balanced",
        target_loudness: float = -14.0,
        enhance_bass: bool = False,
        enhance_treble: bool = False,
        stereo_width: float = 1.0
    ) -> Dict[str, Any]:
        """Apply mastering chain to audio asynchronously"""
        try:
            return await run_in_threadpool(
                MasteringProcessor._master_audio_sync,
                input_path, output_path, preset, target_loudness,
                enhance_bass, enhance_treble, stereo_width
            )
        except Exception as e:
            logger.error(f"Error in mastering process: {e}")
            return {"success": False, "error": str(e)}