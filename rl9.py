from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
from transformers import AutoProcessor, SeamlessM4Tv2Model
from pydub import AudioSegment
import torch
import os
import shutil
import re

from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
import time


# Initialize the FastAPI app
app = FastAPI()

# Mount the current directory to serve audio files
app.mount("/audio", StaticFiles(directory="."), name="audio")


# Initialize SeamlessM4T model and processor
print("Loading SeamlessM4T model...")
processor = AutoProcessor.from_pretrained("facebook/seamless-m4t-v2-large", use_fast=False)
model = SeamlessM4Tv2Model.from_pretrained("facebook/seamless-m4t-v2-large")
print("SeamlessM4T model loaded successfully.")

# Request model for FastAPI
class TranslationRequest(BaseModel):
    youtube_url: str
    language_code: str

# Language options
LANGUAGE_MAP = {
        "cat": "Catalan",
        "cmn": "Mandarin",
        "por": "Portuguese",
        "spa": "Spanish",
        "pes": "Western Persian"
    }

# Wordplay examples with durations
LANGUAGE_WORDPLAY_EXAMPLES = {
    "cat": {
        "positive": [
            {"text": "Fantàstic!", "duration": 1.42},
            {"text": "Espero que tinguis un gran dia!", "duration": 2.32},
            {"text": "Això és absolutament meravellós!", "duration": 2.64},
            {"text": "No puc creure com de genial és això!", "duration": 2.74},
            {"text": "Quina experiència tan meravellosa!", "duration": 2.52}
        ],
        "neutral": [
            {"text": "Si us plau.", "duration": 1.38},
            {"text": "Si us plau, tingues-ho en compte.", "duration": 2.78},
            {"text": "Aquest és un punt important.", "duration": 2.22},
            {"text": "Si us plau, recorda això amb atenció.", "duration": 2.9},
            {"text": "Tingues-ho present, és rellevant.", "duration": 2.62}
        ],
        "negative": [
            {"text": "Això és preocupant.", "duration": 1.86},
            {"text": "Aquest no era el resultat esperat.", "duration": 2.6},
            {"text": "Hi ha un problema amb això.", "duration": 2.02},
            {"text": "No estic satisfet amb aquest resultat.", "duration": 2.64},
            {"text": "Aquest enfocament podria ser millor.", "duration": 2.54}
        ]
    },
    "cmn": {
        "positive": [
            {"text": "太棒了!", "duration": 1.34},
            {"text": "希望你今天过得愉快!", "duration": 2.6},
            {"text": "这绝对令人惊叹!", "duration": 2.14},
            {"text": "我简直不敢相信有多棒!", "duration": 2.8},
            {"text": "这真是一次美妙的体验!", "duration": 2.76}
        ],
        "neutral": [
            {"text": "请注意。", "duration": 1.38},
            {"text": "请记住这一点。", "duration": 1.92},
            {"text": "这是一个重要的细节。", "duration": 2.3},
            {"text": "请务必关注这个问题。", "duration": 2.52},
            {"text": "这是需要仔细考虑的。", "duration": 2.5}
        ],
        "negative": [
            {"text": "这令人担忧。", "duration": 1.8},
            {"text": "这不是预期的结果。", "duration": 2.2},
            {"text": "这个有一些问题。", "duration": 1.9},
            {"text": "我对此并不满意。", "duration": 2.1},
            {"text": "这个方法可以改进。", "duration": 2.28}
        ]
    },
    "por": {
        "positive": [
            {"text": "Isso é incrível!", "duration": 1.38},
            {"text": "Espero que você tenha um ótimo dia!", "duration": 2.06},
            {"text": "Isso é absolutamente maravilhoso!", "duration": 2.32},
            {"text": "Eu não consigo acreditar como isso é bom!", "duration": 2.6},
            {"text": "Que experiência fantástica!", "duration": 1.86}
        ],
        "neutral": [
            {"text": "Por favor.", "duration": 1.18},
            {"text": "Por favor, leve isso em consideração.", "duration": 2.36},
            {"text": "Certifique-se de lembrar disso.", "duration": 2.04},
            {"text": "Este é um detalhe importante.", "duration": 2.02},
            {"text": "Considere isso cuidadosamente.", "duration": 2.18}
        ],
        "negative": [
            {"text": "Isso é preocupante.", "duration": 1.46},
            {"text": "Este não foi o resultado esperado.", "duration": 2.16},
            {"text": "Há um problema com isso.", "duration": 1.64},
            {"text": "Não estou satisfeito com este resultado.", "duration": 2.64},
            {"text": "Essa abordagem poderia ser melhor.", "duration": 2.36}
        ]
    },
    "spa": {
        "positive": [
            {"text": "¡Esto es increíble!", "duration": 1.34},
            {"text": "¡Espero que tengas un día fantástico!", "duration": 2.12},
            {"text": "¡Esto es absolutamente maravilloso!", "duration": 2.3},
            {"text": "¡No puedo creer lo genial que es esto!", "duration": 2.06},
            {"text": "¡Qué experiencia tan fantástica!", "duration": 1.68}
        ],
        "neutral": [
            {"text": "Por favor.", "duration": 1.1},
            {"text": "Por favor, ten esto en cuenta.", "duration": 2.12},
            {"text": "Esto es importante, recuérdalo.", "duration": 2.12},
            {"text": "Asegúrate de considerar este detalle.", "duration": 2.42},
            {"text": "Es un punto relevante a revisar.", "duration": 2.1}
        ],
        "negative": [
            {"text": "Esto es preocupante.", "duration": 1.44},
            {"text": "Este no era el resultado esperado.", "duration": 2.26},
            {"text": "Hay un problema con esto.", "duration": 1.5},
            {"text": "No estoy satisfecho con este resultado.", "duration": 2.38},
            {"text": "Este enfoque podría ser mejor.", "duration": 2.02}
        ]
    },
    "pes": {
        "positive": [
            {"text": "این شگفت انگیز است!", "duration": 1.92},
            {"text": "امیدوارم روز فوق العاده ای داشته باشید!", "duration": 3.12},
            {"text": "این کاملاً شگفت انگیز است!", "duration": 2.36},
            {"text": "نمی توانم باور کنم که چقدر عالی است!", "duration": 2.94},
            {"text": "چه تجربه فوق العاده ای!", "duration": 2.26}
        ],
        "neutral": [
            {"text": "لطفاً.", "duration": 1.18},
            {"text": "لطفاً به این موضوع توجه کنید.", "duration": 2.42},
            {"text": "این موضوع مهم است، آن را به خاطر بسپارید.", "duration": 3.32},
            {"text": "این نکته مهمی است، لطفاً در نظر داشته باشید.", "duration": 3.56},
            {"text": "این نیاز به توجه دقیق دارد.", "duration": 2.32}
        ],
        "negative": [
            {"text": "این موضوع نگران کننده است.", "duration": 2.26},
            {"text": "این نتیجه مورد انتظار نبود.", "duration": 2.44},
            {"text": "مشکلی در این وجود دارد.", "duration": 2.16},
            {"text": "من از این نتیجه راضی نیستم.", "duration": 2.24},
            {"text": "این رویکرد می تواند بهتر باشد.", "duration": 2.5}
        ]
    }
}

