from flask import Flask, render_template, request, jsonify
import openai
import yt_dlp
import subprocess
import re
from youtube_transcript_api import YouTubeTranscriptApi

app = Flask(__name__)

# Set your OpenAI API key
openai.api_key = 'sk-proj-bzjpPLTd8--vJF-AzQB26ODd-h-uT0C2lQGj0ZAKpstjX2uOzAaxydX9B94wtgvLPSHPC2vHk3Qa47a99GsA'  # Replace with your OpenAI API key

def download_youtube_audio(youtube_url):
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

        print("Audio downloaded successfully!")
        return 'audio.mp3'
    except Exception as e:
        print(f"Error downloading audio: {e}")
        return None

def transcribe_audio(audio_file):
    try:
        result = subprocess.run(['whisper', audio_file, '--model', 'base'], stdout=subprocess.PIPE, text=True)
        transcript_file = audio_file.replace('.mp3', '.txt')

        with open(transcript_file, 'r') as file:
            transcript = file.read()

        print("Transcription complete!")
        return transcript
    except Exception as e:
        print(f"Error transcribing audio: {e}")
        return None

def summarize_text(text):
    try:
        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=f"Summarize the following text: {text}",
            max_tokens=200,
            n=1,
            stop=None,
            temperature=0.7,
        )
        print("Summary generated!")
        return response['choices'][0]['text'].strip()
    except Exception as e:
        print(f"Error summarizing text: {e}")
        return None

def extract_video_id(url):
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
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = "\n".join([item['text'] for item in transcript])
        return transcript_text
    except Exception as e:
        print(f"Error fetching transcript: {str(e)}")  # Print detailed error
        return None


@app.route("/", methods=["GET", "POST"])
def home():
    summary = None
    transcript = None

    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        # Check if the URL can fetch a transcript
        video_id = extract_video_id(youtube_url)

        if video_id:
            # Try to get the transcript
            transcript = get_youtube_transcript(video_id)

            if transcript:
                print("Transcript retrieved successfully!")
            else:
                # If transcript not available, download audio and transcribe
                audio_file = download_youtube_audio(youtube_url)

                if audio_file:
                    transcript = transcribe_audio(audio_file)
                    if transcript:
                        summary = summarize_text(transcript)

    return render_template("index.html", summary=summary, transcript=transcript)

if __name__ == "__main__":
    app.run(debug=True)
