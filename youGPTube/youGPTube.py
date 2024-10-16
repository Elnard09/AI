import os
import shutil
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
import librosa
import openai
import soundfile as sf
import yt_dlp
from yt_dlp.utils import DownloadError
import logging
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor
import datetime

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Configure SQLite Database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_summaries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "helloworld")

# Database Model for storing summaries and transcriptions
class VideoSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    youtube_url = db.Column(db.String(255), nullable=False)
    transcriptions = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.datetime.utcnow)

    def __repr__(self):
        return f"<VideoSummary {self.youtube_url}>"

# Initialize the database
def create_tables():
    with app.app_context():
        db.create_all()

# Utility function to find audio files
def find_audio_files(path, extension=".mp3"):
    return [os.path.join(root, f) for root, dirs, files in os.walk(path) for f in files if f.endswith(extension)]

# Function to download audio from YouTube
def youtube_to_mp3(youtube_url: str, output_dir: str) -> str:
    ydl_config = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "verbose": True,
    }

    os.makedirs(output_dir, exist_ok=True)

    try:
        with yt_dlp.YoutubeDL(ydl_config) as ydl:
            ydl.download([youtube_url])
    except DownloadError as e:
        logging.error(f"Download error: {str(e)}")
        raise ValueError("Could not download the video. Please check the URL.")

    audio_files = find_audio_files(output_dir)
    if not audio_files:
        raise FileNotFoundError("No audio files found after download.")
    
    return audio_files[0]

# Function to chunk audio into smaller segments
def chunk_audio(filename, segment_length: int, output_dir):
    os.makedirs(output_dir, exist_ok=True)

    audio, sr = librosa.load(filename, sr=44100)
    duration = librosa.get_duration(y=audio, sr=sr)
    num_segments = int(duration / segment_length) + 1

    chunked_audio_files_with_times = []

    for i in range(num_segments):
        start = i * segment_length
        end = (i + 1) * segment_length * sr
        segment = audio[start:end]
        chunk_filename = os.path.join(output_dir, f"segment_{str(i).zfill(3)}.mp3")
        sf.write(chunk_filename, segment, sr)
        chunked_audio_files_with_times.append((chunk_filename, start))

    return chunked_audio_files_with_times

# Function to transcribe audio using OpenAI, with concurrency
def transcribe_audio_concurrent(audio_files_with_times: list, model="whisper-1") -> list:
    transcripts = []
    with ThreadPoolExecutor() as executor:
        futures = [executor.submit(transcribe_single_audio, file, start_time, model) for file, start_time in audio_files_with_times]
        for future in futures:
            try:
                result = future.result()
                if result:
                    transcripts.append(result)
            except Exception as e:
                logging.error(f"Error transcribing audio: {str(e)}")
    return transcripts

# Helper function for transcription
def transcribe_single_audio(audio_file, start_time, model="whisper-1"):
    with open(audio_file, "rb") as audio:
        try:
            response = openai.Audio.transcribe(model, audio)
            if "text" in response:
                return {"timestamp": start_time, "text": response["text"]}
        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise

# Function to summarize transcribed audio
def summarize(transcriptions, system_prompt):
    transcriptions = remove_redundant_phrases(transcriptions)

    modified_prompt = f"{system_prompt}\n\nHere is the transcription:\n{transcriptions}"

    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": modified_prompt}
        ]
    )
    return response['choices'][0]['message']['content']

def remove_redundant_phrases(transcriptions):
    if isinstance(transcriptions, list):
        transcriptions = ' '.join(item['text'] for item in transcriptions if 'text' in item)

    lines = transcriptions.split('\n')
    unique_lines = list(dict.fromkeys(lines))  # Remove duplicates while preserving order
    return '\n'.join(unique_lines)

# Main function to process YouTube videos
def summarize_youtube_video(youtube_url, outputs_dir):
    raw_audio_dir = f"{outputs_dir}/raw_audio/"
    chunks_dir = f"{outputs_dir}/chunks"
    segment_length = 10 * 60

    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
    os.makedirs(outputs_dir)

    try:
        audio_filename = youtube_to_mp3(youtube_url, output_dir=raw_audio_dir)
        chunked_audio_files = chunk_audio(audio_filename, segment_length=segment_length, output_dir=chunks_dir)
        transcriptions = transcribe_audio_concurrent(chunked_audio_files)
        system_prompt = "You are a helpful assistant that summarizes YouTube videos. Summarize the transcription into clear bullet points."
        summary = summarize(transcriptions, system_prompt=system_prompt)

        # Save result to database
        save_summary_to_db(youtube_url, transcriptions, summary)

        return transcriptions, summary
    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        raise

# Function to save transcription and summary to the database
def save_summary_to_db(youtube_url, transcriptions, summary):
    transcription_text = "\n".join([f"[{t['timestamp']}] {t['text']}" for t in transcriptions])
    video_summary = VideoSummary(youtube_url=youtube_url, transcriptions=transcription_text, summary=summary)
    db.session.add(video_summary)
    db.session.commit()

# Flask Routes
@app.route('/')
def index():
    return redirect(url_for('home'))

@app.route('/files')
def files():
    # Logic to retrieve and display files
    return render_template('files.html')  # Ensure you have a files.html template

@app.route('/main')
def home():
    logging.debug("Home route accessed.")
    return render_template('main.html')

@app.route('/chatAI', methods=["GET", "POST"])
def chatAI():
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        outputs_dir = "outputs/"
        
        try:
            transcriptions, long_summary = summarize_youtube_video(youtube_url, outputs_dir)
            logging.debug(f"Long summary: {long_summary}")
            return render_template("result.html", transcriptions=transcriptions, long_summary=long_summary)
        except Exception as e:
            logging.error(f"Error processing {youtube_url}: {str(e)}")
            flash(f"An error occurred while processing the video: {str(e)}", "error")
            return redirect(url_for('home'))

    return render_template('chatAI.html')

@app.route('/history')
def history():
    # Retrieve saved video summaries from the database
    summaries = VideoSummary.query.all()
    return render_template('history.html', summaries=summaries)

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/help')
def help():
    logging.debug("Help route accessed.")
    return render_template('help.html')


if __name__ == "__main__":
    create_tables()
    app.run(debug=True)