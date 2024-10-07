document.getElementById('toggle-btn').addEventListener('click', function() {
    const sidebar = document.getElementById('sidebar');
    const toggleBtn = document.getElementById('toggle-btn');
    // const toggleChatBtn = document.getElementById('new-chat-btn');
    

    sidebar.classList.toggle('collapsed');

    if (sidebar.classList.contains('collapsed')) {
        toggleBtn.style.right = '5px'; // Adjust button position when collapsed
    } else {
        toggleBtn.style.right = '20px'; // Adjust button position when expanded
    }
});
