"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { api } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export default function OnboardingPage() {
  const router = useRouter();
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  const [supabaseUrl, setSupabaseUrl] = useState("");
  const [supabaseKey, setSupabaseKey] = useState("");
  const [schemaName, setSchemaName] = useState("public");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const orgId = user?.organizations[0]?.organization_id;

  const handleTestConnection = async () => {
    if (!orgId) return;

    setIsTesting(true);
    setError("");
    setTestResult(null);

    try {
      // First save the connection
      await api.post(`/api/v1/organizations/${orgId}/warehouse`, {
        supabase_url: supabaseUrl,
        supabase_key: supabaseKey,
        schema_name: schemaName,
      });

      // Then test it
      const result = await api.post<{ success: boolean; message: string; tables_found: number }>(
        `/api/v1/organizations/${orgId}/warehouse/test`
      );

      setTestResult({
        success: result.success,
        message: result.success
          ? `Connected! Found ${result.tables_found} tables.`
          : result.message,
      });

      if (result.success) {
        setStep(2);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to connect");
    } finally {
      setIsTesting(false);
    }
  };

  const handleFinish = () => {
    router.push("/dashboard");
  };

  if (!user?.organizations.length) {
    return (
      <div className="flex items-center justify-center h-[calc(100vh-4rem)]">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">No Organization</h2>
          <p className="mt-2 text-gray-600">
            You need to be part of an organization to continue.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] flex items-center justify-center px-4 py-8">
      <div className="w-full max-w-xl">
        {/* Progress indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-center gap-2">
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= 1 ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600"
              }`}
            >
              1
            </div>
            <div className={`w-16 h-1 ${step >= 2 ? "bg-blue-600" : "bg-gray-200"}`} />
            <div
              className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
                step >= 2 ? "bg-blue-600 text-white" : "bg-gray-200 text-gray-600"
              }`}
            >
              2
            </div>
          </div>
          <div className="flex justify-center mt-2">
            <span className="text-sm text-gray-600">
              {step === 1 ? "Connect Warehouse" : "Ready to Go!"}
            </span>
          </div>
        </div>

        {step === 1 && (
          <Card>
            <CardHeader>
              <CardTitle>Connect Your Data Warehouse</CardTitle>
              <CardDescription>
                Connect to your Supabase project where your transformed data will be stored.
                Your data stays in your own account.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Supabase signup link */}
              <div className="p-4 bg-blue-50 rounded-lg">
                <p className="text-sm text-blue-800">
                  Don&apos;t have a Supabase account?{" "}
                  <a
                    href="https://supabase.com/dashboard"
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-medium underline"
                  >
                    Create one for free
                  </a>
                </p>
                <p className="text-xs text-blue-600 mt-1">
                  Free tier includes 500MB of storage
                </p>
              </div>

              {error && (
                <div className="p-3 text-sm text-red-600 bg-red-50 rounded-md">
                  {error}
                </div>
              )}

              {testResult && (
                <div
                  className={`p-3 text-sm rounded-md ${
                    testResult.success
                      ? "text-green-600 bg-green-50"
                      : "text-red-600 bg-red-50"
                  }`}
                >
                  {testResult.message}
                </div>
              )}

              <div className="space-y-4">
                <div className="space-y-2">
                  <label htmlFor="supabaseUrl" className="text-sm font-medium">
                    Supabase Project URL
                  </label>
                  <Input
                    id="supabaseUrl"
                    type="url"
                    placeholder="https://your-project.supabase.co"
                    value={supabaseUrl}
                    onChange={(e) => setSupabaseUrl(e.target.value)}
                    disabled={isLoading || isTesting}
                  />
                  <p className="text-xs text-gray-500">
                    Found in Project Settings → API → Project URL
                  </p>
                </div>

                <div className="space-y-2">
                  <label htmlFor="supabaseKey" className="text-sm font-medium">
                    Supabase Service Role Key
                  </label>
                  <Input
                    id="supabaseKey"
                    type="password"
                    placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI..."
                    value={supabaseKey}
                    onChange={(e) => setSupabaseKey(e.target.value)}
                    disabled={isLoading || isTesting}
                  />
                  <p className="text-xs text-gray-500">
                    Found in Project Settings → API → Service Role Key (secret)
                  </p>
                </div>

                <div className="space-y-2">
                  <label htmlFor="schemaName" className="text-sm font-medium">
                    Schema Name
                  </label>
                  <Input
                    id="schemaName"
                    type="text"
                    placeholder="public"
                    value={schemaName}
                    onChange={(e) => setSchemaName(e.target.value)}
                    disabled={isLoading || isTesting}
                  />
                  <p className="text-xs text-gray-500">
                    Usually &quot;public&quot;, or create a custom schema for your data
                  </p>
                </div>
              </div>

              <Button
                onClick={handleTestConnection}
                className="w-full"
                size="lg"
                disabled={!supabaseUrl || !supabaseKey || isTesting}
              >
                {isTesting ? "Testing Connection..." : "Connect & Test"}
              </Button>
            </CardContent>
          </Card>
        )}

        {step === 2 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-center">You&apos;re All Set!</CardTitle>
              <CardDescription className="text-center">
                Your warehouse is connected. Now you can start adding data sources
                and transforming your data.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 bg-green-50 rounded-lg text-center">
                <div className="w-12 h-12 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-3">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <p className="text-green-800 font-medium">Warehouse Connected</p>
                <p className="text-sm text-green-600 mt-1">{supabaseUrl}</p>
              </div>

              <div className="space-y-3">
                <h3 className="font-medium">Next Steps:</h3>
                <ul className="space-y-2 text-sm text-gray-600">
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">1.</span>
                    Upload a CSV file or connect Google Sheets
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">2.</span>
                    Sync your data to the warehouse
                  </li>
                  <li className="flex items-start gap-2">
                    <span className="text-blue-600">3.</span>
                    Transform and analyze your data
                  </li>
                </ul>
              </div>

              <Button onClick={handleFinish} className="w-full" size="lg">
                Go to Workspace
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
