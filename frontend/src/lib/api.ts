const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface ApiError {
  detail: string;
}

class ApiClient {
  private token: string | null = null;

  setToken(token: string | null) {
    this.token = token;
    if (token) {
      localStorage.setItem("token", token);
    } else {
      localStorage.removeItem("token");
    }
  }

  getToken(): string | null {
    if (this.token) return this.token;
    if (typeof window !== "undefined") {
      this.token = localStorage.getItem("token");
    }
    return this.token;
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {
      "Content-Type": "application/json",
      ...options.headers,
    };

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred",
      }));
      throw new Error(error.detail);
    }

    if (response.status === 204) {
      return {} as T;
    }

    return response.json();
  }

  async get<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "GET" });
  }

  async post<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async put<T>(endpoint: string, data?: unknown): Promise<T> {
    return this.request<T>(endpoint, {
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  async delete<T>(endpoint: string): Promise<T> {
    return this.request<T>(endpoint, { method: "DELETE" });
  }

  async postForm<T>(endpoint: string, formData: FormData): Promise<T> {
    const token = this.getToken();
    const headers: HeadersInit = {};

    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }

    const response = await fetch(`${API_URL}${endpoint}`, {
      method: "POST",
      headers,
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "An error occurred",
      }));
      throw new Error(error.detail);
    }

    return response.json();
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    const response = await fetch(`${API_URL}/api/v1/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded",
      },
      body: formData,
    });

    if (!response.ok) {
      const error: ApiError = await response.json().catch(() => ({
        detail: "Login failed",
      }));
      throw new Error(error.detail);
    }

    const data: { access_token: string } = await response.json();
    this.setToken(data.access_token);
    return data;
  }

  async getMe() {
    return this.get<User>("/api/v1/auth/me");
  }

  async validateInvite(token: string) {
    return this.get<InviteValidation>(`/api/v1/auth/invite/${token}`);
  }

  async signup(token: string, fullName: string, password: string) {
    const data = await this.post<{ access_token: string }>("/api/v1/auth/signup", {
      token,
      full_name: fullName,
      password,
    });
    this.setToken(data.access_token);
    return data;
  }

  logout() {
    this.setToken(null);
  }
}

export const api = new ApiClient();

// Types
export interface User {
  id: string;
  email: string;
  full_name: string;
  is_active: boolean;
  is_superadmin: boolean;
  created_at: string;
  organizations: OrganizationMembership[];
}

export interface OrganizationMembership {
  organization_id: string;
  organization_name: string;
  role: string;
}

export interface InviteValidation {
  valid: boolean;
  email?: string;
  organization_name?: string;
  role?: string;
  message?: string;
}

export interface WarehouseStatus {
  connected: boolean;
  has_warehouse: boolean;
  supabase_url?: string;
  schema_name?: string;
  table_count: number;
  last_connected_at?: string;
}

export interface WarehouseConnection {
  supabase_url: string;
  supabase_key: string;
  schema_name?: string;
}

export interface Source {
  id: string;
  name: string;
  source_type: string;
  warehouse_table_name?: string;
  last_synced_at?: string;
  column_count: number;
  created_at: string;
}

export interface WarehouseTable {
  name: string;
  schema_name: string;
  row_count?: number;
  columns: { name: string; data_type: string; is_nullable: boolean }[];
}
