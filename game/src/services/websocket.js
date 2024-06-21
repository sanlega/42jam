let websocket;

export const initWebSocket = (onMessage) => {
  websocket = new WebSocket(`ws://localhost:8000/ws`);

  websocket.onopen = () => {
    console.log('WebSocket connection opened');
  };

  websocket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    onMessage(message);
    if (message.status) {
      websocket.close();  // Close the connection if the game has ended
    }
  };

  websocket.onerror = (error) => {
    console.error('WebSocket error', error);
  };

  websocket.onclose = () => {
    console.log('WebSocket connection closed');
  };

  return websocket;
};

export const sendMessage = (message, health, power, currentDay, messagesSent) => {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    const data = JSON.stringify({ message, health, power, currentDay, messagesSent });
    websocket.send(data);
  }
};
