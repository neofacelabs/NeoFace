"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { useQuery } from "@tanstack/react-query";
import { CheckCircle2, XCircle, ChevronLeft, ChevronRight } from "lucide-react";
import { usersApi } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { AdminGuard } from "@/components/admin-guard";

interface UserList {
  total: number; page: number; page_size: number;
  users: Array<{ id: string; name: string; email: string; role: string; is_active: boolean; is_enrolled: boolean; created_at: string }>;
}

export default function UsersPage() {
  const [page, setPage] = useState(1);
  const { data, isLoading } = useQuery<UserList>({
    queryKey: ["users", page],
    queryFn: () => usersApi.list(page, 20).then(r => r.data),
  });
  const totalPages = data ? Math.ceil(data.total / 20) : 1;

  return (
    <AdminGuard>
    <div className="space-y-5">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">User Management</h1>
        <p className="text-[13px] text-[rgba(255,255,255,0.35)] mt-0.5">
          {data ? `${data.total.toLocaleString()} registered users platform-wide` : "Loading…"}
        </p>
      </div>

      <div className="rounded-2xl border border-[rgba(255,255,255,0.07)] bg-[rgba(255,255,255,0.025)] overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 gap-3 px-5 py-3 border-b border-[rgba(255,255,255,0.06)]">
          {["User", "Role", "Enrolled", "Status", "Joined"].map((h, i) => (
            <div key={h} className={`text-[10px] font-semibold text-[rgba(255,255,255,0.28)] uppercase tracking-wider ${i === 0 ? "col-span-4" : "col-span-2"}`}>
              {h}
            </div>
          ))}
        </div>

        {isLoading ? (
          <div className="p-5 space-y-2.5">
            {[...Array(8)].map((_, i) => <div key={i} className="h-12 rounded-xl bg-[rgba(255,255,255,0.03)] animate-pulse" />)}
          </div>
        ) : (
          <div className="divide-y divide-[rgba(255,255,255,0.04)]">
            {data?.users.map((user, i) => (
              <motion.div
                key={user.id}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: i * 0.03 }}
                className="grid grid-cols-12 gap-3 px-5 py-4 hover:bg-[rgba(255,255,255,0.02)] transition-colors"
              >
                <div className="col-span-4 flex items-center gap-3">
                  <div className="w-7 h-7 rounded-full bg-[rgba(124,124,255,0.15)] border border-[rgba(124,124,255,0.2)] flex items-center justify-center text-[11px] font-bold text-[#a5b4fc] shrink-0">
                    {user.name[0]?.toUpperCase()}
                  </div>
                  <div className="min-w-0">
                    <p className="text-[13px] text-white font-medium truncate">{user.name}</p>
                    <p className="text-[11px] text-[rgba(255,255,255,0.3)] truncate">{user.email}</p>
                  </div>
                </div>
                <div className="col-span-2 flex items-center">
                  <Badge variant={user.role === "admin" ? "default" : "ghost"}>{user.role}</Badge>
                </div>
                <div className="col-span-2 flex items-center">
                  {user.is_enrolled
                    ? <span className="flex items-center gap-1.5 text-[12px] text-[#34d399]"><CheckCircle2 size={13} />Yes</span>
                    : <span className="flex items-center gap-1.5 text-[12px] text-[rgba(255,255,255,0.3)]"><XCircle size={13} />No</span>}
                </div>
                <div className="col-span-2 flex items-center">
                  <Badge variant={user.is_active ? "success" : "error"}>
                    {user.is_active ? "Active" : "Inactive"}
                  </Badge>
                </div>
                <div className="col-span-2 flex items-center">
                  <span className="text-[11px] text-[rgba(255,255,255,0.28)]">{formatDate(user.created_at)}</span>
                </div>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      <div className="flex items-center justify-between">
        <p className="text-[12px] text-[rgba(255,255,255,0.3)]">Page {page} of {totalPages}</p>
        <div className="flex gap-2">
          <button disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="w-8 h-8 rounded-lg border border-[rgba(255,255,255,0.07)] flex items-center justify-center text-[rgba(255,255,255,0.4)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] disabled:opacity-30 disabled:cursor-not-allowed transition-all">
            <ChevronLeft size={14} />
          </button>
          <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)} className="w-8 h-8 rounded-lg border border-[rgba(255,255,255,0.07)] flex items-center justify-center text-[rgba(255,255,255,0.4)] hover:text-white hover:bg-[rgba(255,255,255,0.04)] disabled:opacity-30 disabled:cursor-not-allowed transition-all">
            <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </div>
    </AdminGuard>
  );
}
