import { useState } from "react";
import { login, register, forgotPassword } from "../api.js";

export default function LoginPage({ onLogin }) {
  const [mode, setMode] = useState("login"); // "login" | "register" | "forgot"
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    try {
      if (mode === "login") {
        const data = await login(email, password);
        onLogin(data.user, data.workspace);
      } else if (mode === "register") {
        const data = await register(email, password, displayName);
        setSuccess(data.message || "Registration successful.");
        setMode("login");
        setPassword("");
      } else if (mode === "forgot") {
        await forgotPassword(email);
        setSuccess("If that email exists, a reset link has been sent.");
        setMode("login");
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  return (
    <div style={{
      minHeight: "100vh", background: "#07080b", display: "flex",
      alignItems: "center", justifyContent: "center", fontFamily: "'DM Sans',sans-serif",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet" />
      <style>{`html, body { background: #07080b !important; margin: 0; } @keyframes p{0%,100%{opacity:1}50%{opacity:.25}}`}</style>

      <div style={{ width: 360, padding: 32 }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 40, justifyContent: "center" }}>
          <div style={{
            width: 10, height: 10, borderRadius: "50%", background: "#34d399",
            boxShadow: "0 0 10px rgba(52,211,153,0.4)", animation: "p 2.5s infinite",
          }} />
          <span style={{
            fontSize: 16, fontWeight: 700, letterSpacing: "0.08em",
            color: "rgba(255,255,255,0.7)", fontFamily: "'JetBrains Mono',monospace",
          }}>SENTINEL</span>
        </div>

        {success && (
          <div style={{
            padding: "10px 14px", marginBottom: 16, borderRadius: 6,
            background: "rgba(52,211,153,0.06)", border: "1px solid rgba(52,211,153,0.2)",
            color: "rgba(52,211,153,0.8)", fontSize: 12, lineHeight: 1.5,
          }}>{success}</div>
        )}

        {error && (
          <div style={{
            padding: "10px 14px", marginBottom: 16, borderRadius: 6,
            background: "rgba(239,68,68,0.06)", border: "1px solid rgba(239,68,68,0.2)",
            color: "rgba(239,68,68,0.8)", fontSize: 12,
          }}>{error}</div>
        )}

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <input
              type="text"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Display name"
              style={inputStyle}
            />
          )}

          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="Email"
            required
            autoFocus
            style={inputStyle}
          />

          {mode !== "forgot" && (
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              minLength={mode === "register" ? 8 : 1}
              style={inputStyle}
            />
          )}

          <button type="submit" disabled={loading} style={{
            width: "100%", padding: "10px 0", borderRadius: 6,
            background: loading ? "rgba(52,211,153,0.04)" : "rgba(52,211,153,0.1)",
            border: "1px solid rgba(52,211,153,0.25)",
            color: "rgba(52,211,153,0.85)", fontSize: 13, fontWeight: 600,
            cursor: loading ? "wait" : "pointer", fontFamily: "'DM Sans',sans-serif",
            transition: "all 0.15s", marginTop: 4,
          }}>
            {loading ? "..." : mode === "login" ? "Sign In" : mode === "register" ? "Register" : "Send Reset Link"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 20, display: "flex", flexDirection: "column", gap: 8 }}>
          {mode === "login" && (
            <button
              onClick={() => { setMode("forgot"); setError(null); setSuccess(null); }}
              style={{
                background: "none", border: "none", color: "rgba(255,255,255,0.2)",
                fontSize: 11, cursor: "pointer", fontFamily: "'DM Sans',sans-serif",
              }}
            >
              Forgot password?
            </button>
          )}
          <button
            onClick={() => { setMode(mode === "login" ? "register" : "login"); setError(null); setSuccess(null); }}
            style={{
              background: "none", border: "none", color: "rgba(255,255,255,0.3)",
              fontSize: 12, cursor: "pointer", fontFamily: "'DM Sans',sans-serif",
            }}
          >
            {mode === "login" ? "Need an account? Register" : "Already have an account? Sign in"}
          </button>
        </div>
      </div>
    </div>
  );
}

const inputStyle = {
  width: "100%", boxSizing: "border-box", padding: "10px 12px",
  background: "rgba(255,255,255,0.03)", border: "1px solid rgba(255,255,255,0.08)",
  borderRadius: 6, color: "rgba(255,255,255,0.7)", fontSize: 13,
  fontFamily: "'DM Sans',sans-serif", outline: "none", marginBottom: 12,
};
