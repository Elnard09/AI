// ===============================
// Initialization Functions
// ===============================

// Wait for DOM to be fully loaded before initializing
document.addEventListener("DOMContentLoaded", function() {
    initializePage();
    initializeModalFunctionality();
    initializeFlashMessages();
    initializeSidebarFunctionality();
    initializeNavigationListeners();
    initializeNicknameUpdate();
    initializePasswordUpdate();
    initializeFileUpload(); // File summarizer
    handleCodeAnalyzer();   // Code analyzer
    handleImageAnalyzer();  // Image analyzer
    initializeVideoSummarizer(); // Video summarizer
    initializeChatAI();     // For ChatAI interactions
});

function initializePage() {
    const currentPath = window.location.pathname;
    const submitBtn = document.getElementById('submit-chat-ai-button');
    const userInput = document.getElementById('user-chat-ai-input');
    const sidebar = document.getElementById('sidebar');

    if (!sidebar) {
        initializeSidebarFunctionality();
    }

    if (submitBtn && userInput) {
        submitBtn.addEventListener('click', function () {
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
            } else if (currentPath.includes('/chatAI')) {
                if (inputText) {
                    sessionStorage.setItem('initialMessage', inputText);
                    sessionStorage.setItem('sourcePage', currentPath);
                    window.location.href = "/chatAI";
                }
            }
        });

        userInput.addEventListener('keypress', function (e) {
            if (e.key === 'Enter') {
                submitBtn.click();
            }
        });
    }

    if (currentPath.includes('/chatAI')) {
        const chatWindow = document.getElementById("chat-window");
        const fileSummary = sessionStorage.getItem("fileSummary");
        const aiMessage = sessionStorage.getItem("aiMessage");

        // Display file summary if available
        if (fileSummary) {
            displayAIResponse(`Summary of your uploaded document:\n\n${fileSummary}`);
            sessionStorage.removeItem("fileSummary"); // Clear after use
        }

        // Display AI message if available
        if (aiMessage) {
            displayAIResponse(aiMessage);
            sessionStorage.removeItem("aiMessage"); // Clear after use
        }

        initializeChatAI(); // Continue with the chat initialization
    }
}

// ===============================
// UI and Modal Functions
// ===============================

function initializeModalFunctionality() {
    // Nickname modal elements
    const nicknameButton = document.getElementById('edit-nickname-button');
    const nicknameModal = document.getElementById('edit-nickname-modal');
    const closeNicknameModalButton = document.getElementById('close-nickname-modal');

    // Password modal elements
    const passwordButton = document.getElementById('edit-password-button');
    const passwordModal = document.getElementById('edit-password-modal');
    const closePasswordModalButton = document.getElementById('close-password-modal');

    // Nickname Modal Events
    if (nicknameButton && nicknameModal && closeNicknameModalButton) {
        nicknameButton.addEventListener('click', () => {
            nicknameModal.style.display = 'block';
        });

        closeNicknameModalButton.addEventListener('click', () => {
            nicknameModal.style.display = 'none';
        });

        window.addEventListener('click', (event) => {
            if (event.target === nicknameModal) {
                nicknameModal.style.display = 'none';
            }
        });
    }

    // Password Modal Events
    if (passwordButton && passwordModal && closePasswordModalButton) {
        passwordButton.addEventListener('click', () => {
            passwordModal.style.display = 'block';
        });

        closePasswordModalButton.addEventListener('click', () => {
            passwordModal.style.display = 'none';
        });

        window.addEventListener('click', (event) => {
            if (event.target === passwordModal) {
                passwordModal.style.display = 'none';
            }
        });
    }
}

function initializeFlashMessages() {
    const flashMessages = document.querySelectorAll(".flash-message");
    flashMessages.forEach(message => {
        setTimeout(() => message.style.display = "none", 1000);
    });
}

function initializeSidebarFunctionality() {
    const toggleBtn = document.getElementById('toggle-btn');
    const sidebar = document.getElementById('sidebar');
    
    if (toggleBtn && sidebar) {
        toggleBtn.addEventListener('click', function() {
            sidebar.classList.toggle('collapsed');
            toggleBtn.style.right = sidebar.classList.contains('collapsed') ? '5px' : '20px';
        });
    }
}

