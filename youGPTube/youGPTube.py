import datetime
import os
import shutil
import subprocess 
from flask import Flask, render_template, request, jsonify, session
import librosa
import openai
import soundfile as sf
import yt_dlp
from yt_dlp.utils import DownloadError
import logging
from dotenv import load_dotenv
import ffmpeg
from flask_sqlalchemy import SQLAlchemy



load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///video_summaries.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Set the OpenAI API key from the environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
app.secret_key = os.getenv("FLASK_SECRET_KEY", "helloworld")

# Database model for history
class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String, nullable=False)  # You might want to use db.DateTime for actual timestamps
    user_input = db.Column(db.String, nullable=False)
    ai_response = db.Column(db.String, nullable=False)

    def __repr__(self):
        return f"<History(id={self.id}, timestamp={self.timestamp}, user_input={self.user_input})>"


# Check if FFmpeg is installed
def check_ffmpeg():
    try:
        subprocess.run(['ffmpeg', '-version'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except FileNotFoundError:
        return False

# Utility function to find audio files
def find_audio_files(path, extension=".mp3"):
    return [os.path.join(root, f) for root, _, files in os.walk(path) for f in files if f.endswith(extension)]

# Function to download audio from YouTube
def youtube_to_mp3(youtube_url: str, output_dir: str, retries: int = 3) -> str:
    if not check_ffmpeg():
        raise RuntimeError("FFmpeg is not installed. Please install FFmpeg to continue.")

    ydl_config = {
        "format": "bestaudio/best",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "outtmpl": os.path.join(output_dir, "%(title)s.%(ext)s"),
        "verbose": True,
        "socket_timeout": 30,
    }

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    for attempt in range(retries):
        try:
            with yt_dlp.YoutubeDL(ydl_config) as ydl:
                ydl.download([youtube_url])

            audio_files = find_audio_files(output_dir)
            if not audio_files:
                raise RuntimeError("No audio files found after download.")
            return audio_files[0]
        except DownloadError as e:
            logging.error(f"Attempt {attempt + 1}: Download error: {str(e)}")
            if attempt < retries - 1:
                logging.info("Retrying...")
                continue  # Retry the download
            else:
                raise RuntimeError(f"Error downloading video after {retries} attempts: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error: {str(e)}")
            raise

# Function to chunk audio into smaller segments
def chunk_audio(filename, segment_length: int, output_dir):
    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    audio, sr = librosa.load(filename, sr=44100)
    duration = librosa.get_duration(y=audio, sr=sr)
    num_segments = int(duration / segment_length) + 1

    chunked_audio_files_with_times = []
    for i in range(num_segments):
        start = int(i * segment_length * sr)
        end = int((i + 1) * segment_length * sr)
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
            response = openai.Audio.transcribe(model=model, file=audio)  # Updated method to transcribe audio
            if "text" in response:
                transcripts.append({"timestamp": start_time, "text": response["text"]})
        except Exception as e:  # Catch all exceptions since openai.error is no longer available
            logging.error(f"Error during transcription: {str(e)}")
            raise RuntimeError(f"Error during transcription: {str(e)}")
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
    raw_audio_dir = os.path.join(outputs_dir, "raw_audio")
    chunks_dir = os.path.join(outputs_dir, "chunks")
    segment_length = 10 * 60  # 10 minutes

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
    
@app.route('/history_item/<int:history_id>', methods=['GET'])
def get_history_item(history_id):
    history_record = History.query.get(history_id)
    
    if history_record:
        return jsonify({
            "success": True,
            "history": {
                "user_input": history_record.user_input,
                "ai_response": history_record.ai_response
            }
        })
    else:
        return jsonify({"success": False, "error": "History record not found"}), 404



@app.route('/')
def home():
    return render_template('summarizer.html')

# Flask Routes

@app.route('/chatAI')
def chatAI():
    return render_template('chatAI.html')

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/history')
def history():
    # Fetch all history records from the database
    history_records = History.query.all()
    logging.info(f"Fetched {len(history_records)} records from the database at {os.path.abspath('video_summaries.db')}.")
    return render_template('history.html', messages=history_records)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/process_video', methods=["POST"])
def process_video():
    data = request.json
    youtube_url = data.get("youtube_url")

    if not youtube_url:
        return jsonify({"error": "No YouTube URL provided"}), 400
    
    try:
        # Process video
        transcriptions, summaries = summarize_youtube_video(youtube_url, outputs_dir="outputs")
        
        # Store results in session
        session['video_data'] = {
            'transcriptions': transcriptions,
            'summary': "\n".join(summaries) if summaries else "",
            'url': youtube_url
        }
        
        return jsonify({"success": True})
    except RuntimeError as e:
        logging.error(f"Runtime error processing {youtube_url}: {str(e)}")
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        logging.error(f"Error processing {youtube_url}: {str(e)}", exc_info=True)
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 400

@app.route("/chat_response", methods=["POST"])
def chat_response():
    data = request.json
    question = data.get("question")
    video_data = session.get('video_data', {})

    if not video_data:
        return jsonify({"error": "No video context found"}), 400

    try:
        # Construct context from video data
        context = f"""
        Video URL: {video_data.get('url')}
        Summary: {video_data.get('summary')}
        Detailed transcription: {video_data.get('transcriptions')}
        
        Based on the above video content, please answer this question: {question}
        """

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are an AI assistant that helps users understand YouTube video content. Answer questions based on the video's transcription and summary."},
                {"role": "user", "content": context}
            ]
        )

        answer = response["choices"][0]["message"]["content"]

        # Save user input and AI response to the database
        new_history = History(timestamp=str(datetime.datetime.now()), user_input=question, ai_response=answer)
        db.session.add(new_history)

        try:
            db.session.commit()  # Attempt to commit changes
            logging.info(f"Saved history: {new_history}")
        except Exception as e:
            logging.error(f"Error saving to database: {str(e)}")
            db.session.rollback()  # Roll back the session in case of an error
            return jsonify({"error": "Could not save history."}), 500

        return jsonify({"response": answer})
    except Exception as e:
        logging.error(f"Error generating chat response: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400

@app.route('/get_history', methods=['GET'])
def get_history():
    history_records = History.query.all()
    return render_template('history.html', history=history_records)


if __name__ == "__main__":
    with app.app_context():  # Create an application context
        db.create_all()  # This will create all tables
    app.run(debug=True)
