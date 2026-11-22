"""Choix de la SIM selon l'opérateur du destinataire (06 → MTN, 05/04 → Airtel).

Lancer :  python -m unittest tests.test_sim_routing   (depuis le dossier app/)
"""
import sys
import tempfile
import unittest
from os.path import abspath, dirname, join

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from services import simRouting as s

SIMS = [{"id": 3, "emplacement": 0, "operateur": "MTN CG"}, {"id": 7, "emplacement": 1, "operateur": "Airtel CONGO"}]


class SimTest(unittest.TestCase):
    def setUp(self):
        self.dossier = tempfile.TemporaryDirectory()
        self._avant = s.fichier_reglages
        s.fichier_reglages = join(self.dossier.name, "sim_routing.json")

    def tearDown(self):
        s.fichier_reglages = self._avant
        self.dossier.cleanup()

    def test_numero_local(self):
        self.assertEqual(s.numero_local("+242 06 123 45 67"), "061234567")
        self.assertEqual(s.numero_local("00242051234567"), "051234567")
        self.assertEqual(s.numero_local("242041234567"), "041234567")
        self.assertEqual(s.numero_local("06 123 45 67"), "061234567")
        self.assertEqual(s.numero_local("61234567"), "061234567")

    def test_choix_par_operateur(self):
        r = s.lire_reglages()  # réglages par défaut
        self.assertEqual(s.choisir_sim("+242061234567", SIMS, r)["id"], 3)
        self.assertEqual(s.choisir_sim("+242051234567", SIMS, r)["id"], 7)
        self.assertEqual(s.choisir_sim("041234567", SIMS, r)["id"], 7)
        self.assertIsNone(s.choisir_sim("+242011234567", SIMS, r))  # aucun préfixe connu : SIM par défaut

    def test_sim_absente_une_seule_sim_ou_desactive(self):
        r = s.lire_reglages()
        self.assertIsNone(s.choisir_sim("061234567", [SIMS[1], {"id": 9, "emplacement": 1, "operateur": "Orange"}], r))
        self.assertIsNone(s.choisir_sim("061234567", [SIMS[0]], r))
        self.assertIsNone(s.choisir_sim("061234567", SIMS, {**r, "actif": False}))

    def test_reglages_enregistres(self):
        s.ecrire_reglages({"actif": True, "regles": [{"operateur": "Airtel", "prefixes": s.normaliser_prefixes("05, 04 ; 05")}]})
        r = s.lire_reglages()
        self.assertEqual(r["regles"], [{"operateur": "Airtel", "prefixes": ["05", "04"]}])
        self.assertIsNone(s.choisir_sim("061234567", SIMS, r))  # plus de règle MTN

    def test_prefixe_le_plus_long(self):
        r = {"actif": True, "regles": [{"operateur": "MTN", "prefixes": ["0"]}, {"operateur": "Airtel", "prefixes": ["05"]}]}
        self.assertEqual(s.choisir_sim("051234567", SIMS, r)["id"], 7)


if __name__ == "__main__":
    unittest.main()
