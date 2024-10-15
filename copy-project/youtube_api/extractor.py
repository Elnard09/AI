from flask import Flask, render_template, request, jsonify
import openai
import yt_dlp
import subprocess
import re
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = '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'  # Replace with your OpenAI API key

def download_youtube_audio(youtube_url):
    """Download audio from a YouTube video."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'audio.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        return 'audio.mp3'
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def transcribe_audio(audio_file):
    """Transcribe the audio file using Whisper."""
    try:
        result = subprocess.run(['whisper', audio_file, '--model', 'base'], stdout=subprocess.PIPE, text=True)
        transcript_file = audio_file.replace('.mp3', '.txt')
        with open(transcript_file, 'r') as file:
            transcript = file.read()
        return transcript
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def summarize_text(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # Use gpt-3.5-turbo or gpt-4 if available
            messages=[
                {"role": "user", "content": f"Summarize the following text: {text}"}
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")  # Print the error for debugging
        return None



def extract_video_id(url):
    """Extract the video ID from a YouTube URL."""
    patterns = [
        r"(?:https?:\/\/)?(?:www\.)?youtu\.?be(?:\.com)?\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(?:\S*v=)?(?:v\/)?(\S{11})",
        r"^[a-zA-Z0-9_-]{11}$"
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_transcript(video_id):
    """Fetch the transcript of a YouTube video using the YouTube Transcript API."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = "\n".join([item['text'] for item in transcript])
        return transcript_text
    except Exception as e:
        print(f"Error fetching transcript: {e}")
        return None

def extract_summary_and_transcript(url):
    """Combine transcript extraction and summarization."""
    video_id = extract_video_id(url)
    
    if not video_id:
        print("Invalid YouTube URL; no video ID extracted.")
        return None, None

    # Attempt to get the transcript first
    transcript = get_youtube_transcript(video_id)
    
    # If transcript is not available, download audio and transcribe
    if not transcript:
        print("Transcript not found; downloading audio.")
        audio_file = download_youtube_audio(url)
        if not audio_file:
            print("Failed to download audio.")
            return None, None
        transcript = transcribe_audio(audio_file)
    
    if not transcript:
        print("Failed to obtain transcript.")
        return None, None

    summary = summarize_text(transcript)
    
    return summary, transcript

@app.route("/", methods=["GET"])
def home():
    """Render the main page."""
    return render_template("summarizer.html")

@app.route("/summarize", methods=["POST"])
def summarize():
    """Handle the summarization request."""
    youtube_url = request.json.get("youtube_url")
    
    if not youtube_url:
        return jsonify({"error": "Invalid YouTube URL"}), 400
    
    summary, transcript = extract_summary_and_transcript(youtube_url)
    
    if not transcript:
        return jsonify({"error": "Failed to obtain transcript"}), 500
    
    if not summary:
        return jsonify({"error": "Failed to generate summary"}), 500

    return jsonify({
        "summary": summary,
        "transcript": transcript
    })

if __name__ == "__main__":
    app.run(debug=True)
