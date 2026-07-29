"use client";

import { AccessLogEntry } from "@/lib/api";
import { CheckCircle2, XCircle } from "lucide-react";

function formatTime(ts: string): string {
  const date = new Date(ts);
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function Row({ entry }: { entry: AccessLogEntry }) {
  const granted = entry.status === "GRANTED";
  return (
    <div
      className={`flap-enter grid grid-cols-[90px_1fr_140px_90px] items-center gap-3 border-b border-[#1a2027] px-4 py-3 text-sm ${
        granted ? "bg-[#0f1a15]" : "bg-[#1a1113]"
      }`}
    >
      <span className="font-mono text-[11px] text-[#6b747d]">{formatTime(entry.timestamp)}</span>

      <span className="truncate font-medium">
        {entry.student_name ?? <span className="text-[#7a828b]">Unrecognized face</span>}
      </span>

      <span className="truncate text-xs text-[#8b939c]">{entry.camera_name ?? entry.camera_id.slice(0, 8)}</span>

      <span
        className={`flex items-center gap-1.5 justify-self-end text-xs font-semibold tracking-wide ${
          granted ? "text-[#3ecf8e]" : "text-[#e5484d]"
        }`}
      >
        {granted ? <CheckCircle2 className="h-3.5 w-3.5" /> : <XCircle className="h-3.5 w-3.5" />}
        {entry.status}
      </span>
    </div>
  );
}

export function LiveGateTicker({ entries, connected }: { entries: AccessLogEntry[]; connected: boolean }) {
  return (
    <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] overflow-hidden">
      <div className="flex items-center justify-between border-b border-[#1e252d] bg-[#11151b] px-4 py-3">
        <h2 className="font-display font-bold text-sm tracking-wide uppercase text-[#c7cdd2]">
          Live Gate Feed
        </h2>
        <div className="flex items-center gap-1.5 font-mono text-[11px] text-[#6b747d]">
          <span
            className={`h-1.5 w-1.5 rounded-full ${connected ? "bg-[#3ecf8e]" : "bg-[#e5484d]"}`}
          />
          {connected ? "LIVE" : "RECONNECTING"}
        </div>
      </div>

      <div className="grid grid-cols-[90px_1fr_140px_90px] gap-3 border-b border-[#1a2027] bg-[#0a0d12] px-4 py-2 font-mono text-[10px] uppercase tracking-wider text-[#5c6570]">
        <span>Time</span>
        <span>Identity</span>
        <span>Gate</span>
        <span className="text-right">Status</span>
      </div>

      <div className="max-h-[560px] overflow-y-auto">
        {entries.length === 0 ? (
          <div className="px-4 py-10 text-center text-sm text-[#5c6570]">
            No gate activity yet — events appear here the moment a camera reports one.
          </div>
        ) : (
          entries.map((entry) => <Row key={entry.id} entry={entry} />)
        )}
      </div>
    </div>
  );
}
