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
    
    fetch('/process_video', {
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
        // Redirect to chat interface after successful processing
        window.location.href = '/chatAI';
    })
    .catch(error => {
        showError(error.message || 'An error occurred. Please make sure ffmpeg is installed and try again.');
        submitBtn.disabled = false;
        submitBtn.textContent = '➔';
    })
    .finally(() => {
        if (document.getElementById('loading-message')) {
            document.getElementById('loading-message').remove();
        }
    });
}

// Function to initialize the Chat AI page
function initializeChatAI() {
    const chatWindow = document.getElementById('chat-window');
    const chatInputSection = document.getElementById('chat-input-section');
    
    chatWindow.style.display = 'flex';
    chatInputSection.style.display = 'flex';
    
    const initialMessage = sessionStorage.getItem('initialMessage');
    const sourcePage = sessionStorage.getItem('sourcePage');
    
    if (initialMessage) {
        let aiResponse;
        if (sourcePage && sourcePage.includes('/summarizer')) {
            addMessageToChat(`YouTube URL: ${initialMessage}`, 'user');
            aiResponse = "I'll analyze this YouTube video for you. What specific information would you like to know about it?";
        } else {
            addMessageToChat(initialMessage, 'user');
            aiResponse = "Thanks for your message! How can I help you further?";
        }
        
        setTimeout(function() {
            addMessageToChat(`AI: ${aiResponse}`, 'ai');
        }, 1000);
        
        sessionStorage.removeItem('initialMessage');
        sessionStorage.removeItem('sourcePage');
    }

    const chatSubmitBtn = document.getElementById('chat-submit-btn');
    const chatInput = document.getElementById('chat-input');

    chatSubmitBtn.addEventListener('click', handleChatSubmit);
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            handleChatSubmit();
        }
    });
}


function addMessageToChat(message, sender) {
    const chatWindow = document.getElementById('chat-window');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
    messageDiv.innerText = message;
    chatWindow.appendChild(messageDiv);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Initialize the page when the DOM is loaded
document.addEventListener('DOMContentLoaded', initializePage);

// New fetch logic for handling the YouTube URL form submission
// New fetch logic for handling the YouTube URL form submission
// document.getElementById('summarizer-form').addEventListener('submit', function(e) {
//     e.preventDefault();  // Prevent default form submission
    
//     const youtubeUrl = document.getElementById('user-chat-ai-input').value;
//     const submitBtn = document.getElementById('submit-chat-ai-button');
    
//     submitBtn.disabled = true;
//     submitBtn.textContent = 'Processing...';

//     fetch('/process_video', {  // Make sure this route matches your Flask route
//         method: 'POST',
//         headers: {
//             'Content-Type': 'application/json',  // Ensure content-type is JSON
//         },
//         body: JSON.stringify({ youtube_url: youtubeUrl }),  // Send JSON data
//     })
//     .then(response => response.json())
//     .then(data => {
//         if (data.error) {
//             throw new Error(data.error);
//         }
//         window.location.href = '/chatAI';  // Redirect to the chat page
//     })
//     .catch(error => {
//         alert('Error: ' + error.message);
//     })
//     .finally(() => {
//         submitBtn.disabled = false;
//         submitBtn.textContent = '➔';
//     });
// });

// Function to handle chat submission
function handleChatSubmit() {
    const chatInput = document.getElementById('chat-input');
    const message = chatInput.value.trim();
    
    if (message) {
        addMessageToChat(message, 'user');
        chatInput.value = '';
        
        // Send the question to the backend
        fetch('/chat_response', {  // Match this route to your Flask route
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ question: message }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            addMessageToChat(data.response, 'ai');
        })
        .catch(error => {
            addMessageToChat("Error: " + error.message, 'ai');
        });
    }
}
