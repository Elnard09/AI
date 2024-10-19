from flask import Flask, render_template, request, jsonify
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

# Initialize Flask and the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Your API Keys (now loaded from the environment)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
YOUTUBE_API_KEY = os.getenv('YOUTUBE_API_KEY')

# Set OpenAI API key for use
openai.api_key = OPENAI_API_KEY

# Initialize YouTube API
youtube = build('youtube', 'v3', developerKey=YOUTUBE_API_KEY)

# Model to store video information
class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=False)

# Create the database
with app.app_context():
    db.create_all()

# Function to extract video info and transcript
def get_video_info_and_transcript(video_id):
    # Get video details using YouTube Data API
    video_response = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()

    video_info = video_response['items'][0]['snippet']
    video_title = video_info['title']
    video_description = video_info['description']

    # Get the transcript (assuming captions are available)
    try:
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript_text = ' '.join([item['text'] for item in transcript_list])
    except Exception:
        transcript_text = "Transcript not available."

    return video_title, video_description, transcript_text

# Save the video info to the database
def save_video_to_db(video_id, title, description, transcript):
    video = YouTubeVideo(video_id=video_id, title=title, description=description, transcript=transcript)
    db.session.add(video)
    db.session.commit()

# Retrieve video data from the database
def get_video_data(video_id):
    video = YouTubeVideo.query.filter_by(video_id=video_id).first()
    if video:
        return video.title, video.description, video.transcript
    return None

# Function to interact with OpenAI
def get_openai_response(prompt, video_data):
    video_title, video_description, video_transcript = video_data

    # If the user specifically asks for the transcript, return it directly
    if "transcript" in prompt.lower():
        return f"Here is the transcript of the video:\n\n{video_transcript}"

    # Otherwise, use OpenAI to generate a response based on the video content
    conversation_prompt = (
        f"Video Title: {video_title}\n"
        f"Description: {video_description}\n"
        f"Transcript: {video_transcript}\n\n"
        f"User: {prompt}\nAI:"
    )

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "You are an AI assistant that answers questions based on the video content."},
            {"role": "user", "content": conversation_prompt}
        ],
        temperature=0.7
    )
    
    return response['choices'][0]['message']['content']


# Route to process YouTube link
@app.route('/process_youtube_link', methods=['POST'])
def process_youtube_link():
    youtube_link = request.form['youtube_link']
    video_id = youtube_link.split('v=')[1]

    # Check if the video already exists in the database
    video_data = get_video_data(video_id)
    if not video_data:
        title, description, transcript = get_video_info_and_transcript(video_id)
        save_video_to_db(video_id, title, description, transcript)
        video_data = (title, description, transcript)

    return jsonify({'message': 'Video data saved! You can now ask questions.'})

# Route for chatting
@app.route('/ask_question', methods=['POST'])
def ask_question():
    youtube_link = request.form['youtube_link']
    video_id = youtube_link.split('v=')[1]
    question = request.form['question']

    # Fetch video data from the database
    video_data = get_video_data(video_id)
    if video_data:
        ai_response = get_openai_response(question, video_data)
        return jsonify({'response': ai_response})
    else:
        return jsonify({'error': 'Video not found.'})

# Main route to render the interface
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '_main_':
    app.run(debug=True)