function initializeNavigationListeners() {
    const navigations = {
        'new-chat-for-logo': '/main',
        'new-chat-page': '/main',
        'tab-summarizer': '/summarizer',
        'tab-history': '/history',
        'nav-summarizer': '/summarizer',
        'summarizer-btn': '/summarizer',
        'nav-files': '/files',
        'file-btn': '/files',
        'nav-history': '/history',
        'history-btn': '/history',
        'nav-help': '/help',
        'user-profile': '/profile'
    };

    Object.keys(navigations).forEach(id => {
        const element = document.getElementById(id);
        if (element) element.addEventListener('click', () => window.location.href = navigations[id]);
    });
}

// ===============================
// Chat Functions
// ===============================

function initializeChatAI() {
    const chatWindow = document.getElementById('chat-window');
    const chatInputSection = document.getElementById('chat-input-section');
    const submitBtn = document.getElementById('chat-submit-btn');
    const inputField = document.getElementById('chat-input');
    
    chatWindow.style.display = 'block';
    chatInputSection.style.display = 'flex';

    const aiMessage = sessionStorage.getItem("aiMessage");

    if (aiMessage) {
        displayAIResponse(aiMessage);
        sessionStorage.removeItem("aiMessage");
    }

    submitBtn.addEventListener('click', () => {
        const question = inputField.value.trim();
        if (!question) return;

        displayUserMessage(question);  // Display user message in the chat window
        inputField.value = '';

        // Send the question to the backend and get the response
        askQuestion(question);
    });

    inputField.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') submitBtn.click();
    });
}

function askQuestion(question) {
    const submitBtn = document.getElementById('chat-submit-btn');
    const loadingDiv = createLoadingMessage("Processing your question... Please wait.");
    document.body.appendChild(loadingDiv);

    submitBtn.disabled = true;
    submitBtn.textContent = 'Processing...';

    const content_type = sessionStorage.getItem('content_type');  // Get content type (file, code, video, etc.)
    const session_id = sessionStorage.getItem('currentSessionId');  // Get session ID from sessionStorage

    fetch('/ask_question', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            question: question,
            content_type: content_type, // Send content type to the backend
            session_id: session_id,  // Send session_id to fetch correct content
        }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.error) {
            throw new Error(data.error);
        }

        displayAIResponse(data.response);  // Display AI response
    })
    .catch(error => {
        console.error('Error:', error);
        showError(error.message || 'An error occurred. Please try again.');
    })
    .finally(() => {
        submitBtn.disabled = false;
        submitBtn.textContent = 'Send';
        if (document.getElementById('loading-message')) {
            document.getElementById('loading-message').remove();
        }
    });
}

function displayUserMessage(messageText) {
    const chatWindow = document.getElementById('chat-window');
    const userMessageElement = document.createElement('div');
    userMessageElement.className = 'user-message';
    userMessageElement.textContent = messageText;
    chatWindow.appendChild(userMessageElement);
    chatWindow.scrollTop = chatWindow.scrollHeight;
}

