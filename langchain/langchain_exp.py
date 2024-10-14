import os
from dotenv import load_dotenv
from flask import Flask, render_template, request
from langchain.chat_models import ChatOpenAI
from langchain import LLMChain
from langchain.prompts import PromptTemplate

# Load environment variables from the .env file
load_dotenv()

# Initialize Flask app
app = Flask(__name__)

# Retrieve the OpenAI API key from the environment
api_key = os.getenv("OPENAI_API_KEY")

# Initialize the OpenAI chat model with the API key
llm = ChatOpenAI(model="gpt-3.5-turbo", api_key=api_key, temperature=0.7)

# Define the prompt template
template = """
You are a helpful assistant. Use the following text to answer the question.

Text:
{text}

Question: {question}
Answer:
"""

# Create a prompt object
prompt = PromptTemplate(input_variables=["text", "question"], template=template)

# Create the chain (combining the LLM and the prompt template)
chain = LLMChain(llm=llm, prompt=prompt)

# Sample text to work with
sample_text = """
LangChain is a framework for developing applications powered by language models.
It helps manage prompts, chains of LLMs, and various workflows involving NLP tasks.
"""

# Flask route for the homepage
@app.route('/', methods=['GET', 'POST'])
def index():
    answer = None
    if request.method == 'POST':
        # Get the user question from the form
        user_question = request.form['question']

        # Get the answer from the chain using the user's question
        answer = chain.run({"text": sample_text, "question": user_question})

    # Render the template, passing in the answer (if available)
    return render_template('index.html', answer=answer)

# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)
