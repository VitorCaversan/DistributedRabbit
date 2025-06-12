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

var source = new EventSource("{{ url_for('sse.stream') }}");
source.addEventListener('publish', function(event) {
    const data = JSON.parse(event.data);

    if (data.reserve === "APPROVED") { mark("reserve", "success"); markLine(1, "success"); }
    if (data.reserve === "FAILED")   { mark("reserve", "failed");  stop(); return; }

    if (data.payment === "APPROVED") { mark("payment", "success"); markLine(2, "success"); }
    if (data.payment === "DENIED")   { mark("payment", "failed");  stop(); return; }

    if (data.ticket === "GENERATED") { mark("ticket", "success");  stop(); return; }
}, false);
source.addEventListener('error', function(event) {
    console.log("Error"+ event)
    alert("Failed to connect to event stream. Is Redis running?");
}, false);

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
