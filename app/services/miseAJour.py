""" Mise à jour de Kelaplus SMS — ajout Kelaplus.

L'application demande à GitHub la dernière version publiée (dépôt greatfycg-png/kelaplus-sms). Si elle est plus récente que celle installée, elle le
propose ; « Mettre à jour » télécharge le fichier signé KelaplusSMS.apk (lien fixe), que l'on ouvre pour l'installer par-dessus : réglages, historique
et connexions avec Kelaplus sont gardés (même signature).
"""

import re

DEPOT = "greatfycg-png/kelaplus-sms"
API_DERNIERE = f"https://api.github.com/repos/{DEPOT}/releases/latest"
LIEN_APK = f"https://github.com/{DEPOT}/releases/latest/download/KelaplusSMS.apk"


def version_tuple(version: str) -> tuple:
    """ « v1.4.0 », « 1.4 » → (1, 4, 0) ; les parties non numériques sont ignorées. """
    nombres = [int(x) for x in re.findall(r"\d+", str(version or ""))[:3]]
    return tuple(nombres + [0] * (3 - len(nombres)))


def plus_recente(distante: str, locale: str) -> bool:
    return version_tuple(distante) > version_tuple(locale)


def derniere_version(delai: float = 8.0) -> dict | None:
    """ {"version": "1.5.0", "notes": "…"} de la dernière version publiée ; None sans internet ou en cas d'erreur. """
    try:
        import requests
        r = requests.get(API_DERNIERE, headers={"Accept": "application/vnd.github+json", "User-Agent": "KelaplusSMS"}, timeout=delai)
        if r.status_code != 200:
            return None
        j = r.json()
        tag = str(j.get("tag_name") or "")
        if not tag:
            return None
        return {"version": tag.lstrip("vV"), "notes": str(j.get("body") or "")[:600]}
    except Exception as e:
        print(f"Mise à jour : vérification impossible : {e}")
        return None
