"""Jumelage Kelaplus : le déroulement complet, sans téléphone (les fichiers sont dans un dossier temporaire).

Lancer :  python -m unittest tests.test_pairing   (depuis le dossier app/)
"""
import json
import sys
import tempfile
import time
import unittest
from os.path import abspath, dirname, join

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from services import pairing


class JumelageTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self._avant = (pairing.fichier_demande, pairing.fichier_cles)
        pairing.fichier_demande = join(self.dossier.name, "pair_request.json")
        pairing.fichier_cles = join(self.dossier.name, "keys.json")

    def tearDown(self):
        pairing.fichier_demande, pairing.fichier_cles = self._avant
        self.dossier.cleanup()

    def test_autorisation_complete(self):
        d = pairing.creer_demande("KELASI-PC", "Complexe Test")
        self.assertEqual(d["statut"], "attente")
        self.assertEqual(pairing.etat_demande(d["id"]), {"statut": "attente"})
        # Le téléphone montre la demande, l'utilisateur autorise.
        self.assertEqual(pairing.demande_en_attente()["poste"], "KELASI-PC")
        self.assertTrue(pairing.accepter(d["id"]))
        # Kelaplus reçoit la clé UNE SEULE fois.
        etat = pairing.etat_demande(d["id"])
        self.assertEqual(etat["statut"], "accepte")
        self.assertTrue(etat["cle"].startswith("osms_"))
        self.assertEqual(pairing.etat_demande(d["id"]), {"statut": "termine"})
        # La clé est enregistrée (hachée) pour le service : la même que celle remise.
        with open(pairing.fichier_cles) as f:
            cles = json.load(f)
        self.assertIn(pairing._hacher(etat["cle"]), cles)
        self.assertEqual(pairing.ordinateurs_connectes(), ["KELASI-PC"])
        self.assertIsNone(pairing.demande_en_attente())

    def test_refus_et_demande_inconnue(self):
        d = pairing.creer_demande("PC")
        pairing.refuser(d["id"])
        self.assertEqual(pairing.etat_demande(d["id"]), {"statut": "refuse"})
        self.assertFalse(pairing.accepter(d["id"]))  # trop tard : refusée
        self.assertEqual(pairing.etat_demande("n-importe-quoi"), {"statut": "inconnue"})
        self.assertEqual(pairing.ordinateurs_connectes(), [])

    def test_la_demande_expire(self):
        d = pairing.creer_demande("PC")
        with open(pairing.fichier_demande) as f:
            contenu = json.load(f)
        contenu["cree"] = time.time() - pairing.DUREE_DEMANDE_S - 1
        with open(pairing.fichier_demande, "w") as f:
            json.dump(contenu, f)
        self.assertEqual(pairing.etat_demande(d["id"]), {"statut": "expire"})
        self.assertIsNone(pairing.demande_en_attente())
        self.assertFalse(pairing.accepter(d["id"]))

    def test_plusieurs_ordinateurs_gardent_leur_cle(self):
        a = pairing.creer_demande("PC-A")
        pairing.accepter(a["id"])
        cle_a = pairing.etat_demande(a["id"])["cle"]
        b = pairing.creer_demande("PC-B")
        pairing.accepter(b["id"])
        self.assertEqual(sorted(pairing.ordinateurs_connectes()), ["PC-A", "PC-B"])
        with open(pairing.fichier_cles) as f:
            self.assertIn(pairing._hacher(cle_a), json.load(f))  # la clé du premier marche toujours

    def test_la_meme_demande_repetee_ne_recommence_pas(self):
        a = pairing.creer_demande("PC")
        b = pairing.creer_demande("PC")
        self.assertEqual(a["id"], b["id"])


if __name__ == "__main__":
    unittest.main()
