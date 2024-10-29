from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import re
import logging 
from werkzeug.security import generate_password_hash, check_password_hash


load_dotenv()

# Initialize Flask and the database
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///youtube_videos.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Your API Keys (make sure to keep them secure!)
openai.api_key = os.getenv("OPENAI_API_KEY")
youtube = build('youtube', 'v3', developerKey=os.getenv("YOUTUBE_API_KEY"))
app.secret_key = os.getenv("SECRET_KEY")
# print("Secret Key:", app.secret_key)  # Remove after debugging


# Model to store video information
class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=False)

class User(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        email = db.Column(db.String(120), unique=True, nullable=False)
        nickname = db.Column(db.String(50), nullable=False)
        password = db.Column(db.String(200), nullable=False)

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

    conversation_prompt = (
        f"Video Title: {video_title}\n"
        f"Description: {video_description}\n"
        f"Transcript: {video_transcript}\n\n"
        f"User: {prompt}\nAI:"
    )

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an AI assistant that answers questions based on the video content."},
            {"role": "user", "content": conversation_prompt}
        ],
        temperature=0.7
    )
    
    return response['choices'][0]['message']['content']

# Function to retrieve a user by ID
def get_user_by_id(user_id):
    return User.query.get(user_id)

@app.route('/process_youtube_link', methods=['POST'])
def process_youtube_link():
    try:
        data = request.get_json()
        youtube_link = data['youtube_url']
        video_id = extract_video_id(youtube_link)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL provided.'}), 400

        # Check if video is in the database
        video_data = get_video_data(video_id)
        if not video_data:
            # Get video info and transcript if not found in database
            title, description, transcript = get_video_info_and_transcript(video_id)

            # Check if the video already exists before saving
            existing_video = YouTubeVideo.query.filter_by(video_id=video_id).first()
            if existing_video:
                return jsonify({'message': 'Video already exists in the database.', 'transcript': transcript})

            # Save video to database
            save_video_to_db(video_id, title, description, transcript)
            video_data = (title, description, transcript)
        else:
            title, description, transcript = video_data

        # Return the transcript immediately after processing the link
        return jsonify({
            'message': 'Video processed successfully!',
            'transcript': transcript,
            'title': title,
            'description': description
        })
    except Exception as e:
        logging.error(f"Error processing YouTube link: {e}")
        return jsonify({'error': str(e)}), 400


@app.route('/ask_question', methods=['POST'])
def ask_question():
    try:
        # Retrieve the JSON payload
        data = request.get_json()

        # Extract YouTube URL and question from the JSON payload
        youtube_link = data.get('youtube_url')
        question = data.get('question')

        if not youtube_link or not question:
            return jsonify({'error': 'YouTube URL or question not provided.'}), 400

        # Extract video ID from the YouTube URL
        video_id = extract_video_id(youtube_link)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL provided.'}), 400

        # Fetch the video data from the database
        video_data = get_video_data(video_id)
        if video_data:
            if video_data[2] == "Transcript not available.":
                return jsonify({'error': 'Transcript is not available for this video.'}), 400
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
    return render_template('login.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            flash("Logged in successfully!", "success")
            return redirect(url_for('summarizer'))  # Redirect to summarizer page
        else:
            flash("Invalid email or password.", "error")
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form['email']
        nickname = request.form['nickname']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if not nickname:
            flash('Nickname is required.', 'error')
            return redirect(url_for('signup'))
        
        print(f"Email: {email}, Nickname: {nickname}, Password: {password}")

        # Check if passwords match
        if password != confirm_password:
            flash("Passwords do not match.", "error")
            return redirect(url_for('signup'))

        # Check if the user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("Email already registered.", "error")
            return redirect(url_for('signup'))

        # Hash the password and create a new user
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')
        new_user = User(email=email, nickname = nickname, password=hashed_password)

        # Save the new user to the database
        db.session.add(new_user)
        db.session.commit()

        flash("Account created successfully!", "success")
        return redirect(url_for('login'))

    return render_template('signup.html')


@app.route('/forgotpassword')
def forgotpassword():
    return render_template('forgotpassword.html')

@app.route('/chatAI')
def chatAI():
    return render_template('chatAI.html')

@app.route('/summarizer')
def summarizer():
    return render_template('summarizer.html')

@app.route('/history')
def history():
    # Query the database for all videos
    videos = YouTubeVideo.query.all()
    
    # Pass the videos to the template
    return render_template('history.html', videos=videos)

@app.route('/help')
def help():
    return render_template('help.html')

@app.route('/profile')
def profile():
    return render_template('profile.html')

@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    user_id = session.get('user_id')  # Assume user_id is stored in session after login
    user = get_user_by_id(user_id)  # Replace with your DB query to get user data by ID
    if user:
        return f'{{"email": "{user.email}", "nickname": "{user.nickname}"}}'  # Return user data as a string
    else:
        return f'{{"error": "User not found"}}', 404

if __name__ == '__main__':
    app.run(debug=True)