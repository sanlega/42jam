import React, { useState, useEffect } from 'react';
import Message from './Message';
import StatusPanel from './StatusPanel';
import { initWebSocket, sendMessage } from '../services/websocket';
import './Chat.css';

function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [health, setHealth] = useState(100);
  const [power, setPower] = useState(10);
  const [currentDay, setCurrentDay] = useState(1);
  const [messagesSent, setMessagesSent] = useState(0);

  useEffect(() => {
    const playerId = 1; // Replace this with the actual logic to get the player ID
    const websocket = initWebSocket(playerId, (message) => {
      const data = JSON.parse(message);
      setMessages((prev) => [...prev, { text: data.message, from: 'npc' }]);
      setHealth(data.health);
      setPower(data.power);
      setCurrentDay(data.currentDay);
      setMessagesSent(data.messagesSent);
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
      <div className="chat-box">
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
      <StatusPanel 
        health={health} 
        power={power} 
        currentDay={currentDay} 
        messagesSent={messagesSent} 
        messagesPerDay={5} 
      />
    </div>
  );
}

export default Chat;
