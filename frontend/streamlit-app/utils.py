import csv
import io


def compute_concordance(ia_diagnosis, doctor_diagnosis):
    if not doctor_diagnosis:
        return None, None

    doctor_category = "Sain" if doctor_diagnosis == "Sain" else "Malade"

    if ia_diagnosis == "Incertain":
        return "Non comparable (IA incertaine)", 50

    if ia_diagnosis == doctor_category:
        return "Concordant", 100

    return "Discordant", 0


def export_diagnostics_to_csv(rows):

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Nom de l'analyse", "Fichier original", "Diagnostic IA",
        "Confiance (%)", "Date", "Avis médecin", "Notes médecin", "Concordance",
    ])

    for row in rows:
        display_name = row["analysis_name"] if row["analysis_name"] else row["filename"]
        statut, _ = compute_concordance(row["diagnosis"], row["doctor_diagnosis"])
        confidence = row["confidence"]

        writer.writerow([
            row["id"],
            display_name,
            row["filename"],
            row["diagnosis"],
            f"{confidence * 100:.1f}" if confidence is not None else "",
            row["created_at"][:19].replace("T", " "),
            row["doctor_diagnosis"] or "",
            row["doctor_notes"] or "",
            statut or "",
            ])

    return output.getvalue()