import os
import librosa
import numpy as np
import soundfile as sf
from typing import Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class AudioProcessor:
    """Audio processing utilities"""
    
    @staticmethod
    def extract_metadata(file_path: str) -> Dict[str, Any]:
        """Extract comprehensive audio metadata"""
        try:
            # Get basic file info
            info = sf.info(file_path)
            
            # Load audio for analysis
            y, sr = librosa.load(file_path, sr=None)
            
            # Calculate additional metrics
            duration = len(y) / sr
            rms = librosa.feature.rms(y=y)[0]
            loudness_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
            peak_db = 20 * np.log10(np.max(np.abs(y)))
            dynamic_range = AudioProcessor._calculate_dynamic_range(y)
            spectral_centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))
            zero_crossing_rate = np.mean(librosa.feature.zero_crossing_rate(y))
            
            # Detect tempo and key
            tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
            chroma = librosa.feature.chroma_stft(y=y, sr=sr)
            key = AudioProcessor._estimate_key(chroma)
            
            return {
                "duration": duration,
                "sample_rate": info.samplerate,
                "channels": info.channels,
                "format": info.format,
                "codec": info.subtype,
                "bit_rate": None,  # Would need more advanced analysis
                "loudness_lufs": loudness_lufs,
                "peak_db": peak_db,
                "dynamic_range": dynamic_range,
                "spectral_centroid": spectral_centroid,
                "zero_crossing_rate": zero_crossing_rate,
                "tempo": tempo,
                "key": key,
                "rms_energy": np.mean(rms)
            }
        except Exception as e:
            logger.error(f"Error extracting audio metadata: {e}")
            return {
                "duration": None,
                "sample_rate": None,
                "channels": None,
                "format": None,
                "codec": None,
                "bit_rate": None,
                "loudness_lufs": None,
                "peak_db": None,
                "dynamic_range": None,
                "spectral_centroid": None,
                "zero_crossing_rate": None,
                "tempo": None,
                "key": None,
                "rms_energy": None
            }
    
    @staticmethod
    def _calculate_loudness_lufs(y: np.ndarray, sr: int) -> float:
        """Calculate LUFS loudness (simplified implementation)"""
        try:
            # This is a simplified LUFS calculation
            # In production, use a proper LUFS library like pyloudnorm
            rms = np.sqrt(np.mean(y**2))
            lufs = 20 * np.log10(rms) - 0.691
            return float(lufs)
        except:
            return -23.0  # Default LUFS value
    
    @staticmethod
    def _calculate_dynamic_range(y: np.ndarray) -> float:
        """Calculate dynamic range"""
        try:
            # Calculate RMS in dB
            rms_db = 20 * np.log10(np.sqrt(np.mean(y**2)))
            peak_db = 20 * np.log10(np.max(np.abs(y)))
            return float(peak_db - rms_db)
        except:
            return 0.0
    
    @staticmethod
    def _estimate_key(chroma: np.ndarray) -> str:
        """Estimate musical key from chroma features"""
        try:
            # Simple key estimation based on chroma
            key_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
            chroma_mean = np.mean(chroma, axis=1)
            key_idx = np.argmax(chroma_mean)
            return key_names[key_idx]
        except:
            return "Unknown"
    
    @staticmethod
    def normalize_audio(input_path: str, output_path: str, target_lufs: float = -23.0) -> bool:
        """Normalize audio to target LUFS"""
        try:
            y, sr = librosa.load(input_path, sr=None)
            
            # Calculate current LUFS
            current_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
            
            # Calculate gain adjustment
            gain_db = target_lufs - current_lufs
            gain_linear = 10 ** (gain_db / 20)
            
            # Apply gain
            y_normalized = y * gain_linear
            
            # Prevent clipping
            if np.max(np.abs(y_normalized)) > 1.0:
                y_normalized = y_normalized / np.max(np.abs(y_normalized)) * 0.99
            
            # Save normalized audio
            sf.write(output_path, y_normalized, sr)
            return True
        except Exception as e:
            logger.error(f"Error normalizing audio: {e}")
            return False
    
    @staticmethod
    def apply_eq(input_path: str, output_path: str, eq_settings: Dict[str, float]) -> bool:
        """Apply EQ to audio file"""
        try:
            y, sr = librosa.load(input_path, sr=None)
            
            # This is a simplified EQ implementation
            # In production, use proper audio processing libraries
            
            # Apply basic filtering based on eq_settings
            if eq_settings.get("bass_gain", 0) != 0:
                # Apply bass boost/cut (simplified)
                bass_gain = eq_settings["bass_gain"]
                y = y * (1 + bass_gain * 0.1)
            
            if eq_settings.get("treble_gain", 0) != 0:
                # Apply treble boost/cut (simplified)
                treble_gain = eq_settings["treble_gain"]
                y = y * (1 + treble_gain * 0.1)
            
            # Prevent clipping
            if np.max(np.abs(y)) > 1.0:
                y = y / np.max(np.abs(y)) * 0.99
            
            sf.write(output_path, y, sr)
            return True
        except Exception as e:
            logger.error(f"Error applying EQ: {e}")
            return False
    
    @staticmethod
    def apply_compression(input_path: str, output_path: str, ratio: float = 4.0, threshold: float = -20.0) -> bool:
        """Apply compression to audio file"""
        try:
            y, sr = librosa.load(input_path, sr=None)
            
            # Simple compression implementation
            threshold_linear = 10 ** (threshold / 20)
            
            # Find samples above threshold
            above_threshold = np.abs(y) > threshold_linear
            
            # Apply compression
            y_compressed = y.copy()
            y_compressed[above_threshold] = (
                np.sign(y[above_threshold]) * 
                (threshold_linear + (np.abs(y[above_threshold]) - threshold_linear) / ratio)
            )
            
            sf.write(output_path, y_compressed, sr)
            return True
        except Exception as e:
            logger.error(f"Error applying compression: {e}")
            return False
    
    @staticmethod
    def convert_format(input_path: str, output_path: str, target_format: str = "wav") -> bool:
        """Convert audio to different format"""
        try:
            y, sr = librosa.load(input_path, sr=None)
            
            # Determine output format
            if target_format.lower() == "mp3":
                # For MP3, you'd need additional libraries like pydub
                logger.warning("MP3 conversion requires additional libraries")
                return False
            
            sf.write(output_path, y, sr, format=target_format.upper())
            return True
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return False

