"use client";

import { useAuth } from "@/lib/auth";

export default function DashboardPage() {
  const { user } = useAuth();

  if (!user) return null;

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-zinc-900 dark:text-zinc-100">
        Dashboard
      </h2>

      <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Welcome back
        </h3>
        <p className="mt-1 text-xl font-semibold text-zinc-900 dark:text-zinc-100">
          {user.full_name}
        </p>
        <p className="mt-1 text-sm text-zinc-500">{user.email}</p>
      </div>

      <div className="rounded-xl border border-zinc-200 bg-white p-6 dark:border-zinc-800 dark:bg-zinc-900">
        <h3 className="mb-4 text-sm font-medium text-zinc-500 dark:text-zinc-400">
          Your Organizations
        </h3>
        <div className="space-y-3">
          {user.organizations.map((org) => (
            <div
              key={org.id}
              className="flex items-center justify-between rounded-lg border border-zinc-100 p-4 dark:border-zinc-800"
            >
              <div>
                <p className="font-medium text-zinc-900 dark:text-zinc-100">
                  {org.name}
                </p>
                <p className="text-sm text-zinc-500 capitalize">{org.role}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
