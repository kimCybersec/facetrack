"use client";

import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useLiveLogs } from "@/lib/useLiveLogs";
import { LiveGateTicker } from "@/components/LiveGateTicker";
import { ShieldCheck, ShieldX, Activity } from "lucide-react";

export default function GateMonitorPage() {
  const { data: history } = useQuery({
    queryKey: ["logs", "history"],
    queryFn: () => api.logs.list(50),
  });

  const { entries: liveEntries, connected } = useLiveLogs();

  // Merge live entries (newest) with the initial history fetch, de-duped by id.
  const allEntries = useMemo(() => {
    const seen = new Set<string>();
    const merged = [...liveEntries, ...(history ?? [])];
    return merged.filter((e) => {
      if (seen.has(e.id)) return false;
      seen.add(e.id);
      return true;
    });
  }, [liveEntries, history]);

  const grantedToday = allEntries.filter((e) => e.status === "GRANTED").length;
  const deniedToday = allEntries.filter((e) => e.status === "DENIED").length;

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display font-bold text-2xl">Gate Monitor</h1>
        <p className="text-sm text-[#8b939c] mt-1">Live access attempts across all active gates.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_260px] gap-6">
        <LiveGateTicker entries={allEntries} connected={connected} />

        <div className="space-y-4">
          <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] p-4">
            <div className="flex items-center gap-2 text-[#3ecf8e]">
              <ShieldCheck className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider text-[#8b939c]">Granted</span>
            </div>
            <p className="font-mono text-3xl font-bold mt-2">{grantedToday}</p>
          </div>

          <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] p-4">
            <div className="flex items-center gap-2 text-[#e5484d]">
              <ShieldX className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider text-[#8b939c]">Denied</span>
            </div>
            <p className="font-mono text-3xl font-bold mt-2">{deniedToday}</p>
          </div>

          <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] p-4">
            <div className="flex items-center gap-2 text-[#7c8791]">
              <Activity className="h-4 w-4" />
              <span className="text-xs uppercase tracking-wider text-[#8b939c]">Feed status</span>
            </div>
            <p className="text-sm mt-2 text-[#c7cdd2]">
              {connected ? "Streaming live" : "Reconnecting to server…"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
