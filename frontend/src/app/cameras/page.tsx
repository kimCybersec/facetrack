"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, Camera } from "@/lib/api";
import { CameraCard } from "@/components/CameraCard";
import { ScanSearch, Loader2 } from "lucide-react";

export default function CamerasPage() {
  const queryClient = useQueryClient();

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

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="font-display font-bold text-2xl">Cameras</h1>
          <p className="text-sm text-[#8b939c] mt-1">
            ZKTeco gate cameras discovered on the campus network.
          </p>
        </div>
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

      {isLoading ? (
        <p className="text-sm text-[#5c6570]">Loading cameras…</p>
      ) : !cameras || cameras.length === 0 ? (
        <div className="rounded-lg border border-dashed border-[#2a323a] p-12 text-center">
          <p className="text-sm text-[#8b939c]">
            No cameras registered yet. Run a network scan to discover ZKTeco devices on the gate subnet.
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
