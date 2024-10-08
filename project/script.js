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
document.getElementById('new-chat-page').addEventListener('click', function() {
    window.location.href = '/project/NavPages/newchat.html';
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

// Redirect to profile Page when clicked
document.getElementById('user-profile').addEventListener('click', function() {
    window.location.href = '/project/NavPages/profile.html';
});
