document.getElementById('toggle-btn').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');

    sidebar.classList.toggle('collapsed');

    if (sidebar.classList.contains('collapsed')) {
        toggleBtn.style.right = '5px'; // Adjust button position when collapsed
    } else {
        toggleBtn.style.right = '20px'; // Adjust button position when expanded
    }
});

// Redirect to New Chat Page when clicked
document.getElementById('new-chat-for-logo').addEventListener('click', function() {
    window.location.href = '/project/main.html';
});

document.getElementById('new-chat-page').addEventListener('click', function() {
    window.location.href = '/project/main.html';
});

// Redirect to different HTML files based on nav item clicked
document.getElementById('nav-summarizer').addEventListener('click', function() {
    window.location.href = '/project/NavPages/summarizer.html';
});

document.getElementById('nav-files').addEventListener('click', function() {
    window.location.href = '/project/NavPages/files.html';
});

document.getElementById('nav-history').addEventListener('click', function() {
    window.location.href = '/project/NavPages/history.html';
});

document.getElementById('nav-help').addEventListener('click', function() {
    window.location.href = '/project/NavPages/help.html';
});

document.getElementById('user-profile').addEventListener('click', function() {
    window.location.href = '/project/NavPages/profile.html';
});


// for AI CHAT DEV
document.getElementById('submit-btn').addEventListener('click', function() {
    const userInput = document.getElementById('user-input').value;
    const chatWindow = document.getElementById('chat-window');
    const initialContent = document.getElementById('initial-content');
    const chatInputSection = document.getElementById('chat-input-section');

    // Check if input is not empty
    if (userInput.trim()) {
        // Hide initial content and show chat window + chat input
        initialContent.style.display = 'none';
        chatWindow.style.display = 'flex';
        chatInputSection.style.display = 'flex';

        // Add user message to chat window
        addMessageToChat(userInput, 'user');

        // Clear the input field
        document.getElementById('user-input').value = '';
    }
});

// Function to handle continuous messaging
document.getElementById('chat-submit-btn').addEventListener('click', function() {
    const chatInput = document.getElementById('chat-input').value;

    // Check if input is not empty
    if (chatInput.trim()) {
        // Add user message to chat window
        addMessageToChat(chatInput, 'user');

        // Clear the input field
        document.getElementById('chat-input').value = '';

        // Simulate AI response
        setTimeout(function() {
            addMessageToChat("AI: This is a simulated response.", 'ai');
        }, 1000); // Simulated delay for AI response
    }
});

// Reusable function to add messages to the chat window
function addMessageToChat(message, sender) {
    const chatWindow = document.getElementById('chat-window');
    const messageDiv = document.createElement('div');
    messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
    messageDiv.innerText = message;
    chatWindow.appendChild(messageDiv);

    // Scroll to the bottom of the chat window
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

document.getElementById('chat-input').addEventListener('keypress', function(e) {
    if (e.key === 'Enter') {
        document.getElementById('chat-submit-btn').click();
    }
});


