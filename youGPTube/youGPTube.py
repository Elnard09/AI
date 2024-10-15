import os
import shutil
from flask import Flask, render_template, request, flash, redirect, url_for, jsonify
import librosa
import openai
import soundfile as sf
import yt_dlp
from yt_dlp.utils import DownloadError
import logging
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the OpenAI API key from the environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")

app.secret_key = os.getenv("FLASK_SECRET_KEY", "helloworld")

# Utility function to find audio files
def find_audio_files(path, extension=".mp3"):
    audio_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(extension):
                audio_files.append(os.path.join(root, f))
    return audio_files

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

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        with yt_dlp.YoutubeDL(ydl_config) as ydl:
            ydl.download([youtube_url])
    except DownloadError:
        print("Download error occurred, please check the URL or try again.")

    audio_filename = find_audio_files(output_dir)[0]
    return audio_filename

# Function to chunk audio into smaller segments
def chunk_audio(filename, segment_length: int, output_dir):
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

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

# Function to transcribe audio using OpenAI
def transcribe_audio(audio_files_with_times: list, model="whisper-1") -> list:
    transcripts = []
    for audio_file, start_time in audio_files_with_times:
        audio = open(audio_file, "rb")
        try:
            response = openai.Audio.transcribe(model, audio)
            if "text" in response:
                transcripts.append({"timestamp": start_time, "text": response["text"]})
        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    return transcripts

# Function to summarize transcribed audio
def summarize(chunks_with_timestamps: list, system_prompt: str, model="gpt-3.5-turbo"):
    summaries = []
    for chunk in chunks_with_timestamps:
        timestamp = chunk.get("timestamp", "N/A")
        content = chunk.get("text", "")
        timestamp_formatted = f"{timestamp // 60}:{timestamp % 60}"

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
        summary = response["choices"][0]["message"]["content"]
        summaries.append(f"[{timestamp_formatted}] {summary}")

    return summaries

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
        transcriptions = transcribe_audio(chunked_audio_files)
        system_prompt = "You are a helpful assistant that summarizes YouTube videos. Summarize the transcription to clear bullet points."
        summaries = summarize(transcriptions, system_prompt=system_prompt)

        return transcriptions, summaries
    except Exception as e:
        logging.error(f"An error occurred during video processing: {str(e)}", exc_info=True)
        raise

# Flask Routes
@app.route('/main')
def home():
    return render_template('main.html')

@app.route('/chatAI')
def chatAI():
    return render_template('chatAI.html')

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/files')
def files():
    return render_template('files.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')


@app.route("/summarize", methods=["POST"])
def summarize_video():
    data = request.json
    youtube_url = data.get("youtube_url")
    outputs_dir = "outputs/"
    
    try:
        transcriptions, summaries = summarize_youtube_video(youtube_url, outputs_dir)
        return jsonify({
            "transcript": transcriptions,
            "summary": "\n".join(summaries)
        })
    except Exception as e:
        logging.error(f"Error processing {youtube_url}: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400

@app.route("/ask_question", methods=["POST"])
def ask_question():
    data = request.json
    question = data.get("question")
    summary = data.get("summary")

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Use the following summary to answer the question."},
                {"role": "user", "content": f"Summary: {summary}\n\nQuestion: {question}"}
            ]
        )
        answer = response["choices"][0]["message"]["content"]
        return jsonify({"answer": answer})
    except Exception as e:
        logging.error(f"Error processing the question: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400

if __name__ == "__main__":
    app.run(debug=True)