function displayAIResponse(responseText) {
    const chatWindow = document.getElementById("chat-window");
    const responseElement = document.createElement("div");
    responseElement.className = "ai-message";
    
    const formattedText = responseText
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')  // Convert bold
    .replace(/\*(.*?)\*/g, '<em>$1</em>')  // Convert italic
    .split("\n").join("<br>");  // Add line breaks
    
    responseElement.innerHTML = formattedText;
    
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

// Speech-to-Text functionality
function startSpeechRecognition() {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
        alert("Speech recognition is not supported in your browser.");
        return;
    }

    let currentTranscript = ""; // Holds the cumulative transcript
    let interimTranscript = ""; // Holds the current interim transcript
    let isPaused = false; // Tracks whether recognition is paused

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;

    // Get references to UI elements
    const speechPopup = document.getElementById("speech-popup");
    const speechTranscript = document.getElementById("speech-transcript");
    const speechStatus = document.getElementById("speech-status");
    const pausePlayButton = document.getElementById("pause-play-button");

    // Initialize popup
    speechTranscript.innerHTML = ""; // Clear previous transcript
    speechStatus.textContent = "Listening..."; // Set initial status
    speechPopup.style.display = "block";
    pausePlayButton.style.display = "none"; // Hide Pause/Play initially
    recognition.start();

    recognition.onresult = (event) => {
        interimTranscript = ""; // Reset interim transcript
        for (let i = 0; i < event.results.length; i++) {
            if (event.results[i].isFinal) {
                currentTranscript += event.results[i][0].transcript + " "; // Add final results
            } else {
                interimTranscript += event.results[i][0].transcript; // Update interim results
            }
        }

        // Update the display with current transcript and interim text
        speechTranscript.textContent = currentTranscript + interimTranscript;
        pausePlayButton.style.display = "inline"; // Show Pause/Play button
    };

    recognition.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
        speechStatus.textContent = `Error: ${event.error}`; // Update status dynamically
        closeSpeechPopup();
    };

    recognition.onend = () => {
        if (!isPaused) {
            speechStatus.textContent = "Speech recognition ended."; // Update status
            pausePlayButton.textContent = "Play"; // Change to "Play" after speech ends
            isPaused = true; // Treat as paused after ending
        }
    };

    // Attach event listeners
    pausePlayButton.onclick = () => togglePausePlay();
    document.querySelector(".popup-buttons button:nth-child(1)").onclick = () => clearTranscript();
    document.querySelector(".popup-buttons button:nth-child(3)").onclick = () => submitTranscript();

    function togglePausePlay() {
        if (isPaused) {
            // Resume listening and continue appending results
            recognition.start();
            speechStatus.textContent = "Listening...";
            pausePlayButton.textContent = "Pause";
            isPaused = false;
        } else {
            // Pause listening
            recognition.stop();
            speechStatus.textContent = "Paused";
            pausePlayButton.textContent = "Play";
            isPaused = true;
        }
    }

    function clearTranscript() {
        currentTranscript = ""; // Clear the cumulative transcript
        speechTranscript.textContent = ""; // Clear displayed text
    }

    function submitTranscript() {
        const chatInput = document.getElementById("chat-input");
        chatInput.value = currentTranscript.trim(); // Set the chat input value
        closeSpeechPopup(); // Close the popup
    }
}

function closeSpeechPopup() {
    const speechPopup = document.getElementById("speech-popup");
    speechPopup.style.display = "none";
}

// ===============================
// File Summarizer Functions
// ===============================

function initializeFileUpload() {
    const fileInput = document.getElementById("user-chat-ai-input-file");
    const fileSubmitBtn = document.getElementById("submit-chat-ai-button-file");

    if (fileSubmitBtn && fileInput) {
        fileSubmitBtn.addEventListener("click", async () => {
            const file = fileInput.files[0];
            if (!file) {
                alert("Please select a file to upload.");
                return;
            }

            const formData = new FormData();
            formData.append("file", file);

            const loadingDiv = createLoadingMessage("Analyzing file... This may take a few seconds.");
            document.body.appendChild(loadingDiv);

            try {
                const response = await fetch("/upload-file", {
                    method: "POST",
                    body: formData,
                });

                const data = await response.json();

                if (response.ok) {
                    // Store content type and AI message in sessionStorage
                    sessionStorage.setItem('currentSessionId', data.session_id); // Store session_id in sessionStorage
                    sessionStorage.setItem('content_type', 'file');  // Set content type (file)
                    sessionStorage.setItem("aiMessage", data.aiMessage);  // Store AI message

                    // Redirect to /chatAI after processing
                    window.location.href = "/chatAI";
                } else {
                    alert(data.error || "Failed to process the file.");
                }
            } catch (error) {
                console.error("Error:", error);
                alert("An error occurred while uploading the file.");
            } finally {
                if (document.getElementById('loading-message')) {
                    document.getElementById('loading-message').remove();
                }
            }
        });
    }
}

