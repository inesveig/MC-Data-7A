import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import AnomalyViewer from "../components/AnomalyViewer";
import { useAuth } from "../auth/AuthContext";
import type { AnalyzeResponse } from "../types";

const SEVERITY_FR: Record<string, string> = {
  none: "Aucune",
  low: "Faible",
  moderate: "Modérée",
  high: "Élevée",
  critical: "Critique",
};

export default function Platform() {
  const { username, logout } = useAuth();
  const navigate = useNavigate();
  const inputRef = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<AnalyzeResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);

  async function analyze(file: File) {
    setError(null);
    setResult(null);
    setLoading(true);
    setFilename(file.name);
    const form = new FormData();
    form.append("file", file);
    try {
      const { data } = await api.post<AnalyzeResponse>("/analyses/analyze/", form);
      setResult(data);
    } catch (err: any) {
      setError(err?.response?.data?.detail ?? "L'analyse a échoué.");
    } finally {
      setLoading(false);
    }
  }

  const a = result?.analysis;

  return (
    <div className="platform">
      <header className="nav">
        <span className="brand">◎ MedScan</span>
        <div className="nav-right">
          <span className="user">{username}</span>
          <button
            className="btn btn-ghost"
            onClick={() => {
              logout();
              navigate("/");
            }}
          >
            Déconnexion
          </button>
        </div>
      </header>

      <main className="platform-body">
        <section className="upload-pane">
          <h2>Analyser une radiographie</h2>
          <div
            className="dropzone"
            onClick={() => inputRef.current?.click()}
            onDragOver={(e) => e.preventDefault()}
            onDrop={(e) => {
              e.preventDefault();
              const f = e.dataTransfer.files?.[0];
              if (f) analyze(f);
            }}
          >
            <input
              ref={inputRef}
              type="file"
              accept=".dcm,.dicom,image/*"
              hidden
              onChange={(e) => {
                const f = e.target.files?.[0];
                if (f) analyze(f);
              }}
            />
            <p>📤 Glissez une radio ici, ou cliquez pour choisir</p>
            <small>DICOM (.dcm) ou image — max 25 Mo</small>
          </div>
          {filename && <p className="filename">Fichier : {filename}</p>}
          {result?.mock && (
            <p className="badge-mock">Mode démo (analyse simulée)</p>
          )}
        </section>

        <section className="result-pane">
          {loading && <div className="card center">Analyse en cours…</div>}
          {error && <div className="card error">{error}</div>}

          {a && result && (
            <>
              <AnomalyViewer
                imageBase64={result.image_png_base64}
                circle={a.circle}
                severityLabel={a.severity_label}
              />

              <div className={`card severity sev-${a.severity_label}`}>
                <div className="severity-head">
                  <span>
                    {a.anomaly_present ? "Anomalie détectée" : "Aucune anomalie"}
                  </span>
                  <span className="sev-score">{a.severity}/10</span>
                </div>
                <div className="sev-meter">
                  <div
                    className="sev-fill"
                    style={{ width: `${a.severity * 10}%` }}
                  />
                </div>
                <p className="sev-label">
                  Gravité : {SEVERITY_FR[a.severity_label] ?? a.severity_label}
                  {a.region ? ` · ${a.region}` : ""}
                </p>
              </div>

              {a.findings.length > 0 && (
                <div className="card">
                  <h3>Observations</h3>
                  <ul>
                    {a.findings.map((f, i) => (
                      <li key={i}>{f}</li>
                    ))}
                  </ul>
                </div>
              )}

              {a.explanation && (
                <div className="card">
                  <h3>Pourquoi c'est important</h3>
                  <p>{a.explanation}</p>
                </div>
              )}

              {a.recommendation && (
                <div className="card">
                  <h3>Conduite à tenir</h3>
                  <p>{a.recommendation}</p>
                </div>
              )}
            </>
          )}

          {!a && !loading && !error && (
            <div className="card placeholder">
              Les résultats s'afficheront ici après l'analyse.
            </div>
          )}
        </section>
      </main>
    </div>
  );
}
