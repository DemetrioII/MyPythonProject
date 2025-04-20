document.addEventListener('DOMContentLoaded', function() {
    const urlParams = new URLSearchParams(window.location.search);
    const error = urlParams.get('error');
    const success = urlParams.get('success');

    if (error) {
        alert(error);
    }

    if (success) {
        alert(success);
    }

    const registerForm = document.querySelector('form[action="/register"]');
    if (registerForm) {
        registerForm.addEventListener('submit', function(e) {
            const password = document.getElementById('password').value;
            const passwordRepeat = document.getElementById('password_repeat').value;

            if (password !== passwordRepeat) {
                e.preventDefault();
                alert('Пароли не совпадают!');
                return false;
            }

            if (password.length < 7) {
                e.preventDefault();
                alert('Пароль должен содержать минимум 7 символов!');
                return false;
            }
        });
    }
});