// ===============================
// Function to Handle Code Analyzer
// ===============================
function handleCodeAnalyzer() {
    const codeSubmitBtn = document.getElementById("submit-chat-ai-button-code");
    const codeInputField = document.getElementById("code-creator-input");

    if (codeSubmitBtn && codeInputField) {
        codeSubmitBtn.addEventListener("click", async () => {
            const codeBlock = codeInputField.value.trim();
            if (!codeBlock) {
                alert("Please enter a code block.");
                return;
            }

            const loadingDiv = createLoadingMessage("Analyzing code... This may take a few seconds.");
            document.body.appendChild(loadingDiv);

            try {
                const response = await fetch("/summarize-code", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ code: codeBlock }),
                });

                const data = await response.json();

                if (response.ok) {
                    // Store content type and AI message in sessionStorage
                    sessionStorage.setItem('currentSessionId', data.session_id); // Store session_id in sessionStorage
                    sessionStorage.setItem('content_type', 'code');  // Set content type (code)
                    sessionStorage.setItem("aiMessage", data.aiMessage);  // Store AI message

                    // Redirect to /chatAI after processing
                    window.location.href = "/chatAI";
                } else {
                    alert(data.error || "Failed to analyze the code.");
                }
            } catch (error) {
                console.error("Error:", error);
                alert("An error occurred while analyzing the code.");
            } finally {
                if (document.getElementById('loading-message')) {
                    document.getElementById('loading-message').remove();
                }
            }
        });
    }
}

// ===============================
// Function to Handle Image Analyzer
// ===============================
function handleImageAnalyzer() {
    const imageSubmitBtn = document.getElementById("submit-chat-ai-button-image");
    const imageInputField = document.getElementById("image-uploader-input");

    if (imageSubmitBtn && imageInputField) {
        imageSubmitBtn.addEventListener("click", async () => {
            const imageFile = imageInputField.files[0];
            if (!imageFile) {
                alert("Please upload an image file.");
                return;
            }

            const loadingDiv = createLoadingMessage("Analyzing image... Please wait.");
            document.body.appendChild(loadingDiv);

            const formData = new FormData();
            formData.append("image", imageFile);

            try {
                const response = await fetch("/analyze-image", {
                    method: "POST",
                    body: formData,
                });

                const data = await response.json();

                if (response.ok) {
                    sessionStorage.setItem("content_type", data.content_type);  // Set content type (image)
                    sessionStorage.setItem("aiMessage", data.analysis);  // Store AI analysis message
                    window.location.href = "/chatAI";  // Redirect after image analysis
                } else {
                    alert(data.error || "Failed to analyze the image.");
                }
            } catch (error) {
                console.error("Error:", error);
                alert("An error occurred while analyzing the image.");
            } finally {
                if (document.getElementById('loading-message')) {
                    document.getElementById('loading-message').remove();
                }
            }
        });
    }
}


// ===============================
// User Profile Functions
// ===============================

function initializeNicknameUpdate() {
    const nicknameForm = document.getElementById('edit-nickname-form');

    if (nicknameForm) {
        nicknameForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const newNickname = document.getElementById('new-nickname').value;

            try {
                const response = await fetch('/update_nickname', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ nickname: newNickname })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.message) {
                        document.getElementById('USERTITLE').textContent = newNickname;
                        showSuccessPopup('Nickname updated successfully!');
                        document.getElementById('edit-nickname-modal').style.display = 'none';
                    } else {
                        throw new Error(result.error || 'An error occurred while updating the nickname.');
                    }
                } else {
                    throw new Error(`Network response was not ok (${response.status})`);
                }
            } catch (error) {
                console.error('Error:', error);
                alert(error.message);
            }
        });
    }
}

function initializePasswordUpdate() {
    const passwordForm = document.getElementById('edit-password-form');

    if (passwordForm) {
        passwordForm.addEventListener('submit', async function(event) {
            event.preventDefault();
            const currentPassword = document.getElementById('current-password').value;
            const newPassword = document.getElementById('new-password').value;
            const verifyPassword = document.getElementById('verify-password').value;

            // Client-side validation: Check if new password matches verification password
            if (newPassword !== verifyPassword) {
                showErrorPopup('Passwords do not match. Please try again.');
                return;
            }

            try {
                const response = await fetch('/update_password', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        current_password: currentPassword,
                        new_password: newPassword
                    })
                });

                if (response.ok) {
                    const result = await response.json();
                    if (result.message) {
                        // Password updated successfully
                        showSuccessPopup('Password updated successfully!');
                        document.getElementById('edit-password-modal').style.display = 'none'; // Close the modal
                    } else {
                        // Server-side error (e.g., incorrect current password)
                        showErrorPopup(result.error || 'An error occurred while updating the password.');
                    }
                } else {
                    const errorData = await response.json();
                    showErrorPopup(errorData.error || 'An error occurred while updating the password.');
                }
            } catch (error) {
                console.error('Error:', error);
                showErrorPopup(error.message);
            }
        });
    }
}

