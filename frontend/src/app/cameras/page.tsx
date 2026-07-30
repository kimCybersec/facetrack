"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Camera } from "@/lib/api";
import { CameraCard } from "@/components/CameraCard";
import { ScanSearch, Loader2, PlusCircle } from "lucide-react";

export default function CamerasPage() {
  const queryClient = useQueryClient();
  const [showManualForm, setShowManualForm] = useState(false);
  const [manualError, setManualError] = useState<string | null>(null);

  const { data: cameras, isLoading } = useQuery({
    queryKey: ["cameras"],
    queryFn: api.cameras.list,
    refetchInterval: 10000,
  });

  const discoverMutation = useMutation({
    mutationFn: api.cameras.discover,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["cameras"] }),
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, active }: { id: string; active: boolean }) => api.cameras.toggle(id, active),
    onSuccess: (updated: Camera) => {
      queryClient.setQueryData<Camera[]>(["cameras"], (prev) =>
        prev ? prev.map((c) => (c.id === updated.id ? updated : c)) : prev
      );
    },
  });

  const manualMutation = useMutation({
    mutationFn: api.cameras.addManual,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cameras"] });
      setManualError(null);
      setShowManualForm(false);
    },
    onError: (err: Error) => setManualError(err.message),
  });

  function handleManualSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    const formData = new FormData(e.currentTarget);
    setManualError(null);
    manualMutation.mutate({
      name: String(formData.get("name")),
      nvr_ip: String(formData.get("nvr_ip")),
      channel: Number(formData.get("channel")),
      username: String(formData.get("username")),
      password: String(formData.get("password")),
      port: formData.get("port") ? Number(formData.get("port")) : 554,
      main_stream: formData.get("stream") !== "sub",
      location_label: String(formData.get("location_label") || "") || undefined,
    });
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display font-bold text-2xl">Cameras</h1>
          <p className="text-sm text-[#8b939c] mt-1">
            ZKTeco gate cameras discovered on the campus network.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setShowManualForm((v) => !v)}
            className="flex items-center gap-2 rounded-md border border-[#2a323a] px-4 py-2.5 text-sm font-semibold text-[#c7cdd2] hover:border-[#3ecf8e] transition-colors"
          >
            <PlusCircle className="h-4 w-4" />
            Add NVR channel
          </button>
          <button
            onClick={() => discoverMutation.mutate()}
            disabled={discoverMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0d12] hover:bg-[#35b87d] transition-colors disabled:opacity-60"
          >
            {discoverMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ScanSearch className="h-4 w-4" />
            )}
            Scan network
          </button>
        </div>
      </div>

      {showManualForm && (
        <form
          onSubmit={handleManualSubmit}
          className="mb-8 rounded-lg border border-[#1e252d] bg-[#0d1116] p-5 space-y-4"
        >
          <div>
            <h2 className="font-display font-bold text-sm uppercase tracking-wide text-[#c7cdd2]">
              Add a camera behind your NVR
            </h2>
            <p className="text-xs text-[#8b939c] mt-1">
              Use this when cameras plug into the NVR&apos;s own PoE ports and aren&apos;t
              individually reachable on the LAN — this pulls the stream through the NVR&apos;s
              per-channel RTSP path instead.
            </p>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">Camera name</label>
              <input
                name="name"
                required
                placeholder="e.g. Main Gate — Channel 1"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">NVR IP address</label>
              <input
                name="nvr_ip"
                required
                placeholder="192.168.1.152"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">Channel number</label>
              <input
                name="channel"
                type="number"
                min={1}
                required
                placeholder="1"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">Stream</label>
              <select
                name="stream"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              >
                <option value="main">Main (high quality)</option>
                <option value="sub">Sub (lower bandwidth)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">NVR username</label>
              <input
                name="username"
                required
                defaultValue="admin"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">NVR password</label>
              <input
                name="password"
                type="password"
                required
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">RTSP port (optional)</label>
              <input
                name="port"
                type="number"
                placeholder="554"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
            <div>
              <label className="block text-xs text-[#8b939c] mb-1.5">Location label (optional)</label>
              <input
                name="location_label"
                placeholder="e.g. Main Gate"
                className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              />
            </div>
          </div>

          {manualError && <p className="text-xs text-[#e5484d]">{manualError}</p>}

          <button
            type="submit"
            disabled={manualMutation.isPending}
            className="flex items-center gap-2 rounded-md bg-[#3ecf8e] px-4 py-2.5 text-sm font-semibold text-[#0a0d12] hover:bg-[#35b87d] transition-colors disabled:opacity-60"
          >
            {manualMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" />}
            Add camera
          </button>
        </form>
      )}

      {isLoading ? (
        <p className="text-sm text-[#5c6570]">Loading cameras…</p>
      ) : !cameras || cameras.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#2a323a] p-12 text-center">
          <p className="text-sm text-[#8b939c]">
            No cameras registered yet. If your cameras are behind an NVR, use{" "}
            <strong>Add NVR channel</strong> above — network scan only finds ONVIF devices
            directly reachable on the LAN.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {cameras.map((camera) => (
            <CameraCard
              key={camera.id}
              camera={camera}
              onToggle={(id, active) => toggleMutation.mutateAsync({ id, active })}
            />
          ))}
        </div>
      )}
    </div>
  );
}

