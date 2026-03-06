import { useState, useEffect, useRef } from 'react';

export default function TypewriterText({ text, speed = 22, onComplete, style, started }) {
  const [charCount, setCharCount] = useState(0);
  const idx = useRef(0);

  useEffect(() => {
    if (!started || !text?.length) return;
    idx.current = 0;
    setCharCount(0);
    const interval = setInterval(() => {
      idx.current++;
      if (idx.current >= text.length) {
        setCharCount(text.length);
        clearInterval(interval);
        if (onComplete) onComplete();
      } else {
        setCharCount(idx.current);
      }
    }, speed);
    return () => clearInterval(interval);
  }, [text, speed, started]);

  if (!started || !text?.length) return <span style={{ ...style, visibility: "hidden" }}>{text || ""}</span>;
  const done = charCount >= text.length;
  return (
    <span style={{ position: "relative", ...style }}>
      <span style={{ visibility: "hidden" }}>{text}</span>
      <span style={{ position: "absolute", top: 0, left: 0, right: 0 }}>
        {text.slice(0, charCount)}
        <span style={{ opacity: done ? 0 : 1, transition: "opacity 0.3s", color: "#ffffff" }}>▎</span>
      </span>
    </span>
  );
}
