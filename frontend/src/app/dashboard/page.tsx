"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api, WarehouseStatus } from "@/lib/api";
import { Workspace } from "@/components/workspace";

export default function DashboardPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [warehouseStatus, setWarehouseStatus] = useState<WarehouseStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (user?.organizations.length) {
      checkWarehouseStatus();
    } else {
      setIsLoading(false);
    }
  }, [user]);

  const checkWarehouseStatus = async () => {
    try {
      const orgId = user?.organizations[0]?.organization_id;
      if (orgId) {
        const status = await api.get<WarehouseStatus>(
          `/api/v1/organizations/${orgId}/warehouse`
        );
        setWarehouseStatus(status);

        // If no warehouse configured, redirect to onboarding
        if (!status.has_warehouse) {
          router.replace("/dashboard/onboarding");
          return;
        }
      }
    } catch (error) {
      console.error("Failed to check warehouse status:", error);
    } finally {
      setIsLoading(false);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading workspace...</p>
        </div>
      </div>
    );
  }

  if (!user?.organizations.length) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">No Organization</h2>
          <p className="mt-2 text-gray-600">
            You are not part of any organization yet.
          </p>
        </div>
      </div>
    );
  }

  if (!warehouseStatus?.has_warehouse) {
    return null; // Will redirect to onboarding
  }

  return (
    <Workspace
      orgId={user.organizations[0].organization_id}
      warehouseStatus={warehouseStatus}
    />
  );
}
