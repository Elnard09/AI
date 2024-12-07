from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import login_required, LoginManager, UserMixin, logout_user, current_user
from googleapiclient.discovery import build
from youtube_transcript_api import YouTubeTranscriptApi
import openai
import asyncio
import pyttsx3
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv
import os
import re
import logging 
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from werkzeug.utils import secure_filename
import pytesseract


load_dotenv()

engine = pyttsx3.init()
engine.setProperty('rate', 150)
engine.setProperty('volume', 1)
AUDIO_FILE_PATH = 'static/audio_output.mp3'



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

# Configuration for file uploads
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

class YoutubeSummary(db.Model):
    id = db.Column(db.Integer, primary_key = True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
class FileSummary(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(255), nullable=False)
    summary = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    upload_date = db.Column(db.DateTime, default=datetime.utcnow)


class CodeAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.Text, nullable=False)
    explanation = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)


class ImageAnalysis(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_path = db.Column(db.String(255), nullable=False)
    extracted_text = db.Column(db.Text, nullable=False)
    analysis = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    analysis_date = db.Column(db.DateTime, default=datetime.utcnow)


# Model to store video information
# Updated YouTubeVideo model (optional; no foreign keys required for this example)
class YouTubeVideo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.String(100), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    transcript = db.Column(db.Text, nullable=False)

# User model with no changes
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    nickname = db.Column(db.String(50), nullable=False)
    password = db.Column(db.String(200), nullable=False)
    # Adding relationship to ChatSession
    chat_sessions = db.relationship('ChatSession', backref='user', lazy=True)

# ChatSession now references User and has a relationship with ChatMessage
class ChatSession(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Foreign key to User table
    date = db.Column(db.DateTime, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)


# ChatMessage references ChatSession via foreign key
class ChatMessage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('chat_session.id'), nullable=False)  # Reference to ChatSession
    message = db.Column(db.Text, nullable=False)
    is_user = db.Column(db.Boolean, nullable=False)  # True for user message, False for AI response
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

# Create the database
with app.app_context():
    db.create_all()


def create_chat_session(user_id, title, description):
    chat_session = ChatSession(
        user_id=user_id,  # Associate the session with the user
        date=datetime.utcnow(),
        title=title,
        description=description
    )
    db.session.add(chat_session)
    db.session.commit()
    return chat_session.id

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_file(filepath):
    if filepath.endswith('.txt'):
        with open(filepath, 'r', encoding='utf-8') as f:
            return f.read()
    elif filepath.endswith('.pdf'):
        from PyPDF2 import PdfReader
        reader = PdfReader(filepath)
        return ''.join([page.extract_text() for page in reader.pages])
    elif filepath.endswith('.docx'):
        import docx
        doc = docx.Document(filepath)
        return '\n'.join([paragraph.text for paragraph in doc.paragraphs])
    else:
        return None

def save_message(session_id, message, is_user):
    chat_message = ChatMessage(
        session_id=session_id,
        message=message,
        is_user=is_user
    )
    db.session.add(chat_message)
    db.session.commit()


    
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
        return None, None, None  # Return three None values if the video is not found.
    
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
    if not video:
        # Fetch data from YouTube and save to the database
        try:
            title, description, transcript = get_video_info_and_transcript(video_id)
            save_video_to_db(video_id, title, description, transcript)
            return title, description, transcript
        except Exception as e:
            logging.error(f"Failed to fetch video data: {e}")
            return None
    return video.title, video.description, video.transcript


# Function to interact with OpenAI and get both a response and a session summary
def get_openai_response(prompt, video_data, generate_summary=False):
    video_title, video_description, video_transcript = video_data

    conversation_prompt = (
        f"Video Title: {video_title}\n"
        f"Description: {video_description}\n"
        f"Transcript: {video_transcript}\n\n"
        f"User: {prompt}\nAI:"
    )

    messages = [
        {"role": "system", "content": "You are an AI assistant that answers questions based on the video content."},
        {"role": "user", "content": conversation_prompt}
    ]

    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=messages,
        temperature=0.7
    )

    ai_response = response['choices'][0]['message']['content']

    # Generate a session title and description if requested
    if generate_summary:
        summary_prompt = (
            "Based on this chat session, provide a brief title and description that summarize the main topics."
        )
        messages.append({"role": "user", "content": summary_prompt})
        
        summary_response = openai.ChatCompletion.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.7
        )

        title, description = summary_response['choices'][0]['message']['content'].split('\n', 1)
        return ai_response, title.strip(), description.strip()
    
    return ai_response

# def get_dynamic_title_and_description(question, ai_response):
   # Combine question and response to create a summary
#     title = question if len(question) < 50 else question[:47] + "..."
#     description = ai_response if len(ai_response) < 150 else ai_response[:147] + "..."
#     return title, description

