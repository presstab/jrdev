#!/usr/bin/env python3
"""
TTS functionality for JrDev terminal.
Handles text-to-speech using the Venice API and audio playback.
Combined and refactored from legacy audio module and tts.py.
"""

import os
import asyncio
import tempfile
import logging
import subprocess
import sys
import time
import glob
import re
from typing import Optional
from collections import deque
import json
from datetime import datetime as dt

from jrdev.file_utils import JRDEV_DIR

logger = logging.getLogger("jrdev.tts")

# Create an audio directory inside the JRDEV_DIR
AUDIO_DIR = os.path.join(JRDEV_DIR, "audio")
os.makedirs(AUDIO_DIR, exist_ok=True)

# Maximum number of audio files to keep
MAX_AUDIO_FILES = 50

# Audio playback queue management
audio_player_running = False
audio_queue = deque()
audio_queue_event = asyncio.Event()
queue_lock = asyncio.Lock()

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


async def cleanup_old_audio_files() -> None:
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


async def generate_audio(client, text: str, output_path: Optional[str] = None, topic: Optional[str] = None) -> str:
    """
    Generate audio from text using Venice TTS API.

    Args:
        client: The Venice API client
        text: The text to convert to speech
        output_path: Optional path to save the audio file
        topic: Optional topic identifier for the audio file name

    Returns:
        Path to the generated audio file
    """
    try:
        await cleanup_old_audio_files()
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
        voice_models = [
            {"model": "tts-kokoro", "voice": "af_aoede", "speed": 1.1},
        ]
        response = None
        success = False
        for voice_config in voice_models:
            try:
                logger.info(f"Trying voice model: {voice_config['model']} with voice: {voice_config['voice']}")
                # DEV FUNCTION: Log the API request parameters verbatim. Not intended for production use.
                request_params = {
                    "model": voice_config['model'],
                    "voice": voice_config['voice'],
                    "speed": voice_config['speed'],
                    "response_format": "mp3",
                    "file": topic + ".mp3",
                    "input_text": text
                }
                dev_log_audio_request(request_params)
                response = await client.audio.speech.create(
                    model=voice_config['model'],
                    voice=voice_config['voice'],
                    speed=voice_config['speed'],
                    response_format="mp3",
                    input=text
                )
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
        with open(output_path, "wb") as f:
            f.write(response.content)
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            logger.info(f"Audio file saved to {output_path} (size: {file_size} bytes)")
            if file_size < 100:
                logger.warning(f"Generated audio file is suspiciously small ({file_size} bytes), likely corrupt")
        else:
            logger.error(f"Failed to create audio file at {output_path}")
        return output_path
    except Exception as e:
        logger.error(f"Error generating audio: {str(e)}")
        if output_path and os.path.exists(output_path):
            try:
                os.remove(output_path)
            except Exception:
                pass
        raise


async def _play_audio_file(audio_file: str) -> bool:
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
        if PLAYSOUND_AVAILABLE:
            try:
                await asyncio.to_thread(playsound, audio_file)
                logger.info("playsound playback completed successfully")
                return True
            except Exception as e:
                logger.warning(f"playsound failed: {e}")
        command = None
        if sys.platform.startswith('linux'):
            if audio_file.lower().endswith('.mp3'):
                command = f'mpg123 -q --no-control "{audio_file}"'
            else:
                command = f'aplay -q "{audio_file}"'
        elif sys.platform.startswith('win'):
            command = f'start /wait "" "{audio_file}"'
        elif sys.platform.startswith('darwin'):
            command = f'afplay "{audio_file}"'
        if command:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await process.communicate()
            if process.returncode == 0:
                logger.info("System audio playback completed successfully")
                return True
            else:
                logger.warning(f"System audio playback failed with status {process.returncode}")
                return False
        else:
            logger.error("Unsupported platform for audio playback")
            return False
    except Exception as e:
        logger.error(f"Error playing audio: {e}")
        return False


