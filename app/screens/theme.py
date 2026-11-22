""" Identité visuelle de Kelaplus pour l'application Kelaplus SMS : couleurs, dégradé de la marque, composants communs (bandeau, cartes, pastilles). """

from kivy.graphics.texture import Texture
from kivy.lang import Builder
from kivy.properties import StringProperty, ColorProperty
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard

# Couleurs de Kelaplus (logo magenta, dégradé indigo → violet → magenta).
INDIGO = "#4338CA"
VIOLET = "#9305D3"
MAGENTA = "#C615D1"
VIOLET_PALE = "#F3E8FF"
FOND = "#F5F3FA"
CARTE = "#FFFFFF"
BORDURE = "#E9E4F2"
TEXTE = "#1F1B2E"
GRIS = "#6B6880"
VERT = "#16A34A"
VERT_PALE = "#DCFCE7"
ROUGE = "#DC2626"
ROUGE_PALE = "#FEE2E2"
ORANGE = "#EA580C"


def _rgb(hexa: str) -> tuple:
    hexa = hexa.lstrip("#")
    return tuple(int(hexa[i:i + 2], 16) for i in (0, 2, 4))


def degrade(couleurs=(INDIGO, VIOLET, MAGENTA), largeur=256) -> Texture:
    """ Texture horizontale du dégradé de la marque (pour le bandeau du haut). """
    arrets = [_rgb(c) for c in couleurs]
    buf = bytearray()
    for i in range(largeur):
        t = i / (largeur - 1) * (len(arrets) - 1)
        k = min(int(t), len(arrets) - 2)
        f = t - k
        a, b = arrets[k], arrets[k + 1]
        buf += bytes(int(a[j] + (b[j] - a[j]) * f) for j in range(3)) + b"\xff"
    tex = Texture.create(size=(largeur, 1), colorfmt="rgba")
    tex.blit_buffer(bytes(buf), colorfmt="rgba", bufferfmt="ubyte")
    tex.wrap = "clamp_to_edge"
    return tex


Builder.load_string(f'''
<CarteKela>:
    orientation: "vertical"
    adaptive_height: True
    padding: dp(16)
    spacing: dp(10)
    radius: [dp(18)]
    style: "outlined"
    theme_bg_color: "Custom"
    md_bg_color: "{CARTE}"
    theme_line_color: "Custom"
    line_color: "{BORDURE}"

<TitreCarte>:
    adaptive_height: True
    spacing: dp(10)
    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: "{VIOLET}"
        size_hint: None, None
        size: dp(24), dp(24)
        pos_hint: {{"center_y": .5}}
    MDLabel:
        text: root.text
        font_style: "Title"
        role: "medium"
        bold: True
        theme_text_color: "Custom"
        text_color: "{TEXTE}"
        adaptive_height: True
        pos_hint: {{"center_y": .5}}

<Pastille>:
    adaptive_size: True
    padding: dp(10), dp(4)
    radius: [dp(12)]
    md_bg_color: root.fond
    MDLabel:
        text: root.text
        adaptive_size: True
        font_style: "Label"
        role: "large"
        bold: True
        theme_text_color: "Custom"
        text_color: root.couleur

<ChiffreKela>:
    orientation: "vertical"
    adaptive_height: True
    padding: dp(12), dp(10)
    spacing: dp(2)
    radius: [dp(16)]
    style: "outlined"
    theme_bg_color: "Custom"
    md_bg_color: "{CARTE}"
    theme_line_color: "Custom"
    line_color: "{BORDURE}"
    MDLabel:
        text: root.valeur
        font_style: "Headline"
        role: "small"
        bold: True
        halign: "center"
        theme_text_color: "Custom"
        text_color: root.couleur
        adaptive_height: True
    MDLabel:
        text: root.libelle
        font_style: "Label"
        role: "medium"
        halign: "center"
        theme_text_color: "Custom"
        text_color: "{GRIS}"
        adaptive_height: True
''')


class CarteKela(MDCard):
    pass


class TitreCarte(MDBoxLayout):
    icon = StringProperty("circle")
    text = StringProperty("")


class Pastille(MDBoxLayout):
    text = StringProperty("")
    couleur = ColorProperty(VERT)
    fond = ColorProperty(VERT_PALE)


class ChiffreKela(MDCard):
    valeur = StringProperty("0")
    libelle = StringProperty("")
    couleur = ColorProperty(VIOLET)
