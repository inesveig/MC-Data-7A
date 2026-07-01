"""Configuration pytest du service IA.

On force le mode mock AVANT tout import de `medgemma`/`main` : la constante
`MOCK` y est lue au moment de l'import, donc l'environnement doit être posé ici.
"""
import os

os.environ.setdefault("AI_MOCK", "1")
