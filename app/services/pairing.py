""" Jumelage d'un ordinateur Kelaplus avec ce téléphone (ajout Kelaplus à OpenSMS).

Déroulement :
  1. Kelaplus trouve le téléphone sur le réseau Wi-Fi de l'école (GET /kelaplus/ping) ;
  2. l'utilisateur clique sur « Connexion » dans Kelaplus : le logiciel envoie une demande (POST /kelaplus/pair) ;
  3. le service du téléphone enregistre la demande dans `pair_request.json` ; l'application (au premier plan) l'affiche : « Autoriser Kelaplus ? » ;
  4. si l'utilisateur autorise sur le téléphone, une clé API propre à cet ordinateur est créée (`keys.json`) et rendue UNE SEULE FOIS à Kelaplus
     (GET /kelaplus/pair/<id>) ; sinon la demande est refusée, ou expire au bout de 90 secondes ;
  5. Kelaplus garde l'adresse et la clé : il envoie ensuite ses SMS par le téléphone (POST /sms/, comme avant).

Le service (qui reçoit les requêtes réseau) et l'application (qui affiche la fenêtre) sont deux processus : ils s'échangent la demande par le fichier
`pair_request.json`, dans le dossier de configuration. Rien n'est jamais accepté sans un clic sur le téléphone.
"""

import hashlib
import json
import os
import platform as _platform
import secrets
import time
import uuid
from os.path import exists, join

from services.config import app_name
from services.pathMgr import get_os_platform

DUREE_DEMANDE_S = 90
platform = get_os_platform()

if platform == "android":
    from android.storage import app_storage_path
    base_path = app_storage_path()
else:
    from services.pathMgr import get_user_data_dir
    base_path = get_user_data_dir(app_name)

config_dir = join(base_path, "config")
os.makedirs(config_dir, exist_ok=True)
fichier_demande = join(config_dir, "pair_request.json")
fichier_cles = join(config_dir, "keys.json")


def _hacher(cle: str) -> str:
    return hashlib.sha256(cle.encode("utf-8")).hexdigest()


def _lire(chemin: str, defaut):
    try:
        with open(chemin, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defaut


def _ecrire(chemin: str, donnees) -> None:
    """ Écriture atomique : l'autre processus ne lit jamais un fichier à moitié écrit. """
    temporaire = f"{chemin}.tmp"
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(donnees, f)
    os.replace(temporaire, chemin)


def nom_appareil() -> str:
    """ Le nom du téléphone, montré dans Kelaplus (« samsung SM-A125F »). """
    if platform == "android":
        try:
            from jnius import autoclass
            build = autoclass("android.os.Build")
            return f"{build.MANUFACTURER} {build.MODEL}".strip()
        except Exception:
            return "Téléphone Android"
    return _platform.node() or "Appareil"


def _demande() -> dict | None:
    d = _lire(fichier_demande, None)
    if not isinstance(d, dict) or "id" not in d:
        return None
    # Une demande en attente depuis trop longtemps expire d'elle-même.
    if d.get("statut") == "attente" and time.time() - float(d.get("cree", 0)) > DUREE_DEMANDE_S:
        d["statut"] = "expire"
        _ecrire(fichier_demande, d)
    return d


def creer_demande(poste: str, ecole: str = "") -> dict:
    """ Service : une nouvelle demande de Kelaplus (elle remplace la précédente si celle-ci n'est plus en attente ou date de plus de 5 s). """
    poste = (poste or "Ordinateur").strip()[:60] or "Ordinateur"
    ecole = (ecole or "").strip()[:80]
    ancienne = _demande()
    if ancienne and ancienne.get("statut") == "attente" and ancienne.get("poste") == poste:
        return ancienne  # la même demande répétée : on ne recommence pas
    d = {"id": uuid.uuid4().hex, "poste": poste, "ecole": ecole, "cree": time.time(), "statut": "attente"}
    _ecrire(fichier_demande, d)
    return d


def demande_en_attente() -> dict | None:
    """ Application : la demande à montrer à l'utilisateur, ou None. """
    d = _demande()
    return d if d and d.get("statut") == "attente" else None


def refuser(id_demande: str) -> None:
    d = _demande()
    if d and d.get("id") == id_demande and d.get("statut") == "attente":
        d["statut"] = "refuse"
        _ecrire(fichier_demande, d)


def accepter(id_demande: str) -> bool:
    """ Application : l'utilisateur a autorisé sur le téléphone. Crée la clé de cet ordinateur et la met de côté pour Kelaplus (une seule lecture). """
    d = _demande()
    if not d or d.get("id") != id_demande or d.get("statut") != "attente":
        return False
    cle = f"osms_{secrets.token_urlsafe(32)}"
    cles = _lire(fichier_cles, {})
    if not isinstance(cles, dict):
        cles = {}
    cles[_hacher(cle)] = {"name": d.get("poste", "kelaplus"), "scopes": ["sms:write"], "kelaplus": True, "cree": time.time()}
    _ecrire(fichier_cles, cles)
    d["statut"] = "accepte"
    d["cle"] = cle
    _ecrire(fichier_demande, d)
    return True


def etat_demande(id_demande: str) -> dict:
    """ Service : l'état d'une demande pour Kelaplus. La clé n'est rendue qu'une fois, puis effacée du fichier. """
    d = _demande()
    if not d or d.get("id") != id_demande:
        return {"statut": "inconnue"}
    if d.get("statut") == "accepte" and d.get("cle"):
        cle = d.pop("cle")
        d["statut"] = "termine"
        _ecrire(fichier_demande, d)
        return {"statut": "accepte", "cle": cle}
    if d.get("statut") == "termine":
        return {"statut": "termine"}
    return {"statut": d.get("statut", "inconnue")}


def ordinateurs_connectes() -> list[str]:
    """ Les noms des ordinateurs Kelaplus jumelés avec ce téléphone. """
    cles = _lire(fichier_cles, {})
    if not isinstance(cles, dict):
        return []
    return [str(v.get("name", "")) for v in cles.values() if isinstance(v, dict) and v.get("kelaplus")]