# Function to retrieve a user by ID
def get_user_by_id(user_id):
    return User.query.get(user_id)

def text_to_speech(text):
    engine.save_to_file(text, AUDIO_FILE_PATH)
    engine.runAndWait()
    
@app.route('/text-to-speech', methods=['POST'])
@login_required
def text_to_speech_route():
    data = request.get_json()
    text = data.get('text')
    
    if not text:
        return jsonify({'error': 'Text is required.'}), 400
    
    # Convert the text to speech and save the audio file
    text_to_speech(text)
    
    # Return the path of the saved audio file
    return jsonify({'audio_file': AUDIO_FILE_PATH})

@app.route('/process_youtube_link', methods=['POST'])
@login_required
def process_youtube_link():
    try:
        data = request.get_json()
        youtube_link = data['youtube_url']
        video_id = extract_video_id(youtube_link)

        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL provided.'}), 400

        # Check if the video is already saved in the database
        video_data = get_video_data(video_id)
        if not video_data:
            # Fetch from YouTube API
            title, description, transcript = get_video_info_and_transcript(video_id)
            save_video_to_db(video_id, title, description, transcript)
            video_data = (title, description, transcript)

        # Return the video data
        title, description, transcript = video_data
        return jsonify({
            'title': title,
            'description': description,
            'transcript': transcript
        })
    except Exception as e:
        logging.error(f"Error processing YouTube link: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/ask_question', methods=['POST'])
@login_required
def ask_question():
    try:
        data = request.get_json()
        logging.debug(f"Request payload: {data}")

        youtube_link = data.get('youtube_url')
        question = data.get('question')
        session_id = data.get('session_id')
        file_summary = data.get('file_summary')
        code_explanation = data.get('code_explanation')
        image_analysis = data.get('image_analysis')

        if not question:
            logging.error("Question not provided.")
            return jsonify({'error': 'Question not provided.'}), 400

        # Build the context dynamically
        context = ""
        if youtube_link:
            video_id = extract_video_id(youtube_link)
            if not video_id:
                logging.error(f"Invalid YouTube URL: {youtube_link}")
                return jsonify({'error': 'Invalid YouTube URL provided.'}), 400
            
            video_data = get_video_data(video_id)
            if video_data and len(video_data) == 3:
                context += f"Video Title: {video_data[0]}\n"
                context += f"Video Description: {video_data[1]}\n"
                context += f"Transcript: {video_data[2]}\n"
            else:
                logging.error(f"Video data not found for video_id: {video_id}")
                return jsonify({'error': 'Video data not available.'}), 400

        if file_summary:
            context += f"File Summary: {file_summary}\n"
        if code_explanation:
            context += f"Code Explanation: {code_explanation}\n"
        if image_analysis:
            context += f"Image Analysis: {image_analysis}\n"

        if not context:
            logging.error("No context available for the question.")
            return jsonify({'error': 'No context available for the question.'}), 400

        # Create a new session if none exists
        if not session_id:
            session_id = create_chat_session(
                user_id=current_user.id,
                title="Chat with AI",
                description="Conversation based on the summarized content."
            )

        # Save the user question
        save_message(session_id, question, is_user=True)

        # Generate AI response
        try:
            ai_response = get_openai_response(question, context)
        except Exception as e:
            logging.error(f"Error generating OpenAI response: {e}")
            return jsonify({'error': 'Failed to generate AI response.'}), 500

        # Save the AI response
        save_message(session_id, ai_response, is_user=False)

        return jsonify({'response': ai_response, 'session_id': session_id})

    except Exception as e:
        logging.error(f"Unexpected error in ask_question: {e}")
        return jsonify({'error': 'An unexpected error occurred.'}), 500


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
            return redirect(url_for('main'))
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

@app.route('/main')
@login_required
def main():
    return render_template('main.html', nickname=current_user.nickname, email=current_user.email)

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
@login_required
def save_chat_session():
    data = request.get_json()
    date_str = data['date']
    title = data['title']
    description = data['description']

    # Convert date_str to a datetime object
    try:
        date_obj = datetime.strptime(date_str, '%m/%d/%Y, %I:%M:%S %p')
    except ValueError as e:
        return jsonify({"error": f"Invalid date format: {e}"}), 400

    # Ensure the current user's ID is saved in the ChatSession
    session = ChatSession(date=date_obj, title=title, description=description, user_id=current_user.id)
    db.session.add(session)
    db.session.commit()

    return jsonify({"success": True})


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

@app.route('/delete-chat-session/<int:session_id>', methods=['DELETE'])
def delete_chat_session(session_id):
    try:
        # Query the session based on the session_id
        chat_session = ChatSession.query.get(session_id)
        
        if chat_session:
            db.session.delete(chat_session)
            db.session.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logging.error(f"Error deleting session: {e}")
        return jsonify({'error': 'An error occurred while deleting the session.'}), 500

@app.route('/chat-session/<int:session_id>', methods=['GET'])
def get_chat_session(session_id):
    try:
        session = ChatSession.query.get_or_404(session_id)
        messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
        return jsonify({
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'messages': [
                {'message': msg.message, 'is_user': msg.is_user, 'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
                for msg in messages
            ]
        })
    except Exception as e:
        logging.error(f"Error fetching session: {e}")
        return jsonify({'error': 'Failed to retrieve session messages.'}), 500

@app.route('/chat-session/<int:session_id>', methods=['GET'])
def get_chat_session_with_messages(session_id):
    session = ChatSession.query.get_or_404(session_id)
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()
    return jsonify({
        'title': session.title,
        'description': session.description,
        'messages': [
            {'message': msg.message, 'is_user': msg.is_user, 'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')}
            for msg in messages
        ]
    })
    
@app.route('/get-chat-history', methods=['GET'])
@login_required
def get_chat_history():
    sessions = ChatSession.query.order_by(ChatSession.date.desc()).all()  # Fetch all chat sessions
    session_data = [
        {
            'id': session.id,
            'title': session.title,
            'description': session.description,
            'date': session.date.strftime('%Y-%m-%d %H:%M:%S')
        }
        for session in sessions
    ]
    return jsonify(session_data)

@app.route('/chat-session/view/<int:session_id>', methods=['GET'])
@login_required
def view_chat_session(session_id):
    session = ChatSession.query.get_or_404(session_id)
    messages = ChatMessage.query.filter_by(session_id=session_id).order_by(ChatMessage.timestamp).all()

    return render_template(
        'view_chat.html',
        title=session.title,
        description=session.description,
        messages=[
            {
                'message': msg.message,
                'is_user': msg.is_user,
                'timestamp': msg.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for msg in messages
        ]
    )

@app.route('/upload-file', methods=['POST'])
@login_required
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part in the request'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            text_content = extract_text_from_file(filepath)
            if not text_content:
                return jsonify({'error': 'Failed to extract text from the file'}), 400

            # Summarize the content
            summary_prompt = f"Summarize the following text:\n{text_content}\n\nSummary:"
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "user", "content": summary_prompt}
                ]
            )
            summary = response['choices'][0]['message']['content']

            # Save to database
            new_file_summary = FileSummary(
                file_name=filename,
                summary=summary,
                user_id=current_user.id
            )
            db.session.add(new_file_summary)
            db.session.commit()

            return jsonify({'summary': summary})
        except Exception as e:
            logging.error(f"Error processing file: {e}")
            return jsonify({'error': 'Failed to process the file.'}), 500
    else:
        return jsonify({'error': 'Invalid file type. Allowed types are txt, pdf, docx.'}), 400

