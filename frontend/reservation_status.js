document.addEventListener("DOMContentLoaded", () => {

    const $        = sel => document.querySelector(sel);
    const circle   = step => $(`.circle[data-step="${step}"]`);
    const line     = n    => $(`#line-${n}`);
    const spinner  = $("#spinner");

    function mark(step, state = "success") {
        const c = circle(step);
        if (!c) return;
        c.classList.remove("success", "failed");
        c.classList.add(state);
    }

    function markLine(n, state = "success") {
        const l = line(n);
        if (!l) return;
        l.classList.remove("success", "failed");
        l.classList.add(state);
    }

    function finish() {
        spinner.hidden = true;
        evtSource.close();
    }

    spinner.hidden = false;

    const reserveId = new URLSearchParams(location.search).get("id");
    const api = `/status/${reserveId}`;
    const streamURL = `/stream?channel=reserve-${reserveId}`;

    fetch(api)
    .then(r => r.ok ? r.json() : null)
    .then(st => {
        if (st) applyStatus(st);
        spinner.hidden = !!st;
    })
    .catch(console.error);

    const evt = new EventSource(streamURL);
    evt.addEventListener("status", ev => applyStatus(JSON.parse(ev.data)));
    evt.onerror = err => console.error("SSE error", err);

    function applyStatus(st){
        if (st.reserve === "APPROVED") { mark("reserve","success"); markLine(1); }
        if (st.reserve === "FAILED")   { mark("reserve","failed");  markLine(1,"failed"); finish(); return; }

        if (st.payment === "APPROVED") { mark("payment","success"); markLine(2); }
        if (st.payment === "DENIED")   { mark("payment","failed");  markLine(2,"failed"); finish(); return; }

        if (st.ticket  === "GENERATED"){ mark("ticket","success");  finish(); }
    }

    function finish(){ spinner.hidden = true; }

});
