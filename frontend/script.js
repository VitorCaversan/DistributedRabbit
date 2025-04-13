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
        location.reload();
    } else {
        alert('Invalid credentials');
    }
}

async function loadItineraries() {
    try {
      const res = await fetch('../databank/cruises.json');
      const data = await res.json();
  
      const container = document.querySelector('.itineraries');
      container.innerHTML = '<h2>Cruise Itineraries</h2>'; // limpar antes
  
      data.itineraries.forEach(cruise => {
        const places = cruise.visited_places.join(' • ');
        const dates = cruise.departure_dates.join(', ');
  
        const card = document.createElement('div');
        card.classList.add('card');
  
        card.innerHTML = `
          <h3>${cruise.ship}</h3>
          <p><strong>Departure Dates:</strong> ${dates}</p>
          <p><strong>Embark Port:</strong> ${cruise.embark_port}</p>
          <p><strong>Return Port:</strong> ${cruise.return_port}</p>
          <p><strong>Visited Places:</strong> ${places}</p>
          <p><strong>Duration:</strong> ${cruise.nights} nights</p>
          <p><strong>Price per person:</strong> $${cruise.price}</p>
        `;
  
        container.appendChild(card);
      });
    } catch (err) {
      console.error('Error loading itineraries:', err);
      document.querySelector('.itineraries').innerHTML += `<p>Could not load itineraries.</p>`;
    }
  }
  
  window.addEventListener('DOMContentLoaded', () => {
    loadItineraries();
  
    const user = JSON.parse(sessionStorage.getItem('loggedInUser'));
    if (user) {
      document.querySelector('.login-form').innerHTML = `
        <p>Logged in as <strong>${user.username}</strong></p>
      `;
    }
  });
  
  