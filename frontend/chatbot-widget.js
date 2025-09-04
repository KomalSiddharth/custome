(function () {
  // Create floating button
  const button = document.createElement("button");
  button.id = "chatbot-button";
  button.innerHTML = "💬";
  document.body.appendChild(button);

  // Create chatbot window
  const windowDiv = document.createElement("div");
  windowDiv.id = "chatbot-window";
  windowDiv.innerHTML = `
    <div id="chatbot-header">Mitesh AI Assistant</div>
    <div id="chatbot-messages"></div>
    <div id="chatbot-input">
      <input type="text" id="chatbot-text" placeholder="Type or speak..."/>
      <button id="chatbot-voice">🎤</button>
      <button id="chatbot-send">➤</button>
    </div>
  `;
  document.body.appendChild(windowDiv);

  const messagesDiv = windowDiv.querySelector("#chatbot-messages");
  const inputField = windowDiv.querySelector("#chatbot-text");
  const sendBtn = windowDiv.querySelector("#chatbot-send");
  const voiceBtn = windowDiv.querySelector("#chatbot-voice");

  // Toggle chat window
  button.addEventListener("click", () => {
    windowDiv.style.display =
      windowDiv.style.display === "flex" ? "none" : "flex";
    if (windowDiv.style.display === "flex") {
      windowDiv.style.flexDirection = "column";
    }
  });

  // Add message to chat
  function addMessage(text, sender) {
    const msg = document.createElement("div");
    msg.classList.add("chatbot-msg", sender);
    msg.innerText = text;
    messagesDiv.appendChild(msg);
    messagesDiv.scrollTop = messagesDiv.scrollHeight;
  }

  // Handle send
  async function sendMessage() {
    const text = inputField.value.trim();
    if (!text) return;
    addMessage(text, "user");
    inputField.value = "";

    try {
      const res = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await res.json();
      addMessage(data.reply, "bot");

      // Text-to-Speech for bot reply
      if ("speechSynthesis" in window) {
        const utterance = new SpeechSynthesisUtterance(data.reply);
        utterance.lang = "en-IN"; // English (India)
        speechSynthesis.speak(utterance);
      }
    } catch (err) {
      addMessage("⚠️ Error connecting to server.", "bot");
    }
  }

  sendBtn.addEventListener("click", sendMessage);
  inputField.addEventListener("keypress", (e) => {
    if (e.key === "Enter") sendMessage();
  });

  // Speech-to-Text (Voice input)
  if ("webkitSpeechRecognition" in window) {
    const recognition = new webkitSpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = "en-US";

    voiceBtn.addEventListener("click", () => {
      recognition.start();
      voiceBtn.innerText = "🎙";
    });

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript;
      inputField.value = transcript;
      voiceBtn.innerText = "🎤";
      sendMessage(); // auto-send after speaking
    };

    recognition.onerror = () => {
      voiceBtn.innerText = "🎤";
      alert("⚠️ Voice recognition error. Try again.");
    };
  } else {
    voiceBtn.disabled = true;
    voiceBtn.title = "Voice not supported in this browser";
  }
})();
