import { useRef, useEffect } from 'react';
import useDragScroll from '../hooks/useDragScroll.js';
import StaticCard from './StaticCard.jsx';
import LiveCardSlot from './LiveCardSlot.jsx';

export default function ScrollRow({ row, zIndex, cards, getSilo, onCardClick, liveCard, onLiveComplete, compact, interactions, showScore, rowExtra }) {
  const scrollRef = useRef(null);
  const animRef = useRef(null);
  const hovRef = useRef(false);
  const pauseRef = useRef(false);
  const cardRefs = useRef({});
  const hasDragged = useDragScroll(scrollRef);

  useEffect(() => {
    if (liveCard) {
      pauseRef.current = true;
      if (scrollRef.current) scrollRef.current.scrollTo({ left: 0, behavior: "smooth" });
    }
  }, [liveCard]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el || cards.length === 0) return;
    // Only auto-scroll when we have enough cards for the infinite loop
    if (cards.length < 6) return;
    const tick = () => {
      if (!hovRef.current && !pauseRef.current) {
        el.scrollLeft += 0.3;
        const half = el.scrollWidth / 2;
        if (half > 0 && el.scrollLeft >= half) el.scrollLeft -= half;
      }
      animRef.current = requestAnimationFrame(tick);
    };
    animRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animRef.current);
  }, [cards.length]);

  const handleCardClick = (card) => { if (!hasDragged.current) onCardClick(card); };
  // Only duplicate for infinite scroll when we have enough cards to fill the viewport
  const displayCards = cards.length >= 6 && !liveCard ? [...cards, ...cards] : cards;

  const scrollToCard = (cardId) => {
    const el = cardRefs.current[cardId];
    const container = scrollRef.current;
    if (!el || !container) return;
    pauseRef.current = true;
    hovRef.current = true;
    const containerRect = container.getBoundingClientRect();
    const cardRect = el.getBoundingClientRect();
    const offset = cardRect.left - containerRect.left - (containerRect.width / 2) + (cardRect.width / 2);
    container.scrollBy({ left: offset, behavior: "smooth" });
    setTimeout(() => { pauseRef.current = false; hovRef.current = false; }, 4000);
  };

  return (
    <div style={{ marginBottom: compact ? 6 : 10, position: "relative", zIndex }}>
      <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "12px 24px 6px" }}>
        <span onClick={() => { if (cards.length > 0) scrollToCard(cards[0].id); }} style={{ fontSize: 10, fontWeight: row.bright ? 700 : 500, textTransform: "uppercase", letterSpacing: "0.1em", color: row.bright ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.4)", fontFamily: "'JetBrains Mono',monospace", cursor: cards.length > 0 ? "pointer" : "default", transition: "color 0.15s" }}
          onMouseEnter={e => { if (cards.length > 0) e.currentTarget.style.color = row.bright ? "rgba(255,255,255,0.95)" : "rgba(255,255,255,0.6)"; }}
          onMouseLeave={e => { e.currentTarget.style.color = row.bright ? "rgba(255,255,255,0.8)" : "rgba(255,255,255,0.4)"; }}
        >{row.label}</span>
        {rowExtra}
        <div style={{ display: "flex", alignItems: "center", gap: 4, marginLeft: 4 }}>
          {liveCard && <div style={{ width: 5, height: 5, borderRadius: "50%", background: getSilo(liveCard.silo).color, opacity: 0.9, boxShadow: liveCard.silo === "alpha" ? "0 0 4px rgba(255,255,255,0.4)" : "none", animation: "p 1s infinite" }} />}
          {cards.map(c => {
            const cs = getSilo(c.silo);
            return <div key={c.id} onClick={() => scrollToCard(c.id)} style={{ width: 5, height: 5, borderRadius: "50%", background: cs.color, opacity: c.silo === "alpha" ? 0.9 : 0.55, boxShadow: c.silo === "alpha" ? "0 0 4px rgba(255,255,255,0.3)" : "none", cursor: "pointer", transition: "transform 0.15s, opacity 0.15s" }}
              onMouseEnter={e => { e.currentTarget.style.transform = "scale(1.8)"; e.currentTarget.style.opacity = "1"; }}
              onMouseLeave={e => { e.currentTarget.style.transform = "scale(1)"; e.currentTarget.style.opacity = c.silo === "alpha" ? "0.9" : "0.55"; }}
            />;
          })}
        </div>
      </div>
      <div ref={scrollRef}
        onMouseEnter={() => { hovRef.current = true; }}
        onMouseLeave={() => { hovRef.current = false; }}
        style={{ display: "flex", gap: 12, overflowX: "auto", padding: compact ? "4px 24px 30px" : "4px 24px 14px", scrollbarWidth: "none", cursor: "grab", userSelect: "none", alignItems: "flex-start" }}>
        <style>{`div::-webkit-scrollbar{display:none}`}</style>
        {liveCard && <LiveCardSlot card={liveCard} silo={getSilo(liveCard.silo)} onComplete={onLiveComplete} compact={compact} />}
        {displayCards.length > 0 ? displayCards.map((c, i) => (
          <StaticCard key={`${c.id}-${i}`} card={c} silo={getSilo(c.silo)} onClick={handleCardClick} compact={compact} elRef={i < cards.length ? (el) => { if (el) cardRefs.current[c.id] = el; } : undefined} interaction={interactions?.[String(c.id)]} showScore={showScore} />
        )) : !liveCard && (
          <div style={{ flex: "0 0 auto", width: 180, height: compact ? 105 : 140, padding: "20px 16px", textAlign: "center", color: "rgba(255,255,255,0.06)", fontSize: 10, fontFamily: "'JetBrains Mono',monospace", border: "1px dashed rgba(255,255,255,0.03)", borderRadius: 10, display: "flex", alignItems: "center", justifyContent: "center" }}>Clear</div>
        )}
      </div>
    </div>
  );
}
