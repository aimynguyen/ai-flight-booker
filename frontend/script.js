const form = document.getElementById("chat-form");
const input = document.getElementById("message-input");
const chatBox = document.getElementById("chat-box");

function addMessage(message, sender) {
  const messageDiv = document.createElement("div");

  messageDiv.className = `message ${sender}`;

  const avatar = document.createElement("div");

  avatar.className =
    sender === "user" ? "avatar user-avatar" : "avatar bot-avatar";

  avatar.textContent = sender === "user" ? "👤" : "✦";

  const wrapper = document.createElement("div");

  wrapper.className = "message-wrapper";

  const senderName = document.createElement("div");

  senderName.className = "sender";

  senderName.innerHTML =
    sender === "user"
      ? "You <span>•</span> Just now"
      : "SkyMate AI <span>•</span> Just now";

  const content = document.createElement("div");

  content.className = "message-content";

  content.innerHTML = message.replace(/\n/g, "<br>");

  wrapper.appendChild(senderName);

  wrapper.appendChild(content);

  messageDiv.appendChild(avatar);

  messageDiv.appendChild(wrapper);

  chatBox.appendChild(messageDiv);

  chatBox.scrollTop = chatBox.scrollHeight;

  return messageDiv;
}

function useSuggestion(text) {
  input.value = text;

  input.focus();
}

function newChat() {
  chatBox.innerHTML = `

        <div class="welcome">

            <div class="welcome-icon">
                ✈
            </div>

            <h2>
                Where would you like to fly?
            </h2>

            <p>
                I can search, book and complete your flight
                reservation using your requirements.
            </p>

        </div>

    `;

  addMessage(
    "Hi! I'm your AI flight booking assistant. Tell me where you want to fly and I'll find the best valid option for you.",
    "bot",
  );
}

form.addEventListener("submit", async function (event) {
  event.preventDefault();

  const message = input.value.trim();

  if (!message) {
    return;
  }

  addMessage(message, "user");

  input.value = "";

  input.disabled = true;

  const loadingMessage = addMessage("Thinking...", "bot");

  try {
    const response = await fetch("/chat", {
      method: "POST",

      headers: {
        "Content-Type": "application/json",
      },

      body: JSON.stringify({
        message: message,
      }),
    });

    const data = await response.json();

    loadingMessage.remove();

    addMessage(data.reply, "bot");
  } catch (error) {
    loadingMessage.remove();

    addMessage("Sorry, something went wrong. Please try again.", "bot");

    console.error(error);
  }

  input.disabled = false;

  input.focus();
});
