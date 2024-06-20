import React, { useState, useEffect } from 'react';
import Message from './Message';
import { initWebSocket, sendMessage } from '../services/websocket';
import './Chat.css';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  useEffect(() => {
    const websocket = initWebSocket((message) => {
      setMessages((prev) => [...prev, { text: message, from: 'npc' }]);
    });

    return () => websocket.close();
  }, []);

  const handleSendMessage = () => {
    setMessages((prev) => [...prev, { text: input, from: 'user' }]);
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, index) => (
          <Message key={index} message={msg} />
        ))}
      </div>
      <div className="input-container">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          placeholder="Type a message" 
        />
        <button onClick={handleSendMessage}>Send</button>
      </div>
    </div>
  );
}

export default Chat;

