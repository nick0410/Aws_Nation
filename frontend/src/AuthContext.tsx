import { createContext, useContext, useState, type ReactNode } from "react";

interface User {
  username: string;
  aws_region: string;
  token: string;
}

interface AuthContextType {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  signup: (
    username: string,
    password: string,
    aws_access_key_id: string,
    aws_secret_access_key: string,
    aws_region: string,
  ) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

function getStoredUser(): User | null {
  try {
    const stored = localStorage.getItem("autonation_user");
    return stored ? JSON.parse(stored) : null;
  } catch {
    localStorage.removeItem("autonation_user");
    return null;
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(getStoredUser);

  const login = async (username: string, password: string) => {
    const resp = await fetch("http://127.0.0.1:8000/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Login failed");
    const u: User = {
      username: data.username,
      aws_region: data.aws_region,
      token: data.token,
    };
    setUser(u);
    localStorage.setItem("autonation_user", JSON.stringify(u));
  };

  const signup = async (
    username: string,
    password: string,
    aws_access_key_id: string,
    aws_secret_access_key: string,
    aws_region: string,
  ) => {
    const resp = await fetch("http://127.0.0.1:8000/auth/signup", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        username,
        password,
        aws_access_key_id,
        aws_secret_access_key,
        aws_region,
      }),
    });
    const data = await resp.json();
    if (!resp.ok) throw new Error(data.detail || "Signup failed");
    const u: User = {
      username: data.username,
      aws_region: data.aws_region,
      token: data.token,
    };
    setUser(u);
    localStorage.setItem("autonation_user", JSON.stringify(u));
  };

  const logout = () => {
    if (user?.token) {
      fetch("http://127.0.0.1:8000/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${user.token}` },
      }).catch(() => {});
    }
    setUser(null);
    localStorage.removeItem("autonation_user");
  };

  return (
    <AuthContext.Provider value={{ user, login, signup, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
