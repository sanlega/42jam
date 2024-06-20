let websocket;

export const initWebSocket = (onMessage) => {
  websocket = new WebSocket('ws://localhost:8000/ws');

  websocket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    onMessage(message);
  };

  return websocket;
};

export const sendMessage = (message) => {
  if (websocket && websocket.readyState === WebSocket.OPEN) {
    websocket.send(message);
  }
};

