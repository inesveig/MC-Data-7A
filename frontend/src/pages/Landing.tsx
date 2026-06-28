import { Link } from "react-router-dom";

export default function Landing() {
  return (
    <div className="landing">
      <header className="nav">
        <span className="brand">◎ MedScan</span>
        <Link className="btn btn-ghost" to="/login">
          Se connecter
        </Link>
      </header>

      <main className="hero">
        <p className="eyebrow">IA d'aide au diagnostic · imagerie thoracique</p>
        <h1>
          Détectez les anomalies pulmonaires
          <br />
          en quelques secondes.
        </h1>
        <p className="lead">
          Téléversez une radiographie, MedGemma l'analyse, localise la zone
          suspecte et évalue sa gravité. Vous gardez le contrôle de la décision.
        </p>
        <div className="cta-row">
          <Link className="btn btn-primary" to="/login">
            Accéder à la plateforme
          </Link>
          <a className="btn btn-ghost" href="#how">
            Comment ça marche
          </a>
        </div>

        <section id="how" className="steps">
          <div className="step">
            <span className="step-n">1</span>
            <h3>Téléversez</h3>
            <p>Une radio DICOM ou PNG, glissée-déposée.</p>
          </div>
          <div className="step">
            <span className="step-n">2</span>
            <h3>Analyse IA</h3>
            <p>MedGemma repère l'anomalie et estime la gravité.</p>
          </div>
          <div className="step">
            <span className="step-n">3</span>
            <h3>Visualisez</h3>
            <p>Zone cerclée + explication clinique en clair.</p>
          </div>
        </section>

        <p className="disclaimer">
          ⚠️ Outil d'aide à la décision, à but démonstratif. Ne remplace pas
          l'avis d'un médecin.
        </p>
      </main>
    </div>
  );
}
