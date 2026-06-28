import type { Circle } from "../types";

interface Props {
  imageBase64: string;
  circle: Circle | null;
  severityLabel: string;
}

// Couleur du cercle selon la gravité.
const COLORS: Record<string, string> = {
  none: "#22c55e",
  low: "#84cc16",
  moderate: "#f59e0b",
  high: "#f97316",
  critical: "#ef4444",
};

/**
 * Affiche la radio convertie et superpose un cercle SVG sur l'anomalie.
 * Les coordonnées du cercle sont des fractions [0,1] → on travaille dans un
 * viewBox 100x100 pour rester indépendant de la résolution réelle.
 */
export default function AnomalyViewer({ imageBase64, circle, severityLabel }: Props) {
  const color = COLORS[severityLabel] ?? "#f97316";

  return (
    <div className="viewer">
      <img src={`data:image/png;base64,${imageBase64}`} alt="Radiographie analysée" />
      {circle && (
        <svg className="overlay" viewBox="0 0 100 100" preserveAspectRatio="none">
          <circle
            cx={circle.cx * 100}
            cy={circle.cy * 100}
            r={circle.r * 100}
            fill="none"
            stroke={color}
            strokeWidth={0.8}
          />
          <circle
            cx={circle.cx * 100}
            cy={circle.cy * 100}
            r={circle.r * 100 + 2}
            fill="none"
            stroke={color}
            strokeOpacity={0.35}
            strokeWidth={0.4}
          />
        </svg>
      )}
    </div>
  );
}
