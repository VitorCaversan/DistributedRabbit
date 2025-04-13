function handleSearch() {
    const input = document.getElementById('searchBox').value;
    if (input.trim()) {
      alert(`Searching cruises for: ${input}`);
    } else {
      alert('Please enter a destination.');
    }
}

async function login() {
    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const res = await fetch('../databank/users.json');
    const data = await res.json();

    const user = data.users.find(u => u.username === username && u.password === password);

    if (user) {
        sessionStorage.setItem('loggedInUser', JSON.stringify(user));
        alert(`Welcome, ${user.username}!`);
        location.reload(); // opcional: atualizar interface
    } else {
        alert('Invalid credentials');
    }
}

// Mostrar status do login
window.addEventListener('DOMContentLoaded', () => {
    const user = JSON.parse(sessionStorage.getItem('loggedInUser'));
    if (user) {
        document.querySelector('.login-form').innerHTML = `
        <p>Logged in as <strong>${user.username}</strong></p>
        `;
    }
});
  