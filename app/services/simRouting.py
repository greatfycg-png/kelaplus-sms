""" Choix de la SIM d'envoi selon l'opérateur du destinataire (téléphone double SIM) — ajout Kelaplus.

Au Congo, l'indicatif +242 retiré, les numéros MTN commencent par 06, ceux d'Airtel par 05 ou 04. Chaque règle associe des préfixes à un
nom d'opérateur ; au moment d'envoyer, on cherche la SIM active dont l'opérateur porte ce nom (« MTN CG », « Airtel CONGO »…) et le SMS
part par elle. Pas de règle, pas de SIM de cet opérateur, routage désactivé ou téléphone à une seule SIM : la SIM par défaut d'Android.

Les réglages sont dans `sim_routing.json` (dossier de configuration) : l'application les écrit, le service les relit à chaque envoi.
"""

import json
import os
import re
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
fichier_reglages = join(config_dir, "sim_routing.json")

INDICATIF = "242"
REGLAGES_PAR_DEFAUT = {
    "actif": True,
    "regles": [
        {"operateur": "MTN", "prefixes": ["06"]},
        {"operateur": "Airtel", "prefixes": ["05", "04"]},
    ],
}


def numero_local(numero: str) -> str:
    """ « +242 06 123 45 67 », « 00242061234567 », « 242061234567 » → « 061234567 » (chiffres seuls, indicatif retiré). """
    chiffres = re.sub(r"\D", "", str(numero or ""))
    for prefixe in ("00" + INDICATIF, INDICATIF):
        if chiffres.startswith(prefixe) and len(chiffres) > len(prefixe) + 6:
            chiffres = chiffres[len(prefixe):]
            break
    # Un numéro local saisi sans son 0 (« 61234567 ») : on remet le 0.
    if len(chiffres) == 8 and not chiffres.startswith("0"):
        chiffres = "0" + chiffres
    return chiffres


def normaliser_prefixes(texte) -> list:
    """ « 05, 04 » ou ["05", " 04 "] → ["05", "04"] (chiffres seuls, sans doublon). """
    morceaux = texte if isinstance(texte, list) else re.split(r"[,;\s/]+", str(texte or ""))
    vus = []
    for m in morceaux:
        p = re.sub(r"\D", "", str(m))
        if p and p not in vus:
            vus.append(p)
    return vus


def lire_reglages() -> dict:
    try:
        with open(fichier_reglages, "r", encoding="utf-8") as f:
            r = json.load(f)
        regles = [
            {"operateur": str(x.get("operateur", "")).strip()[:30], "prefixes": normaliser_prefixes(x.get("prefixes", []))}
            for x in r.get("regles", [])
            if isinstance(x, dict)
        ]
        return {"actif": bool(r.get("actif", True)), "regles": [x for x in regles if x["operateur"]]}
    except Exception:
        return json.loads(json.dumps(REGLAGES_PAR_DEFAUT))


def ecrire_reglages(reglages: dict) -> None:
    temporaire = f"{fichier_reglages}.tmp"
    with open(temporaire, "w", encoding="utf-8") as f:
        json.dump(reglages, f, ensure_ascii=False)
    os.replace(temporaire, fichier_reglages)


def _norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(t or "").lower())


def operateur_du_numero(numero: str, reglages: dict) -> str | None:
    """ Le nom d'opérateur de la règle dont un préfixe ouvre le numéro (le préfixe le plus long l'emporte). """
    local = numero_local(numero)
    meilleur, longueur = None, 0
    for regle in reglages.get("regles", []):
        for p in regle.get("prefixes", []):
            if p and local.startswith(p) and len(p) > longueur:
                meilleur, longueur = regle.get("operateur"), len(p)
    return meilleur


def choisir_sim(numero: str, sims: list, reglages: dict) -> dict | None:
    """
    La SIM par laquelle envoyer : celle dont l'opérateur (nom affiché par Android) contient le nom de la règle. `sims` :
    [{"id": <subscriptionId>, "emplacement": 0, "operateur": "MTN CG"}]. None : la SIM par défaut.
    """
    if not reglages.get("actif") or len(sims) < 2:
        return None
    operateur = operateur_du_numero(numero, reglages)
    if not operateur:
        return None
    cible = _norm(operateur)
    for sim in sims:
        if cible and cible in _norm(sim.get("operateur", "")):
            return sim
    return None


def sims_actives() -> list:
    """ Les SIM actives du téléphone (Android 5.1 et plus ; permission « Téléphone »). Hors Android, ou en cas de refus : aucune. """
    if platform != "android":
        return []
    try:
        from jnius import autoclass
        contexte = None
        try:
            contexte = autoclass("org.kivy.android.PythonService").mService
        except Exception:
            contexte = None
        if contexte is None:
            contexte = autoclass("org.kivy.android.PythonActivity").mActivity
        SubscriptionManager = autoclass("android.telephony.SubscriptionManager")
        gestion = SubscriptionManager.from_(contexte) if hasattr(SubscriptionManager, "from_") else getattr(SubscriptionManager, "from")(contexte)
        liste = gestion.getActiveSubscriptionInfoList()
        sims = []
        if liste is not None:
            for i in range(liste.size()):
                info = liste.get(i)
                nom = info.getCarrierName()
                affiche = info.getDisplayName()
                sims.append({
                    "id": int(info.getSubscriptionId()),
                    "emplacement": int(info.getSimSlotIndex()),
                    "operateur": str(nom.toString() if nom is not None else (affiche.toString() if affiche is not None else "")),
                })
        return sims
    except Exception as e:
        print(f"SIM : lecture impossible : {e}")
        return []
