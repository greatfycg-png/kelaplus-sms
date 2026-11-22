"""Solde de SMS des SIM : lecture de la réponse de l'opérateur, estimation, seuil.

Lancer :  python -m unittest tests.test_solde_sms   (depuis le dossier app/)
"""
import sys
import tempfile
import time
import unittest
from os.path import abspath, dirname, join

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from services import soldeSms as s


class SoldeTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self._avant = s.fichier_soldes
        s.fichier_soldes = join(self.dossier.name, "solde_sms.json")

    def tearDown(self):
        s.fichier_soldes = self._avant
        self.dossier.cleanup()

    def test_extraire_restants(self):
        self.assertEqual(s.extraire_restants("Cher client, il vous reste 245 SMS valables jusqu'au 30/11/2026."), 245)
        self.assertEqual(s.extraire_restants("SMS restants : 1 200. Merci."), 1200)
        self.assertEqual(s.extraire_restants("Votre bonus: 50 SMS, 100 Mo"), 50)
        self.assertEqual(s.extraire_restants("Solde principal 1500 FCFA"), None)
        self.assertIsNone(s.extraire_restants(""))

    def test_code_valide(self):
        self.assertTrue(s.code_valide("*123#"))
        self.assertTrue(s.code_valide("*144*2*1#"))
        self.assertFalse(s.code_valide("123"))
        self.assertFalse(s.code_valide("*123#; rm"))

    def test_segments(self):
        self.assertEqual(s.segments("a" * 160), 1)
        self.assertEqual(s.segments("a" * 161), 2)
        self.assertEqual(s.segments("a" * 307), 3)

    def test_estimation_apres_reponse_operateur(self):
        s.enregistrer_reponse("MTN", "Il vous reste 100 SMS", True)
        r = s.lire()
        o = s.operateur(r, "MTN CG")
        apres = time.time() + 1
        envois = [
            {"envoye": True, "date": apres, "sim": "MTN CG", "message": "court"},
            {"envoye": True, "date": apres, "sim": "MTN CG", "message": "x" * 200},  # 2 SMS
            {"envoye": True, "date": apres, "sim": "Airtel CONGO", "message": "court"},  # autre SIM
            {"envoye": False, "date": apres, "sim": "MTN CG", "message": "échec"},  # pas facturé
        ]
        e = s.etat(o, envois, 50)
        self.assertEqual(e["restants"], 97)
        self.assertTrue(e["estimation"])
        self.assertFalse(e["bas"])
        self.assertEqual(s.etat(o, [], 50)["estimation"], False)  # rien envoyé depuis : le solde de l'opérateur

    def test_recharge_et_seuil(self):
        s.recharge("Airtel", 40)
        r = s.lire()
        e = s.etat(s.operateur(r, "Airtel"), [], r["seuil"])
        self.assertEqual(e["restants"], 40)
        self.assertTrue(e["bas"])  # 40 ≤ 50
        self.assertEqual(s.resume_pour_kelaplus([])[0]["operateur"], "Airtel")

    def test_reponse_sans_nombre(self):
        d = s.enregistrer_reponse("MTN", "Service indisponible", True)
        self.assertIsNone(d["restants"])
        self.assertIsNone(s.etat(s.operateur(s.lire(), "MTN"), [], 50)["restants"])


if __name__ == "__main__":
    unittest.main()
