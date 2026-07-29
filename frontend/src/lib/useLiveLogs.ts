"use client";

import { useEffect, useRef, useState } from "react";
import { AccessLogEntry, liveLogsSocketUrl } from "./api";

const MAX_ENTRIES = 50;

export function useLiveLogs() {
  const [entries, setEntries] = useState<AccessLogEntry[]>([]);
  const [connected, setConnected] = useState(false);
  const socketRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    let retryTimeout: ReturnType<typeof setTimeout>;

    function connect() {
      const socket = new WebSocket(liveLogsSocketUrl());
      socketRef.current = socket;

      socket.onopen = () => {
        if (!cancelled) setConnected(true);
      };

      socket.onmessage = (event) => {
        try {
          const entry: AccessLogEntry = JSON.parse(event.data);
          setEntries((prev) => [entry, ...prev].slice(0, MAX_ENTRIES));
        } catch {
          // ignore malformed payloads
        }
      };

      socket.onclose = () => {
        if (cancelled) return;
        setConnected(false);
        retryTimeout = setTimeout(connect, 2000);
      };

      socket.onerror = () => {
        socket.close();
      };
    }

    connect();

    return () => {
      cancelled = true;
      clearTimeout(retryTimeout);
      socketRef.current?.close();
    };
  }, []);

  return { entries, connected };
}
