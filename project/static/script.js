$(document).ready(function () {
    // Sidebar toggle functionality
    $('#toggle-btn').on('click', function () {
        const sidebar = $('#sidebar');
        const toggleBtn = $('#toggle-btn');

        sidebar.toggleClass('collapsed');

        if (sidebar.hasClass('collapsed')) {
            toggleBtn.css('right', '5px');
        } else {
            toggleBtn.css('right', '20px');
        }
    });

    // Event listeners for navigation to Summarizer
    const summarizerIds = ['#nav-summarizer', '#summarizer-btn'];
    summarizerIds.forEach(function (id) {
        $(id).on('click', function () {
            window.location.href = '/summarizer';
        });
    });

    // Event listeners for navigation to Files
    const filesIds = ['#nav-files', '#file-btn'];
    filesIds.forEach(function (id) {
        $(id).on('click', function () {
            window.location.href = '/files';
        });
    });

    // Event listeners for navigation to History
    const historyIds = ['#nav-history', '#history-btn'];
    historyIds.forEach(function (id) {
        $(id).on('click', function () {
            window.location.href = '/history';
        });
    });

    // Navigation for Help page
    $('#nav-help').on('click', function () {
        window.location.href = '/help';
    });

    // Navigation for User Profile
    $('#user-profile').on('click', function () {
        window.location.href = '/profile';
    });

    // Function to validate YouTube URL
    function isValidYoutubeUrl(url) {
        const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com|youtu\.be)\/.+/;
        return youtubeRegex.test(url);
    }

    // Function to show error message
    function showError(message) {
        let popup = $('#error-message');

        if (!popup.length) {
            popup = $('<div></div>', {
                id: 'error-message',
                css: {
                    position: 'fixed',
                    top: '50%',
                    left: '50%',
                    transform: 'translate(-50%, -50%)',
                    padding: '20px',
                    backgroundColor: 'rgba(255, 0, 0, 0.8)',
                    color: 'white',
                    borderRadius: '5px',
                    boxShadow: '0 0 10px rgba(0, 0, 0, 0.5)',
                    zIndex: 1000,
                },
            }).appendTo('body');
        }

        popup.text(message).show();

        setTimeout(function () {
            popup.hide();
        }, 3000);
    }

    // Function to check which page we're on and initialize accordingly
    function initializePage() {
        const currentPath = window.location.pathname;
        const submitBtn = $('#submit-chat-ai-button');
        const userInput = $('#user-chat-ai-input');

        if (submitBtn.length && userInput.length) {
            submitBtn.on('click', function () {
                const inputText = userInput.val().trim();

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

            userInput.on('keypress', function (e) {
                if (e.key === 'Enter') {
                    submitBtn.click();
                }
            });
        }

        if (currentPath.includes('/chatAI')) {
            initializeChatAI();
        }
    }

    // Function to process the video and navigate to the chat interface
    function summarizeVideo(youtubeUrl) {
        const submitBtn = $('#submit-chat-ai-button');
        const loadingDiv = $('<div></div>', {
            id: 'loading-message',
            text: 'Processing video... This may take a few minutes.',
            css: {
                color: 'white',
                backgroundColor: 'rgba(0, 0, 0, 0.7)',
                padding: '20px',
                position: 'fixed',
                top: '50%',
                left: '50%',
                transform: 'translate(-50%, -50%)',
                borderRadius: '5px',
            },
        }).appendTo('body');

        submitBtn.prop('disabled', true).text('Processing...');

        $.ajax({
            url: '/process_video',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ youtube_url: youtubeUrl }),
            success: function (data) {
                if (data.error) {
                    throw new Error(data.error);
                }
                window.location.href = '/chatAI';
            },
            error: function (xhr) {
                showError(xhr.responseText || 'An error occurred. Please try again.');
                submitBtn.prop('disabled', false).text('➔');
            },
            complete: function () {
                $('#loading-message').remove();
            },
        });
    }

    // Function to initialize the Chat AI page
    function initializeChatAI() {
        const chatWindow = $('#chat-window');
        const chatInputSection = $('#chat-input-section');
        const submitBtn = $('#submit-chat-ai-button');
        const userInput = $('#user-chat-ai-input');

        // Handle chat form submission
        submitBtn.on('click', function () {
            const inputText = userInput.val().trim();
            if (inputText) {
                addMessageToChat(inputText, 'User');
                handleChatSubmit(inputText);
            }
        });

        userInput.on('keypress', function (e) {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        });
    }

    // Function to add message to chat window
    function addMessageToChat(message, sender) {
        const chatWindow = $('#chat-window');
        const messageDiv = $('<div></div>', {
            class: `message ${sender.toLowerCase()}`,
            text: message,
        });

        chatWindow.append(messageDiv);
        chatWindow.scrollTop(chatWindow.prop('scrollHeight'));
    }

    // Function to handle chat submission and interact with AI
    function handleChatSubmit(inputText) {
        const submitBtn = $('#submit-chat-ai-button');
        submitBtn.prop('disabled', true);

        $.ajax({
            url: '/chat_with_ai',
            method: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ message: inputText }),
            success: function (response) {
                addMessageToChat(response.reply, 'AI');
            },
            error: function (xhr) {
                addMessageToChat('An error occurred. Please try again.', 'AI');
            },
            complete: function () {
                submitBtn.prop('disabled', false);
            },
        });
    }

    // Initialize the page
    initializePage();
});
