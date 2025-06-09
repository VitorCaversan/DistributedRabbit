const reserveId = new URLSearchParams(location.search).get("id");
const POLL_INTERVAL = 2000;

const circle = step => document.querySelector(`.circle[data-step="${step}"]`);
const line   = n    => document.getElementById(`line-${n}`);

function mark(step, state) {
    const c = circle(step);
    c.classList.remove("success", "failed");
    if (state === "success") c.classList.add("success");
    if (state === "failed")  c.classList.add("failed");
}

function markLine(n, state) {
    const l = line(n);
    l.classList.toggle("success", state === "success");
}

async function poll() {
    try {
        if (!reserveId) return;
        const r = await fetch(`/status/${reserveId}`);
        if (!r.ok) throw new Error(await r.text());
        const d = await r.json();

        if (d.reserve === "APPROVED") { mark("reserve", "success"); markLine(1, "success"); }
        if (d.reserve === "FAILED")   { mark("reserve", "failed");  stop(); return; }

        if (d.payment === "APPROVED") { mark("payment", "success"); markLine(2, "success"); }
        if (d.payment === "DENIED")   { mark("payment", "failed");  stop(); return; }

        if (d.ticket === "GENERATED") { mark("ticket", "success");  stop(); return; }
    } catch (e) { console.error(e); }
}

let timer;
function start() {
    document.getElementById("spinner").hidden = false;
    timer = setInterval(poll, POLL_INTERVAL);
}
function stop() {
    document.getElementById("spinner").hidden = true;
    clearInterval(timer);
}

start();
