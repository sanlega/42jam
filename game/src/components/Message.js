import React from 'react';
import './Message.css';

function Message({ message }) {
  return (
    <div className={`message ${message.from}`}>
      {message.text}
    </div>
  );
}

export default Message;

