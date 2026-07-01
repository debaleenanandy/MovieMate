import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./Chatbot.css";

const API_BASE_URL = "http://localhost:5000";

const Chatbot = () => {
  const [inputType, setInputType] = useState("movie");
  const [userInput, setUserInput] = useState("");
  const [messages, setMessages] = useState([]);
  const [isTyping, setIsTyping] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [recommendations, setRecommendations] = useState([]);
  const [darkMode, setDarkMode] = useState(false);

 const chatboxRef = useRef(null);

  const movieRelatedQuestions = [
    "Suggest a thriller movie",
    "What are some popular comedy movies?",
    "Recommend a sci-fi movie",
    "Find me a highly-rated drama movie"
  ];

  useEffect(() => {
    if (chatboxRef.current) {
      chatboxRef.current.scrollTop = chatboxRef.current.scrollHeight;
    }
  }, [messages]);

  const speak = (text) => {
    const utter = new SpeechSynthesisUtterance(text);
    speechSynthesis.speak(utter);
  };

  const handleSpeechInput = () => {
    const SpeechRecognition =
      window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      alert("Speech recognition not supported");
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.start();
    setIsListening(true);

    recognition.onresult = (e) => {
      const speechText = e.results[0][0].transcript;
      setUserInput(speechText);
      handleSendMessage(speechText);
    };

    recognition.onend = () => setIsListening(false);
  };

const handleSendMessage = async (text) => {
  if (!text.trim()) return;

  const newMessages = [...messages, { sender: "user", text }];
  setMessages(newMessages);
  setUserInput("");
  setIsTyping(true);

  try {
    const res = await axios.post(`${API_BASE_URL}/recommend`, {
      input_type: inputType,
      user_input: text
    });

    let botMessage = { sender: "bot", text: "No response found." };

    if (res.data.error) {
      botMessage.text = res.data.error;
      setRecommendations([]); 
    } else if (res.data.recommendations && res.data.recommendations.length > 0) {
      setRecommendations(res.data.recommendations);
      botMessage.text = "Here are your movie recommendations 🎬";
    }  else {
    botMessage.text = "No movies found 😅";
    setRecommendations([]);
  }

    setTimeout(() => {
      setMessages([...newMessages, botMessage]);
      speak(botMessage.text);
      setIsTyping(false);
    }, 800);

  } catch (err) {
    console.error(err);
    setMessages([
      ...newMessages,
      { sender: "bot", text: "Server error. Try again later." }
    ]);
    setIsTyping(false);
  }
};


  return (
    <div className={`chat-container ${darkMode ? "dark-mode" : ""}`}>
      
      {/* LEFT PANEL */}
      <div className="recommendations-section">
        <h2>🎬 Recommendations</h2>

        <div className="recommendations-list">
          {recommendations.length === 0 && (
            <p style={{ textAlign: "center", opacity: 0.6 }}>
              Ask for a movie recommendation 👇
            </p>
          )}

          {recommendations.map((m, i) => (
            <div key={i} className="movie-card">
              <div className="movie-card-content">
                <div className="movie-title">{m.title}</div>
                <p>{m.genres}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT PANEL */}
      <div className="chat-section">
        <div className="chat-header">
          🎥 MovieMate
          <button
            className="dark-mode-toggle"
            onClick={() => setDarkMode(!darkMode)}
          >
            {darkMode ? "Light" : "Dark"}
          </button>
        </div>

        <div ref={chatboxRef} className="chatbox">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={msg.sender === "user" ? "user-message" : "bot-message"}
            >
              {msg.text}
            </div>
          ))}

          {isTyping && <div className="bot-message">Typing...</div>}
        </div>

        <div className="quick-replies">
          {movieRelatedQuestions.map((q, i) => (
            <button key={i} onClick={() => handleSendMessage(q)}>
              {q}
            </button>
          ))}
        </div>

        <div className="input-area">
          <select
            className="dropdown"
            value={inputType}
            onChange={(e) => setInputType(e.target.value)}
          >
            <option value="movie">Movie Name</option>
            <option value="mood">Mood</option>
            <option value="text">Text</option>
            <option value="cast">Cast Name</option>
          </select>
  {inputType === "cast" ? (
  <input
    className="input"
    type="text"
    placeholder="Enter actor / actress name"
    value={userInput}
    onChange={(e) => setUserInput(e.target.value)}
  />
) : (
  <input
    className="input"
    value={userInput}
    onChange={(e) => setUserInput(e.target.value)}
    placeholder="Type or speak..."
  />
)}


          <button
            className={`mic-button ${isListening ? "listening" : ""}`}
            onClick={handleSpeechInput}
            disabled={isListening}
          >
            🎤
          </button>

          <button
            className="send-button"
            onClick={() => handleSendMessage(userInput)}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default Chatbot;