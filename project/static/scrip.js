// Common sidebar functionality for all pages
document.getElementById('toggle-btn').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');

    sidebar.classList.toggle('collapsed');

    if (sidebar.classList.contains('collapsed')) {
        toggleBtn.style.right = '5px';
    } else {
        toggleBtn.style.right = '20px';
    }
});

// Add event listeners for summarizer navigation
const summarizerIds = ['nav-summarizer', 'summarizer-btn'];
summarizerIds.forEach(function(id) {
    const element = document.getElementById(id);
    if (element) {
        element.addEventListener('click', function() {
            window.location.href = '/summarizer';
        });
    }
});

// Add event listeners for files navigation
const filesIds = ['nav-files', 'file-btn'];
filesIds.forEach(function(id) {
    const element = document.getElementById(id);
    if (element) {
        element.addEventListener('click', function() {
            window.location.href = '/files';
        });
    }
});

// Add event listeners for history navigation
const historyIds = ['nav-history', 'history-btn'];
historyIds.forEach(function(id) {
    const element = document.getElementById(id);
    if (element) {
        element.addEventListener('click', function() {
            window.location.href = '/history';
        });
    }
});

document.getElementById('nav-help').addEventListener('click', function() {
    window.location.href = '/help';
});

document.getElementById('user-profile').addEventListener('click', function() {
    window.location.href = '/profile';
});

// Function to validate YouTube URL
function isValidYoutubeUrl(url) {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
    return youtubeRegex.test(url);
}

// Function to show error message
function showError(message) {
    let popup = document.getElementById('error-message');
    if (!popup) {
        popup = document.createElement('div');
        popup.id = 'error-message';
        popup.style.position = 'fixed';
        popup.style.top = '50%';
        popup.style.left = '50%';
        popup.style.transform = 'translate(-50%, -50%)';
        popup.style.padding = '20px';
        popup.style.backgroundColor = 'rgba(255, 0, 0, 0.8)';
        popup.style.color = 'white';
        popup.style.borderRadius = '5px';
        popup.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.5)';
        popup.style.zIndex = '1000';

        document.body.appendChild(popup);
    }

    popup.style.display = 'block';
    popup.textContent = message;

    setTimeout(() => {
        popup.style.display = 'none';
    }, 3000);
}

// Function to check which page we're on and initialize accordingly
function initializePage() {
    const currentPath = window.location.pathname;
    const submitBtn = document.getElementById('submit-chat-ai-button');
    const userInput = document.getElementById('user-chat-ai-input');

    if (submitBtn && userInput) {
        submitBtn.addEventListener('click', function() {
            const inputText = userInput.value.trim();
            
            if (currentPath.includes('/summarizer')) {
                if (!inputText) {
                    showError('Please enter a YouTube URL');
                    return;
                }
                if (!isValidYoutubeUrl(inputText)) {
                    showError('Please enter a valid YouTube URL');
                    return;
                }
                summarizeVideo(inputText);
            } else {
                if (inputText) {
                    sessionStorage.setItem('initialMessage', inputText);
                    sessionStorage.setItem('sourcePage', currentPath);
                    window.location.href = "/chatAI";
                }
            }
        });

        userInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        });
    }

    if (currentPath.includes('/chatAI')) {
        initializeChatAI();
    }
}

function summarizeVideo(youtubeUrl) {
    const submitBtn = document.getElementById('submit-chat-ai-button');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-message';
    loadingDiv.innerHTML = 'Processing video... This may take a few minutes.';
    loadingDiv.style.color = 'white';
    loadingDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    loadingDiv.style.padding = '20px';
    loadingDiv.style.position = 'fixed';
    loadingDiv.style.top = '50%';
    loadingDiv.style.left = '50%';
    loadingDiv.style.transform = 'translate(-50%, -50%)';
    loadingDiv.style.borderRadius = '5px';
    document.body.appendChild(loadingDiv);
    
    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';
    
    fetch('/process_youtube_link', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ youtube_url: youtubeUrl }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        // Store the YouTube link in session storage for later use
        sessionStorage.setItem('youtubeLink', youtubeUrl);
        // Redirect to chat interface after successful processing
        window.location.href = '/chatAI';
    })
    .catch(error => {
        showError(error.message || 'An error occurred. Please try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = '➔';
    })
    .finally(() => {
        if (document.getElementById('loading-message')) {
            document.getElementById('loading-message').remove();
        }
    });
}

// Function to ask a question and get AI response
function askQuestion(question, youtubeUrl) {
    const submitBtn = document.getElementById('chat-submit-btn');
    const loadingDiv = document.createElement('div');
    loadingDiv.id = 'loading-message';
    loadingDiv.innerHTML = 'Processing your question... Please wait.';
    loadingDiv.style.color = 'white';
    loadingDiv.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
    loadingDiv.style.padding = '20px';
    loadingDiv.style.position = 'fixed';
    loadingDiv.style.top = '50%';
    loadingDiv.style.left = '50%';
    loadingDiv.style.transform = 'translate(-50%, -50%)';
    loadingDiv.style.borderRadius = '5px';
    document.body.appendChild(loadingDiv);

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    fetch('/ask_question', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            youtube_url: youtubeUrl,
            question: question,
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }
        // Display the AI's response
        displayAIResponse(data.response);
    })
    .catch(error => {
        showError(error.message || 'An error occurred. Please try again.');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Ask';
        if (document.getElementById('loading-message')) {
            document.getElementById('loading-message').remove();
        }
    });
}

// Function to display user message in chat
function displayUserMessage(messageText) {
    const chatWindow = document.getElementById('chat-window');
    const userMessageElement = document.createElement('div');
    userMessageElement.className = 'user-message'; // CSS class for user message
    userMessageElement.textContent = messageText;
    chatWindow.appendChild(userMessageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to bottom
}

// Function to display AI response in chat
function displayAIResponse(responseText) {
    const chatWindow = document.getElementById('chat-window');
    const responseElement = document.createElement('div');
    responseElement.className = 'ai-message'; // CSS class for AI response
    responseElement.textContent = responseText;
    chatWindow.appendChild(responseElement);
    chatWindow.scrollTop = chatWindow.scrollHeight; // Scroll to bottom
}

// Function to handle chat and questions
function initializeChatAI() {
    const chatWindow = document.getElementById('chat-window');
    const chatInputSection = document.getElementById('chat-input-section');
    const submitBtn = document.getElementById('chat-submit-btn');
    const inputField = document.getElementById('chat-input');

    chatWindow.style.display = 'block';
    chatInputSection.style.display = 'flex';

    submitBtn.addEventListener('click', function() {
        const question = inputField.value.trim();
        if (!question) {
            // showError('Please enter a question');
            return;
        }

        const youtubeLink = sessionStorage.getItem('youtubeLink');
        if (!youtubeLink) {
            showError('No YouTube link found.');
            return;
        }

        // Display the user message
        displayUserMessage(question);
        
        // Ask the question
        askQuestion(question, youtubeLink);

        // Clear the input field
        inputField.value = '';
    });

    inputField.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            submitBtn.click();
        }
    });
}

// Initialize the page based on the current view
window.onload = function() {
    initializeChatAI();
};

// Call initialize function on page load
initializePage();
