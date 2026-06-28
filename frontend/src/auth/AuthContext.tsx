import {
  createContext,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api } from "../api/client";

interface AuthState {
  isAuthenticated: boolean;
  username: string | null;
  login: (username: string, password: string) => Promise<void>;
  register: (username: string, password: string, email: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [username, setUsername] = useState<string | null>(
    localStorage.getItem("username")
  );

  const value = useMemo<AuthState>(() => {
    async function login(user: string, password: string) {
      const { data } = await api.post("/auth/login/", {
        username: user,
        password,
      });
      localStorage.setItem("access", data.access);
      localStorage.setItem("refresh", data.refresh);
      localStorage.setItem("username", user);
      setUsername(user);
    }

    async function register(user: string, password: string, email: string) {
      await api.post("/auth/register/", { username: user, password, email });
      await login(user, password);
    }

    function logout() {
      localStorage.clear();
      setUsername(null);
    }

    return {
      isAuthenticated: Boolean(localStorage.getItem("access")),
      username,
      login,
      register,
      logout,
    };
  }, [username]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth doit être utilisé dans AuthProvider");
  return ctx;
}
