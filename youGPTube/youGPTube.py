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

    # iterate through segments and save them
    for i in range(num_segments):
        start = i * segment_length * sr
        end = (i + 1) * segment_length * sr
        segment = audio[start:end]
        sf.write(os.path.join(output_dir, f"segment_{i}.mp3"), segment, sr)

    chunked_audio_files = find_audio_files(output_dir)
    return sorted(chunked_audio_files)

def transcribe_audio(audio_files: list, output_file=None, model="whisper-1") -> list:
    transcripts = []
    for audio_file in audio_files:
        audio = open(audio_file, "rb")
        try:
            response = openai.Audio.transcribe(model, audio)
            transcripts.append(response["text"])
        except openai.error.OpenAIError as e:
            logging.error(f"OpenAI API error: {str(e)}")
            raise
    return transcripts

def summarize(
    chunks: list[str], system_prompt: str, model="gpt-3.5-turbo", output_file=None
):

    print(f"Summarizing with {model=}")

    summaries = []
    for chunk in chunks:
        response = openai.ChatCompletion.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": chunk},
            ],
        )
        summary = response["choices"][0]["message"]["content"]
        summaries.append(summary)

    if output_file is not None:
        # save all transcripts to a .txt file
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

        return long_summary, short_summary

    except Exception as e:
        logging.error(f"An error occurred during video processing: {str(e)}", exc_info=True)
        raise

@app.route("/", methods=["GET", "POST"])
def home():
    if request.method == "POST":
        youtube_url = request.form.get("youtube_url")
        outputs_dir = "outputs/"
        
        try:
            long_summary, short_summary = summarize_youtube_video(youtube_url, outputs_dir)
            return render_template("result.html", long_summary=long_summary, short_summary=short_summary)
        except Exception as e:
            logging.error(f"Error processing {youtube_url}: {str(e)}", exc_info=True)
            flash(f"An error occurred while processing the video: {str(e)}", "error")
            return redirect(url_for('home'))

    return render_template("index.html")

if __name__ == "__main__":
    app.run(debug=True)