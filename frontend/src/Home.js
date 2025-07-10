import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';

function Home() {
  const [prompt, setPrompt] = useState('');
  const navigate = useNavigate();

  const handleStartConversation = () => {
    if (prompt.trim() !== '') {
      const conversationId = 'new-conversation-' + Date.now();
      navigate(`/chat/${conversationId}`, { state: { initialPrompt: prompt } });
    }
  };

  const handlePillClick = (text) => {
    setPrompt(text + '.');
  };

  return (
    <>
      <header>
        <div className="logo">Lovable</div>

        <nav>
          <a href="#">Community</a>
          <a href="#">Pricing</a>
          <a href="#">Enterprise</a>
          <a href="#">Learn</a>
          <a href="#">Launched</a>
        </nav>

        <div className="actions">
          <a href="#" className="btn-outline">Log&nbsp;in</a>
          <a href="#" className="btn-primary">Get&nbsp;started</a>
        </div>
      </header>

      <main>
        <h1>Build something <span className="emoji">❤</span>&nbsp;Lovable</h1>
        <div className="tagline">Create apps and websites by chatting with AI</div>

        <div className="chat-box" data-component="prompt-box">
          <button className="attach" title="Attach file">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21.44 11.05L12 20.5a5 5 0 01-7.07-7.07l8.6-8.59a3 3 0 014.24 4.24l-8.48 8.48a1 1 0 01-1.42-1.42l8.37-8.37"/></svg>
          </button>

          <textarea
            placeholder="Ask Lovable to create a website for …"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleStartConversation();
              }
            }}
          ></textarea>

          <button className="send" title="Send" onClick={handleStartConversation}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M22 2L11 13"></path><path d="M22 2L15 22 11 13 2 9 22 2z"></path></svg>
          </button>
        </div>

        <div className="presets">
          <div className="pill" onClick={() => handlePillClick('Create a financial app')}>Create a financial app</div>
          <div className="pill" onClick={() => handlePillClick('Design a directory site')}>Design a directory site</div>
          <div className="pill" onClick={() => handlePillClick('Make a landing page')}>Make a landing page</div>
          <div className="pill" onClick={() => handlePillClick('Generate a CRM')}>Generate a CRM</div>
          <div className="pill" onClick={() => handlePillClick('Build a mobile app')}>Build a mobile app</div>
        </div>
      </main>

      <footer>©&nbsp;2025&nbsp;Your&nbsp;Company.&nbsp;All&nbsp;rights&nbsp;reserved.</footer>
    </>
  );
}

export default Home;