# Tracks used examples for each tone and language
USED_EXAMPLES_TRACKER = {
    lang: {tone: [] for tone in ["positive", "neutral", "negative"]}
    for lang in LANGUAGE_WORDPLAY_EXAMPLES
}

def extract_video_id(youtube_url: str) -> str:
    """
    Extract the video ID from a YouTube URL.
    Supports standard YouTube URLs and shortened youtu.be links.
    """
    try:
        # Match standard YouTube URL or shortened URL
        match = re.search(r"(?:v=|\/)([a-zA-Z0-9_-]{11})", youtube_url)
        if not match:
            raise ValueError("Invalid YouTube URL. Could not extract video ID.")
        return match.group(1)
    except Exception as e:
        print(f"Error in extract_video_id: {e}")
        raise


def fetch_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        print(f"Fetched {len(transcript)} transcript entries.")
        return transcript
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def adjust_transcript_timing(transcript, video_speed):
    adjusted_transcript = []
    for entry in transcript:
        adjusted_entry = {
            "text": entry["text"],
            "start": entry["start"] / video_speed,
            "duration": entry["duration"] / video_speed
        }
        adjusted_transcript.append(adjusted_entry)
    print(f"Adjusted transcript timings for video speed {video_speed}x.")
    return adjusted_transcript

def find_best_wordplay_example(tgt_lang, tone, duration, margin=2.0):
    examples = LANGUAGE_WORDPLAY_EXAMPLES.get(tgt_lang, {}).get(tone, [])
    if not examples:
        return None

    usable_examples = [
        (idx, example)
        for idx, example in enumerate(examples)
        if abs(example["duration"] - duration) <= margin
        and idx not in USED_EXAMPLES_TRACKER[tgt_lang][tone]
    ]

    if not usable_examples:
        print(f"All examples used for {tgt_lang}-{tone}. Resetting tracker.")
        USED_EXAMPLES_TRACKER[tgt_lang][tone] = []
        usable_examples = [
            (idx, example)
            for idx, example in enumerate(examples)
            if abs(example["duration"] - duration) <= margin
        ]

    if not usable_examples:
        return None

    selected_idx, selected_example = usable_examples[0]
    USED_EXAMPLES_TRACKER[tgt_lang][tone].append(selected_idx)
    print(f"Chosen wordplay example: '{selected_example['text']}' (duration: {selected_example['duration']}s)")
    return selected_example

