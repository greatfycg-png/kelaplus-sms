""" Historique des SMS envoyés par ce téléphone (ajout Kelaplus).

Le service (qui reçoit les demandes d'envoi de Kelaplus) inscrit chaque SMS dans `sms_history.json`, dans le dossier de configuration ;
l'application l'affiche dans l'onglet « Historique ». On garde les 2 000 derniers envois. Écriture atomique : l'application ne lit jamais
un fichier à moitié écrit.
"""

import json
import os
import time
import uuid
from os.path import join

from services.config import app_name
from services.pathMgr import get_os_platform

MAX_ENVOIS = 2000
platform = get_os_platform()

if platform == "android":
    from android.storage import app_storage_path
    base_path = app_storage_path()
else:
    from services.pathMgr import get_user_data_dir
    base_path = get_user_data_dir(app_name)

config_dir = join(base_path, "config")
os.makedirs(config_dir, exist_ok=True)
fichier_historique = join(config_dir, "sms_history.json")


def _lire() -> list:
    try:
        with open(fichier_historique, "r", encoding="utf-8") as f:
            donnees = json.load(f)
        return donnees if isinstance(donnees, list) else []
    except Exception:
        return []


def _ecrire(envois: list) -> None:
    temporaire = f"{fichier_historique}.tmp"
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(envois, f, ensure_ascii=False)
    os.replace(temporaire, fichier_historique)


def ajouter(numero: str, message: str, envoye: bool, ordinateur: str = "") -> dict:
    """ Inscrit un envoi ; renvoie l'enregistrement. """
    envoi = {
        "id": uuid.uuid4().hex[:12],
        "date": time.time(),
        "numero": str(numero),
        "message": str(message)[:1600],
        "envoye": bool(envoye),
        "ordinateur": str(ordinateur or "")[:60],
    }
    envois = _lire()
    envois.append(envoi)
    _ecrire(envois[-MAX_ENVOIS:])
    return envoi


def envois(limite: int = 300) -> list:
    """ Les derniers envois, du plus récent au plus ancien. """
    return list(reversed(_lire()))[:limite]


def resume() -> dict:
    """ Totaux affichés en haut de l'historique : aujourd'hui, réussis, échecs. """
    tous = _lire()
    debut_jour = time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, -1))
    return {
        "total": len(tous),
        "aujourdhui": sum(1 for e in tous if e.get("date", 0) >= debut_jour),
        "envoyes": sum(1 for e in tous if e.get("envoye")),
        "echecs": sum(1 for e in tous if not e.get("envoye")),
    }


def vider() -> None:
    _ecrire([])