async def _audio_player_task():
    """
    Background task that processes the audio queue and plays files in sequence.
    Ensures only one audio file plays at a time.
    """
    global audio_player_running
    try:
        audio_player_running = True
        logger.info("Audio player task started")
        currently_playing = False
        while True:
            if not currently_playing:
                if not audio_queue:
                    logger.debug("Audio queue empty, waiting for new files")
                    await audio_queue_event.wait()
                    audio_queue_event.clear()
                audio_file = None
                async with queue_lock:
                    if audio_queue:
                        audio_file = audio_queue.popleft()
                        if audio_queue:
                            logger.debug(f"Remaining files in queue: {len(audio_queue)}")
                if audio_file:
                    logger.info(f"Playing next audio file from queue: {audio_file}")
                    currently_playing = True
                    success = await _play_audio_file(audio_file)
                    logger.debug("Adding 1 second pause between audio files")
                    await asyncio.sleep(1.0)
                    currently_playing = False
                    if not success:
                        logger.warning(f"Failed to play audio file: {audio_file}")
            else:
                await asyncio.sleep(0.1)
    except asyncio.CancelledError:
        logger.info("Audio player task was cancelled")
        audio_player_running = False
    except Exception as e:
        logger.error(f"Error in audio player task: {str(e)}")
        audio_player_running = False


async def _ensure_player_running():
    """
    Ensure the audio player task is running.
    """
    global audio_player_running
    if not audio_player_running:
        asyncio.create_task(_audio_player_task())


async def queue_audio(audio_file: str) -> None:
    """
    Add an audio file to the playback queue.

    Args:
        audio_file: Path to the audio file to queue
    """
    if not os.path.exists(audio_file):
        logger.error(f"Audio file not found for queueing: {audio_file}")
        return
    await _ensure_player_running()
    async with queue_lock:
        audio_queue.append(audio_file)
        logger.info(f"Added audio file to queue: {audio_file}")
    audio_queue_event.set()


async def play_audio(audio_file: str) -> None:
    """
    Queue an audio file for non-blocking playback.

    Args:
        audio_file: Path to the audio file to play
    """
    await queue_audio(audio_file)


# TTS-specific functionality

async def play_narration(venice_client, narration_text: str, topic: str = None, max_length: int = 4080):
    """
    Generate and play audio narration from the provided text.
    Optionally truncates the narration_text if it exceeds max_length characters.
    """
    try:
        if len(narration_text) > max_length:
            logger.info(f"Truncating narration text from {len(narration_text)} to {max_length} characters.")
            narration_text = narration_text[:max_length-3] + "..."
        if topic and not topic.startswith("init_"):
            topic = f"init_{topic}"
        audio_file = await generate_audio(venice_client, narration_text, topic=topic)
        if audio_file and os.path.exists(audio_file):
            file_size = os.path.getsize(audio_file)
            if file_size < 100:
                logger.warning(f"Audio file appears too small ({file_size} bytes). It might be corrupt.")
            else:
                await play_audio(audio_file)
                logger.info("Audio narration played successfully.")
        else:
            logger.error("Audio file not generated correctly.")
    except Exception as e:
        logger.error(f"Error playing audio narration: {e}")


#################################################################################################
# DEV FUNCTION: Logs the API request parameters verbatim to jrdev/requests.log.
# This function is for development/debugging purposes only and is not intended for production use.
def dev_log_audio_request(request_params: dict) -> None:
    log_file = os.path.join(JRDEV_DIR, "requests.log")
    log_entry = f"[DEV LOG] Request at {dt.now().isoformat()}:\n" + json.dumps(request_params, indent=2) + "\n\n"
    try:
        with open(log_file, "a") as f:
            f.write(log_entry)
    except Exception as e:
        logging.getLogger("jrdev.tts").error(f"Failed to log API request: {e}")
