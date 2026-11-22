"""Mise à jour : comparaison des versions et lecture de la dernière version publiée.

Lancer :  python -m unittest tests.test_mise_a_jour   (depuis le dossier app/)
"""
import sys
import unittest
from os.path import abspath, dirname

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from services import miseAJour as m


class MiseAJourTest(unittest.TestCase):
    def test_comparaison(self):
        self.assertTrue(m.plus_recente("v1.5.0", "1.4.0"))
        self.assertTrue(m.plus_recente("1.10.0", "1.9.3"))
        self.assertFalse(m.plus_recente("v1.4.0", "1.4.0"))
        self.assertFalse(m.plus_recente("1.3", "1.4.0"))
        self.assertEqual(m.version_tuple("v2"), (2, 0, 0))

    def test_lien_fixe(self):
        self.assertTrue(m.LIEN_APK.endswith("/releases/latest/download/KelaplusSMS.apk"))


if __name__ == "__main__":
    unittest.main()
