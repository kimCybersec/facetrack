"use client";

import { useState } from "react";
import { Camera as CameraType } from "@/lib/api";
import { Video, VideoOff, MapPin, Cpu } from "lucide-react";

interface Props {
  camera: CameraType;
  onToggle: (id: string, active: boolean) => Promise<unknown>;
}

export function CameraCard({ camera, onToggle }: Props) {
  const [pending, setPending] = useState(false);

  async function handleToggle() {
    setPending(true);
    try {
      await onToggle(camera.id, !camera.is_active);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] overflow-hidden flex flex-col">
      <div className="relative aspect-video bg-[#05070a] flex items-center justify-center">
        {camera.is_active ? (
          <div className="flex flex-col items-center gap-2 text-[#3ecf8e]">
            <Video className="h-8 w-8" strokeWidth={1.5} />
            <span className="font-mono text-[10px] tracking-wider text-[#5c6570]">
              RTSP STREAM ACTIVE
            </span>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2 text-[#3a4149]">
            <VideoOff className="h-8 w-8" strokeWidth={1.5} />
            <span className="font-mono text-[10px] tracking-wider">FEED OFFLINE</span>
          </div>
        )}
        <div className="absolute top-2 left-2 flex items-center gap-1.5 rounded bg-black/60 px-2 py-1">
          <span
            className={`h-1.5 w-1.5 rounded-full ${camera.is_active ? "bg-[#3ecf8e]" : "bg-[#5c6570]"}`}
          />
          <span className="font-mono text-[10px] text-[#c7cdd2]">
            {camera.is_active ? "RECOGNIZING" : "STANDBY"}
          </span>
        </div>
      </div>

      <div className="p-4 flex-1 flex flex-col gap-3">
        <div>
          <h3 className="font-display font-bold text-sm">{camera.name}</h3>
          <p className="text-xs text-[#8b939c]">{camera.manufacturer} {camera.model ?? ""}</p>
        </div>

        <div className="space-y-1 font-mono text-[11px] text-[#7c8791]">
          <div className="flex items-center gap-1.5">
            <Cpu className="h-3 w-3" /> {camera.ip_address}:{camera.onvif_port}
          </div>
          {camera.location_label && (
            <div className="flex items-center gap-1.5">
              <MapPin className="h-3 w-3" /> {camera.location_label}
            </div>
          )}
        </div>

        <div className="mt-auto flex items-center justify-between pt-2 border-t border-[#1a2027]">
          <span className="text-xs text-[#8b939c]">Gate recognition</span>
          <button
            onClick={handleToggle}
            disabled={pending}
            aria-pressed={camera.is_active}
            className={`relative h-6 w-11 rounded-full transition-colors disabled:opacity-50 focus:outline-none focus-visible:ring-2 focus-visible:ring-[#3ecf8e] focus-visible:ring-offset-2 focus-visible:ring-offset-[#0d1116] ${
              camera.is_active ? "bg-[#3ecf8e]" : "bg-[#2a323a]"
            }`}
          >
            <span
              className={`absolute top-0.5 h-5 w-5 rounded-full bg-[#0a0d12] transition-transform ${
                camera.is_active ? "translate-x-[22px]" : "translate-x-0.5"
              }`}
            />
          </button>
        </div>
      </div>
    </div>
  );
}
