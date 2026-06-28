export interface Circle {
  cx: number; // centre X, fraction [0,1]
  cy: number; // centre Y, fraction [0,1]
  r: number; // rayon, fraction [0,1] de la largeur
}

export interface Analysis {
  anomaly_present: boolean;
  findings: string[];
  region: string | null;
  circle: Circle | null;
  severity: number; // 0..10
  severity_label: "none" | "low" | "moderate" | "high" | "critical";
  explanation: string;
  recommendation: string;
}

export interface AnalyzeResponse {
  id?: number;
  analysis: Analysis;
  image_png_base64: string;
  image_width: number;
  image_height: number;
  model: string;
  mock: boolean;
}
