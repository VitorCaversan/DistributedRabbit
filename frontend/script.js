/*  ──────────────────────────────────────────────────────────────
    CruiseSync - Frontend logic
    -------------------------------------------------------------
    • Carrega itinerários do JSON
    • Filtra por destino, porto e data
    • Envia reserva (POST /reserve) e redireciona para
      reservation_status.html?id=<reserve_id>
    • Faz login rápido usando users.json + /login
   ────────────────────────────────────────────────────────────── */

   let cruiseData = [];

   /* ---------- carga inicial ----------------------------------- */
   async function loadItineraries() {
     try {
       const res  = await fetch("/databank/cruises.json");
       const data = await res.json();
       cruiseData = data.itineraries;
       renderItineraries(cruiseData);         // mostra todos de início
     } catch (err) {
       console.error("Error loading itineraries:", err);
       document.querySelector(".itineraries").innerHTML =
         "<h2>Cruise Itineraries</h2><p>Could not load itineraries.</p>";
     }
   }
   
   /* ---------- helpers ----------------------------------------- */
   function formatDate(inputDate) {
     // de yyyy-mm-dd ➜ dd/mm/yyyy
     if (!inputDate) return "";
     const [y, m, d] = inputDate.split("-");
     return `${d}/${m}/${y}`;
   }
   
   /* ---------- renderização ------------------------------------ */
   function renderItineraries(itineraries) {
     const container = document.querySelector(".itineraries");
     container.innerHTML = "<h2>Cruise Itineraries</h2>";
   
     if (!itineraries.length) {
       container.innerHTML += "<p>No matching itineraries found.</p>";
       return;
     }
   
     itineraries.forEach((cruise) => {
       const places = cruise.visited_places.join(" • ");
       const dates  = cruise.departure_dates.join(", ");
   
       const card = document.createElement("div");
       card.className = "card";
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
             <button onclick='reserveCruise(${JSON.stringify(cruise)})'>
               Reserve
             </button>
           </div>
         </div>`;
       container.appendChild(card);
     });
   }
   
   /* ---------- busca ------------------------------------------- */
   function handleSearch() {
     const destination = document
       .getElementById("destination")
       .value.toLowerCase()
       .trim();
     const embarkPort = document
       .getElementById("embarkPort")
       .value.toLowerCase()
       .trim();
     const rawDate = document.getElementById("departureDate").value.trim();
   
     if (!destination || !embarkPort || !rawDate) {
       alert("Please fill in all fields.");
       return;
     }
     const departureDate = formatDate(rawDate);
   
     const filtered = cruiseData.filter((c) => {
       const matchDestination = c.visited_places.some((p) =>
         p.toLowerCase().includes(destination)
       );
       const matchPort = c.embark_port.toLowerCase().includes(embarkPort);
       const matchDate = c.departure_dates.includes(departureDate);
       return matchDestination && matchPort && matchDate;
     });
   
     renderItineraries(filtered);
   }
   
   /* ---------- reserva ----------------------------------------- */
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
       cabins: 1,
     };
   
     fetch("http://localhost:5000/reserve", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify(reservation),
     })
       .then((r) => r.json())
       .then((data) => {
         if (!data.status) {
           alert(`Reservation error: ${data.error}`);
           return;
         }
         // redireciona para a página de progresso
         window.location.href =
           "reservation_status.html?id=" + reservation.id;
       })
       .catch((err) => {
         console.error("Error reserving cruise:", err);
         alert("Error sending reservation.");
       });
   }
   
   /* ---------- login ------------------------------------------- */
   async function login() {
     const username = document.getElementById("username").value;
     const password = document.getElementById("password").value;
   
     const res  = await fetch("/databank/users.json");
     const data = await res.json();
     const user = data.users.find(
       (u) => u.username === username && u.password === password
     );
   
     if (!user) {
       alert("Invalid credentials");
       return;
     }
   
     sessionStorage.setItem("loggedInUser", JSON.stringify(user));
   
     fetch("http://localhost:5000/login", {
       method: "POST",
       headers: { "Content-Type": "application/json" },
       body: JSON.stringify({ id: user.id }),
     })
       .then((r) => r.json())
       .then((payload) => {
         if (payload.status === "success") {
           alert(`Welcome, ${user.username}!`);
           location.reload();
         } else {
           alert(`Login failed: ${payload.error}`);
         }
       })
       .catch((err) => {
         console.error("Error talking to server:", err);
         alert("Could not log in.");
       });
   }
   
   /* ---------- init -------------------------------------------- */
   window.addEventListener("DOMContentLoaded", () => {
     loadItineraries();
   
     const user = JSON.parse(sessionStorage.getItem("loggedInUser"));
     if (user) {
       document.querySelector(".login-form").innerHTML =
         `<p>Logged in as <strong>${user.username}</strong></p>`;
     }
   });
   