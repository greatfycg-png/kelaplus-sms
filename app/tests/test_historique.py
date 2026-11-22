"""Historique des SMS envoyés : enregistrement, ordre, totaux, limite.

Lancer :  python -m unittest tests.test_historique   (depuis le dossier app/)
"""
import sys
import tempfile
import time
import unittest
from os.path import abspath, dirname, join

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from services import historique


class HistoriqueTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self._avant = historique.fichier_historique
        historique.fichier_historique = join(self.dossier.name, "sms_history.json")

    def tearDown(self):
        historique.fichier_historique = self._avant
        self.dossier.cleanup()

    def test_enregistre_du_plus_recent_au_plus_ancien(self):
        historique.ajouter("+242061234567", "Bonjour", True, "PC-DIRECTION")
        historique.ajouter("+242069999999", "Rappel", False, "PC-CAISSE")
        e = historique.envois()
        self.assertEqual([x["message"] for x in e], ["Rappel", "Bonjour"])
        self.assertEqual(e[1]["ordinateur"], "PC-DIRECTION")
        self.assertFalse(e[0]["envoye"])

    def test_totaux(self):
        historique.ajouter("1", "a", True)
        historique.ajouter("2", "b", False)
        r = historique.resume()
        self.assertEqual((r["total"], r["envoyes"], r["echecs"], r["aujourdhui"]), (2, 1, 1, 2))

    def test_limite_et_vider(self):
        ancien = historique.MAX_ENVOIS
        historique.MAX_ENVOIS = 3
        try:
            for i in range(5):
                historique.ajouter(str(i), f"m{i}", True)
            self.assertEqual([x["numero"] for x in historique.envois()], ["4", "3", "2"])
        finally:
            historique.MAX_ENVOIS = ancien
        historique.vider()
        self.assertEqual(historique.envois(), [])

    def test_fichier_absent_ou_abime(self):
        self.assertEqual(historique.envois(), [])
        with open(historique.fichier_historique, "w") as f:
            f.write("{pas du json")
        self.assertEqual(historique.envois(), [])


if __name__ == "__main__":
    unittest.main()
