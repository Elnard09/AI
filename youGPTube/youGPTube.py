import datetime
import os
from transformers import pipeline
import shutil
import subprocess 
from flask import Flask, render_template, request, jsonify, session, url_for, redirect
import librosa
import openai
import soundfile as sf
import yt_dlp
from yt_dlp.utils import DownloadError
import logging
from dotenv import load_dotenv
import ffmpeg
from flask_sqlalchemy import SQLAlchemy
from youtube_transcript_api import YouTubeTranscriptApi
import re

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

def extract_video_id(url):
    # Extract the video ID from various forms of YouTube URLs
    video_id_match = re.search(r"(?:v=|\/)([0-9A-Za-z_-]{11}).*", url)
    if video_id_match:
        return video_id_match.group(1)
    return None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript])
    except Exception as e:
        print(f"An error occurred while fetching the transcript: {str(e)}")
        return None



def get_transcription_from_youtube(youtube_url):
    try:
        video_id = extract_video_id(youtube_url)
        if not video_id:
            raise ValueError("Invalid YouTube URL")
        
        logging.debug(f"Fetching transcript for video ID: {video_id}")
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        
        # Log transcript details
        logging.debug(f"Transcript for video ID {video_id}: {transcript}")
        
        transcription_text = " ".join([item['text'] for item in transcript])
        return transcription_text

    except Exception as e:
        logging.error(f"Failed to get transcription for {youtube_url}: {str(e)}")
        raise Exception(f"Failed to get transcription: {str(e)}")

# Utility function to find audio files
def find_audio_files(path, extension=".mp3"):
    return [os.path.join(root, f) for root, _, files in os.walk(path) for f in files if f.endswith(extension)]

# Function to download audio from YouTube
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
        
        # Handle yt-dlp specific DownloadError exceptions
        except DownloadError as e:
            logging.error(f"Attempt {attempt + 1}: Download error: {str(e)}")
            if attempt < retries - 1:
                logging.info("Retrying...")
                continue  # Retry the download
            else:
                raise RuntimeError(f"Error downloading video after {retries} attempts: {str(e)}")

        # Catch any other exceptions
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

def get_transcription_from_youtube(youtube_url):
    try:
        # Extract video ID from the YouTube URL
        video_id = youtube_url.split('v=')[-1]

        # Retrieve the transcript
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # Join the transcript parts into a single string
        transcription_text = " ".join([item['text'] for item in transcript])

        return transcription_text

    except Exception as e:
        # Handle any errors (e.g., video has no captions)
        raise Exception(f"Failed to get transcription: {str(e)}")
    
def summarize_text(text, max_length=150, min_length=50):
    summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
    
    # Split the text into chunks that the model can handle
    max_chunk_length = 1024
    chunks = [text[i:i+max_chunk_length] for i in range(0, len(text), max_chunk_length)]
    
    summaries = []
    for chunk in chunks:
        summary = summarizer(chunk, max_length=max_length, min_length=min_length, do_sample=False)[0]['summary_text']
        summaries.append(summary)
    
    return summaries


# Function to summarize transcribed audio
def summarize(chunks_with_timestamps: list, system_prompt: str, model="gpt-3.5-turbo"):
    summaries = []
    for chunk in chunks_with_timestamps:
        timestamp = chunk.get("timestamp", 0)
        content = chunk.get("text", "")
        
        # Format the timestamp in minutes and seconds
        minutes = timestamp // 60
        seconds = timestamp % 60
        timestamp_formatted = f"{minutes:02d}:{seconds:02d}"

        # Generate the summary using OpenAI ChatCompletion
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
        summary = response["choices"][0]["message"]["content"]
        
        # Append the formatted timestamp and summary
        summaries.append(f"[{timestamp_formatted}] {summary}")

    return summaries

def your_summarization_function(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return ["Invalid YouTube URL"]
    
    transcript = get_transcript(video_id)
    if not transcript:
        return ["Unable to fetch video transcript"]
    
    summaries = summarize_text(transcript)
    return summaries

@app.route('/summarize_video', methods=['POST'])
def summarize_video():
    video_url = request.json['video_url']
    # Clear any existing summary data for this session
    session.pop('video_data', None)
    
    summaries = your_summarization_function(video_url)
    
    # Store the new summaries in the session
    session['video_data'] = {'summaries': summaries}
    
    return jsonify({'summaries': summaries})

# Main function to process YouTube videos
def summarize_youtube_video(youtube_url, outputs_dir):
    raw_audio_dir = os.path.join(outputs_dir, "raw_audio")
    chunks_dir = os.path.join(outputs_dir, "chunks")
    segment_length = 10 * 60  # 10 minutes

    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
    os.makedirs(outputs_dir)

    try:
        # Download audio and chunk it
        audio_filename = youtube_to_mp3(youtube_url, output_dir=raw_audio_dir)
        chunked_audio_files = chunk_audio(audio_filename, segment_length=segment_length, output_dir=chunks_dir)
        
        # Transcribe the chunked audio files
        transcriptions = transcribe_audio(chunked_audio_files)
        
        # Generate summaries
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
    
@app.route('/delete_history/<int:history_id>', methods=['DELETE'])
def delete_history(history_id):
    history_record = History.query.get(history_id)
    
    if not history_record:
        return jsonify({"success": False, "error": "History record not found"}), 404
    
    db.session.delete(history_record)
    db.session.commit()
    logging.info(f"Deleted history record with id: {history_id}")
    return jsonify({"success": True})

@app.route('/clear_session')
def clear_session():
    session.clear()
    return redirect(url_for('home'))





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

@app.route('/process_video', methods=['POST'])
def process_video():
    data = request.get_json()
    youtube_url = data.get('youtube_url')
    
    logging.debug(f"Processing video: {youtube_url}")

    try:
        transcriptions, summaries = summarize_youtube_video(youtube_url, outputs_dir='output/')
        
        session['video_data'] = {
            'url': youtube_url,
            'summaries': summaries,
            'transcriptions': transcriptions
        }

        return jsonify({'success': True, 'redirect_url': url_for('chat_page')})

    except Exception as e:
        logging.error(f"Error processing video: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route("/chat_response", methods=["POST"])
def chat_response():
    data = request.json
    question = data.get("question")
    video_data = session.get('video_data', {})

    if not video_data:
        return jsonify({"error": "No video context found"}), 400

    try:
        # Construct context from video data
        summaries = "\n".join(video_data.get('summaries', []))  # Join all summaries into a single string
        context = f"""
        Video URL: {video_data.get('url')}
        Summary:
        {summaries}
        
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

        return jsonify({"response": answer, "summaries": summaries})  # Include summaries in the response
    except Exception as e:
        logging.error(f"Error generating chat response: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 400


@app.route('/get_history', methods=['GET'])
def get_history():
    history_records = History.query.all()
    return render_template('history.html', history=history_records)

@app.route('/chatAI')
def chat_page():
    video_data = session.get('video_data', None)
    logging.debug(f"Session video data: {video_data}")

    if video_data:
        return render_template('chatAI.html', transcription=video_data['transcriptions'])
    else:
        return redirect(url_for('summarizer'))  # Redirect if no transcription is found




if __name__ == "__main__":
    with app.app_context():  # Create an application context
        db.create_all()  # This will create all tables
    app.run(debug=True)
