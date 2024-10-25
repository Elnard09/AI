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
    } else if (currentPath.includes('/history')) {
        displayChatHistory();
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
    responseElement.className = 'ai-message';
    
    const formattedText = smartFormatResponse(responseText, false);
    responseElement.innerHTML = formattedText
        .split('\n')
        .filter(line => line.trim() !== '')
        .join('<br>');
    
    // Add basic styling
    responseElement.style.whiteSpace = 'pre-wrap';
    responseElement.style.wordBreak = 'break-word';
    responseElement.style.lineHeight = '1.5';
    
    chatWindow.appendChild(responseElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

// Improve the formatting and structure of AI responses to make it more context-aware and visually pleasing
function smartFormatResponse(text, isUserMessage = false) {
    if (isUserMessage) {
        return text.trim();
    }

    // Content type patterns
    const patterns = {
        tableOfContents: /^(Table of Contents|TOC):/im,
        levelHeaders: /^(Level \d|Basic TOC|Detailed TOC|Expanded|Summary)/im,
        bulletList: /^[-•*]/m,
        numberedList: /^\d+[\.)]/m,
        keyPoints: /^(Key (Points|Tips|Takeaways)|Main Points):/im,
        stepByStep: /^(Step \d|Steps to|How to|Instructions):/im,
        definition: /^(Definition|What is|Meaning):/im,
        comparison: /^(Comparison|Versus|Differences between):/im,
        summary: /^(Summary|Overview|Conclusion):/im,
        question: /^Q:|^Question:/im,
        answer: /^A:|^Answer:/im
    };

    // Detect content type
    let contentType = 'general';
    if (patterns.tableOfContents.test(text) || patterns.levelHeaders.test(text)) {
        contentType = 'tableOfContents';
    } else if (patterns.stepByStep.test(text)) {
        contentType = 'stepByStep';
    } else if (patterns.keyPoints.test(text)) {
        contentType = 'keyPoints';
    } else if (patterns.comparison.test(text)) {
        contentType = 'comparison';
    } else if (patterns.question.test(text) && patterns.answer.test(text)) {
        contentType = 'qAndA';
    } else if (patterns.bulletList.test(text)) {
        contentType = 'bulletList';
    } else if (patterns.numberedList.test(text)) {
        contentType = 'numberedList';
    }

    // Format based on content type
    let formattedText = text;

    switch (contentType) {
        case 'tableOfContents':
            formattedText = text
                // Format headers and levels
                .replace(/^(#{1,3}|Level \d|Table of Contents|TOC|Basic TOC|Detailed TOC|Expanded|Summary)/gim, '\n\n$1')
                // Format numbered items
                .replace(/^(\d+[\.)]\s*)(.*?)$/gm, '$1$2')
                // Format bullet points with indentation
                .replace(/^([-•*]\s*)(.*?)$/gm, '    $1$2')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        case 'stepByStep':
            formattedText = text
                // Format step headers
                .replace(/^(Step \d|Steps to|How to|Instructions):/im, '\n$1:\n')
                // Format numbered steps
                .replace(/^(\d+[\.)]\s*)(.*?)$/gm, '\n$1 $2')
                // Format substeps or bullet points
                .replace(/^([-•*]\s*)(.*?)$/gm, '    $1 $2')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        case 'bulletList':
        case 'keyPoints':
            formattedText = text
                // Format section headers
                .replace(/^(Key (Points|Tips|Takeaways)|Main Points):/im, '$1:\n')
                // Format bullet points with consistent spacing
                .replace(/^([-•*]\s*)(.*?)$/gm, '\n$1 $2')
                // Format nested bullet points
                .replace(/^\s*([-•*])\s*([^-•*].*?)$/gm, '  $1 $2')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        case 'numberedList':
            formattedText = text
                // Format numbered items with consistent spacing
                .replace(/^(\d+[\.)]\s*)(.*?)$/gm, '\n$1 $2')
                // Format sub-items with indentation
                .replace(/^(\s+\d+[\.)]\s*)(.*?)$/gm, '    $1 $2')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        case 'comparison':
            formattedText = text
                // Format comparison headers
                .replace(/^(Comparison|Versus|Differences between):/im, '$1:\n')
                // Format comparison points
                .replace(/^([-•*]\s*)(.*?)$/gm, '\n$1 $2')
                // Add line breaks for versus comparisons
                .replace(/vs\./gi, 'vs.\n')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        case 'qAndA':
            formattedText = text
                // Format questions with spacing
                .replace(/^Q:|^Question:/gim, '\nQ:')
                // Format answers with spacing
                .replace(/^A:|^Answer:/gim, '\nA:')
                // Clean up spacing
                .replace(/\n{3,}/g, '\n\n')
                .trim();
            break;

        default:
            // For general content, preserve natural paragraph breaks
            formattedText = text
                .split(/\n\s*\n/)
                .map(paragraph => paragraph
                    .replace(/\s+/g, ' ')
                    .trim()
                )
                .filter(paragraph => paragraph.length > 0)
                .join('\n\n');
    }

    // Apply consistent spacing for all types
    formattedText = formattedText
        .replace(/\s+$/gm, '')           // Remove trailing spaces
        .replace(/^\s+/gm, '')           // Remove leading spaces
        .replace(/\n{3,}/g, '\n\n')      // Normalize multiple line breaks
        .trim();

    // Add consistent paragraph spacing for readability
    if (contentType === 'general') {
        formattedText = formattedText
            .replace(/([.!?])\s+(?=[A-Z])/g, '$1\n')  // Split sentences on punctuation
            .replace(/\n{3,}/g, '\n\n');              // Clean up excessive line breaks
    }

    return formattedText;
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


// Function to display chat history
function displayChatHistory() {
    const chatHistoryContainer = document.getElementById('chat-history');
    const noDataMessage = document.getElementById('no-data-message');
    const sessions = JSON.parse(localStorage.getItem('chatSessions')) || [];

    if (sessions.length === 0) {
        noDataMessage.style.display = 'block';
    } else {
        sessions.forEach(session => {
            const row = document.createElement('tr');
            row.innerHTML = `
                <td>${session.date}</td>
                <td>${session.message}</td>
                <td>${session.response}</td>
                <td>
                    <button type="button" class="action-button" onclick="reinteractSession('${session.date}')">
                        <span class="material-symbols-outlined">chat</span>
                    </button>
                    <button type="button" class="action-button" onclick="deleteSession('${session.date}')">
                        <span class="material-symbols-outlined">delete</span>
                    </button>
                </td>
            `;
            chatHistoryContainer.appendChild(row);
        });
    }
}

// Function to save session data
function saveSession(date, message, response) {
    let sessions = JSON.parse(localStorage.getItem('chatSessions')) || [];
    sessions.push({ date, message, response });
    localStorage.setItem('chatSessions', JSON.stringify(sessions));
}

// Function to delete a session
function deleteSession(date) {
    let sessions = JSON.parse(localStorage.getItem('chatSessions')) || [];
    sessions = sessions.filter(session => session.date !== date);
    localStorage.setItem('chatSessions', JSON.stringify(sessions));
    window.location.reload(); // Reload the page to update the table
}

// Function to re-interact with a session
function reinteractSession(date) {
    const sessions = JSON.parse(localStorage.getItem('chatSessions')) || [];
    const sessionToInteract = sessions.find(session => session.date === date);
    if (sessionToInteract) {
        // Redirect to chatAI.html with session data, e.g., using URL parameters
        localStorage.setItem('currentSession', JSON.stringify(sessionToInteract));
        window.location.href = '/chatAI.html';
    }
}

// Call initialize function on page load
initializePage();
