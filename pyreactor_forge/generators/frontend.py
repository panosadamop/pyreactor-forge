"""Frontend generator - scaffolds Vite + React (JS or TS) app."""

from pathlib import Path


class FrontendGenerator:
    def __init__(self, config: dict, output_dir: Path):
        self.config = config
        self.out = output_dir
        self.name = config["name"]
        self.ts = config.get("frontend", "react-ts") == "react-ts"
        self.ext = "tsx" if self.ts else "jsx"
        self.ext_plain = "ts" if self.ts else "js"
        self.auth = config.get("auth", "jwt")

    def generate(self):
        # Directory tree
        src = self.out / "src"
        for d in ["components/ui", "components/layout", "pages", "services",
                  "hooks", "store", "utils", "types"]:
            (src / d).mkdir(parents=True)
        (self.out / "public").mkdir()

        self._write_package_json()
        self._write_vite_config()
        self._write_tsconfig()
        self._write_index_html()
        self._write_main()
        self._write_app()
        self._write_pages()
        self._write_components()
        self._write_services()
        self._write_hooks()
        self._write_store()
        self._write_types()
        self._write_utils()
        self._write_env()

    def _write_package_json(self):
        name = self.name.lower().replace(" ", "-")
        ts_deps = '"typescript": "^5.4.5",' if self.ts else ""
        ts_types = '"@types/react": "^18.3.3", "@types/react-dom": "^18.3.0",' if self.ts else ""

        (self.out / "package.json").write_text(f'''{{
  "name": "{name}-frontend",
  "version": "0.1.0",
  "private": true,
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "{"tsc -b && " if self.ts else ""}vite build",
    "preview": "vite preview",
    "lint": "eslint src --ext .{self.ext},.{self.ext_plain}",
    "test": "vitest run"
  }},
  "dependencies": {{
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.23.0",
    "axios": "^1.7.2",
    "@tanstack/react-query": "^5.45.0",
    "zustand": "^4.5.2",
    "react-hook-form": "^7.51.5",
    "zod": "^3.23.8",
    "@hookform/resolvers": "^3.6.0",
    "lucide-react": "^0.383.0",
    "clsx": "^2.1.1",
    "tailwind-merge": "^2.3.0"
  }},
  "devDependencies": {{
    {ts_types}
    {ts_deps}
    "@vitejs/plugin-react": "^4.3.0",
    "vite": "^5.3.0",
    "vitest": "^1.6.0",
    "tailwindcss": "^3.4.4",
    "autoprefixer": "^10.4.19",
    "postcss": "^8.4.38",
    "eslint": "^8.57.0"
  }}
}}
''', encoding="utf-8")

    def _write_vite_config(self):
        (self.out / f"vite.config.{self.ext_plain}").write_text(f'''import {{ defineConfig }} from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({{
  plugins: [react()],
  resolve: {{
    alias: {{
      "@": path.resolve(__dirname, "./src"),
    }},
  }},
  server: {{
    port: 5173,
    proxy: {{
      "/api": {{
        target: "http://localhost:8000",
        changeOrigin: true,
      }},
    }},
  }},
}});
''', encoding="utf-8")

    def _write_tsconfig(self):
        if not self.ts:
            return
        (self.out / "tsconfig.json").write_text('''{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "baseUrl": ".",
    "paths": {
      "@/*": ["./src/*"]
    }
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
''', encoding="utf-8")
        (self.out / "tsconfig.node.json").write_text('''{
  "compilerOptions": {
    "composite": true,
    "skipLibCheck": true,
    "module": "ESNext",
    "moduleResolution": "bundler",
    "allowSyntheticDefaultImports": true,
    "strict": true
  },
  "include": ["vite.config.ts"]
}
''', encoding="utf-8")

    def _write_index_html(self):
        (self.out / "index.html").write_text(f'''<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{self.name}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.{self.ext}"></script>
  </body>
</html>
''', encoding="utf-8")

    def _write_main(self):
        (self.out / "src" / f"main.{self.ext}").write_text(f'''import React from "react";
import ReactDOM from "react-dom/client";
import {{ QueryClient, QueryClientProvider }} from "@tanstack/react-query";
import App from "./App";
import "./index.css";

const queryClient = new QueryClient({{
  defaultOptions: {{
    queries: {{ retry: 1, staleTime: 30_000 }},
  }},
}});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <QueryClientProvider client={{queryClient}}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
''', encoding="utf-8")

        (self.out / "src" / "index.css").write_text("""@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --radius: 0.5rem;
  }
}
""", encoding="utf-8")

    def _write_app(self):
        (self.out / "src" / f"App.{self.ext}").write_text(f'''import {{ BrowserRouter, Routes, Route, Navigate }} from "react-router-dom";
import {{ useAuthStore }} from "./store/authStore";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import Layout from "./components/layout/Layout";

function PrivateRoute({{ children }}: {{ children: React.ReactNode }}) {{
  const token = useAuthStore((s) => s.token);
  return token ? <>{{children}}</> : <Navigate to="/login" replace />;
}}

export default function App() {{
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={{<LoginPage />}} />
        <Route path="/register" element={{<RegisterPage />}} />
        <Route
          path="/"
          element={{
            <PrivateRoute>
              <Layout />
            </PrivateRoute>
          }}
        >
          <Route index element={{<DashboardPage />}} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}}
''', encoding="utf-8")

    def _write_pages(self):
        pages = self.out / "src" / "pages"

        (pages / f"LoginPage.{self.ext}").write_text(f'''import {{ useForm }} from "react-hook-form";
import {{ zodResolver }} from "@hookform/resolvers/zod";
import {{ z }} from "zod";
import {{ Link, useNavigate }} from "react-router-dom";
import {{ useAuthStore }} from "../store/authStore";
import {{ authService }} from "../services/authService";
import {{ useState }} from "react";

const schema = z.object({{
  email: z.string().email("Invalid email"),
  password: z.string().min(1, "Password is required"),
}});

type FormData = z.infer<typeof schema>;

export default function LoginPage() {{
  const navigate = useNavigate();
  const setToken = useAuthStore((s) => s.setToken);
  const [error, setError] = useState<string | null>(null);

  const {{ register, handleSubmit, formState: {{ errors, isSubmitting }} }} = useForm<FormData>({{
    resolver: zodResolver(schema),
  }});

  const onSubmit = async (data: FormData) => {{
    try {{
      setError(null);
      const res = await authService.login(data.email, data.password);
      setToken(res.access_token);
      navigate("/");
    }} catch (e: any) {{
      setError(e.response?.data?.detail || "Login failed");
    }}
  }};

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">{self.name}</h1>
        <p className="text-gray-500 mb-6 text-sm">Sign in to your account</p>
        {{error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{{error}}</div>
        )}}
        <form onSubmit={{handleSubmit(onSubmit)}} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              {{...register("email")}}
              type="email"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="you@example.com"
            />
            {{errors.email && <p className="mt-1 text-xs text-red-500">{{errors.email.message}}</p>}}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              {{...register("password")}}
              type="password"
              className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="••••••••"
            />
            {{errors.password && <p className="mt-1 text-xs text-red-500">{{errors.password.message}}</p>}}
          </div>
          <button
            type="submit"
            disabled={{isSubmitting}}
            className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors"
          >
            {{isSubmitting ? "Signing in..." : "Sign in"}}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          Don\'t have an account?{{" "}}
          <Link to="/register" className="text-blue-600 hover:underline">Register</Link>
        </p>
      </div>
    </div>
  );
}}
''', encoding="utf-8")

        (pages / f"RegisterPage.{self.ext}").write_text(f'''import {{ useForm }} from "react-hook-form";
import {{ zodResolver }} from "@hookform/resolvers/zod";
import {{ z }} from "zod";
import {{ Link, useNavigate }} from "react-router-dom";
import {{ authService }} from "../services/authService";
import {{ useState }} from "react";

const schema = z.object({{
  email: z.string().email("Invalid email"),
  username: z.string().min(3, "At least 3 characters").regex(/^[a-zA-Z0-9_-]+$/, "Letters, numbers, _ and - only"),
  password: z.string().min(8, "At least 8 characters"),
  full_name: z.string().optional(),
}});

type FormData = z.infer<typeof schema>;

export default function RegisterPage() {{
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);

  const {{ register, handleSubmit, formState: {{ errors, isSubmitting }} }} = useForm<FormData>({{
    resolver: zodResolver(schema),
  }});

  const onSubmit = async (data: FormData) => {{
    try {{
      setError(null);
      await authService.register(data);
      navigate("/login");
    }} catch (e: any) {{
      setError(e.response?.data?.detail || "Registration failed");
    }}
  }};

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="w-full max-w-md bg-white rounded-xl shadow-sm border p-8">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Create account</h1>
        <p className="text-gray-500 mb-6 text-sm">Join {self.name} today</p>
        {{error && (
          <div className="mb-4 text-sm text-red-600 bg-red-50 px-4 py-2 rounded-lg">{{error}}</div>
        )}}
        <form onSubmit={{handleSubmit(onSubmit)}} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Full name</label>
            <input {{...register("full_name")}} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email *</label>
            <input {{...register("email")}} type="email" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            {{errors.email && <p className="mt-1 text-xs text-red-500">{{errors.email.message}}</p>}}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username *</label>
            <input {{...register("username")}} className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            {{errors.username && <p className="mt-1 text-xs text-red-500">{{errors.username.message}}</p>}}
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password *</label>
            <input {{...register("password")}} type="password" className="w-full border rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
            {{errors.password && <p className="mt-1 text-xs text-red-500">{{errors.password.message}}</p>}}
          </div>
          <button type="submit" disabled={{isSubmitting}} className="w-full bg-blue-600 text-white py-2 rounded-lg text-sm font-medium hover:bg-blue-700 disabled:opacity-50 transition-colors">
            {{isSubmitting ? "Creating account..." : "Create account"}}
          </button>
        </form>
        <p className="mt-4 text-center text-sm text-gray-500">
          Already have an account?{{" "}}
          <Link to="/login" className="text-blue-600 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}}
''', encoding="utf-8")

        (pages / f"DashboardPage.{self.ext}").write_text(f'''import {{ useCurrentUser }} from "../hooks/useCurrentUser";

export default function DashboardPage() {{
  const {{ data: user, isLoading }} = useCurrentUser();

  if (isLoading) {{
    return <div className="flex items-center justify-center h-full text-gray-400">Loading...</div>;
  }}

  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">
        Welcome back{{}}{{}}{{}}{{}}{{}}{{}}{{}}{{}}{{}}{{}}{{}}{{}}, {{user?.full_name || user?.username}}! 👋
      </h1>
      <p className="text-gray-500 mb-8">Here\'s what\'s happening in {self.name}.</p>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        {{[
          {{ label: "Email", value: user?.email }},
          {{ label: "Username", value: user?.username }},
          {{ label: "Member since", value: user?.created_at ? new Date(user.created_at).toLocaleDateString() : "-" }},
        ].map((item) => (
          <div key={{item.label}} className="bg-white border rounded-xl p-5">
            <p className="text-xs text-gray-400 uppercase tracking-wide mb-1">{{item.label}}</p>
            <p className="font-medium text-gray-900">{{item.value || "-"}}</p>
          </div>
        ))}}
      </div>
    </div>
  );
}}
''', encoding="utf-8")

    def _write_components(self):
        layout = self.out / "src" / "components" / "layout"

        (layout / f"Layout.{self.ext}").write_text(f'''import {{ Outlet, Link, useNavigate }} from "react-router-dom";
import {{ useAuthStore }} from "../../store/authStore";
import {{ LogOut, LayoutDashboard }} from "lucide-react";

export default function Layout() {{
  const logout = useAuthStore((s) => s.logout);
  const navigate = useNavigate();

  const handleLogout = () => {{
    logout();
    navigate("/login");
  }};

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {{/* Sidebar */}}
      <aside className="w-56 bg-white border-r flex flex-col py-6 px-4">
        <div className="font-bold text-lg text-gray-900 mb-8 px-2">{self.name}</div>
        <nav className="flex-1 space-y-1">
          <Link
            to="/"
            className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-700 hover:bg-gray-50 font-medium"
          >
            <LayoutDashboard size={{16}} />
            Dashboard
          </Link>
        </nav>
        <button
          onClick={{handleLogout}}
          className="flex items-center gap-2 px-3 py-2 rounded-lg text-sm text-gray-500 hover:bg-gray-50 mt-auto"
        >
          <LogOut size={{16}} />
          Sign out
        </button>
      </aside>

      {{/* Main content */}}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}}
''', encoding="utf-8")

    def _write_services(self):
        svc = self.out / "src" / "services"

        (svc / "api.ts" if self.ts else svc / "api.js").write_text('''import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

// Attach JWT token to all requests
api.interceptors.request.use((config) => {
  const raw = localStorage.getItem("auth-storage");
  if (raw) {
    try {
      const token = JSON.parse(raw)?.state?.token;
      if (token) config.headers.Authorization = `Bearer ${token}`;
    } catch {}
  }
  return config;
});

// Handle 401 globally
api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("auth-storage");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
''', encoding="utf-8")

        (svc / f"authService.{self.ext_plain}").write_text(f'''import api from "./api";

export const authService = {{
  login: async (email: string, password: string) => {{
    const res = await api.post("/auth/login", {{ email, password }});
    return res.data as {{ access_token: string; token_type: string }};
  }},

  register: async (data: {{
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }}) => {{
    const res = await api.post("/auth/register", data);
    return res.data;
  }},
}};
''', encoding="utf-8")

        (svc / f"userService.{self.ext_plain}").write_text(f'''import api from "./api";

export interface User {{
  id: number;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  is_superuser: boolean;
  created_at: string;
}}

export const userService = {{
  getMe: async (): Promise<User> => {{
    const res = await api.get("/users/me");
    return res.data;
  }},

  updateMe: async (data: Partial<Pick<User, "full_name" | "email">>) => {{
    const res = await api.patch("/users/me", data);
    return res.data as User;
  }},
}};
''', encoding="utf-8")

    def _write_hooks(self):
        hooks = self.out / "src" / "hooks"
        (hooks / f"useCurrentUser.{self.ext_plain}").write_text(f'''import {{ useQuery }} from "@tanstack/react-query";
import {{ userService }} from "../services/userService";
import {{ useAuthStore }} from "../store/authStore";

export function useCurrentUser() {{
  const token = useAuthStore((s) => s.token);
  return useQuery({{
    queryKey: ["me"],
    queryFn: userService.getMe,
    enabled: !!token,
  }});
}}
''', encoding="utf-8")

    def _write_store(self):
        store = self.out / "src" / "store"
        (store / f"authStore.{self.ext_plain}").write_text(f'''import {{ create }} from "zustand";
import {{ persist }} from "zustand/middleware";

interface AuthState {{
  token: string | null;
  setToken: (token: string) => void;
  logout: () => void;
}}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({{
      token: null,
      setToken: (token) => set({{ token }}),
      logout: () => set({{ token: null }}),
    }}),
    {{ name: "auth-storage" }}
  )
);
''', encoding="utf-8")

    def _write_types(self):
        if not self.ts:
            return
        (self.out / "src" / "types" / "index.ts").write_text('''export type { User } from "../services/userService";

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
}

export interface ApiError {
  detail: string;
  status_code?: number;
}
''', encoding="utf-8")

    def _write_utils(self):
        (self.out / "src" / "utils" / f"cn.{self.ext_plain}").write_text(f'''import {{ clsx, type ClassValue }} from "clsx";
import {{ twMerge }} from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {{
  return twMerge(clsx(inputs));
}}
''', encoding="utf-8")

    def _write_env(self):
        (self.out / ".env.example").write_text("""VITE_APP_NAME=MyApp
VITE_API_BASE_URL=http://localhost:8000
""", encoding="utf-8")

        (self.out / "tailwind.config.js").write_text("""/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
""", encoding="utf-8")

        (self.out / "postcss.config.js").write_text("""export default {
  plugins: { tailwindcss: {}, autoprefixer: {} },
};
""", encoding="utf-8")
