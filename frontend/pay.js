const pathParts = location.pathname.split("/").filter(Boolean);
const rid = pathParts[pathParts.length - 2];
const userId = pathParts[pathParts.length - 1];

document.getElementById("rid").textContent = rid;

document.getElementById("payForm").addEventListener("submit", e => {
    e.preventDefault();
    fetch(`/pay/${rid}/${userId}/confirm`, { method: "POST" })
        .then(() => {
            alert("Pagamento confirmado!");
            window.location.href = "reservation_status.html?id=" + rid;
        });
});

document.getElementById("denyBtn").addEventListener("click", e => {
    e.preventDefault();
    fetch(`/pay/${rid}/${userId}/deny`, { method: "POST" })
        .then(() => {
            alert("Pagamento recusado!");
            window.location.href = "reservation_status.html?id=" + rid;
        });
});
