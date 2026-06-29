"""Helpers UI : export CSV et overlay du cercle d'anomalie.

Les données viennent désormais de l'API Django (dictionnaires JSON), plus de
la base SQLite locale. La concordance IA/médecin est calculée côté serveur.
"""
import csv
import io

from PIL import Image, ImageDraw


def export_diagnostics_to_csv(rows: list[dict]) -> str:
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Nom de l'analyse", "Fichier original", "Diagnostic IA",
        "Confiance (%)", "Gravité", "Région", "Date",
        "Avis médecin", "Notes médecin", "Concordance",
    ])

    for row in rows:
        display_name = row.get("analysis_name") or row.get("filename", "")
        confidence = row.get("confidence")
        created = (row.get("created_at") or "")[:19].replace("T", " ")
        writer.writerow([
            row.get("id"),
            display_name,
            row.get("filename", ""),
            row.get("diagnosis", ""),
            f"{confidence * 100:.1f}" if confidence is not None else "",
            row.get("severity", ""),
            row.get("region") or "",
            created,
            row.get("doctor_diagnosis") or "",
            row.get("doctor_notes") or "",
            row.get("concordance_status") or "",
        ])

    return output.getvalue()


def draw_circle(img: Image.Image, circle: dict | None) -> Image.Image:
    """Dessine le cercle d'anomalie (coords en fractions 0-1) sur l'image."""
    if not circle:
        return img
    try:
        cx, cy, r = float(circle["cx"]), float(circle["cy"]), float(circle["r"])
    except (KeyError, TypeError, ValueError):
        return img

    out = img.convert("RGB").copy()
    draw = ImageDraw.Draw(out)
    w, h = out.size
    # Rayon en pixels : moyenne largeur/hauteur pour rester rond.
    rp = r * (w + h) / 2
    x0, y0 = cx * w - rp, cy * h - rp
    x1, y1 = cx * w + rp, cy * h + rp
    thickness = max(2, int(min(w, h) * 0.006))
    draw.ellipse([x0, y0, x1, y1], outline=(255, 60, 60), width=thickness)
    return out
