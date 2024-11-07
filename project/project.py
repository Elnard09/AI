from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, LoginManager, UserMixin, logout_user, current_user
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import re
import logging 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime



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

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'  # Optional: Sets flash message category


# Model to store video information
class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=False)

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)

class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f"ChatSession(id={self.id}, date='{self.date}', title='{self.title}', description='{self.description}')"

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

from flask_login import login_user

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash("Logged in successfully!", "success")
            return redirect(url_for('summarizer'))
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
@login_required
def chatAI():
    return render_template('chatAI.html', nickname=current_user.nickname, email=current_user.email)

@app.route('/summarizer')
@login_required
def summarizer():
    return render_template('summarizer.html', nickname=current_user.nickname, email=current_user.email)

@app.route('/history')
@login_required
def history():
    # Query the database for all videos
    videos = YouTubeVideo.query.all()
    
    # Pass the videos to the template
    return render_template('history.html', videos=videos, nickname=current_user.nickname, email=current_user.email)

@app.route('/help')
@login_required
def help():
    return render_template('help.html', nickname=current_user.nickname, email=current_user.email)

@app.route('/profile')
@login_required
def profile():
    return render_template('profile.html', nickname=current_user.nickname, email=current_user.email)

@app.route('/get_user_data', methods=['GET'])
def get_user_data():
    user_id = session.get('user_id')  # Assume user_id is stored in session after login
    user = get_user_by_id(user_id)  # Replace with your DB query to get user data by ID
    if user:
        return f'{{"email": "{user.email}", "nickname": "{user.nickname}"}}'  # Return user data as a string
    else:
        return f'{{"error": "User not found"}}', 404

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))  # Replace User with your user model

@app.route('/logout')
def logout():
    logout_user()
    flash("You have been logged out.", "success")
    return redirect(url_for('login'))

# Route to update nickname
@app.route('/update_nickname', methods=['POST'])
@login_required
def update_nickname():
    data = request.get_json()
    new_nickname = data.get('nickname')

    if not new_nickname:
        return jsonify({'error': 'Nickname cannot be empty.'}), 400

    # Update nickname in the database
    current_user.nickname = new_nickname
    db.session.commit()
    return jsonify({'message': 'Nickname updated successfully.'})

# Route to update password
@app.route('/update_password', methods=['POST'])
@login_required
def update_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')

    # Check if the current password is correct
    if not check_password_hash(current_user.password, current_password):
        return jsonify({'error': 'Current password is incorrect.'}), 400

    # Check if new password is provided and valid
    if not new_password or len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters long.'}), 400

    # Update password
    current_user.password = generate_password_hash(new_password)
    db.session.commit()
    return jsonify({'message': 'Password updated successfully.'})
@app.route('/save-chat-session', methods=['POST'])
def save_chat_session():
    data = request.get_json()
    date_str = data['date']
    title = data['title']
    description = data['description']

    # Convert date_str to a datetime object
    try:
        date_obj = datetime.strptime(date_str, '%m/%d/%Y, %I:%M:%S %p')
    except ValueError as e:
        return {"error": f"Invalid date format: {e}"}, 400

    # Use date_obj instead of date_str when creating the ChatSession
    session = ChatSession(date=date_obj, title=title, description=description)
    db.session.add(session)
    db.session.commit()
    
    return {"success": True}


@app.route('/chat-sessions', methods=['GET'])
def get_chat_sessions():
    sessions = ChatSession.query.all()
    return jsonify([
        {
            'date': session.date.strftime('%Y-%m-%d %H:%M:%S'),
            'title': session.title,
            'description': session.description
        } for session in sessions
    ])

@app.route('/delete-chat-session/<date>', methods=['DELETE'])
def delete_chat_session(date):
    try:
        # Parse the date from the URL back into a datetime object
        date_obj = datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        
        # Query the session based on the parsed date object
        chat_session = ChatSession.query.filter_by(date=date_obj).first()
        
        if chat_session:
            db.session.delete(chat_session)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Session not found'}), 404
    except ValueError:
        # Handle incorrect date format in the URL
        return jsonify({'error': 'Invalid date format'}), 400

@app.route('/get-chat-session/<date>', methods=['GET'])
def get_chat_session(date):
    session = ChatSession.query.filter_by(date=date).first()
    if session:
        return jsonify({
            'date': session.date.strftime('%Y-%m-%d %H:%M:%S'),
            'title': session.title,
            'description': session.description
        })
    else:
        return jsonify({'error': 'Session not found'}), 404


if __name__ == '__main__':
    app.run(debug=True)