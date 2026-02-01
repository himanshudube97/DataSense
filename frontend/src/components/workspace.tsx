"use client";

import { useState, useEffect, useRef } from "react";
import { api, Source, WarehouseStatus, WarehouseTable } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";

interface WorkspaceProps {
  orgId: string;
  warehouseStatus: WarehouseStatus;
}

export function Workspace({ orgId, warehouseStatus }: WorkspaceProps) {
  const [sources, setSources] = useState<Source[]>([]);
  const [tables, setTables] = useState<WarehouseTable[]>([]);
  const [isLoadingSources, setIsLoadingSources] = useState(true);
  const [isLoadingTables, setIsLoadingTables] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState("");
  const [syncingSourceId, setSyncingSourceId] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadSources();
    loadTables();
  }, [orgId]);

  const loadSources = async () => {
    try {
      const data = await api.get<Source[]>(`/api/v1/organizations/${orgId}/sources`);
      setSources(data);
    } catch (error) {
      console.error("Failed to load sources:", error);
    } finally {
      setIsLoadingSources(false);
    }
  };

  const loadTables = async () => {
    try {
      const data = await api.get<WarehouseTable[]>(
        `/api/v1/organizations/${orgId}/warehouse/tables`
      );
      setTables(data);
    } catch (error) {
      console.error("Failed to load tables:", error);
    } finally {
      setIsLoadingTables(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setUploadError("");

    try {
      const formData = new FormData();
      formData.append("file", file);
      formData.append("name", file.name.replace(".csv", ""));

      await api.postForm(`/api/v1/organizations/${orgId}/sources/csv`, formData);
      await loadSources();
    } catch (error) {
      setUploadError(error instanceof Error ? error.message : "Upload failed");
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    }
  };

  const handleSync = async (sourceId: string) => {
    setSyncingSourceId(sourceId);
    try {
      await api.post(`/api/v1/organizations/${orgId}/sources/${sourceId}/sync`);
      await loadSources();
      await loadTables();
    } catch (error) {
      console.error("Sync failed:", error);
    } finally {
      setSyncingSourceId(null);
    }
  };

  const handleDelete = async (sourceId: string) => {
    if (!confirm("Are you sure you want to delete this source?")) return;

    try {
      await api.delete(`/api/v1/organizations/${orgId}/sources/${sourceId}`);
      await loadSources();
    } catch (error) {
      console.error("Delete failed:", error);
    }
  };

  return (
    <div className="h-[calc(100vh-4rem)] flex">
      {/* Left Panel - Sources */}
      <div className="w-1/2 border-r border-gray-200 overflow-auto p-6">
        <div className="max-w-xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-lg font-semibold">Data Sources</h2>
            <div>
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileUpload}
                className="hidden"
                id="csv-upload"
              />
              <Button
                onClick={() => fileInputRef.current?.click()}
                disabled={isUploading}
                size="sm"
              >
                {isUploading ? "Uploading..." : "+ Upload CSV"}
              </Button>
            </div>
          </div>

          {uploadError && (
            <div className="mb-4 p-3 text-sm text-red-600 bg-red-50 rounded-md">
              {uploadError}
            </div>
          )}

          {isLoadingSources ? (
            <div className="text-center py-8 text-gray-500">Loading sources...</div>
          ) : sources.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                    />
                  </svg>
                </div>
                <h3 className="font-medium text-gray-900 mb-2">No sources yet</h3>
                <p className="text-sm text-gray-500 mb-4">
                  Upload a CSV file to get started
                </p>
                <Button
                  onClick={() => fileInputRef.current?.click()}
                  variant="outline"
                >
                  Upload CSV
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {sources.map((source) => (
                <Card key={source.id}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium">{source.name}</h3>
                        <p className="text-sm text-gray-500">
                          {source.source_type.toUpperCase()} • {source.column_count} columns
                          {source.warehouse_table_name && (
                            <span className="ml-2">
                              → <code className="text-xs bg-gray-100 px-1 rounded">
                                {source.warehouse_table_name}
                              </code>
                            </span>
                          )}
                        </p>
                        {source.last_synced_at && (
                          <p className="text-xs text-gray-400 mt-1">
                            Last synced: {new Date(source.last_synced_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleSync(source.id)}
                          disabled={syncingSourceId === source.id}
                        >
                          {syncingSourceId === source.id ? "Syncing..." : "Sync"}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          onClick={() => handleDelete(source.id)}
                          className="text-red-600 hover:text-red-700 hover:bg-red-50"
                        >
                          Delete
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel - Warehouse Tables */}
      <div className="w-1/2 overflow-auto p-6 bg-gray-50">
        <div className="max-w-xl mx-auto">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-semibold">Warehouse</h2>
              <p className="text-sm text-gray-500">
                {warehouseStatus.supabase_url?.replace("https://", "").split(".")[0]}
              </p>
            </div>
            <Button size="sm" variant="outline" onClick={loadTables}>
              Refresh
            </Button>
          </div>

          {isLoadingTables ? (
            <div className="text-center py-8 text-gray-500">Loading tables...</div>
          ) : tables.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center">
                <div className="w-12 h-12 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <svg
                    className="w-6 h-6 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4"
                    />
                  </svg>
                </div>
                <h3 className="font-medium text-gray-900 mb-2">No tables yet</h3>
                <p className="text-sm text-gray-500">
                  Sync a source to create tables in your warehouse
                </p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {tables.map((table) => (
                <Card key={table.name}>
                  <CardContent className="py-4">
                    <div className="flex items-center justify-between">
                      <div>
                        <h3 className="font-medium font-mono text-sm">{table.name}</h3>
                        <p className="text-sm text-gray-500">
                          {table.columns.length} columns
                          {table.row_count !== undefined && (
                            <span> • {table.row_count.toLocaleString()} rows</span>
                          )}
                        </p>
                      </div>
                    </div>
                    {table.columns.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-1">
                        {table.columns.slice(0, 5).map((col) => (
                          <span
                            key={col.name}
                            className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded"
                          >
                            {col.name}
                          </span>
                        ))}
                        {table.columns.length > 5 && (
                          <span className="text-xs text-gray-400 px-2 py-1">
                            +{table.columns.length - 5} more
                          </span>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
