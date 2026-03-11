import { useState, useEffect } from 'react';
import LiveCard from './LiveCard.jsx';

export default function LiveCardSlot({ card, silo, onComplete, compact }) {
  const [expanded, setExpanded] = useState(false);
  const [settled, setSettled] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => requestAnimationFrame(() => setExpanded(true)));
    const t = setTimeout(() => setSettled(true), 550);
    return () => clearTimeout(t);
  }, []);

  return (
    <div style={{
      flex: "0 0 auto",
      width: expanded ? 270 : 0,
      minHeight: compact ? 105 : 140,
      overflow: settled ? "visible" : "hidden",
      transition: "width 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
    }}>
      <LiveCard card={card} silo={silo} onComplete={onComplete} expandReady={expanded} compact={compact} />
    </div>
  );
}