def translate_and_adjust_duration(sentence, duration, src_lang, tgt_lang, segment_idx, chunk_folder):
    print(f"\nTranslating: {sentence}")
    try:
        text_inputs = processor(text=sentence, src_lang=src_lang, return_tensors="pt")
        with torch.no_grad():
            audio_array = model.generate(**text_inputs, tgt_lang=tgt_lang)[0].cpu().numpy().squeeze()

        audio_array_int16 = (audio_array * 32767).astype("int16")
        audio_segment = AudioSegment(
            audio_array_int16.tobytes(),
            frame_rate=16000,
            sample_width=2,
            channels=1
        )

        current_duration = len(audio_segment) / 1000
        print(f"Generated audio segment (duration: {current_duration}s). Expected duration: {duration}s.")

        if abs(current_duration - duration) <= 2:
            print("Audio duration within margin, no adjustment needed.")
            chunk_file = os.path.join(chunk_folder, f"chunk_{segment_idx}.wav")
            audio_segment.export(chunk_file, format="wav")
            return audio_segment

        tone = "neutral"
        print(f"Detected tone: {tone}")

        if current_duration < duration:
            best_example = find_best_wordplay_example(
                tgt_lang, tone, duration - current_duration
            )
            if best_example:
                print(f"Adding wordplay: '{best_example['text']}' (duration: {best_example['duration']}s).")
                new_sentence = sentence + " " + best_example["text"]
                text_inputs = processor(text=new_sentence, src_lang=src_lang, return_tensors="pt")
                with torch.no_grad():
                    audio_array = model.generate(**text_inputs, tgt_lang=tgt_lang)[0].cpu().numpy().squeeze()
                audio_array_int16 = (audio_array * 32767).astype("int16")
                audio_segment = AudioSegment(
                    audio_array_int16.tobytes(),
                    frame_rate=16000,
                    sample_width=2,
                    channels=1
                )

        chunk_file = os.path.join(chunk_folder, f"chunk_{segment_idx}.wav")
        audio_segment.export(chunk_file, format="wav")
        print(f"Saved chunk {segment_idx} to {chunk_file}")
        return audio_segment
    except Exception as e:
        print(f"Error translating or adjusting duration: {e}")
        return AudioSegment.silent(duration=duration * 1000)

import os
import shutil
from pydub import AudioSegment

