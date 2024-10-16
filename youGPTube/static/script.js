// Common sidebar functionality for all pages
document.addEventListener('DOMContentLoaded', function() {
    const toggleBtn = document.getElementById('toggle-btn');
    if (toggleBtn) {
        toggleBtn.addEventListener('click', function() {
            const sidebar = document.getElementById('sidebar');
            if (sidebar) {
                sidebar.classList.toggle('collapsed');
                toggleBtn.style.right = sidebar.classList.contains('collapsed') ? '5px' : '20px';
            }
        });
    }

    // Navigation event listeners for all pages
    const navButtons = [
        { id: 'new-chat-for-logo', url: '/main' },
        { id: 'new-chat-page', url: '/main' },
        { id: 'nav-summarizer', url: '/summarizer' },
        { id: 'nav-files', url: '/files' },
        { id: 'nav-history', url: '/history' },
        { id: 'nav-help', url: '/help' },
        { id: 'user-profile', url: '/profile' }
    ];

    navButtons.forEach(button => {
        const element = document.getElementById(button.id);
        if (element) {
            element.addEventListener('click', function() {
                window.location.href = button.url;
            });
        }
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
                    summarizeVideo(inputText); // Call the summarize function directly
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

    // Function to summarize video and get AI response
    function summarizeVideo(youtubeUrl) {
        const submitBtn = document.getElementById('submit-chat-ai-button');
        const results = document.getElementById('results');
        const summaryElement = document.getElementById('summary');
        const transcriptElement = document.getElementById('transcript');
    
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.textContent = 'Processing...';
        }
    
        fetch('/summarize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ youtube_url: youtubeUrl }),
        })
        .then(response => response.json())
        .then(data => {
            console.log('API Response:', data);  // Debugging line
            if (data.error) {
                throw new Error(data.error);
            }
    
            // Set text content if elements exist
            if (summaryElement && transcriptElement) {
                summaryElement.textContent = data.summary;  // Set the summary text
                transcriptElement.textContent = JSON.stringify(data.transcript, null, 2);  // Set the transcript text
                results.style.display = 'block';  // Make the results section visible
            } else {
                console.error("Summary or Transcript element is null.");
            }
        })
        .catch(error => {
            showError('Error: ' + error.message);
        })
        .finally(() => {
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.textContent = '➔';
            }
        });
    }
    
    // Initialize the Chat AI page
    function initializeChatAI() {
        const chatWindow = document.getElementById('chat-window');
        const chatInputSection = document.getElementById('chat-input-section');

        if (chatWindow && chatInputSection) {
            chatWindow.style.display = 'flex';
            chatInputSection.style.display = 'flex';
        }

        const initialMessage = sessionStorage.getItem('initialMessage');
        const sourcePage = sessionStorage.getItem('sourcePage');

        if (initialMessage) {
            addMessageToChat(`YouTube URL: ${initialMessage}`, 'user');
            const aiResponse = "I'll analyze this YouTube video for you. What specific information would you like to know about it?";
            setTimeout(function() {
                addMessageToChat(`AI: ${aiResponse}`, 'ai');
            }, 1000);

            sessionStorage.removeItem('initialMessage');
            sessionStorage.removeItem('sourcePage');
        }

        const chatSubmitBtn = document.getElementById('chat-submit-btn');
        const chatInput = document.getElementById('chat-input');

        if (chatSubmitBtn && chatInput) {
            chatSubmitBtn.addEventListener('click', handleChatSubmit);
            chatInput.addEventListener('keypress', function(e) {
                if (e.key === 'Enter') {
                    handleChatSubmit();
                }
            });
        }
    }

    function handleChatSubmit() {
        const chatInput = document.getElementById('chat-input');
        const message = chatInput.value.trim();

        if (message) {
            addMessageToChat(message, 'user');
            chatInput.value = '';

            // Simulate AI response (or you can implement actual AI response logic)
            setTimeout(function() {
                addMessageToChat("AI: This is a simulated response to your message.", 'ai');
            }, 1000);
        }
    }

    function addMessageToChat(message, sender) {
        const chatWindow = document.getElementById('chat-window');
        if (chatWindow) {
            const messageDiv = document.createElement('div');
            messageDiv.classList.add('message', sender === 'user' ? 'user-message' : 'ai-message');
            messageDiv.innerText = message;
            chatWindow.appendChild(messageDiv);
            chatWindow.scrollTop = chatWindow.scrollHeight;
        }
    }

    // Initialize the page when the DOM is loaded
    initializePage();
});
