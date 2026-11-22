""" Solde de SMS de chaque SIM (forfaits MTN, Airtel…) — ajout Kelaplus.

Deux sources, affichées ensemble :
  1. le VRAI solde, demandé à l'opérateur par un code USSD (« *xxx# », réglable par opérateur) envoyé sur la SIM ; la réponse de l'opérateur est
     gardée telle quelle et on en tire le nombre de SMS restants quand il y figure ;
  2. une ESTIMATION entre deux consultations : le dernier solde connu (ou le forfait saisi à la recharge) moins les SMS partis depuis par cette SIM
     (historique ; un SMS long compte pour plusieurs).
Sous le seuil d'alerte, le solde est signalé en rouge. Réglages et dernières réponses : `solde_sms.json`, dans le dossier de configuration ;
le service les lit aussi pour les donner à Kelaplus (GET /kelaplus/ping).
"""

import json
import math
import os
import re
import time
from os.path import join

from services.config import app_name
from services.pathMgr import get_os_platform

platform = get_os_platform()
if platform == "android":
    from android.storage import app_storage_path
    base_path = app_storage_path()
else:
    from services.pathMgr import get_user_data_dir
    base_path = get_user_data_dir(app_name)

config_dir = join(base_path, "config")
os.makedirs(config_dir, exist_ok=True)
fichier_soldes = join(config_dir, "solde_sms.json")

REGLAGES_PAR_DEFAUT = {
    # Seuil d'alerte (SMS restants) et vérification automatique (heures, 0 : jamais) pendant que l'application est ouverte.
    "seuil": 50,
    "auto_heures": 6,
    "operateurs": [
        {"operateur": "MTN", "code": "", "forfait": 0, "depuis": 0, "dernier": None},
        {"operateur": "Airtel", "code": "", "forfait": 0, "depuis": 0, "dernier": None},
    ],
}


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(t or "").lower())


def lire() -> dict:
    try:
        with open(fichier_soldes, "r", encoding="utf-8") as f:
            r = json.load(f)
        ops = []
        for o in r.get("operateurs", []):
            if not isinstance(o, dict) or not str(o.get("operateur", "")).strip():
                continue
            ops.append({
                "operateur": str(o["operateur"]).strip()[:30],
                "code": str(o.get("code", "")).strip()[:40],
                "forfait": max(0, int(o.get("forfait") or 0)),
                "depuis": float(o.get("depuis") or 0),
                "dernier": o.get("dernier") if isinstance(o.get("dernier"), dict) else None,
            })
        return {
            "seuil": max(0, int(r.get("seuil", 50) or 0)),
            "auto_heures": max(0, int(r.get("auto_heures", 6) or 0)),
            "operateurs": ops or json.loads(json.dumps(REGLAGES_PAR_DEFAUT["operateurs"])),
        }
    except Exception:
        return json.loads(json.dumps(REGLAGES_PAR_DEFAUT))


def ecrire(reglages: dict) -> None:
    temporaire = f"{fichier_soldes}.tmp"
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(reglages, f, ensure_ascii=False)
    os.replace(temporaire, fichier_soldes)


def operateur(reglages: dict, nom: str) -> dict | None:
    cible = _norm(nom)
    for o in reglages.get("operateurs", []):
        if cible and (_norm(o["operateur"]) in cible or cible in _norm(o["operateur"])):
            return o
    return None


def code_valide(code: str) -> bool:
    """ Un code USSD : commence par * ou #, finit par #, seulement des chiffres, * et #. """
    return bool(re.fullmatch(r"[*#][0-9*#]{1,30}#", str(code or "").strip()))


# Formulations des opérateurs : « Il vous reste 245 SMS », « SMS restants : 245 », « Bonus SMS 245 », « 245 SMS valables jusqu'au… ».
_MOTIFS = [
    r"(?:reste|restant|restants|solde)\D{0,25}?(\d[\d\s.]{0,8})\s*(?:sms|messages?)",
    r"(?:sms|messages?)\s*(?:restants?|disponibles?|bonus)?\s*[:=]?\s*(\d[\d\s.]{0,8})",
    r"(\d[\d\s.]{0,8})\s*(?:sms|messages?)\b",
]


def extraire_restants(texte: str) -> int | None:
    """ Le nombre de SMS restants dans la réponse de l'opérateur ; None s'il n'y figure pas. """
    t = str(texte or "").lower()
    for motif in _MOTIFS:
        m = re.search(motif, t)
        if m:
            chiffres = re.sub(r"\D", "", m.group(1))
            if chiffres:
                n = int(chiffres)
                if n < 1_000_000:
                    return n
    return None


