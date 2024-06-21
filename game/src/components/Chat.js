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
    const websocket = initWebSocket((message) => {
      setMessages((prev) => [...prev, { text: message.message, from: 'npc' }]);
      setHealth(message.health);
      setPower(message.power);
      setCurrentDay(message.currentDay);
      setMessagesSent(message.messagesSent);
    });

    return () => websocket.close();
  }, []);

  const handleSendMessage = () => {
    setMessages((prev) => [...prev, { text: input, from: 'user' }]);
    sendMessage(input, health, power, currentDay, messagesSent);
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
