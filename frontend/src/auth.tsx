import React, { createContext, useContext, useEffect, useState } from "react";

export type CurrentUser = {
  id: string;
  full_name: string;
  first_name: string;
  last_name: string;
  role: "employee" | "admin";
};

interface AuthContextValue {
  currentUser: CurrentUser | null;
  setCurrentUser: (user: CurrentUser | null) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [currentUser, setCurrentUserState] = useState<CurrentUser | null>(null);

  useEffect(() => {
    try {
      const stored = window.localStorage.getItem("currentUser");
      if (stored) {
        const parsed = JSON.parse(stored) as CurrentUser;
        setCurrentUserState(parsed);
      }
    } catch {
      // ignore parse errors
    }
  }, []);

  function setCurrentUser(user: CurrentUser | null) {
    setCurrentUserState(user);
    if (user) {
      window.localStorage.setItem("currentUser", JSON.stringify(user));
    } else {
      window.localStorage.removeItem("currentUser");
    }
  }

  function logout() {
    setCurrentUser(null);
  }

  return (
    <AuthContext.Provider value={{ currentUser, setCurrentUser, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error("useAuth must be used within AuthProvider");
  }
  return ctx;
}