def segments(message: str) -> int:
    """ Nombre de SMS facturés pour un message : 160 caractères pour un SMS seul, 153 par partie au-delà (alphabet GSM). """
    n = len(str(message or ""))
    return 1 if n <= 160 else math.ceil(n / 153)


def envoyes_depuis(envois: list, nom_operateur: str, depuis: float) -> int:
    """ SMS (segments) partis par la SIM de cet opérateur depuis un moment. """
    cible = _norm(nom_operateur)
    total = 0
    for e in envois:
        if e.get("envoye") and e.get("date", 0) >= depuis and cible and cible in _norm(e.get("sim", "")):
            total += segments(e.get("message", ""))
    return total


def etat(o: dict, envois: list, seuil: int) -> dict:
    """
    Ce que l'on affiche pour un opérateur : restants (nombre ou None), estimation (vrai : calculé, faux : donné par l'opérateur),
    bas (sous le seuil), date et texte de la dernière réponse.
    """
    dernier = o.get("dernier") or {}
    base, depuis, estimation = None, 0.0, True
    if isinstance(dernier.get("restants"), int):
        base, depuis = dernier["restants"], float(dernier.get("date") or 0)
        estimation = False
    if o.get("forfait") and o.get("depuis", 0) > depuis:
        base, depuis, estimation = o["forfait"], float(o["depuis"]), True
    restants = None
    if base is not None:
        partis = envoyes_depuis(envois, o["operateur"], depuis)
        restants = max(0, base - partis)
        if partis:
            estimation = True
    return {
        "operateur": o["operateur"],
        "restants": restants,
        "estimation": estimation,
        "bas": restants is not None and restants <= seuil,
        "date": dernier.get("date"),
        "texte": dernier.get("texte", ""),
    }


def enregistrer_reponse(nom_operateur: str, texte: str, ok: bool) -> dict:
    """ Garde la réponse de l'opérateur (et le nombre de SMS restants qu'on y lit). """
    r = lire()
    o = operateur(r, nom_operateur)
    if not o:
        o = {"operateur": nom_operateur[:30], "code": "", "forfait": 0, "depuis": 0, "dernier": None}
        r["operateurs"].append(o)
    o["dernier"] = {"date": time.time(), "texte": str(texte or "")[:500], "ok": bool(ok), "restants": extraire_restants(texte) if ok else None}
    ecrire(r)
    return o["dernier"]


def recharge(nom_operateur: str, forfait: int) -> None:
    """ L'école vient de recharger : le forfait saisi devient le point de départ de l'estimation. """
    r = lire()
    o = operateur(r, nom_operateur)
    if o:
        o["forfait"] = max(0, int(forfait or 0))
        o["depuis"] = time.time()
        ecrire(r)


def resume_pour_kelaplus(envois: list) -> list:
    """ Ce que le téléphone donne à Kelaplus (ping) : opérateur, restants, estimation, bas. """
    r = lire()
    sortie = []
    for o in r["operateurs"]:
        e = etat(o, envois, r["seuil"])
        if e["restants"] is not None:
            sortie.append({"operateur": e["operateur"], "restants": e["restants"], "estimation": e["estimation"], "bas": e["bas"], "date": e["date"]})
    return sortie


# --- Android : envoi du code USSD sur une SIM (Java : com.greatfy.kelaplussms.UssdHelper) -----------------------------------------------------------------

def envoyer_ussd(sim_id: int | None, code: str) -> str | None:
    """ Lance la demande ; None si elle est partie (réponse à lire avec reponse_ussd), sinon le message d'erreur. """
    if platform != "android":
        return "La consultation du solde ne fonctionne que sur le téléphone."
    if not code_valide(code):
        return "Code USSD invalide (exemple : *123#)."
    try:
        from jnius import autoclass
        activite = autoclass("org.kivy.android.PythonActivity").mActivity
        UssdHelper = autoclass("com.greatfy.kelaplussms.UssdHelper")
        UssdHelper.envoyer(activite, int(sim_id if sim_id is not None else -1), str(code))
        return None
    except Exception as e:
        return f"Demande impossible : {e}"


def reponse_ussd() -> tuple:
    """ (etat, texte) : 0 en attente, 1 réponse reçue, 2 échec. """
    if platform != "android":
        return 2, ""
    try:
        from jnius import autoclass
        UssdHelper = autoclass("com.greatfy.kelaplussms.UssdHelper")
        texte = UssdHelper.reponse()
        return int(UssdHelper.etat()), (str(texte) if texte is not None else "")
    except Exception as e:
        return 2, f"Lecture impossible : {e}"
