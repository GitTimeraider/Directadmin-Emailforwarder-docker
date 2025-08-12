// Hamburger Menu Toggle
document.addEventListener('DOMContentLoaded', function() {
    const hamburger = document.getElementById('hamburger');
    const navLinks = document.getElementById('navLinks');
    const body = document.body;

    // Create overlay element
    const overlay = document.createElement('div');
    overlay.className = 'nav-overlay';
    document.body.appendChild(overlay);

    // Toggle menu function
    function toggleMenu() {
        hamburger.classList.toggle('active');
        navLinks.classList.toggle('active');
        overlay.classList.toggle('active');
        body.classList.toggle('menu-open');
    }

    // Hamburger click
    if (hamburger) {
        hamburger.addEventListener('click', toggleMenu);
    }

    // Overlay click (close menu)
    overlay.addEventListener('click', function() {
        if (navLinks.classList.contains('active')) {
            toggleMenu();
        }
    });

    // Close menu when clicking a link
    const navLinksItems = navLinks.querySelectorAll('a');
    navLinksItems.forEach(link => {
        link.addEventListener('click', function() {
            if (window.innerWidth <= 768) {
                toggleMenu();
            }
        });
    });

    // Handle window resize
    let resizeTimer;
    window.addEventListener('resize', function() {
        clearTimeout(resizeTimer);
        resizeTimer = setTimeout(function() {
            if (window.innerWidth > 768) {
                // Reset menu state on desktop
                hamburger.classList.remove('active');
                navLinks.classList.remove('active');
                overlay.classList.remove('active');
                body.classList.remove('menu-open');
            }
        }, 250);
    });

    // Theme persistence - apply theme from localStorage if different from server preference
    const savedTheme = localStorage.getItem('theme-preference');
    const currentTheme = body.getAttribute('data-theme');
    
    if (savedTheme && savedTheme !== currentTheme) {
        body.setAttribute('data-theme', savedTheme);
    }
});

// Global theme toggle function (used in settings page)
window.toggleTheme = async function() {
    const themeToggle = document.getElementById('theme-toggle');
    if (!themeToggle) return;
    
    const newTheme = themeToggle.checked ? 'dark' : 'light';
    
    // Apply theme immediately
    document.body.setAttribute('data-theme', newTheme);
    
    // Save to localStorage for immediate persistence
    localStorage.setItem('theme-preference', newTheme);
    
    try {
        // Save theme preference to server
        const response = await fetch('/settings/api/theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            credentials: 'same-origin',
            body: JSON.stringify({ theme: newTheme })
        });

        if (response.ok) {
            const result = await response.json();
            if (result.success) {
                console.log('Theme preference saved:', newTheme);
            }
        }
    } catch (error) {
        console.error('Error saving theme preference:', error);
        // Don't revert the theme change on save error, user can still use it for this session
    }
};