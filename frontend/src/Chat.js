import React, { useState, useEffect, useRef } from 'react';
import { useParams, useLocation } from 'react-router-dom';

function Chat() {
  const { conversationId } = useParams();
  const location = useLocation();
  const [messages, setMessages] = useState([]);
  const [prompt, setPrompt] = useState('');
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);

  useEffect(() => {
    // Initialize WebSocket connection
    socketRef.current = new WebSocket('ws://localhost:8000');

    socketRef.current.onopen = () => {
      console.log('WebSocket connection established');
      const initialPrompt = location.state?.initialPrompt;
      if (initialPrompt) {
        setMessages((prevMessages) => [...prevMessages, { type: 'user', data: initialPrompt }]);
        socketRef.current.send(JSON.stringify({ prompt: initialPrompt, conversationId: conversationId }));
      }
    };

    socketRef.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'stream') {
        setMessages((prevMessages) => {
          const lastMessage = prevMessages[prevMessages.length - 1];
          if (lastMessage && lastMessage.type === 'bot-stream') {
            return [
              ...prevMessages.slice(0, prevMessages.length - 1),
              { ...lastMessage, data: lastMessage.data + message.data },
            ];
          } else {
            return [...prevMessages, { type: 'bot-stream', data: message.data }];
          }
        });
      } else if (message.type === 'result') {
        console.log('Command finished with return code:', message.returncode);
      }
    };

    socketRef.current.onclose = () => {
      console.log('WebSocket connection closed');
    };

    return () => {
      // Clean up WebSocket connection on component unmount
      socketRef.current.close();
    };
  }, [conversationId, location.state?.initialPrompt]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const sendMessage = () => {
    if (prompt.trim() === '') {
      return;
    }

    setMessages((prevMessages) => [...prevMessages, { type: 'user', data: prompt }]);
    socketRef.current.send(JSON.stringify({ prompt: prompt, conversationId: conversationId }));
    setPrompt('');
  };

  return (
    <div style={{ display: 'flex', height: '100vh' }}>
      <div style={{ flex: 1, borderRight: '1px solid #ccc', padding: '20px', display: 'flex', flexDirection: 'column' }}>
        <h2>Conversation: {conversationId}</h2>
        <div style={{ flexGrow: 1, overflowY: 'auto' }}>
          {messages.map((msg, index) => (
            <div key={index} style={{ textAlign: msg.type === 'user' ? 'right' : 'left', marginBottom: '10px' }}>
              <pre style={{ backgroundColor: '#eee', padding: '10px', borderRadius: '5px', whiteSpace: 'pre-wrap' }}>
                {msg.data}
              </pre>
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>
        <div style={{ display: 'flex', padding: '10px 0' }}>
          <input
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyPress={(e) => { if (e.key === 'Enter') sendMessage(); }}
            placeholder="Enter your prompt..."
            style={{ flexGrow: 1, padding: '10px', border: '1px solid #ccc', borderRadius: '5px' }}
          />
          <button onClick={sendMessage} style={{ marginLeft: '10px', padding: '10px 20px', border: 'none', backgroundColor: '#007bff', color: 'white', borderRadius: '5px', cursor: 'pointer' }}>
            Send
          </button>
        </div>
      </div>
      <div style={{ flex: 2, display: 'flex', justifyContent: 'center', alignItems: 'center' }}>
        <iframe
          src="http://localhost:3000" // Placeholder for the browser preview URL
          title="Browser Preview"
          style={{ width: '100%', height: '100%', border: 'none' }}
        ></iframe>
      </div>
    </div>
  );
}

export default Chat;