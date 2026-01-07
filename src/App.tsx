import { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [status, setStatus] = useState("Initializing Core Services");
  const [error, setError] = useState<string | null>(null);
  const [percent, setPercent] = useState(0);

  useEffect(() => {
    let attempts = 0;
    const checkBackend = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/setup/status");
        if (response.ok) {
          setPercent(100);
          setStatus("Matrix Synced");
          setTimeout(() => {
            window.location.href = "http://localhost:8000";
          }, 800);
        } else {
          throw new Error("Backend not ready");
        }
      } catch (err) {
        attempts++;
        if (attempts > 80) {
          setError("Connection Timeout: Backend Unresponsive");
          setStatus("System Link Failure");
        } else {
          const p = Math.min(95, Math.round((attempts / 80) * 100));
          setPercent(p);
          const messages = [
            "Synchronizing Neural Pathways",
            "Establishing Secure Uplink",
            "Calibrating Task Priorities",
            "Syncing with Notion Matrix",
            "Powering Up Intelligence Engine"
          ];
          setStatus(messages[attempts % messages.length]);
          setTimeout(checkBackend, 1200);
        }
      }
    };

    checkBackend();
  }, []);

  return (
    <main className="cortex-vibrant-loader">
      <div className="bg-blobs">
        <div className="blob blob-1"></div>
        <div className="blob blob-2"></div>
        <div className="blob blob-3"></div>
      </div>

      <div className="content-wrapper">
        <div className="header">
          <div className="status-badge">
            <div className="status-dot"></div>
            <span>System Initializing</span>
          </div>
          <h1 className="main-title">CORTEX</h1>
          <p className="subtitle">INTELLIGENCE AGENT & COMMAND CENTER</p>
        </div>

        <div className="loader-box glass">
          {!error ? (
            <>
              <div className="progress-info">
                <span className="status-label">{status}</span>
                <span className="percent-num">{percent}%</span>
              </div>
              <div className="progress-track">
                <div className="progress-bar-fill" style={{ width: `${percent}%` }}></div>
              </div>
            </>
          ) : (
            <div className="error-state">
              <div className="error-icon">⚡</div>
              <div className="error-title">CONNECTION INTERRUPTED</div>
              <div className="error-desc">{error}</div>
              <button className="reconnect-btn" onClick={() => window.location.reload()}>RETRY CONNECTION</button>
            </div>
          )}
        </div>

        <div className="footer-info">
          <span>v0.1.0-alpha • Secure Desktop Instance</span>
        </div>
      </div>

      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&family=Syncopate:wght@400;700&display=swap');

        :root {
          --cortex-purple: #9d50bb;
          --cortex-blue: #3b82f6;
          --cortex-pink: hsla(339, 49%, 30%, 1);
          --cortex-navy: hsla(225, 39%, 30%, 1);
          --bg-dark: #0b0f19;
        }

        .cortex-vibrant-loader {
          height: 100vh;
          background: var(--bg-dark);
          display: flex;
          justify-content: center;
          align-items: center;
          font-family: 'Outfit', sans-serif;
          color: #fff;
          overflow: hidden;
          position: relative;
        }

        .bg-blobs {
          position: absolute;
          inset: 0;
          z-index: 1;
        }

        .blob {
          position: absolute;
          width: 600px;
          height: 600px;
          border-radius: 50%;
          filter: blur(80px);
          opacity: 0.4;
          animation: float 20s infinite alternate;
        }

        .blob-1 {
          top: -100px;
          left: -100px;
          background: hsla(253, 16%, 7%, 1);
        }

        .blob-2 {
          top: -50px;
          right: -50px;
          background: var(--cortex-pink);
          animation-delay: -5s;
        }

        .blob-3 {
          bottom: -100px;
          left: 50%;
          transform: translateX(-50%);
          background: var(--cortex-navy);
          animation-delay: -10s;
        }

        @keyframes float {
          0% { transform: translate(0, 0) scale(1); }
          50% { transform: translate(100px, 50px) scale(1.1); }
          100% { transform: translate(-50px, 100px) scale(0.9); }
        }

        .content-wrapper {
          position: relative;
          z-index: 10;
          text-align: center;
          width: 440px;
          padding: 20px;
        }

        .header {
          margin-bottom: 64px;
          display: flex;
          flex-direction: column;
          align-items: center;
        }

        .status-badge {
          display: inline-flex;
          align-items: center;
          gap: 8px;
          background: rgba(59, 130, 246, 0.1);
          border: 1px solid rgba(59, 130, 246, 0.2);
          padding: 6px 14px;
          border-radius: 20px;
          font-size: 0.65rem;
          text-transform: uppercase;
          letter-spacing: 0.15rem;
          color: #60a5fa;
          margin-bottom: 32px;
          font-weight: 600;
        }

        .status-dot {
          width: 6px;
          height: 6px;
          background: #3b82f6;
          border-radius: 50%;
          box-shadow: 0 0 10px #3b82f6;
          animation: status-pulse 1.5s infinite;
        }

        @keyframes status-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.4; }
        }

        .main-title {
          font-family: 'Syncopate', sans-serif;
          font-size: 3rem;
          font-weight: 700;
          letter-spacing: 0.8rem;
          margin: 0;
          line-height: 1.2;
          padding-left: 0.8rem;
          background: linear-gradient(to bottom, #fff, #94a3b8);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          filter: drop-shadow(0 10px 20px rgba(0,0,0,0.5));
        }

        .subtitle {
          font-size: 0.7rem;
          color: #64748b;
          font-weight: 600;
          margin-top: 24px;
          letter-spacing: 0.4rem;
          text-transform: uppercase;
        }

        .glass {
          background: rgba(17, 24, 39, 0.4);
          backdrop-filter: blur(16px);
          border: 1px solid rgba(255, 255, 255, 0.08);
          box-shadow: 0 20px 50px rgba(0,0,0,0.5);
          border-radius: 24px;
        }

        .loader-box {
          padding: 32px;
          text-align: left;
        }

        .progress-info {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: 12px;
        }

        .status-label {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.7);
          font-weight: 400;
          letter-spacing: 0.02em;
        }

        .percent-num {
          font-size: 1.1rem;
          font-weight: 700;
          color: #60a5fa;
          font-variant-numeric: tabular-nums;
        }

        .progress-track {
          width: 100%;
          height: 4px;
          background: rgba(255, 255, 255, 0.05);
          border-radius: 2px;
          overflow: hidden;
        }

        .progress-bar-fill {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #9d50bb);
          box-shadow: 0 0 15px rgba(59, 130, 246, 0.3);
          transition: width 0.6s cubic-bezier(0.4, 0, 0.2, 1);
        }

        .footer-info {
          margin-top: 60px;
          font-size: 0.6rem;
          color: rgba(255, 255, 255, 0.15);
          text-transform: uppercase;
          letter-spacing: 0.2rem;
        }

        .error-state {
          text-align: center;
          padding: 10px 0;
        }

        .error-icon {
          font-size: 2rem;
          margin-bottom: 16px;
        }

        .error-title {
          color: #ef4444;
          font-weight: 700;
          font-size: 0.9rem;
          margin-bottom: 8px;
        }

        .error-desc {
          font-size: 0.8rem;
          color: rgba(255, 255, 255, 0.5);
          margin-bottom: 24px;
        }

        .reconnect-btn {
          background: rgba(239, 68, 68, 0.1);
          color: #ef4444;
          border: 1px solid rgba(239, 68, 68, 0.2);
          padding: 10px 24px;
          border-radius: 12px;
          font-size: 0.75rem;
          font-weight: 600;
          cursor: pointer;
          transition: all 0.3s;
        }

        .reconnect-btn:hover {
          background: #ef4444;
          color: #fff;
        }
      `}</style>
    </main>
  );
}

export default App;
