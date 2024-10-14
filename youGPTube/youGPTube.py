import os
import shutil
from flask import Flask, render_template, request, flash, redirect, url_for
import librosa
import openai
import soundfile as sf
import youtube_dl
import yt_dlp
from yt_dlp.utils import DownloadError
import logging
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# Set the OpenAI API key from the environment variable
openai.api_key = os.getenv("OPENAI_API_KEY")
print(f"OpenAI API Key: {openai.api_key}")  # Debugging line

app.secret_key = os.getenv("FLASK_SECRET_KEY", "helloworld")

openai.debug = True

def find_audio_files(path, extension=".mp3"):
    """Recursively find all files with extension in path."""
    
    audio_files = []
    for root, dirs, files in os.walk(path):
        for f in files:
            if f.endswith(extension):
                audio_files.append(os.path.join(root, f))

    return audio_files

def youtube_to_mp3(youtube_url: str, output_dir: str) -> str:
    """Download the audio from a youtube video, save it to output_dir as an .mp3 file.

    Returns the filename of the saved video.
    """

    # config
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

    print(f"Downloading video from {youtube_url}")

    try:
        with yt_dlp.YoutubeDL(ydl_config) as ydl:
            ydl.download([youtube_url])
    except DownloadError:
        print("Download error occurred, please check the URL or try again.")

    audio_filename = find_audio_files(output_dir)[0]
    return audio_filename


def chunk_audio(filename, segment_length: int, output_dir):
    """segment length is in seconds"""
    
    print(f"Chunking audio to {segment_length} second segments...")

    if not os.path.isdir(output_dir):
        os.mkdir(output_dir)

    # load audio file
    audio, sr = librosa.load(filename, sr=44100)

    # calculate duration in seconds
    duration = librosa.get_duration(y=audio, sr=sr)

    # calculate number of segments
    num_segments = int(duration / segment_length) + 1

    print(f"Chunking {num_segments} chunks...")

    chunked_audio_files_with_times = []

    # iterate through segments and save them
    for i in range(num_segments):
        start = i * segment_length
        end = (i + 1) * segment_length * sr
        segment = audio[start:end]
        
        # Use zfill for zero-padding the index in the filename
        chunk_filename = os.path.join(output_dir, f"segment_{str(i).zfill(3)}.mp3")  # Changed here
        sf.write(chunk_filename, segment, sr)
        
        # Save the filename and start time (in seconds)
        chunked_audio_files_with_times.append((chunk_filename, start))

    return chunked_audio_files_with_times



def transcribe_audio(audio_files_with_times: list, output_file=None, model="whisper-1") -> list:
    transcripts = []
    for audio_file, start_time in audio_files_with_times:
        audio = open(audio_file, "rb")
        try:
            # Debug the response to see the exact structure
            response = openai.Audio.transcribe(model, audio)
            print(f"API Response: {response}")  # Debugging line to print the full API response

            # Check if 'text' exists in the response
            if "text" in response:
                # Add the transcript with its timestamp
                transcripts.append({"timestamp": start_time, "text": response["text"]})
            else:
                logging.error(f"No 'text' field found in the response: {response}")
                raise ValueError(f"Invalid API response: {response}")
                
        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    return transcripts


def summarize(chunks_with_timestamps: list, system_prompt: str, model="gpt-3.5-turbo", output_file=None):
    print(f"Summarizing with {model=}")
    summaries = []

    for chunk in chunks_with_timestamps:
        # Check if chunk is a string (single summary) or a dictionary (transcription)
        if isinstance(chunk, str):
            content = chunk
            timestamp_formatted = "N/A"  # If chunk is a string, there's no timestamp
        elif isinstance(chunk, dict):
            timestamp = chunk["timestamp"]
            content = chunk["text"]
            timestamp_formatted = f"{timestamp // 60}:{timestamp % 60}"  # convert to MM:SS format
        else:
            logging.error(f"Invalid chunk format: {chunk}")
            continue  # Skip this iteration

        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content},
            ],
        )
        summary = response["choices"][0]["message"]["content"]
        summaries.append(f"[{timestamp_formatted}] {summary}")

    if output_file is not None:
        # Save all summaries to a .txt file
        with open(output_file, "w") as file:
            for summary in summaries:
                file.write(summary + "\n")

    return summaries


