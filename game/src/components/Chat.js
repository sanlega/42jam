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
  const [gameStatus, setGameStatus] = useState(null);
  const [gameStarted, setGameStarted] = useState(false);

  useEffect(() => {
    const websocket = initWebSocket((message) => {
      if (message.status) {
        setGameStatus(message.status);
        setMessages((prev) => [...prev, { text: message.message, from: 'system' }]);
      } else {
        setMessages((prev) => [...prev, { text: message.message, from: 'npc' }]);
        setHealth(message.health);
        setPower(message.power);
        setCurrentDay(message.currentDay);
        setMessagesSent(message.messagesSent);
      }
    });

    return () => websocket.close();
  }, []);

  const handleSendMessage = () => {
    setMessages((prev) => [...prev, { text: input, from: 'user' }]);
    sendMessage(input, health, power, currentDay, messagesSent);
    setInput('');
  };

  const handleStartGame = () => {
    setGameStarted(true);
    sendMessage("start", health, power, currentDay, messagesSent);
  };

  return (
    <div className="chat-container">
      <div className="chat-box">
        <div className="header">
          <h1>Castle</h1>
        </div>
        <div className="messages">
          {messages.map((msg, index) => (
            <Message key={index} message={msg} />
          ))}
        </div>
        {gameStatus ? (
          <div className="game-over">
            <h2>Game Over</h2>
            <p>{messages[messages.length - 1].text}</p>
          </div>
        ) : gameStarted ? (
          <div className="input-container">
            <input 
              value={input} 
              onChange={(e) => setInput(e.target.value)} 
              placeholder="Type a message" 
            />
            <button onClick={handleSendMessage}>Send</button>
          </div>
        ) : (
          <div className="start-container">
            <button onClick={handleStartGame}>Start Game</button>
          </div>
        )}
      </div>
      <div className="side-panel">
        <div className="image-box"></div>
        <StatusPanel 
          health={health} 
          power={power} 
          currentDay={currentDay} 
          messagesSent={messagesSent} 
          messagesPerDay={5} 
        />
      </div>
    </div>
  );
}

export default Chat;
