import { useEffect, useRef } from 'react';

export default function useSSE({ onInitialTiles, onNewTile, onStatus, onSilosReady }) {
  // Use refs so the SSE connection doesn't reconnect when callbacks change
  const cbRef = useRef({ onInitialTiles, onNewTile, onStatus, onSilosReady });
  cbRef.current = { onInitialTiles, onNewTile, onStatus, onSilosReady };

  useEffect(() => {
    let es = null;
    let reconnectTimer = null;
    let alive = true;
    let backoff = 3000; // start at 3s

    function resetBackoff() {
      backoff = 3000;
    }

    function nextBackoff() {
      const delay = backoff;
      backoff = Math.min(backoff * 2, 60000); // cap at 60s
      return delay;
    }

    function connect() {
      if (!alive) return;
      if (es) es.close();

      es = new EventSource('/api/stream');

      es.addEventListener('initial_tiles', (e) => {
        resetBackoff();
        try {
          const tiles = JSON.parse(e.data);
          cbRef.current.onInitialTiles?.(tiles);
        } catch (err) {
          console.error('Failed to parse initial_tiles:', err);
        }
      });

      es.addEventListener('new_tile', (e) => {
        try {
          const data = JSON.parse(e.data);
          cbRef.current.onNewTile?.(data.tile);
        } catch (err) {
          console.error('Failed to parse new_tile:', err);
        }
      });

      es.addEventListener('agent_thinking', (e) => {
        try {
          const data = JSON.parse(e.data);
          cbRef.current.onStatus?.('thinking', data);
        } catch { /* ignore */ }
      });

      es.addEventListener('agent_idle', () => {
        cbRef.current.onStatus?.('idle', {});
      });

      es.addEventListener('silos_ready', () => {
        cbRef.current.onSilosReady?.();
      });

      es.addEventListener('ping', () => {});

      es.onopen = () => {
        resetBackoff();
      };

      es.onerror = () => {
        es.close();
        if (alive) {
          reconnectTimer = setTimeout(connect, nextBackoff());
        }
      };
    }

    connect();

    return () => {
      alive = false;
      if (es) es.close();
      if (reconnectTimer) clearTimeout(reconnectTimer);
    };
  }, []); // empty deps — connect once, never reconnect due to state changes
}