class MasteringProcessor:
    """Advanced mastering processing"""
    
    @staticmethod
    def master_audio(
        input_path: str, 
        output_path: str, 
        preset: str = "balanced",
        target_loudness: float = -14.0,
        enhance_bass: bool = False,
        enhance_treble: bool = False,
        stereo_width: float = 1.0
    ) -> Dict[str, Any]:
        """Apply mastering chain to audio"""
        try:
            y, sr = librosa.load(input_path, sr=None)
            
            # Apply mastering chain based on preset
            if preset == "loud":
                target_loudness = -9.0
                compression_ratio = 6.0
                compression_threshold = -18.0
            elif preset == "dynamic":
                target_loudness = -18.0
                compression_ratio = 2.0
                compression_threshold = -24.0
            else:  # balanced
                target_loudness = -14.0
                compression_ratio = 4.0
                compression_threshold = -20.0
            
            # 1. Apply EQ if requested
            if enhance_bass or enhance_treble:
                eq_settings = {}
                if enhance_bass:
                    eq_settings["bass_gain"] = 2.0
                if enhance_treble:
                    eq_settings["treble_gain"] = 1.5
                
                # Apply EQ (simplified)
                if enhance_bass:
                    y = y * 1.2  # Simplified bass enhancement
                if enhance_treble:
                    y = y * 1.15  # Simplified treble enhancement
            
            # 2. Apply compression
            threshold_linear = 10 ** (compression_threshold / 20)
            above_threshold = np.abs(y) > threshold_linear
            y[above_threshold] = (
                np.sign(y[above_threshold]) * 
                (threshold_linear + (np.abs(y[above_threshold]) - threshold_linear) / compression_ratio)
            )
            
            # 3. Apply stereo width (if stereo)
            if len(y.shape) > 1 and stereo_width != 1.0:
                # Simplified stereo width processing
                mid = (y[:, 0] + y[:, 1]) / 2
                side = (y[:, 0] - y[:, 1]) / 2
                side = side * stereo_width
                y[:, 0] = mid + side
                y[:, 1] = mid - side
            
            # 4. Normalize to target loudness
            current_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
            gain_db = target_loudness - current_lufs
            gain_linear = 10 ** (gain_db / 20)
            y = y * gain_linear
            
            # 5. Limiter (prevent clipping)
            if np.max(np.abs(y)) > 0.99:
                y = y / np.max(np.abs(y)) * 0.99
            
            # Save mastered audio
            sf.write(output_path, y, sr)
            
            # Calculate quality metrics
            final_lufs = AudioProcessor._calculate_loudness_lufs(y, sr)
            final_peak = 20 * np.log10(np.max(np.abs(y)))
            final_dynamic_range = AudioProcessor._calculate_dynamic_range(y)
            
            return {
                "success": True,
                "final_loudness_lufs": final_lufs,
                "final_peak_db": final_peak,
                "final_dynamic_range": final_dynamic_range,
                "processing_applied": {
                    "preset": preset,
                    "compression": True,
                    "eq": enhance_bass or enhance_treble,
                    "stereo_width": stereo_width,
                    "limiting": True
                }
            }
        except Exception as e:
            logger.error(f"Error in mastering process: {e}")
            return {
                "success": False,
                "error": str(e)
            }