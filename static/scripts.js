document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('loginForm');
    
    form.addEventListener('submit', (e) => {
        const password = form.querySelector('#password').value;
        if (password.length < 7) {
            e.preventDefault();
            alert('Пароль должен быть не менее 7 символов!');
        }
    });
});