// ===============================
// Data Management Functions
// ===============================


function saveSessionToDatabase(date, title, description) {
    fetch('/save-chat-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ date, title, description }),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Session saved to database successfully.');
        } else {
            console.error('Error saving session to database:', data.error);
        }
    })
    .catch(error => {
        console.error('Error saving session to database:', error);
    });
}

function saveCurrentChatSession() {
    const currentSession = {
        date: new Date().toLocaleString(),
        title: 'Chat Session',
        description: 'Description of the current chat session',
    };

    fetch('/save-chat-session', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(currentSession),
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Session saved to database successfully.');
        } else {
            console.error('Error saving session to database:', data.error);
        }
    })
    .catch(error => {
        console.error('Error saving session to database:', error);
    });
}

function displayChatHistory() {
    const historyList = document.getElementById("chat-history");
    const noDataMessage = document.getElementById("no-data-message");

    fetch('/get-chat-history')
        .then(response => response.json())
        .then(chatHistory => {
            if (chatHistory.length > 0) {
                noDataMessage.style.display = "none";

                chatHistory.forEach(session => {
                    const row = document.createElement("tr");

                    row.innerHTML = `
                        <td>${session.date}</td>
                        <td>${session.title}</td>
                        <td>${session.description}</td>
                        <td>
                            <button type="button" class="action-button" onclick="reinteractSession('${session.id}')">
                                <span class="material-symbols-outlined">chat</span>
                            </button>
                            <button type="button" class="action-button" onclick="deleteSession('${session.id}')">
                                <span class="material-symbols-outlined">delete</span>
                            </button>
                        </td>
                    `;

                    historyList.appendChild(row);
                });
            } else {
                noDataMessage.style.display = "block";
            }
        })
        .catch(error => {
            console.error("Error fetching chat history:", error);
            noDataMessage.style.display = "block";
        });
}
document.addEventListener("DOMContentLoaded", displayChatHistory);

function reinteractSession(sessionId) {
    sessionStorage.setItem('currentSessionId', sessionId);
    sessionStorage.removeItem('youtubeLink'); // Clear any previous link
    window.location.href = '/chatAI';
}


function deleteSession(sessionId) {
    fetch(`/delete-chat-session/${sessionId}`, {
        method: 'DELETE',
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Session deleted successfully.');
            window.location.reload(); // Reload the page to update the table
        } else {
            console.error('Error deleting session:', data.error);
        }
    })
    .catch(error => console.error('Error deleting session:', error));
}

// ===============================
// Utility Functions
// ===============================

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

// Function to show an error popup with a custom message
function showErrorPopup(message) {
    // Create popup elements
    const popup = document.createElement('div');
    popup.id = 'error-popup';
    popup.style.position = 'fixed';
    popup.style.top = '50%';
    popup.style.left = '50%';
    popup.style.transform = 'translate(-50%, -50%)';
    popup.style.padding = '20px';
    popup.style.backgroundColor = 'rgba(255, 0, 0, 0.9)'; // Red color for error
    popup.style.color = 'white';
    popup.style.borderRadius = '5px';
    popup.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.5)';
    popup.style.zIndex = '1000';
    popup.style.textAlign = 'center';

    const messageElement = document.createElement('p');
    messageElement.textContent = message;

    const confirmButton = document.createElement('button');
    confirmButton.textContent = 'OK';
    confirmButton.style.marginTop = '10px';
    confirmButton.style.padding = '5px 10px';
    confirmButton.style.border = 'none';
    confirmButton.style.backgroundColor = 'white';
    confirmButton.style.color = 'rgba(255, 0, 0, 0.9)';
    confirmButton.style.borderRadius = '3px';
    confirmButton.style.cursor = 'pointer';

    // Append message and button to popup
    popup.appendChild(messageElement);
    popup.appendChild(confirmButton);
    document.body.appendChild(popup);

    // Event listener for "OK" button to remove the popup
    confirmButton.addEventListener('click', () => {
        popup.remove(); // Remove popup
    });
}