async def process_youtube_transcript(youtube_url, target_language_code, websocket=None):
    # Define the LANGUAGE_MAP
    LANGUAGE_MAP = {
        "cat": "Catalan",
        "cmn": "Mandarin",
        "por": "Portuguese",
        "spa": "Spanish",
        "pes": "Western Persian"
    }

    # Validate the target language code
    target_language_name = LANGUAGE_MAP.get(target_language_code)
    if not target_language_name:
        raise ValueError(f"Invalid language code: {target_language_code}")

    if websocket:
        await websocket.send_json({"progress": 10, "status": "Validating inputs..."})

    print(f"Processing YouTube URL: {youtube_url}")
    print(f"Target Language Code: {target_language_code}")
    print(f"Target Language Name: {target_language_name}")

    # Step 1: Extract video ID
    try:
        video_id = extract_video_id(youtube_url)
        print(f"Video ID: {video_id}")
    except ValueError as ve:
        print(f"Error extracting video ID: {ve}")
        if websocket:
            await websocket.send_json({"progress": -1, "status": "Error extracting video ID."})
        raise ve

    if websocket:
        await websocket.send_json({"progress": 20, "status": "Video ID extracted successfully."})

    # Step 2: Fetch transcript
    transcript = fetch_transcript(video_id)
    if not transcript:
        if websocket:
            await websocket.send_json({"progress": -1, "status": "Transcript could not be fetched."})
        raise ValueError("Transcript could not be fetched for the given video.")

    print(f"Transcript fetched successfully with {len(transcript)} segments.")
    if websocket:
        await websocket.send_json({"progress": 30, "status": "Transcript fetched successfully."})

    # Step 3: Adjust transcript timings
    video_speed = 1.5 if target_language_code in ["cmn", "por", "spa"] else 1.25
    transcript = adjust_transcript_timing(transcript, video_speed)
    if websocket:
        await websocket.send_json({"progress": 40, "status": "Transcript timings adjusted."})

    # Step 4: Prepare for audio generation
    chunk_folder = "audio_chunks"
    os.makedirs(chunk_folder, exist_ok=True)
    final_audio = AudioSegment.silent(duration=0)
    cumulative_timeline = 0
    src_lang = "eng"

    # Step 5: Process each transcript entry
    for idx, entry in enumerate(transcript):
        sentence = entry["text"]
        start_time = entry["start"]
        duration = entry["duration"]
        start_time_ms = int(start_time * 1000)
        duration_ms = int(duration * 1000)

        print(f"\nProcessing sentence {idx + 1}/{len(transcript)}: '{sentence}'")
        print(f"Adjusted Start: {start_time}s, Duration: {duration}s")

        if websocket:
            await websocket.send_json({"progress": 50 + int(50 * (idx + 1) / len(transcript)), 
                                       "status": f"Processing sentence {idx + 1}..."})

        try:
            translated_audio = translate_and_adjust_duration(
                sentence, duration, src_lang, target_language_code, idx + 1, chunk_folder
            )

            if len(translated_audio) == 0:
                print(f"No audio generated for sentence {idx + 1}. Skipping...")
                continue

            if cumulative_timeline < start_time_ms:
                silence_to_add = start_time_ms - cumulative_timeline
                print(f"Adding {silence_to_add / 1000}s of silence to align with start time.")
                final_audio += AudioSegment.silent(duration=silence_to_add)
                cumulative_timeline += silence_to_add

            print(f"Aligning translated audio (Start: {cumulative_timeline / 1000}s, End: {(cumulative_timeline + len(translated_audio)) / 1000}s).")
            final_audio += translated_audio
            cumulative_timeline += len(translated_audio)

        except Exception as e:
            print(f"Error processing sentence {idx + 1}: {e}")
            if websocket:
                await websocket.send_json({"progress": -1, "status": f"Error processing sentence {idx + 1}: {e}"})
            continue

    # Step 6: Export the final audio file
    output_file = f"final_{target_language_code.lower().replace(' ', '_')}_aligned_audio.wav"
    try:
        final_audio.export(output_file, format="wav")
        print(f"\nFinal aligned audio saved as {output_file}")
        if websocket:
            await websocket.send_json({"progress": 100, "status": "Audio file generation complete!"})
    except Exception as e:
        print(f"Error saving final audio file: {e}")
        if websocket:
            await websocket.send_json({"progress": -1, "status": "Error saving final audio file."})
        raise e
    finally:
        # Clean up temporary files
        if os.path.exists(chunk_folder):
            shutil.rmtree(chunk_folder)
            print("Temporary files cleaned up.")

    return output_file, video_speed


# Endpoint to list audio files
@app.get("/list-audio-files")
def list_audio_files():
    # Only show files with `.wav` extension for clarity
    audio_files = [file for file in os.listdir(".") if file.endswith(".wav")]
    return {"files": audio_files}


# WebSocket endpoint for progress updates
@app.websocket("/progress")
async def progress(websocket: WebSocket):
    await websocket.accept()
    try:
        # Wait for the client to send the YouTube URL and language code
        data = await websocket.receive_json()
        youtube_url = data.get("youtube_url")
        language_code = data.get("language_code")

        if not youtube_url or not language_code:
            await websocket.send_json({"progress": -1, "status": "Invalid data received."})
            return

        print(f"WebSocket received YouTube URL: {youtube_url}, Language Code: {language_code}")

        # Call the processing function and pass the WebSocket for updates
        await process_youtube_transcript(youtube_url, language_code, websocket)
    except Exception as e:
        print(f"Error in WebSocket progress: {e}")
        try:
            # Attempt to send the error message to the client before closing
            await websocket.send_json({"progress": -1, "status": f"Error: {e}"})
        except RuntimeError:
            print("WebSocket already closed; skipping error message.")
    finally:
        # Close the WebSocket connection
        try:
            await websocket.close()
        except RuntimeError:
            print("WebSocket already closed; skipping close attempt.")



@app.post("/translate")
async def translate(request: dict):
    try:
        youtube_url = request.get("youtube_url")
        language_code = request.get("language_code")

        if not youtube_url or not language_code:
            raise HTTPException(status_code=400, detail="youtube_url and language_code are required")

        print(f"Received request: YouTube URL: {youtube_url}, Language Code: {language_code}")

        # Call the transcription processing function (await required for async function)
        audio_file, video_speed = await process_youtube_transcript(youtube_url, language_code)

        # Validate the results
        if not audio_file:
            raise HTTPException(status_code=500, detail="Audio generation failed.")
        if not os.path.exists(audio_file):
            raise HTTPException(status_code=500, detail=f"Audio file '{audio_file}' not found on the server.")

        # Return success response
        return {
            "audio_url": f"http://127.0.0.1:8000/audio/{audio_file}",
            "language_code": language_code,
            "video_speed": video_speed
        }
    except Exception as e:
        print(f"Error during translation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error.")


