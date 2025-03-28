#!/usr/bin/env python3
"""
TTS functionality for JrDev terminal.
Handles text-to-speech using the Venice API and audio playback.
"""
#test
import os
import asyncio
import logging
import sys
import time
import glob
import re
import json
from datetime import datetime as dt
from typing import Optional, List, Dict, Any
from collections import deque
from abc import ABC, abstractmethod

from jrdev.file_utils import JRDEV_DIR

logger = logging.getLogger("jrdev.tts")

# Try to import playsound, but don't fail if it's not available
try:
    # Use v1.2.2 which is more compatible
    from playsound import playsound
    PLAYSOUND_AVAILABLE = True
    logger.info("playsound module is available for audio playback")
except ImportError:
    def playsound(sound_file):
        logger.warning(f"playsound not available, cannot play {sound_file}")
    PLAYSOUND_AVAILABLE = False
    logger.warning("playsound module not available, falling back to system commands")

# Create an audio directory inside the JRDEV_DIR
AUDIO_DIR = os.path.join(JRDEV_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Maximum number of audio files to keep
MAX_AUDIO_FILES = 50

class AudioPlayer(ABC):
    """Abstract base class for platform-specific audio playback strategies."""
    
    @abstractmethod
    async def play(self, audio_file: str) -> bool:
        """
        Play an audio file.
        
        Args:
            audio_file: Path to the audio file to play
            
        Returns:
            bool: True if playback was successful, False otherwise
        """
        pass


class PlaysoundPlayer(AudioPlayer):
    """Audio player implementation using playsound library."""
    
    async def play(self, audio_file: str) -> bool:
        """Play audio using playsound library."""
        try:
            await asyncio.to_thread(playsound, audio_file)
            logger.info("playsound playback completed successfully")
            return True
        except Exception as e:
            logger.warning(f"playsound failed: {e}")
            return False


class LinuxSystemPlayer(AudioPlayer):
    """Audio player implementation for Linux systems."""
    
    async def play(self, audio_file: str) -> bool:
        """Play audio using Linux system commands (mpg123 or aplay)."""
        try:
            if audio_file.lower().endswith('.mp3'):
                command = f'mpg123 -q --no-control "{audio_file}"'
            else:
                command = f'aplay -q "{audio_file}"'
                
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                logger.info("Linux audio playback completed successfully")
                return True
            else:
                logger.warning(f"Linux audio playback failed with status {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"Linux audio playback error: {e}")
            return False


class WindowsSystemPlayer(AudioPlayer):
    """Audio player implementation for Windows systems."""
    
    async def play(self, audio_file: str) -> bool:
        """Play audio using Windows system commands."""
        try:
            command = f'start /wait "" "{audio_file}"'
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                logger.info("Windows audio playback completed successfully")
                return True
            else:
                logger.warning(f"Windows audio playback failed with status {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"Windows audio playback error: {e}")
            return False


class MacSystemPlayer(AudioPlayer):
    """Audio player implementation for macOS systems."""
    
    async def play(self, audio_file: str) -> bool:
        """Play audio using macOS system commands."""
        try:
            command = f'afplay "{audio_file}"'
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            
            if process.returncode == 0:
                logger.info("macOS audio playback completed successfully")
                return True
            else:
                logger.warning(f"macOS audio playback failed with status {process.returncode}")
                return False
        except Exception as e:
            logger.error(f"macOS audio playback error: {e}")
            return False


class TTSManager:
    """
    Manager class for text-to-speech functionality.
    Handles audio generation, playback queue, and cleanup.
    """
    
    def __init__(self):
        """Initialize the TTSManager with empty queue and synchronization primitives."""
        self.audio_queue = deque()
        self.audio_player_running = False
        self.queue_lock = asyncio.Lock()
        self.audio_queue_event = asyncio.Event()
        self._init_audio_players()
        self.voice_models = self._load_voice_configuration()
        logger.info("TTSManager initialized")
    
    def _init_audio_players(self):
        """Initialize platform-specific audio players."""
        self.audio_players = []
        
        # Add playsound player first if available (cross-platform)
        if PLAYSOUND_AVAILABLE:
            self.audio_players.append(PlaysoundPlayer())
        
        # Add platform-specific players as fallbacks
        if sys.platform.startswith('linux'):
            self.audio_players.append(LinuxSystemPlayer())
        elif sys.platform.startswith('win'):
            self.audio_players.append(WindowsSystemPlayer())
        elif sys.platform.startswith('darwin'):
            self.audio_players.append(MacSystemPlayer())
    
    def _load_voice_configuration(self) -> List[Dict[str, Any]]:
        """
        Load voice configuration from model_list.json or return defaults if not available.
        """
        try:
            # Try to load from the model_list.json file in the same directory as the module
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, "model_list.json")
            
            if os.path.exists(json_path):
                with open(json_path, "r") as f:
                    config_data = json.load(f)
                    
                # Look for a tts_voices section in the configuration
                if "tts_voices" in config_data and config_data["tts_voices"]:
                    logger.info(f"Loaded {len(config_data['tts_voices'])} voice configurations from model_list.json")
                    return config_data["tts_voices"]
            
            # Fallback to default configuration
            logger.info("Using default voice configuration (no valid config found in model_list.json)")
            return [
                {"model": "tts-kokoro", "voice": "af_aoede", "speed": 1.1}
            ]
        except Exception as e:
            logger.warning(f"Error loading voice configuration: {e}, using defaults")
            return [
                {"model": "tts-kokoro", "voice": "af_aoede", "speed": 1.1}
            ]
    
    async def cleanup_old_audio_files(self) -> None:
        """
        Clean up old audio files to prevent excessive disk usage.
        Keeps the MAX_AUDIO_FILES most recent files and removes the rest.
        """
        try:
            audio_files = glob.glob(os.path.join(AUDIO_DIR, "*.mp3"))
            if len(audio_files) <= MAX_AUDIO_FILES:
                return
                
            audio_files.sort(key=os.path.getmtime, reverse=True)
            files_to_delete = audio_files[MAX_AUDIO_FILES:]
            
            for file_path in files_to_delete:
                try:
                    os.remove(file_path)
                    logger.info(f"Cleaned up old audio file: {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete old audio file {file_path}: {str(e)}")
                    
            logger.info(f"Audio cleanup complete: removed {len(files_to_delete)} files")
        except Exception as e:
            logger.error(f"Error during audio file cleanup: {str(e)}")
    
    async def generate_audio(self, client, text: str, output_path: Optional[str] = None, 
                            topic: Optional[str] = None, max_retries: int = 2) -> Optional[str]:
        """
        Generate audio from text using Venice TTS API with retry logic.
        
        Args:
            client: The Venice API client
            text: The text to convert to speech
            output_path: Optional path to save the audio file
            topic: Optional topic identifier for the audio file name
            max_retries: Maximum number of retry attempts
            
        Returns:
            Path to the generated audio file or None if generation failed
        """
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                await self.cleanup_old_audio_files()
                
                # Create a filename based on topic if no output path is provided
                if not output_path:
                    if topic:
                        safe_topic = re.sub(r'[^\w\-_.]', '_', topic.lower().replace(' ', '_'))
                        filename = f"{safe_topic}.mp3"
                    else:
                        timestamp = int(time.time())
                        filename = f"audio_{timestamp}.mp3"
                        
                    output_path = os.path.join(AUDIO_DIR, filename)
                    logger.info(f"Will save audio to {output_path}")
    
                logger.info(f"Generating audio for text of length {len(text)}")
                
                # Use the voice models loaded from configuration
                voice_models = self.voice_models
                
                response = None
                success = False
                
                # Try each voice model until one works
                for voice_config in voice_models:
                    try:
                        logger.info(f"Trying voice model: {voice_config['model']} with voice: {voice_config['voice']}")
                        
                        # DEV FUNCTION: Log the API request parameters verbatim
                        request_params = {
                            "model": voice_config['model'],
                            "voice": voice_config['voice'],
                            "response_format": "mp3",
                            "speed": voice_config['speed'],
                            "input_text": text,
                            "topic": topic
                        }
                        self._dev_log_audio_request(request_params)
                        
                        # Make the API request to Venice audio endpoint
                        response = await client.audio.speech.create(
                            model=voice_config['model'],
                            voice=voice_config['voice'],
                            response_format="mp3",
                            speed=voice_config['speed'],
                            input=text
                        )
                        
                        # Check if we got a valid response
                        if response and response.content and len(response.content) > 100:
                            logger.info(f"Received valid audio content of size {len(response.content)} bytes")
                            success = True
                            break
                        else:
                            logger.warning(f"Received small or empty response from {voice_config['model']}/{voice_config['voice']}")
                    except Exception as e:
                        logger.warning(f"Error with voice {voice_config['model']}/{voice_config['voice']}: {str(e)}")
                
                if not success or not response:
                    logger.error("All voice models failed to generate audio")
                    raise Exception("Failed to generate audio with any available voice model")
                
                # Use a with statement for better resource management when writing the file
                with open(output_path, "wb") as f:
                    f.write(response.content)
                
                # Verify the file was created with content
                if os.path.exists(output_path):
                    file_size = os.path.getsize(output_path)
                    logger.info(f"Audio file saved to {output_path} (size: {file_size} bytes)")
                    
                    if file_size < 100:
                        logger.warning(f"Generated audio file is suspiciously small ({file_size} bytes), likely corrupt")
                else:
                    logger.error(f"Failed to create audio file at {output_path}")
                    
                return output_path
                
            except Exception as e:
                logger.error(f"Error generating audio (attempt {retry_count + 1}/{max_retries + 1}): {str(e)}")
                retry_count += 1
                
                if retry_count <= max_retries:
                    # Exponential backoff
                    wait_time = 2 ** retry_count
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                else:
                    # Clean up partial file on failure if it exists
                    if output_path and os.path.exists(output_path):
                        try:
                            os.remove(output_path)
                            logger.info(f"Removed incomplete audio file: {output_path}")
                        except Exception:
                            pass
                    return None
    
    async def _play_audio_file(self, audio_file: str) -> bool:
        """
        Internal function to play a single audio file.
        
        Args:
            audio_file: Path to the audio file to play
            
        Returns:
            bool: True if playback was successful, False otherwise
        """
        try:
            if not os.path.exists(audio_file):
                logger.error(f"Audio file not found: {audio_file}")
                return False
    
            file_size = os.path.getsize(audio_file)
            if file_size < 100:
                logger.warning(f"Audio file is suspiciously small ({file_size} bytes), likely corrupt")
                return False
    
            logger.info(f"Playing audio file: {audio_file} (size: {file_size} bytes)")
            
            # Try each audio player in order until one succeeds
            for player in self.audio_players:
                success = await player.play(audio_file)
                if success:
                    return True
                    
            logger.error("All audio playback methods failed")
            return False
            
        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            return False
    
    async def _audio_player_task(self):
        """
        Background task that processes the audio queue and plays files in sequence.
        Ensures only one audio file plays at a time.
        """
        try:
            self.audio_player_running = True
            logger.info("Audio player task started")
            
            currently_playing = False
            
            while True:
                # Only check for new files if we're not currently playing
                if not currently_playing:
                    # Wait for the queue to have items
                    if not self.audio_queue:
                        logger.debug("Audio queue empty, waiting for new files")
                        await self.audio_queue_event.wait()
                        self.audio_queue_event.clear()
                    
                    # Get the next file from the queue
                    audio_file = None
                    async with self.queue_lock:
                        if self.audio_queue:
                            audio_file = self.audio_queue.popleft()
                            # Log remaining files in queue
                            if self.audio_queue:
                                logger.debug(f"Remaining files in queue: {len(self.audio_queue)}")
                    
                    if audio_file:
                        logger.info(f"Playing next audio file from queue: {audio_file}")
                        
                        # Set the flag to indicate we're playing
                        currently_playing = True
                        
                        # Play the audio file
                        success = await self._play_audio_file(audio_file)
                        
                        # Add a pause between files (1 second)
                        logger.debug("Adding 1 second pause between audio files")
                        await asyncio.sleep(1.0)
                        
                        # Reset the playing flag
                        currently_playing = False
                        
                        if not success:
                            logger.warning(f"Failed to play audio file: {audio_file}")
                else:
                    # If we're currently playing, just wait a bit before checking again
                    await asyncio.sleep(0.1)
                    
        except asyncio.CancelledError:
            logger.info("Audio player task was cancelled")
            self.audio_player_running = False
        except Exception as e:
            logger.error(f"Error in audio player task: {str(e)}")
            self.audio_player_running = False
    
    async def _ensure_player_running(self):
        """
        Ensure the audio player task is running.
        """
        if not self.audio_player_running:
            # Start the player task
            asyncio.create_task(self._audio_player_task())
    
    async def queue_audio(self, audio_file: str) -> bool:
        """
        Add an audio file to the playback queue.
        
        Args:
            audio_file: Path to the audio file to queue
            
        Returns:
            bool: True if file was successfully queued, False otherwise
        """
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found for queueing: {audio_file}")
            return False
            
        # Ensure the player task is running
        await self._ensure_player_running()
        
        # Add the file to the queue
        async with self.queue_lock:
            self.audio_queue.append(audio_file)
            logger.info(f"Added audio file to queue: {audio_file}")
        
        # Signal that there are new files in the queue
        self.audio_queue_event.set()
        return True
    
    async def play_audio(self, audio_file: str) -> bool:
        """
        Queue an audio file for non-blocking playback.
        
        Args:
            audio_file: Path to the audio file to play
            
        Returns:
            bool: True if the file was queued successfully, False otherwise
        """
        # Simply add to the queue
        return await self.queue_audio(audio_file)
    
    async def play_narration(self, venice_client, narration_text: str, topic: str = None, max_length: int = 4080):
        """
        Generate and play audio narration from the provided text.
        Optionally truncates the narration_text if it exceeds max_length characters.
        
        Args:
            venice_client: The client used to generate audio
            narration_text: The text to convert to speech
            topic: Optional topic for the narration
            max_length: Maximum allowed length for narration_text
        """
        try:
            if len(narration_text) > max_length:
                logger.info(f"Truncating narration text from {len(narration_text)} to {max_length} characters.")
                narration_text = narration_text[:max_length-3] + "..."
            
            if topic and not topic.startswith("init_"):
                topic = f"init_{topic}"
            
            audio_file = await self.generate_audio(venice_client, narration_text, topic=topic)
            if audio_file and os.path.exists(audio_file):
                file_size = os.path.getsize(audio_file)
                if file_size < 100:
                    logger.warning(f"Audio file appears too small ({file_size} bytes). It might be corrupt.")
                else:
                    await self.play_audio(audio_file)
                    logger.info("Audio narration played successfully.")
            else:
                logger.error("Audio file not generated correctly.")
        except Exception as e:
            logger.error(f"Error playing audio narration: {e}")
    
    def _dev_log_audio_request(self, request_params: dict) -> None:
        """
        DEV FUNCTION: Logs the API request parameters verbatim to jrdev/requests.log.
        This function is for development/debugging purposes only and is not intended for production use.
        """
        # Only log when explicitly in debug mode
        if not os.getenv("JRDEV_DEBUG"):
            return
        
        log_file = os.path.join(JRDEV_DIR, "requests.log")
        log_entry = f"[DEV LOG] Request at {dt.now().isoformat()}:\n" + json.dumps(request_params, indent=2) + "\n\n"
        try:
            with open(log_file, "a") as f:
                f.write(log_entry)
        except Exception as e:
            logger.error(f"Failed to log API request: {e}")


# Create a singleton instance of TTSManager
_tts_manager = TTSManager()

# Provide access to TTSManager's methods via module functions

async def cleanup_old_audio_files() -> None:
    """
    Clean up old audio files to prevent excessive disk usage.
    """
    await _tts_manager.cleanup_old_audio_files()

async def generate_audio(client, text: str, output_path: Optional[str] = None, topic: Optional[str] = None) -> Optional[str]:
    """
    Generate audio from text using Venice TTS API.
    
    Args:
        client: The Venice API client
        text: The text to convert to speech
        output_path: Optional path to save the audio file
        topic: Optional topic identifier for the audio file name
        
    Returns:
        Path to the generated audio file or None if generation failed
    """
    return await _tts_manager.generate_audio(client, text, output_path, topic)

async def play_audio(audio_file: str) -> bool:
    """
    Queue an audio file for non-blocking playback.
    
    Args:
        audio_file: Path to the audio file to play
        
    Returns:
        bool: True if the file was queued successfully, False otherwise
    """
    return await _tts_manager.play_audio(audio_file)

async def play_narration(venice_client, narration_text: str, topic: str = None, max_length: int = 4080):
    """
    Generate and play audio narration from the provided text.
    Optionally truncates the narration_text if it exceeds max_length characters.
    
    Args:
        venice_client: The client used to generate audio
        narration_text: The text to convert to speech
        topic: Optional topic for the narration
        max_length: Maximum allowed length for narration_text
    """
    await _tts_manager.play_narration(venice_client, narration_text, topic, max_length)
