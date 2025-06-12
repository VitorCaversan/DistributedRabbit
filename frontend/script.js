let cruiseData = [];

async function loadItineraries() {
    const baseUrl = "http://127.0.0.1:5050/reserve/itineraries";
    const url = new URL(baseUrl);
    url.searchParams.append("dest", "all");

    const response = await fetch(url);
    if (!response.ok) {
        document.querySelector(".itineraries").innerHTML =
            "<h2>Cruise Itineraries</h2><p>Could not load itineraries.</p>";
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();

    renderItineraries(data);
}

const formatDate = d => d && d.split("-").reverse().join("/");

function renderItineraries(list) {
    const c = document.querySelector(".itineraries");
    c.innerHTML = "<h2>Cruise Itineraries</h2>";
    if (!list.length) {
        c.innerHTML += "<p>No matching itineraries found.</p>";
        return;
    }

    const loggedInUser = JSON.parse(sessionStorage.getItem("loggedInUser") || "null");

    list.forEach(cruise => {
        const places = cruise.visited_places.join(" • ");
        const dates = cruise.departure_dates.join(", ");
        let extraFields = "";
        let reserveButton = "";

        if (loggedInUser) {
            extraFields = `
                <input type="number" min="1" max="${cruise.passenger_count}" 
                    id="passenger_count_${cruise.id}" 
                    placeholder="Number of Passengers" style="margin-right:8px;width:170px;">
                <input type="number" min="1" max="${cruise.available_cabins}" 
                    id="cabins_${cruise.id}" 
                    placeholder="Number of Cabins" style="margin-right:8px;width:150px;">
            `;
            reserveButton = `<button onclick='reserveCruise(${JSON.stringify(cruise)})'>Reserve</button>`;
        }

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
                        <p><strong>Available Cabins:</strong> ${cruise.available_cabins || 0}</p>
                        <p><strong>Max Passengers:</strong> ${cruise.passenger_count || 0}</p>
                    </div>
                    <div class="card-action">
                        ${extraFields}
                        ${reserveButton}
                    </div>
                </div>
            </div>`);
    });
}

/**
 * Pesquisa pelos itinerários filtrados.
 */
async function handleSearch() {
    const dest = document.getElementById("destination").value.toLowerCase().trim();
    const port = document.getElementById("embarkPort").value.toLowerCase().trim();
    const date = formatDate(document.getElementById("departureDate").value.trim());

    if (!dest || !port || !date) {
        alert("Please fill in all fields.");
        return;
    }

    const baseUrl = "http://127.0.0.1:5050/reserve/itineraries";
    const url = new URL(baseUrl);
    url.searchParams.append("dest", dest);
    url.searchParams.append("embark_port", port);
    url.searchParams.append("departure_date", date);

    const response = await fetch(url);
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    renderItineraries(data);
}

async function reserveCruise(cruise) {
    const loggedInUser = JSON.parse(sessionStorage.getItem("loggedInUser") || "null");
    if (!loggedInUser) return;
    const cruiseId = cruise.id;
    const availableCabins = cruise.available_cabins || 1;
    const availablePassengers = cruise.passenger_count || 1;

    const passengerCountEl = document.getElementById(`passenger_count_${cruiseId}`);
    const cabinsEl = document.getElementById(`cabins_${cruiseId}`);

    let passenger_count = 1;
    let cabins = 1;

    if (passengerCountEl && cabinsEl) {
        passenger_count = parseInt(passengerCountEl.value, 10);
        cabins = parseInt(cabinsEl.value, 10);

        if (!passenger_count || !cabins || passenger_count <= 0 || cabins <= 0) {
            toast("Por favor, preencha o número de passageiros e de cabines.");
            return;
        }
        if (cabins > availableCabins) {
            toast("Não há cabines suficientes disponíveis para este cruzeiro.");
            return;
        }
        if (passenger_count > availablePassengers) {
            toast("Não há passageiros suficientes disponíveis para este cruzeiro.");
            return;
        }
    }

    const reservation = {
        id: cruise.id,
        ship: cruise.ship,
        departure_date: cruise.departure_dates ? cruise.departure_dates[0] : cruise.departure_date,
        embark_port: cruise.embark_port,
        return_port: cruise.return_port,
        visited_places: cruise.visited_places,
        nights: cruise.nights,
        price: cruise.price,
        passenger_count: passenger_count,
        cabins: cabins,
        user_id: loggedInUser.id
    };

    fetch("http://127.0.0.1:5050/reserve", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(reservation)
    })
        .then(r => r.json())
        .then(d => {
            if (!d.status || d.status === "error") {
                toast(`❌ Reservation error: ${d.error || d.details}`);
                return;
            }

            const reserveId = d.reserve_id ?? reservation.id;

            if (d.payment_url) {
                window.location.href = d.payment_url;
            } else {
                window.location.href = `/reservation_status.html?id=${reserveId}`;
            }
        })
        .catch(e => {
            console.error(e);
            alert("Error sending reservation.");
            toast("❌ Error sending reservation.");
        });
}

async function login() {
    const u = document.getElementById("username").value;
    const p = document.getElementById("password").value;
    const data = await (await fetch("/databank/users.json")).json();
    const user = data.users.find(x => x.username === u && x.password === p);
    if (!user) { alert("Invalid credentials"); return; }
    const d = await (await fetch("http://127.0.0.1:5050/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ id: user.id })
    })).json();
    if (d.status !== "success") { alert(`Login failed: ${d.error}`); return; }
    sessionStorage.setItem("loggedInUser", JSON.stringify(user));
    renderLogged(user.username, user.wants_promo);
    connectSSE(user.id);
    document.querySelector('.user-reservations').style.display = "block";
    await loadUserReservations();
    loadItineraries();
}

function logout() {
    sessionStorage.removeItem("loggedInUser");
    if (eventSource) {
        eventSource.close();
        eventSource = null;
    }
    document.querySelector(".login-form").innerHTML = `
        <input type="text" id="username" placeholder="Username">
        <input type="password" id="password" placeholder="Password">
        <button onclick="login()">Login</button>`;
    document.getElementById("promoToggleContainer").style.display = "none";
    document.getElementById("promoToggle").checked = 0;
    const userReservations = document.querySelector(".user-reservations");
    userReservations.innerHTML = "";
    userReservations.style.display = "none";
    loadItineraries();
    window.location.reload();
}


function renderLogged(name, wants_promo = false) {
    document.querySelector(".login-form").innerHTML =
        `<p>Logged in as <strong>${name}</strong></p>
        <button onclick="logout()">Sign out</button>`;
    document.getElementById("promoToggleContainer").style.display = "block";
    document.getElementById("promoToggle").checked = !!wants_promo;
}

function toast(msg) {
    const t = document.createElement("div");
    t.className = "toast";
    t.textContent = msg;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 5000);
}

let eventSource = null;

function connectSSE(userId) {
    if (eventSource) eventSource.close();

    // prefixo “/stream” + query string; *não* duplique “/stream”
    eventSource = new EventSource(`/stream?channel=user-${userId}`);

    eventSource.addEventListener("promotion", ev => {
        const d = JSON.parse(ev.data);
        toast(`🔥 Cruise ${d.cruise_id}: new price $${d.promotion_value}`);
        loadItineraries();
    });

    eventSource.onerror = e => console.error("SSE error:", e);
}


window.addEventListener("DOMContentLoaded", async () => {
    loadItineraries();

    const user = JSON.parse(sessionStorage.getItem("loggedInUser") || "null");
    if (user) {
        await fetch("http://127.0.0.1:5050/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ id: user.id })
        });
        renderLogged(user.username, user.wants_promo);
        connectSSE(user.id);
        document.getElementById("promoToggleContainer").style.display = "block";
        document.getElementById("promoToggle").checked = !!user.wants_promo;
        document.querySelector(".user-reservations").style.display = "block";
        loadUserReservations();
    } else {
        document.querySelector(".user-reservations").style.display = "none";
    }
});

async function setUserPromotions(userId, wantsPromo) {
    const url = `http://127.0.0.1:5050/users/${userId}/promotions`;
    const resp = await fetch(url, {
        method: "PUT",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ wants_promo: wantsPromo })
    });

    if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        console.error("Failed to set promotions:", err);
        alert("Could not update promotions");
        return null;
    }

    const data = await resp.json();
    return data.wants_promo;
}

