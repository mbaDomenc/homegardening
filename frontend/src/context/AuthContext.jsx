import React, { createContext, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, setAccessTokenSupplier, setOnTokenRefreshed } from "../api/axiosInstance";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [accessToken, setAccessToken] = useState(null); // token SOLO in memoria (no localStorage)
  const [user, setUser] = useState(null);               // {id, username, email, ruolo, ...}
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate() ;

  // Collego axios al getter/setter del token
  useEffect(() => {
    setAccessTokenSupplier(() => accessToken);
    setOnTokenRefreshed((newToken) => setAccessToken(newToken));
  }, [accessToken]);

  // SILENT REFRESH all'avvio: prova a ottenere un nuovo accessToken dal cookie di refresh
 useEffect(() => {
  let canceled = false;
  setLoading(true);

  (async () => {
    try {
      const { data } = await api.post("/api/utenti/refresh", {});
      const newToken = data?.accessToken;
      if (!newToken || canceled) return;

      setAccessToken(newToken);

      const me = await api.get("/api/utenti/me");
      if (!canceled && me?.data?.utente) {
        setUser(me.data.utente);
      }
    } catch (e) {
      if (!canceled) {
        setAccessToken(null);
        setUser(null);
      }
    } finally {
      if (!canceled) setLoading(false); // ⬅️ FINE
    }
  })();

  return () => { canceled = true; };
}, []);

  //Azioni
  const login = async (emailOrUsername, password) => {
    setLoading(true);
    try {
      // Il backend deve accettare sia email che username nello stesso campo
      const { data } = await api.post("/api/utenti/login", {
        username: emailOrUsername, // o 'email' se lo vuoi distinguere
        password,
      });
      setAccessToken(data.accessToken);
      setUser(data.utente);
      return { ok: true };
    } catch (err) {
      return { ok: false, error: err.response?.data?.detail || "Errore login" };
    } finally {
      setLoading(false);
    }
  };

  const logout = async () => {
    try {
      await api.post("/api/utenti/logout");
    } catch {
      // Anche se fallisce, puliamo lo stato locale
    } finally {
      setAccessToken(null);
      setUser(null);
      navigate("/", { replace: true });
    }
  };

  const value = {
    user,
    accessToken,
    loading,
    isAuthenticated: !!user && !!accessToken,
    login,
    logout,
    setUser,         // se vuoi aggiornare dati profilo in futuro
    setAccessToken,  // se mai necessario
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => useContext(AuthContext);