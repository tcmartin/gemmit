import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
  const [prompt, setPrompt] = useState('');
  const navigate = useNavigate();

  const handleStartConversation = () => {
    if (prompt.trim() !== '') {
      // In a real application, you would make an API call here to start a new conversation
      // and get a conversationId. For now, we'll use a placeholder.
      const conversationId = 'new-conversation-' + Date.now();
      navigate(`/chat/${conversationId}`, { state: { initialPrompt: prompt } });
    }
  };

  return (
    <div>
      <h1>Welcome to Gemable!</h1>
      <input
        type="text"
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder="Start a new conversation..."
      />
      <button onClick={handleStartConversation}>Start Chat</button>
    </div>
  );
}

export default Home;
