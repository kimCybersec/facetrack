"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { UserPlus, Loader2, ImagePlus } from "lucide-react";

export default function StudentsPage() {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [preview, setPreview] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data: students, isLoading } = useQuery({
    queryKey: ["students"],
    queryFn: api.students.list,
  });

  const enrollMutation = useMutation({
    mutationFn: api.students.enroll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["students"] });
      setPreview(null);
      setError(null);
      formRef.current?.reset();
    },
    onError: (err: Error) => setError(err.message),
  });

  const formRef = useRef<HTMLFormElement | null>(null);

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setPreview(URL.createObjectURL(file));
  }

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    const formData = new FormData(e.currentTarget);
    enrollMutation.mutate(formData);
  }

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="font-display font-bold text-2xl">Students</h1>
        <p className="text-sm text-[#8b939c] mt-1">
          Enroll a student photo to generate their gate-recognition embedding.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-6">
        <form
          ref={formRef}
          onSubmit={handleSubmit}
          className="rounded-lg border border-[#1e252d] bg-[#0d1116] p-5 space-y-4 h-fit"
        >
          <h2 className="font-display font-bold text-sm uppercase tracking-wide text-[#c7cdd2]">
            Enroll Student
          </h2>

          <div>
            <label className="block text-xs text-[#8b939c] mb-1.5">Student number</label>
            <input
              name="student_number"
              required
              className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              placeholder="e.g. UGSC/2024/0123"
            />
          </div>

          <div>
            <label className="block text-xs text-[#8b939c] mb-1.5">Full name</label>
            <input
              name="full_name"
              required
              className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              placeholder="Full legal name"
            />
          </div>

          <div>
            <label className="block text-xs text-[#8b939c] mb-1.5">Program (optional)</label>
            <input
              name="program"
              className="w-full rounded-md bg-[#161b21] border border-[#2a323a] px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-[#3ecf8e]"
              placeholder="e.g. BSc Computer Science"
            />
          </div>

          <div>
            <label className="block text-xs text-[#8b939c] mb-1.5">Photo</label>
            <button
              type="button"
              onClick={() => fileInputRef.current?.click()}
              className="w-full flex items-center justify-center gap-2 rounded-md border border-dashed border-[#2a323a] bg-[#161b21] py-6 text-sm text-[#8b939c] hover:border-[#3ecf8e] hover:text-[#c7cdd2] transition-colors overflow-hidden"
            >
              {preview ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={preview} alt="Preview" className="h-24 w-24 object-cover rounded-md" />
              ) : (
                <>
                  <ImagePlus className="h-4 w-4" /> Choose a clear front-facing photo
                </>
              )}
            </button>
            <input
              ref={fileInputRef}
              name="photo"
              type="file"
              accept="image/*"
              required
              onChange={handleFileChange}
              className="hidden"
            />
          </div>

          {error && <p className="text-xs text-[#e5484d]">{error}</p>}

          <button
            type="submit"
            disabled={enrollMutation.isPending}
            className="w-full flex items-center justify-center gap-2 rounded-md bg-[#3ecf8e] py-2.5 text-sm font-semibold text-[#0a0d12] hover:bg-[#35b87d] transition-colors disabled:opacity-60"
          >
            {enrollMutation.isPending ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <UserPlus className="h-4 w-4" />
            )}
            Enroll student
          </button>
        </form>

        <div className="rounded-lg border border-[#1e252d] bg-[#0d1116] overflow-hidden h-fit">
          <div className="grid grid-cols-[1fr_1fr_1fr_80px] gap-3 border-b border-[#1a2027] bg-[#11151b] px-4 py-2.5 font-mono text-[10px] uppercase tracking-wider text-[#5c6570]">
            <span>Name</span>
            <span>Student No.</span>
            <span>Program</span>
            <span className="text-right">Status</span>
          </div>
          {isLoading ? (
            <p className="px-4 py-6 text-sm text-[#5c6570]">Loading roster…</p>
          ) : !students || students.length === 0 ? (
            <p className="px-4 py-6 text-sm text-[#8b939c]">No students enrolled yet.</p>
          ) : (
            students.map((student) => (
              <div
                key={student.id}
                className="grid grid-cols-[1fr_1fr_1fr_80px] gap-3 border-b border-[#1a2027] px-4 py-3 text-sm items-center"
              >
                <span className="truncate font-medium">{student.full_name}</span>
                <span className="truncate font-mono text-xs text-[#8b939c]">{student.student_number}</span>
                <span className="truncate text-xs text-[#8b939c]">{student.program ?? "—"}</span>
                <span
                  className={`text-right text-xs font-semibold ${
                    student.is_active ? "text-[#3ecf8e]" : "text-[#5c6570]"
                  }`}
                >
                  {student.is_active ? "ACTIVE" : "INACTIVE"}
                </span>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