@app.route('/summarize-code', methods=['POST'])
@login_required
def summarize_code():
    try:
        data = request.get_json()
        code_block = data.get('code')

        if not code_block:
            return jsonify({'error': 'Code block is required.'}), 400

        # Summarize and explain the code
        prompt = f"Explain this code:\n{code_block}\n\nExplanation:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        explanation = response['choices'][0]['message']['content']

        # Save to database
        new_code_analysis = CodeAnalysis(
            code=code_block,
            explanation=explanation,
            user_id=current_user.id
        )
        db.session.add(new_code_analysis)
        db.session.commit()

        return jsonify({'explanation': explanation})
    except Exception as e:
        logging.error(f"Error summarizing code: {e}")
        return jsonify({'error': 'Failed to summarize the code.'}), 500

    
@app.route('/analyze-image', methods=['POST'])
@login_required
def analyze_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image uploaded.'}), 400

    image = request.files['image']
    if image.filename == '':
        return jsonify({'error': 'No file selected.'}), 400

    try:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(image.filename))
        image.save(filepath)

        extracted_text = pytesseract.image_to_string(image.open(filepath))

        # Generate analysis
        prompt = f"Analyze this extracted text:\n{extracted_text}\n\nAnalysis:"
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        analysis = response['choices'][0]['message']['content']

        # Save to database
        new_image_analysis = ImageAnalysis(
            image_path=filepath,
            extracted_text=extracted_text,
            analysis=analysis,
            user_id=current_user.id
        )
        db.session.add(new_image_analysis)
        db.session.commit()

        return jsonify({'analysis': analysis})
    except Exception as e:
        logging.error(f"Error analyzing image: {e}")
        return jsonify({'error': 'Failed to analyze the image.'}), 500



if __name__ == '__main__':
    app.run(debug=True)