def summarize_youtube_video(youtube_url, outputs_dir):
    raw_audio_dir = f"{outputs_dir}/raw_audio/"
    chunks_dir = f"{outputs_dir}/chunks"
    transcripts_file = f"{outputs_dir}/transcripts.txt"
    summary_file = f"{outputs_dir}/summary.txt"
    segment_length = 10 * 60  # chunk to 10 minute segments

    if os.path.exists(outputs_dir):
        shutil.rmtree(outputs_dir)
    os.makedirs(outputs_dir)

    try:
        logging.info(f"Processing YouTube URL: {youtube_url}")
        
        audio_filename = youtube_to_mp3(youtube_url, output_dir=raw_audio_dir)
        logging.info(f"Audio downloaded: {audio_filename}")

        chunked_audio_files = chunk_audio(audio_filename, segment_length=segment_length, output_dir=chunks_dir)
        logging.info(f"Audio chunked into {len(chunked_audio_files)} files")

        transcriptions = transcribe_audio(chunked_audio_files, transcripts_file)
        logging.info("Transcription completed")

        system_prompt = """
        You are a helpful assistant that summarizes YouTube videos.
        You are provided chunks of raw audio that were transcribed from the video's audio.
        Summarize the current chunk to succinct and clear bullet points of its contents.
        """
        summaries = summarize(transcriptions, system_prompt=system_prompt, output_file=summary_file)
        logging.info("Initial summarization completed")

        system_prompt_tldr = """
        You are a helpful assistant that summarizes YouTube videos.
        Someone has already summarized the video to key points.
        Summarize the key points to one or two sentences that capture the essence of the video.
        """
        long_summary = "\n".join(summaries)
        short_summary = summarize([long_summary], system_prompt=system_prompt_tldr, output_file=summary_file)[0]
        logging.info("Final summarization completed")

        # Return transcriptions (with timestamps) as well for table of contents
        return transcriptions, long_summary, short_summary

    except Exception as e:
        logging.error(f"An error occurred during video processing: {str(e)}", exc_info=True)
        raise


@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        outputs_dir = "outputs/"
        
        try:
            transcriptions, long_summary, short_summary = summarize_youtube_video(youtube_url, outputs_dir)
            return render_template("result.html", transcriptions=transcriptions, long_summary=long_summary, short_summary=short_summary)
        except Exception as e:
            logging.error(f"Error processing {youtube_url}: {str(e)}", exc_info=True)
            flash(f"An error occurred while processing the video: {str(e)}", "error")
            return redirect(url_for('home'))

    return render_template("index.html")


@app.route("/ask_question", methods=["POST"])
def ask_question():
    # Get the user's question and the summarized content from the form
    question = request.form.get("question")
    summary = request.form.get("summary")

    # Use OpenAI to answer the user's question based on the summary
    system_prompt = "You are a helpful assistant. Use the following summary to answer the question."
    user_prompt = f"Summary: {summary}\n\nQuestion: {question}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        answer = response["choices"][0]["message"]["content"]

        # Render the result page with the AI's answer
        return render_template("result.html", long_summary=summary, short_summary=summary, answer=answer)

    except Exception as e:
        logging.error(f"Error processing the question: {str(e)}", exc_info=True)
        flash(f"An error occurred while processing the question: {str(e)}", "error")
        return redirect(url_for('home'))


@app.template_filter('zfill')
def zfill_filter(s, width):
    return str(s).zfill(width)

if __name__ == "__main__":
    app.run(debug=True)