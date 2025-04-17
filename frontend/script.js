async function loadItineraries() {
  try {
    const res = await fetch('../databank/cruises.json');
    const data = await res.json();
    cruiseData = data.itineraries;
    document.querySelector('.itineraries').innerHTML = '<h2>Cruise Itineraries</h2>';
  } catch (err) {
    console.error('Error loading itineraries:', err);
    document.querySelector('.itineraries').innerHTML += `<p>Could not load itineraries.</p>`;
  }
}

function formatDate(inputDate) {
    try {
      const [year, month, day] = inputDate.trim().split("-");
      return `${day}/${month}/${year}`;
    } catch {
      return "";
    }
}
   
function renderItineraries(itineraries) {
  const container = document.querySelector('.itineraries');
  container.innerHTML = '<h2>Cruise Itineraries</h2>';

  if (itineraries.length === 0) {
    container.innerHTML += `<p>No matching itineraries found.</p>`;
    return;
  }

  itineraries.forEach(cruise => {
    const places = cruise.visited_places.join(' • ');
    const dates = cruise.departure_dates.join(', ');

    const card = document.createElement('div');
    card.classList.add('card');

    card.innerHTML = `
    <div class="card-content">
      <div class="card-info">
        <h3>${cruise.ship}</h3>
        <p><strong>Departure Dates:</strong> ${dates}</p>
        <p><strong>Embark Port:</strong> ${cruise.embark_port}</p>
        <p><strong>Return Port:</strong> ${cruise.return_port}</p>
        <p><strong>Visited Places:</strong> ${places}</p>
        <p><strong>Duration:</strong> ${cruise.nights} nights</p>
        <p><strong>Price per person:</strong> $${cruise.price}</p>
      </div>
      <div class="card-action">
        <button onclick='reserveCruise(${JSON.stringify(cruise)})'>Reserve</button>
      </div>
    </div>
  `;
  
    container.appendChild(card);
  });
}

function handleSearch() {
    const destination = document.getElementById('destination').value.toLowerCase().trim();
    const embarkPort = document.getElementById('embarkPort').value.toLowerCase().trim();
    const rawDate = document.getElementById('departureDate').value.trim();
  
    if (!destination || !embarkPort || !rawDate) {
      alert("Please fill in all fields: destination, embarkation port, and departure date.");
      return;
    }
  
    const departureDate = formatDate(rawDate);
  
    const filtered = cruiseData.filter(cruise => {
      const matchDestination = cruise.visited_places.some(place => place.toLowerCase().includes(destination));
      const matchPort = cruise.embark_port.toLowerCase().includes(embarkPort);
      const matchDate = cruise.departure_dates.includes(departureDate); // agora no formato correto
  
      return matchDestination && matchPort && matchDate;
    });
  
    renderItineraries(filtered);
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

window.addEventListener('DOMContentLoaded', () => {
  loadItineraries();

  const user = JSON.parse(sessionStorage.getItem('loggedInUser'));
  if (user) {
    document.querySelector('.login-form').innerHTML = `
      <p>Logged in as <strong>${user.username}</strong></p>
    `;
  }
});

let cruiseData = [];

async function loadItineraries() {
  try {
    const res = await fetch('../databank/cruises.json');
    const data = await res.json();
    cruiseData = data.itineraries;
    document.querySelector('.itineraries').innerHTML = '<h2>Cruise Itineraries</h2>';
  } catch (err) {
    console.error('Error loading itineraries:', err);
    document.querySelector('.itineraries').innerHTML += `<p>Could not load itineraries.</p>`;
  }
}

function formatDate(inputDate) {
    try {
      const [year, month, day] = inputDate.trim().split("-");
      return `${day}/${month}/${year}`;
    } catch {
      return "";
    }
}
   
function renderItineraries(itineraries) {
  const container = document.querySelector('.itineraries');
  container.innerHTML = '<h2>Cruise Itineraries</h2>';

  if (itineraries.length === 0) {
    container.innerHTML += `<p>No matching itineraries found.</p>`;
    return;
  }

  itineraries.forEach(cruise => {
    const places = cruise.visited_places.join(' • ');
    const dates = cruise.departure_dates.join(', ');

    const card = document.createElement('div');
    card.classList.add('card');

    card.innerHTML = `
    <div class="card-content">
      <div class="card-info">
        <h3>${cruise.ship}</h3>
        <p><strong>Departure Dates:</strong> ${dates}</p>
        <p><strong>Embark Port:</strong> ${cruise.embark_port}</p>
        <p><strong>Return Port:</strong> ${cruise.return_port}</p>
        <p><strong>Visited Places:</strong> ${places}</p>
        <p><strong>Duration:</strong> ${cruise.nights} nights</p>
        <p><strong>Price per person:</strong> $${cruise.price}</p>
      </div>
      <div class="card-action">
        <button onclick='reserveCruise(${JSON.stringify(cruise)})'>Reserve</button>
      </div>
    </div>
  `;
  
    container.appendChild(card);
  });
}

function handleSearch() {
    const destination = document.getElementById('destination').value.toLowerCase().trim();
    const embarkPort = document.getElementById('embarkPort').value.toLowerCase().trim();
    const rawDate = document.getElementById('departureDate').value.trim();
  
    if (!destination || !embarkPort || !rawDate) {
      alert("Please fill in all fields: destination, embarkation port, and departure date.");
      return;
    }
  
    const departureDate = formatDate(rawDate);
  
    const filtered = cruiseData.filter(cruise => {
      const matchDestination = cruise.visited_places.some(place => place.toLowerCase().includes(destination));
      const matchPort = cruise.embark_port.toLowerCase().includes(embarkPort);
      const matchDate = cruise.departure_dates.includes(departureDate); // agora no formato correto
  
      return matchDestination && matchPort && matchDate;
    });
  
    renderItineraries(filtered);
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

window.addEventListener('DOMContentLoaded', () => {
  loadItineraries();

  const user = JSON.parse(sessionStorage.getItem('loggedInUser'));
  if (user) {
    document.querySelector('.login-form').innerHTML = `
      <p>Logged in as <strong>${user.username}</strong></p>
    `;
  }
});

function reserveCruise(cruise) {
    const reservation = {
        id: cruise.id,
        ship: cruise.ship,
        departure_date: cruise.departure_dates[0], 
        embark_port: cruise.embark_port,
        return_port: cruise.return_port,
        visited_places: cruise.visited_places,
        nights: cruise.nights,
        price: cruise.price,
        passenger_count: 1,
        cabins: 1
    };

fetch('http://localhost:5000/reserve', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify(reservation)
    })
    .then(response => response.json())
    .then(data => {
        if (!data.status) {
          alert(`Reservation error: ${data.error}`)
        }
        else{
          alert(`Reservation status: ${data.status}`);
        }
    })
    .catch(err => {
        console.error('Error reserving cruise:', err);
        alert('Error sending reservation.');
    });
}

  

  