document
    .getElementById("promoToggle")
    .addEventListener("change", async (e) => {
        e.preventDefault();
        const wantsPromo = e.target.checked;
        const user = JSON.parse(sessionStorage.getItem("loggedInUser"));
        const updated = await setUserPromotions(user.id, wantsPromo);
        if (updated === null) {
            e.target.checked = !wantsPromo;
        } else {
            user.wants_promo = updated;
            sessionStorage.setItem("loggedInUser", JSON.stringify(user));
        }
    });

async function loadUserReservations() {
    const loggedInUser = JSON.parse(sessionStorage.getItem("loggedInUser") || "null");
    if (!loggedInUser) return;

    const url = `http://127.0.0.1:5050/reserve/user/${loggedInUser.id}?nocache=${Date.now()}`;
    const resp = await fetch(url);
    if (!resp.ok) {
        document.querySelector(".user-reservations").innerHTML =
            "<h2>My Reservations</h2><p>Could not load reservations.</p>";
        return;
    }
    const reservations = await resp.json();
    renderUserReservations(reservations);
}

function renderUserReservations(reservations) {
    const c = document.querySelector(".user-reservations");
    c.innerHTML = "<h2>My Reservations</h2>";
    if (!reservations.length) {
        c.innerHTML += "<p>No reservations found.</p>";
        return;
    }
    reservations.forEach(resv => {
        const places = resv.visited_places.join(" • ");
        const dates = resv.departure_dates.join(", ");

        c.insertAdjacentHTML("beforeend", `
            <div class="card reservation-card">
                <div class="card-content">
                    <div class="card-info">
                        <h3>${resv.ship}</h3>
                        <p><strong>Departure Dates:</strong> ${dates}</p>
                        <p><strong>Embark Port:</strong> ${resv.embark_port}</p>
                        <p><strong>Return Port:</strong> ${resv.return_port}</p>
                        <p><strong>Visited Places:</strong> ${places}</p>
                        <p><strong>Duration:</strong> ${resv.nights} nights</p>
                        <p><strong>Price per person:</strong> $${resv.price}</p>
                        <p><strong>Reserved Passengers:</strong> ${resv.reserved_passengers}</p>
                        <p><strong>Reserved Cabins:</strong> ${resv.reserved_cabins}</p>
                    </div>
                    <div class="card-action">
                        <button onclick="cancelReservation(${resv.cruise_id})" class="cancel-btn">
                            Cancel Reservation
                        </button>
                    </div>
                </div>
            </div>
        `);
    });
}

async function cancelReservation(cruiseId) {
    const loggedInUser = JSON.parse(sessionStorage.getItem("loggedInUser") || "null");
    if (!loggedInUser) return;
    if (!confirm("Are you sure you want to cancel this reservation?")) return;

    const resp = await fetch(`http://127.0.0.1:5050/reserve/cancel`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ cruise_id: cruiseId, user_id: loggedInUser.id })
    });
    const data = await resp.json();
    if (data.status === "success") {
        toast("Reservation cancelled successfully.");
        loadUserReservations();
        loadItineraries();
    } else {
        toast("Failed to cancel reservation: " + (data.error || "Unknown error"));
    }
}