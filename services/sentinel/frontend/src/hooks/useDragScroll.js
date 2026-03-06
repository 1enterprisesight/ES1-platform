import { useRef, useEffect, useCallback } from 'react';

export default function useDragScroll(ref) {
  const isDragging = useRef(false);
  const startX = useRef(0);
  const scrollStart = useRef(0);
  const hasDragged = useRef(false);
  const lastX = useRef(0);
  const lastTime = useRef(0);
  const velocity = useRef(0);
  const momentumRef = useRef(null);

  const stopMomentum = useCallback(() => {
    if (momentumRef.current) {
      cancelAnimationFrame(momentumRef.current);
      momentumRef.current = null;
    }
  }, []);

  const onDown = useCallback((e) => {
    stopMomentum();
    isDragging.current = true;
    hasDragged.current = false;
    const x = e.clientX || e.touches?.[0]?.clientX || 0;
    startX.current = x;
    lastX.current = x;
    lastTime.current = Date.now();
    velocity.current = 0;
    scrollStart.current = ref.current?.scrollLeft || 0;
  }, [ref, stopMomentum]);

  const onMove = useCallback((e) => {
    if (!isDragging.current || !ref.current) return;
    const x = e.clientX || e.touches?.[0]?.clientX || 0;
    const diff = startX.current - x;
    if (Math.abs(diff) > 3) hasDragged.current = true;
    ref.current.scrollLeft = scrollStart.current + diff;
    const now = Date.now();
    const dt = now - lastTime.current;
    if (dt > 0) {
      velocity.current = (lastX.current - x) / dt * 16;
    }
    lastX.current = x;
    lastTime.current = now;
  }, [ref]);

  const onUp = useCallback(() => {
    if (!isDragging.current) return;
    isDragging.current = false;
    const v = velocity.current;
    if (Math.abs(v) > 0.5 && ref.current) {
      let vel = v;
      const coast = () => {
        if (!ref.current || Math.abs(vel) < 0.3) {
          momentumRef.current = null;
          return;
        }
        ref.current.scrollLeft += vel;
        vel *= 0.95;
        momentumRef.current = requestAnimationFrame(coast);
      };
      momentumRef.current = requestAnimationFrame(coast);
    }
  }, [ref]);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    el.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    el.addEventListener('touchstart', onDown, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onUp);
    return () => {
      stopMomentum();
      el.removeEventListener('mousedown', onDown);
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      el.removeEventListener('touchstart', onDown);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onUp);
    };
  }, [ref, onDown, onMove, onUp, stopMomentum]);

  return hasDragged;
}
