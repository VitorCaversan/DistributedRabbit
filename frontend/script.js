/* CruiseSync – Frontend logic */

let cruiseData = [];

/* ---------- carga inicial ---------- */
async function loadItineraries() {
  try {
    const res  = await fetch("/databank/cruises.json");
    const data = await res.json();
    cruiseData = data.itineraries;
    renderItineraries(cruiseData);
  } catch (err) {
    console.error(err);
    document.querySelector(".itineraries").innerHTML =
      "<h2>Cruise Itineraries</h2><p>Could not load itineraries.</p>";
  }
}

/* ---------- helpers ---------- */
const formatDate = d => d && d.split("-").reverse().join("/");

/* ---------- render ---------- */
function renderItineraries(list) {
  const c = document.querySelector(".itineraries");
  c.innerHTML = "<h2>Cruise Itineraries</h2>";
  if (!list.length) { c.innerHTML += "<p>No matching itineraries found.</p>"; return; }

  list.forEach(cruise => {
    const places = cruise.visited_places.join(" • ");
    const dates  = cruise.departure_dates.join(", ");
    c.insertAdjacentHTML("beforeend", `
      <div class="card">
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
      </div>`);
  });
}

/* ---------- busca ---------- */
function handleSearch() {
  const dest  = document.getElementById("destination").value.toLowerCase().trim();
  const port  = document.getElementById("embarkPort").value.toLowerCase().trim();
  const date  = formatDate(document.getElementById("departureDate").value.trim());

  if (!dest || !port || !date) { alert("Please fill in all fields."); return; }

  const filtered = cruiseData.filter(c =>
    c.visited_places.some(p => p.toLowerCase().includes(dest)) &&
    c.embark_port.toLowerCase().includes(port) &&
    c.departure_dates.includes(date)
  );

  renderItineraries(filtered);
}

/* ---------- reserva ---------- */
function reserveCruise(cruise) {
  const reservation = {
    id : cruise.id, ship : cruise.ship,
    departure_date : cruise.departure_dates[0],
    embark_port : cruise.embark_port,
    return_port : cruise.return_port,
    visited_places : cruise.visited_places,
    nights : cruise.nights, price : cruise.price,
    passenger_count : 1, cabins : 1
  };

  fetch("/reserve", {
    method : "POST",
    headers : { "Content-Type":"application/json" },
    body : JSON.stringify(reservation)
  })
  .then(r => r.json())
  .then(d => {
    if (!d.status) { alert(`Reservation error: ${d.error}`); return; }
    window.location.href = `reservation_status.html?id=${reservation.id}`;
  })
  .catch(e => { console.error(e); alert("Error sending reservation."); });
}

/* ---------- login (opcional) ---------- */
async function login() {
  const u = document.getElementById("username").value;
  const p = document.getElementById("password").value;

  const res = await fetch("/databank/users.json"); const data = await res.json();
  const user = data.users.find(x => x.username === u && x.password === p);
  if (!user) { alert("Invalid credentials"); return; }

  sessionStorage.setItem("loggedInUser", JSON.stringify(user));

  fetch("/login", {
    method:"POST", headers:{ "Content-Type":"application/json" },
    body: JSON.stringify({ id:user.id })
  })
  .then(r=>r.json())
  .then(d=>{
    if (d.status==="success") { alert(`Welcome, ${user.username}!`); location.reload(); }
    else { alert(`Login failed: ${d.error}`); }
  })
  .catch(console.error);
}

/* ---------- promoções toast ---------- */
function toast(msg){
  const t=document.createElement("div");
  t.className="toast";
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),5000);
}

function startPromoPolling(){
  setInterval(async ()=>{
    try{
      const r=await fetch("/promos");
      if(!r.ok) return;
      (await r.json()).forEach(p =>
        toast(`🔥 Cruise ${p.cruise_id}: New Value! $${p.promotion_value}`));
    }catch(e){console.error(e);}
  },3000);
}

/* ---------- init ---------- */
window.addEventListener("DOMContentLoaded", ()=>{
  loadItineraries();
  startPromoPolling();
  const user = JSON.parse(sessionStorage.getItem("loggedInUser")||"null");
  if (user){
    document.querySelector(".login-form").innerHTML =
      `<p>Logged in as <strong>${user.username}</strong></p>`;
  }
});