// Function to show a success popup with a custom message
function showSuccessPopup(message) {
    // Create popup elements
    const popup = document.createElement('div');
    popup.id = 'success-popup';
    popup.style.position = 'fixed';
    popup.style.top = '50%';
    popup.style.left = '50%';
    popup.style.transform = 'translate(-50%, -50%)';
    popup.style.padding = '20px';
    popup.style.backgroundColor = 'rgba(0, 128, 0, 0.9)';
    popup.style.color = 'white';
    popup.style.borderRadius = '5px';
    popup.style.boxShadow = '0 0 10px rgba(0, 0, 0, 0.5)';
    popup.style.zIndex = '1000';
    popup.style.textAlign = 'center';

    const messageElement = document.createElement('p');
    messageElement.textContent = message; // Set custom message text

    const confirmButton = document.createElement('button');
    confirmButton.textContent = 'Confirm';
    confirmButton.style.marginTop = '10px';
    confirmButton.style.padding = '5px 10px';
    confirmButton.style.border = 'none';
    confirmButton.style.backgroundColor = 'white';
    confirmButton.style.color = 'rgba(0, 128, 0, 0.9)';
    confirmButton.style.borderRadius = '3px';
    confirmButton.style.cursor = 'pointer';

    // Append message and button to popup
    popup.appendChild(messageElement);
    popup.appendChild(confirmButton);
    document.body.appendChild(popup);

    // Event listener for "Confirm" button to remove the popup
    confirmButton.addEventListener('click', () => {
        popup.remove(); // Remove popup
        window.location.reload(); // Refresh the page
    });
}

// function showLoadingMessage(message) {
//     const loadingDiv = document.createElement("div");
//     loadingDiv.id = "loading-message";
//     loadingDiv.textContent = message;
//     loadingDiv.style.color = "white";
//     loadingDiv.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
//     loadingDiv.style.padding = "20px";
//     loadingDiv.style.position = "fixed";
//     loadingDiv.style.top = "50%";
//     loadingDiv.style.left = "50%";
//     loadingDiv.style.transform = "translate(-50%, -50%)";
//     loadingDiv.style.borderRadius = "5px";
//     document.body.appendChild(loadingDiv);
// }

function createLoadingMessage(message) {
    const loadingDiv = document.createElement("div");
    loadingDiv.id = "loading-message";
    loadingDiv.textContent = message;
    loadingDiv.style.color = "white";
    loadingDiv.style.backgroundColor = "rgba(0, 0, 0, 0.7)";
    loadingDiv.style.padding = "20px";
    loadingDiv.style.position = "fixed";
    loadingDiv.style.top = "50%";
    loadingDiv.style.left = "50%";
    loadingDiv.style.transform = "translate(-50%, -50%)";
    loadingDiv.style.borderRadius = "5px";
    return loadingDiv;
}

function removeLoadingMessage(loadingDiv) {
    if (loadingDiv) {
        loadingDiv.remove();
    }
}

// For video summarizer
function summarizeVideo(youtubeUrl) {
    const submitBtn = document.getElementById('submit-chat-ai-button');
    const loadingDiv = createLoadingMessage('Processing video... This may take a few seconds.');
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
        // Store session_id and content_type in sessionStorage
        sessionStorage.setItem('currentSessionId', data.session_id); // Store session_id from backend
        sessionStorage.setItem('content_type', 'video'); // Set content type to 'video'

        // Optionally, store AI response to display
        sessionStorage.setItem("aiMessage", "You can now ask questions based on the summarized video.");

        // Redirect to /chatAI after processing
        window.location.href = "/chatAI";
    })
    .catch(error => {
        console.error(error);
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