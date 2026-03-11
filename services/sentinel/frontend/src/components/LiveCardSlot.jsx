import { useState, useEffect } from 'react';
import LiveCard from './LiveCard.jsx';

export default function LiveCardSlot({ card, silo, onComplete, compact }) {
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    requestAnimationFrame(() => requestAnimationFrame(() => setExpanded(true)));
  }, []);

  return (
    <div style={{
      flex: "0 0 auto",
      width: expanded ? 270 : 0,
      minHeight: compact ? 105 : 140,
      overflow: "hidden",
      transition: "width 0.5s cubic-bezier(0.4, 0, 0.2, 1)",
    }}>
      <LiveCard card={card} silo={silo} onComplete={onComplete} expandReady={expanded} compact={compact} />
    </div>
  );
}
