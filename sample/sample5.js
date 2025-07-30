document.getElementById("contactForm").addEventListener("submit", function(e) {
  e.preventDefault();
  
  const name = document.getElementById("name").value.trim();
  const email = document.getElementById("email").value.trim();
  const message = document.getElementById("message").value.trim();

  if (!name || !email || !message) {
    document.getElementById("response").innerText = "All fields are required.";
    return;
  }

  document.getElementById("response").innerText = "Thank you for contacting us!";
  
  // Optional: Send to server here using fetch() or XMLHttpRequest
});
