document.addEventListener('DOMContentLoaded', () => {
    const navToggle = document.getElementById('navToggle');
    const navLinks = document.getElementById('navLinks');

    if (navToggle && navLinks) {
        navToggle.addEventListener('click', () => {
            navLinks.classList.toggle('open');
        });
    }

    const flashes = document.querySelectorAll('.flash');
    flashes.forEach((flash) => {
        setTimeout(() => {
            flash.style.opacity = '0';
            flash.style.transform = 'translateY(-8px)';
            flash.style.transition = 'opacity 0.3s, transform 0.3s';
            setTimeout(() => flash.remove(), 300);
        }, 5000);
    });

    const registerForm = document.getElementById('registerForm');
    if (registerForm) {
        const emailPattern = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
        const namePattern = /^[a-zA-Z\s]+$/;
        const usernamePattern = /^[^\s\d][^\s]*$/;

        registerForm.addEventListener('submit', (event) => {
            const username = registerForm.username.value.trim();
            const email = registerForm.email.value.trim();
            const fullName = registerForm.full_name.value.trim();
            const errors = [];

            if (!usernamePattern.test(username)) {
                errors.push('Username cannot contain spaces and cannot start with a number.');
            }
            if (!namePattern.test(fullName)) {
                errors.push('Full name can only contain letters and spaces.');
            }
            if (!emailPattern.test(email)) {
                errors.push('Please enter a valid email address.');
            }

            if (errors.length) {
                event.preventDefault();
                alert(errors.join('\n'));
            }
        });
    }
});
