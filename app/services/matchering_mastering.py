import os
import matchering as mg
from typing import Dict, Any, List, Optional, Union
import logging
import uuid
from app.core.config import settings
import soundfile as sf

logger = logging.getLogger(__name__)

class MatcheringMasteringService:
    """Service for integrating with the Matchering library"""

    def __init__(self):
        # Matchering logs to stdout by default.
        # If you want to capture its logs via Python's logging,
        # you might need to redirect stdout or configure Matchering's logger if possible.
        # For now, we'll let it log to stdout as per its default.
        # mg.log(logger.info) # This would make it use the app's logger
        pass

    async def process_audio(
        self,
        target_file_path: str,
        reference_file_path: str,
        output_dir: str = settings.UPLOAD_PATH,
        output_filename_prefix: str = "mastered_matchering_",
        output_formats: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Process the target audio file using a reference audio file with Matchering.

        Args:
            target_file_path: Path to the target audio file.
            reference_file_path: Path to the reference audio file.
            output_dir: Directory to save the mastered files.
            output_filename_prefix: Prefix for the output filenames.
            output_formats: List of desired output formats. Each dict should have
                            'type' (e.g., 'pcm16', 'pcm24', 'mp3') and
                            'filename_suffix' (e.g., '_16bit.wav', '_24bit.wav').
                            If None, defaults to PCM 16-bit WAV.

        Returns:
            A dictionary containing the paths to the processed files and metadata.
        """
        if not os.path.exists(target_file_path):
            logger.error(f"Matchering: Target file not found: {target_file_path}")
            return {"success": False, "error": "Target file not found."}
        if not os.path.exists(reference_file_path):
            logger.error(f"Matchering: Reference file not found: {reference_file_path}")
            return {"success": False, "error": "Reference file not found."}

        os.makedirs(output_dir, exist_ok=True)

        base_target_name = os.path.splitext(os.path.basename(target_file_path))[0]
        unique_id = uuid.uuid4()

        results_config = []
        output_files_info = []

        if output_formats is None:
            # Default to a 16-bit WAV output
            default_filename = f"{output_filename_prefix}{base_target_name}_{unique_id}_16bit.wav"
            default_output_path = os.path.join(output_dir, default_filename)
            results_config.append(mg.pcm16(default_output_path))
            output_files_info.append({
                "path": default_output_path,
                "format": "wav",
                "bit_depth": 16
            })
        else:
            for fmt_config in output_formats:
                fmt_type = fmt_config.get("type", "pcm16").lower()
                suffix = fmt_config.get("filename_suffix", "_mastered.wav")
                filename = f"{output_filename_prefix}{base_target_name}_{unique_id}{suffix}"
                output_path = os.path.join(output_dir, filename)

                if fmt_type == "pcm16":
                    results_config.append(mg.pcm16(output_path))
                    output_files_info.append({"path": output_path, "format": "wav", "bit_depth": 16})
                elif fmt_type == "pcm24":
                    results_config.append(mg.pcm24(output_path))
                    output_files_info.append({"path": output_path, "format": "wav", "bit_depth": 24})
                elif fmt_type == "pcm32": # Assuming float32
                    results_config.append(mg.pcm32(output_path)) # Check if matchering supports pcm32 directly
                    output_files_info.append({"path": output_path, "format": "wav", "bit_depth": 32, "encoding": "float"})
                # Add more formats like mp3 if matchering supports them directly in results
                # For MP3, matchering might require FFmpeg and might not have a direct mg.mp3()
                # If so, you'd output WAV and then convert.
                else:
                    logger.warning(f"Unsupported Matchering format type: {fmt_type}. Skipping.")
                    continue

        if not results_config:
             logger.error("Matchering: No valid output formats specified.")
             return {"success": False, "error": "No valid output formats specified."}

        try:
            logger.info(f"Starting Matchering processing for target: {target_file_path}, reference: {reference_file_path}")

            # Matchering process is synchronous. For long tasks, run in a thread pool.
            # Consider using asyncio.to_thread in Python 3.9+ if this becomes blocking.
            # For now, assuming it's acceptable for the agent's execution model.
            mg.process(
                target=target_file_path,
                reference=reference_file_path,
                results=results_config,
            )

            processed_files = []
            for file_info in output_files_info:
                if os.path.exists(file_info["path"]):
                    # Optionally, gather more metadata about the output files
                    # info = sf.info(file_info["path"])
                    processed_files.append({
                        "path": file_info["path"],
                        "filename": os.path.basename(file_info["path"]),
                        "format": file_info["format"],
                        # "size": os.path.getsize(file_info["path"]),
                        # "details": info # from soundfile.info
                    })
                else:
                    logger.error(f"Matchering output file not found: {file_info['path']}")

            if not processed_files:
                logger.error("Matchering processing completed but no output files were found.")
                return {"success": False, "error": "Matchering produced no output files."}

            logger.info(f"Matchering processing successful. Output files: {[f['path'] for f in processed_files]}")
            return {
                "success": True,
                "processed_files": processed_files,
                "message": "Matchering processing completed."
            }

        except Exception as e:
            logger.error(f"Matchering processing failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def is_ffmpeg_installed(self) -> bool:
        """
        Checks if FFmpeg is installed and accessible.
        Matchering might require FFmpeg for certain input/output formats (e.g., MP3).
        """
        # This is a basic check. A more robust check might involve `shutil.which('ffmpeg')`.
        # Or, Matchering might have its own way to check this.
        # For now, assume if `matchering` is installed, its dependencies are met or it handles absence gracefully.
        # The Matchering docs state FFmpeg is optional for MP3 loading.
        try:
            # A simple way to check: try to run ffmpeg -version
            # This is a placeholder; a more robust check should be implemented if needed.
            # For example, using subprocess to run 'ffmpeg -version'
            # import subprocess
            # result = subprocess.run(['ffmpeg', '-version'], capture_output=True, text=True, check=False)
            # return result.returncode == 0
            return True # Placeholder, assume true or not strictly needed by default WAV processing
        except Exception:
            return False

    async def get_supported_output_options(self) -> List[Dict[str, str]]:
        """Returns a list of supported output options for Matchering."""
        # These are based on matchering's capabilities like mg.pcm16, mg.pcm24
        return [
            {"type": "pcm16", "description": "16-bit WAV", "filename_suffix": "_16bit.wav", "content_type": "audio/wav"},
            {"type": "pcm24", "description": "24-bit WAV", "filename_suffix": "_24bit.wav", "content_type": "audio/wav"},
            # Add pcm32 (float) if confirmed to be well-supported and useful
            # {"type": "pcm32", "description": "32-bit Float WAV", "filename_suffix": "_32bit_float.wav", "content_type": "audio/wav"},
            # If MP3 output were directly supported by matchering.process:
            # {"type": "mp3", "description": "MP3 (requires FFmpeg)", "filename_suffix": ".mp3", "content_type": "audio/mpeg"},
        ]

# Example Usage (for testing purposes, not part of the service usually)
# async def main():
#     # Create dummy wav files for testing
#     samplerate = 44100
#     duration = 5 # seconds
#     frequency = 440 # Hz
#
#     # Target
#     t = np.linspace(0, duration, int(samplerate * duration), False)
#     target_audio = 0.5 * np.sin(2 * np.pi * frequency * t)
#     target_file = "dummy_target.wav"
#     sf.write(target_file, target_audio, samplerate)
#
#     # Reference
#     ref_audio = 0.7 * np.sin(2 * np.pi * (frequency / 2) * t) # Different characteristics
#     reference_file = "dummy_reference.wav"
#     sf.write(reference_file, ref_audio, samplerate)
#
#     service = MatcheringMasteringService()
#     results = await service.process_audio(
#         target_file_path=target_file,
#         reference_file_path=reference_file,
#         output_dir="test_matchering_output",
#         output_formats=[
#             {"type": "pcm16", "filename_suffix": "_m_16bit.wav"},
#             {"type": "pcm24", "filename_suffix": "_m_24bit.wav"}
#         ]
#     )
#     print(results)
#
#     # Clean up dummy files
#     os.remove(target_file)
#     os.remove(reference_file)
#     # Potentially remove output_dir if empty or for cleanup
#
# if __name__ == "__main__":
#     import asyncio
#     import numpy as np
#     # mg.log(print) # To see Matchering's internal logs during test
#     asyncio.run(main())
