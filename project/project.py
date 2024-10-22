from flask import Flask, render_template, request, jsonify
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import re
import logging 

load_dotenv()

# Initialize Flask and the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Your API Keys (make sure to keep them secure!)
openai.api_key = os.getenv("OPENAI_API_KEY")
youtube = build('youtube', 'v3', developerKey=os.getenv("YOUTUBE_API_KEY"))

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
    
def extract_video_id(youtube_link):
    # Regular expression to extract the video ID from various YouTube URL formats
    video_id_match = re.search(r"(?:https?://)?(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]{11})", youtube_link)
    return video_id_match.group(1) if video_id_match else None


# Function to extract video info and transcript
def get_video_info_and_transcript(video_id):
    video_response = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()

    if not video_response['items']:
        raise ValueError("Video not found.")
    
    video_info = video_response['items'][0]['snippet']
    video_title = video_info['title']
    video_description = video_info['description']

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

    if "transcript" in prompt.lower():
        return f"Here is the transcript of the video:\n\n{video_transcript}"

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

@app.route('/process_youtube_link', methods=['POST'])
def process_youtube_link():
    try:
        data = request.get_json()
        youtube_link = data['youtube_url']
        video_id = extract_video_id(youtube_link)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL provided.'}), 400

        video_data = get_video_data(video_id)
        if not video_data:
            # Get video info and transcript
            title, description, transcript = get_video_info_and_transcript(video_id)
            
            # Check if the video already exists before saving
            existing_video = YouTubeVideo.query.filter_by(video_id=video_id).first()
            if existing_video:
                return jsonify({'message': 'Video already exists in the database. You can now ask questions.'})

            # Save video to database
            save_video_to_db(video_id, title, description, transcript)
            video_data = (title, description, transcript)
        else:
            return jsonify({'message': 'Video data found in database. You can now ask questions.'})

        return jsonify({'message': 'Video data saved! You can now ask questions.'})
    except Exception as e:
        logging.error(f"Error processing YouTube link: {e}")
        return jsonify({'error': str(e)}), 400

@app.route('/ask_question', methods=['POST'])
def ask_question():
    try:
        youtube_link = request.form['youtube_link']
        video_id = extract_video_id(youtube_link)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL provided.'}), 400

        question = request.form['question']

        video_data = get_video_data(video_id)
        if video_data:
            ai_response = get_openai_response(question, video_data)
            return jsonify({'response': ai_response})
        else:
            return jsonify({'error': 'Video not found.'}), 404
    except Exception as e:
        logging.error(f"Error asking question: {e}")
        return jsonify({'error': str(e)}), 400
    
# Main route to render the interface
@app.route('/')
def home():
    return render_template('summarizer.html')

@app.route('/chatAI')
def chatAI():
    return render_template('chatAI.html')

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/history')
def history():
    return render_template('history.html')

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

if __name__ == '__main__':
    app.run(debug=True)
