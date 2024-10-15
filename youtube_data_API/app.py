import os
import re
import logging
from flask import Flask, render_template, request, jsonify, url_for, flash, redirect
import openai
from googleapiclient.discovery import build
from dotenv import load_dotenv
import sqlite3

# Load environment variables from the .env file
load_dotenv()

API_KEY = os.getenv('YOUTUBE_API_KEY')

if not API_KEY:
    raise ValueError("API key not found. Kindly set it in the .env file")

# Initialize the Flask app
app = Flask(__name__)

# Function to extract video ID from a YouTube URL
def extract_video_id(url):
    # Regex pattern to capture the video ID from standard YouTube URLs
    pattern = r'(?:v=|\/)([0-9A-Za-z_-]{11}).*'
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    else:
        raise ValueError("Invalid YouTube URL")
    
def insert_conversation(username, messages):
    # Connect to the database
    conn = sqlite3.connect('ai_conversations.db')
    cursor = conn.cursor()

    # Insert the user
    cursor.execute('INSERT INTO Users (username) VALUES (?)', (username,))
    user_id = cursor.lastrowid  # Get the user ID of the newly created user

    # Start a new conversation
    cursor.execute('INSERT INTO Conversations (user_id) VALUES (?)', (user_id,))
    conversation_id = cursor.lastrowid  # Get the conversation ID

    # Insert messages
    for message in messages:
        cursor.execute('INSERT INTO Messages (conversation_id, message_text) VALUES (?, ?)', (conversation_id, message))

    # Commit the changes and close the connection
    conn.commit()
    conn.close()
    print("Conversation inserted successfully!")


# Route for the homepage
@app.route('/')
def index():
    return render_template('index.html')

# Route for handling the form submission
@app.route('/get_video_info', methods=['POST'])
def get_video_info():
    youtube_url = request.form.get('youtube_url')
    
    # Extract the video ID
    try:
        video_id = extract_video_id(youtube_url)
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    
    # Build the YouTube Data API client
    youtube = build('youtube', 'v3', developerKey=API_KEY)
    
    try:
        # Fetch video details
        api_request = youtube.videos().list(
            part='snippet,contentDetails,statistics',
            id=video_id
        )
        response = api_request.execute()
    except Exception as e:
        # Log the detailed error and return a message to the frontend
        print(f"Error fetching video details: {e}")
        return jsonify({"error": f"Failed to fetch video details: {str(e)}"}), 500
    
    # Return video details as JSON if the request succeeds
    return jsonify(response)

@app.route("/ask_question", methods=["POST"])
def ask_question():
    question = request.form.get("question")
    summary = request.form.get("summary")

    system_prompt = "You are a helpful assistant. Use the following summary to answer the question."
    user_prompt = f"Summary: {summary}\n\nQuestion: {question}"

    messages = [question]

    try:
        # Call OpenAI API
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]
        )
        answer = response["choices"][0]["message"]["content"]

        # Append AI's response to the messages
        messages.append(answer)

        # Save the conversation into the database
        insert_conversation("User", messages)  # Ensure correct username

        # Render the result page with AI's answer
        return render_template("result.html", long_summary=summary, short_summary=summary, answer=answer)

    except Exception as e:
        logging.error(f"Error processing the question: {str(e)}", exc_info=True)
        flash(f"An error occurred while processing the question: {str(e)}", "error")
        return redirect(url_for('index'))

    except Exception as e:
        logging.error(f"Error processing the question: {str(e)}", exc_info=True)
        flash(f"An error occurred while processing the question: {str(e)}", "error")
        # Change 'home' to 'index' here
        return redirect(url_for('index'))

@app.route("/history")
def history():
    # Connect to the database and retrieve messages
    connection = sqlite3.connect('chat_history.db')
    cursor = connection.cursor()

    # Fetch all messages from the history table
    cursor.execute("SELECT timestamp, user_input, ai_response FROM messages ORDER BY timestamp DESC")
    messages = cursor.fetchall()

    # Close the database connection
    connection.close()

    # Convert the fetched messages into a list of dictionaries
    messages_list = [{"timestamp": msg[0], "user_input": msg[1], "ai_response": msg[2]} for msg in messages]

    # Render the history.html template with the messages
    return render_template("history.html", messages=messages_list)

if __name__ == '__main__':
    app.run(debug=True)
