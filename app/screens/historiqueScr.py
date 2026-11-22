""" Onglet « Historique » : les SMS envoyés par ce téléphone pour Kelaplus (services/historique.py), du plus récent au plus ancien. """

import time

from kivy.clock import Clock
from kivy.lang import Builder
from kivy.properties import StringProperty, ColorProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard

from screens import theme as t
from services import historique

AFFICHES = 150

Builder.load_string(f'''
<LigneSms>:
    orientation: "vertical"
    adaptive_height: True
    padding: dp(14), dp(12)
    spacing: dp(6)
    radius: [dp(16)]
    style: "outlined"
    theme_bg_color: "Custom"
    md_bg_color: "{t.CARTE}"
    theme_line_color: "Custom"
    line_color: "{t.BORDURE}"
    MDBoxLayout:
        adaptive_height: True
        spacing: dp(8)
        MDIcon:
            icon: "account-outline"
            theme_text_color: "Custom"
            text_color: "{t.VIOLET}"
            size_hint: None, None
            size: dp(22), dp(22)
            pos_hint: {{"center_y": .5}}
        MDLabel:
            text: root.numero
            font_style: "Title"
            role: "small"
            bold: True
            theme_text_color: "Custom"
            text_color: "{t.TEXTE}"
            adaptive_height: True
            pos_hint: {{"center_y": .5}}
        Pastille:
            text: root.statut
            couleur: root.couleur
            fond: root.fond
            pos_hint: {{"center_y": .5}}
    MDLabel:
        text: root.message
        font_style: "Body"
        role: "medium"
        theme_text_color: "Custom"
        text_color: "{t.TEXTE}"
        adaptive_height: True
    MDLabel:
        text: root.details
        font_style: "Label"
        role: "medium"
        theme_text_color: "Custom"
        text_color: "{t.GRIS}"
        adaptive_height: True

<HistoriqueBox>:
    orientation: "vertical"
    spacing: dp(10)

    MDBoxLayout:
        adaptive_height: True
        padding: dp(4), dp(12), dp(4), 0
        spacing: dp(10)
        ChiffreKela:
            id: h_jour
            libelle: "Aujourd'hui"
            couleur: "{t.VIOLET}"
        ChiffreKela:
            id: h_envoyes
            libelle: "Envoyés"
            couleur: "{t.VERT}"
        ChiffreKela:
            id: h_echecs
            libelle: "Échecs"
            couleur: "{t.ROUGE}"

    MDBoxLayout:
        adaptive_height: True
        padding: dp(4), 0
        spacing: dp(8)
        MDLabel:
            text: "SMS envoyés par ce téléphone"
            font_style: "Title"
            role: "small"
            bold: True
            theme_text_color: "Custom"
            text_color: "{t.TEXTE}"
            adaptive_height: True
            pos_hint: {{"center_y": .5}}
        MDIconButton:
            icon: "refresh"
            theme_icon_color: "Custom"
            icon_color: "{t.VIOLET}"
            on_release: root.actualiser()
        MDIconButton:
            icon: "delete-sweep-outline"
            theme_icon_color: "Custom"
            icon_color: "{t.ROUGE}"
            on_release: app.vider_historique()

    MDScrollView:
        do_scroll_x: False
        bar_width: 0
        MDBoxLayout:
            id: liste_sms
            orientation: "vertical"
            adaptive_height: True
            padding: dp(4), 0, dp(4), dp(12)
            spacing: dp(8)
''')


class LigneSms(MDCard):
    numero = StringProperty("")
    message = StringProperty("")
    details = StringProperty("")
    statut = StringProperty("")
    couleur = ColorProperty(t.VERT)
    fond = ColorProperty(t.VERT_PALE)


def quand(horodatage: float) -> str:
    """ « Aujourd'hui à 14:05 », « Hier à 09:12 », « 21/11/2026 à 16:40 ». """
    try:
        lt = time.localtime(horodatage)
        heure = time.strftime("%H:%M", lt)
        aujourdhui = time.localtime()
        jours = (time.mktime(aujourdhui[:3] + (0, 0, 0, 0, 0, -1)) - time.mktime(lt[:3] + (0, 0, 0, 0, 0, -1))) / 86400
        if jours < 1:
            return f"Aujourd'hui à {heure}"
        if jours < 2:
            return f"Hier à {heure}"
        return f"{time.strftime('%d/%m/%Y', lt)} à {heure}"
    except Exception:
        return ""


class HistoriqueBox(MDBoxLayout):
    _horloge = None
    _signature = None

    def a_l_ouverture(self):
        self.actualiser()
        # Tant que l'onglet est ouvert, les nouveaux SMS apparaissent d'eux-mêmes.
        if not self._horloge:
            self._horloge = Clock.schedule_interval(lambda dt: self.actualiser(), 3)

    def a_la_sortie(self):
        if self._horloge:
            self._horloge.cancel()
            self._horloge = None

    def actualiser(self):
        try:
            resume = historique.resume()
            envois = historique.envois(AFFICHES)
        except Exception as e:
            print(f"Historique illisible : {e}")
            return
        self.ids.h_jour.valeur = str(resume["aujourdhui"])
        self.ids.h_envoyes.valeur = str(resume["envoyes"])
        self.ids.h_echecs.valeur = str(resume["echecs"])
        signature = (resume["total"], envois[0]["id"] if envois else None)
        if signature == self._signature:
            return
        self._signature = signature
        liste = self.ids.liste_sms
        liste.clear_widgets()
        if not envois:
            from kivymd.uix.label import MDLabel
            liste.add_widget(MDLabel(
                text="Aucun SMS envoyé pour l'instant. Les SMS que Kelaplus envoie par ce téléphone s'afficheront ici.",
                theme_text_color="Custom", text_color=t.GRIS, adaptive_height=True, halign="center", padding=(20, 40)))
            return
        for e in envois:
            ok = bool(e.get("envoye"))
            message = str(e.get("message", ""))
            if len(message) > 220:
                message = message[:217] + "…"
            ordinateur = e.get("ordinateur") or ""
            liste.add_widget(LigneSms(
                numero=str(e.get("numero", "")),
                message=message,
                details=quand(e.get("date", 0)) + (f"  ·  depuis {ordinateur}" if ordinateur else ""),
                statut="Envoyé" if ok else "Échec",
                couleur=t.VERT if ok else t.ROUGE,
                fond=t.VERT_PALE if ok else t.ROUGE_PALE,
            ))
