import axios, { AxiosInstance } from "axios";

// Relying on /api rewrite proxy implicitly avoiding CORS!
const GATEWAY = process.env.NEXT_PUBLIC_GATEWAY_URL ?? "";

class ApiClient {
  private http: AxiosInstance;
  private token: string | null = null;

  constructor() {
    this.http = axios.create({ baseURL: GATEWAY, timeout: 30000 });
    this.http.interceptors.request.use(config => {
      if (typeof window !== 'undefined' && !this.token) {
         this.restoreToken();
      }
      if (this.token) {
         config.headers.Authorization = `Bearer ${this.token}`;
      }
      return config;
    });
    this.http.interceptors.response.use(
      r => r,
      err => {
        if (err.response?.status === 401) {
             this.token = null;
             if (typeof window !== 'undefined') localStorage.removeItem("eval_token");
        }
        return Promise.reject(err);
      }
    );
  }

  async authenticate(apiKey: string): Promise<void> {
    const r = await this.http.post("/auth/token", { api_key: apiKey });
    this.token = r.data.access_token;
    if (typeof window !== 'undefined') localStorage.setItem("eval_token", this.token!);
  }

  restoreToken(): void {
    if (typeof window !== 'undefined') {
        this.token = localStorage.getItem("eval_token");
    }
  }

  async get<T>(path: string, params?: object): Promise<T> {
    const r = await this.http.get(path, { params });
    return r.data;
  }
  
  async post<T>(path: string, body?: object): Promise<T> {
      const r = await this.http.post(path, body);
      return r.data;
  }

  async delete<T>(path: string): Promise<T> {
      const r = await this.http.delete(path);
      return r.data;
  }
  
  getToken() {
      return this.token;
  }
}

export const apiClient = new ApiClient();
