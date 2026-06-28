import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      if (mode === "login") await login(username, password);
      else await register(username, password, email);
      navigate("/app");
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "Échec de l'authentification.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth">
      <Link className="brand" to="/">
        ◎ MedScan
      </Link>
      <form className="card auth-card" onSubmit={onSubmit}>
        <h2>{mode === "login" ? "Connexion" : "Créer un compte"}</h2>

        <label>
          Identifiant
          <input
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            autoComplete="username"
            required
          />
        </label>

        {mode === "register" && (
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
            />
          </label>
        )}

        <label>
          Mot de passe
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            required
          />
        </label>

        {error && <p className="error">{error}</p>}

        <button className="btn btn-primary" disabled={loading}>
          {loading ? "…" : mode === "login" ? "Se connecter" : "S'inscrire"}
        </button>

        <p className="switch">
          {mode === "login" ? "Pas de compte ?" : "Déjà inscrit ?"}{" "}
          <button
            type="button"
            className="linklike"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Créer un compte" : "Se connecter"}
          </button>
        </p>
      </form>
    </div>
  );
}
