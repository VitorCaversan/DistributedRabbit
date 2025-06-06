let cruiseData = [];

async function loadItineraries() {
  const baseUrl = "http://127.0.0.1:5050/reserve/itineraries";
  const url = new URL(baseUrl);
  url.searchParams.append("dest",    "all");

  const response = await fetch(url);
  if (!response.ok) {
    document.querySelector(".itineraries").innerHTML =
      "<h2>Cruise Itineraries</h2><p>Could not load itineraries.</p>";
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  console.log("Itineraries API response:", data);
  renderItineraries(data);
}

const formatDate = d => d && d.split("-").reverse().join("/");

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
            <p><strong>Available Cabins:</strong> ${cruise.available_seats}</p>
          </div>
          <div class="card-action">
            <button onclick='reserveCruise(${JSON.stringify(cruise)})'>Reserve</button>
          </div>
        </div>
      </div>`);
  });
}

async function handleSearch() {
  const dest  = document.getElementById("destination").value.toLowerCase().trim();
  const port  = document.getElementById("embarkPort").value.toLowerCase().trim();
  const date  = formatDate(document.getElementById("departureDate").value.trim());

  if (!dest || !port || !date) { alert("Please fill in all fields."); return; }

  const baseUrl = "http://127.0.0.1:5050/reserve/itineraries";
  const url = new URL(baseUrl);
  url.searchParams.append("dest",    dest);
  url.searchParams.append("embark_port",      port);
  url.searchParams.append("departure_date",   date);

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  const data = await response.json();
  console.log("Itineraries API response:", data);
  renderItineraries(data);
}

function reserveCruise(cruise) {
  const reservation = {
    id : cruise.id, ship : cruise.ship,
    departure_date : cruise.departure_dates[0],
    embark_port : cruise.embark_port,
    return_port : cruise.return_port,
    visited_places : cruise.visited_places,
    nights : cruise.nights, price : cruise.price,
    passenger_count : 1,
    cabins : cruise.available_cabins,
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

async function login(){
    const u=document.getElementById("username").value
    const p=document.getElementById("password").value
    const data=await (await fetch("/databank/users.json")).json()
    const user=data.users.find(x=>x.username===u&&x.password===p)
    if(!user){alert("Invalid credentials");return}
    const d=await (await fetch("/login",{method:"POST",
        headers:{ "Content-Type":"application/json"},
        body:JSON.stringify({id:user.id})})).json()
    if(d.status!=="success"){alert(`Login failed: ${d.error}`);return}
    sessionStorage.setItem("loggedInUser",JSON.stringify(user))
    renderLogged(user.username)
    startPromoPolling()
  }
  
  function logout(){
    sessionStorage.removeItem("loggedInUser")
    clearInterval(pollingId); pollingId=null
    document.querySelector(".login-form").innerHTML=`
      <input type="text" id="username" placeholder="Username">
      <input type="password" id="password" placeholder="Password">
      <button onclick="login()">Login</button>`
  }
  
  function renderLogged(name){
    document.querySelector(".login-form").innerHTML=
      `<p>Logged in as <strong>${name}</strong></p>
       <button onclick="logout()">Sign out</button>`
  }

function toast(msg){
  const t=document.createElement("div");
  t.className="toast";
  t.textContent=msg;
  document.body.appendChild(t);
  setTimeout(()=>t.remove(),5000);
}

let pollingId=null
function startPromoPolling(){
  if(pollingId) return
  pollingId=setInterval(async()=>{
    try{
      const r=await fetch("/promos")
      if(!r.ok) return
      ;(await r.json()).forEach(p=>
        toast(`🔥 Cruise ${p.cruise_id}: new price $${p.promotion_value}`)
      )
    }catch(e){console.error(e)}
  },3000)
}

window.addEventListener("DOMContentLoaded",()=>{
    loadItineraries()
    const user=JSON.parse(sessionStorage.getItem("loggedInUser")||"null")
    if(user){ renderLogged(user.username); startPromoPolling() }
  })
