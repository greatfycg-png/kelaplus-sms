from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import MDListItem

from kivy.lang import Builder

from screens import theme as t

# Réglages de Kelaplus SMS : démarrage automatique, port, clé API ; enregistrer ou remettre à zéro.
Builder.load_string(f'''
<ApiKeyTxtbox>:
    mode: "outlined"
    readonly: True

<LigneReglage@MDListItem>:
    theme_bg_color: "Custom"
    md_bg_color: "{t.CARTE}"
    radius: [dp(14)]

<SettingsBox>:
    orientation: "vertical"
    spacing: dp(12)

    MDScrollView:
        do_scroll_x: False
        bar_width: 0

        MDBoxLayout:
            id: main_scroll_bx
            orientation: "vertical"
            adaptive_height: True
            spacing: dp(12)
            padding: dp(4), 0, dp(4), dp(12)

            CarteKela:
                TitreCarte:
                    icon: "cog-outline"
                    text: "Réglages du téléphone"

                LigneReglage:
                    MDListItemLeadingIcon:
                        icon: "rocket-launch-outline"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDListItemHeadlineText:
                        text: "Démarrage automatique"
                    MDListItemSupportingText:
                        text: "Le serveur s'ouvre avec l'appli"
                    MDSwitch:
                        id: auto_start_sw
                        pos_hint: {{"center_y": 0.5}}
                        icon_active: "check"
                        icon_inactive: "close"
                        theme_thumb_color: "Custom"
                        thumb_color_active: "white"
                        theme_track_color: "Custom"
                        track_color_active: "{t.VIOLET}"
                        on_release: app.save_settings(self, "switch")

                LigneReglage:
                    MDListItemLeadingIcon:
                        icon: "server-network"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDListItemHeadlineText:
                        text: "Port du serveur"
                    MDListItemSupportingText:
                        text: "9292 par défaut"
                    MDTextField:
                        id: port_no_inp
                        mode: "outlined"
                        input_filter: 'int'

            CarteKela:
                TitreCarte:
                    icon: "sim-outline"
                    text: "Choix de la SIM (double SIM)"
                MDLabel:
                    text: "Chaque SMS part par la SIM de l'opérateur du destinataire : préfixe du numéro sans le +242 (06 pour MTN, 05 et 04 pour Airtel). Sans SIM de cet opérateur : la SIM par défaut."
                    font_style: "Body"
                    role: "small"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                LigneReglage:
                    MDListItemLeadingIcon:
                        icon: "swap-horizontal"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDListItemHeadlineText:
                        text: "SIM selon l'opérateur"
                    MDListItemSupportingText:
                        text: "Sinon : SIM par défaut"
                    MDSwitch:
                        id: sim_actif
                        pos_hint: {{"center_y": 0.5}}
                        icon_active: "check"
                        icon_inactive: "close"
                        theme_thumb_color: "Custom"
                        thumb_color_active: "white"
                        theme_track_color: "Custom"
                        track_color_active: "{t.VIOLET}"
                MDLabel:
                    id: sims_lbl
                    text: "SIM détectées : —"
                    font_style: "Body"
                    role: "medium"
                    theme_text_color: "Custom"
                    text_color: "{t.TEXTE}"
                    adaptive_height: True
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(8)
                    MDTextField:
                        id: op1
                        mode: "outlined"
                        size_hint_x: .45
                        MDTextFieldHintText:
                            text: "Opérateur 1"
                    MDTextField:
                        id: pref1
                        mode: "outlined"
                        size_hint_x: .55
                        MDTextFieldHintText:
                            text: "Préfixes (ex. 06)"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(8)
                    MDTextField:
                        id: op2
                        mode: "outlined"
                        size_hint_x: .45
                        MDTextFieldHintText:
                            text: "Opérateur 2"
                    MDTextField:
                        id: pref2
                        mode: "outlined"
                        size_hint_x: .55
                        MDTextFieldHintText:
                            text: "Préfixes (ex. 05, 04)"
                MDButton:
                    theme_bg_color: "Custom"
                    md_bg_color: "{t.VIOLET}"
                    pos_hint: {{"center_x": .5}}
                    on_release: app.enregistrer_sim()
                    MDButtonIcon:
                        icon: "content-save-outline"
                        theme_icon_color: "Custom"
                        icon_color: "white"
                    MDButtonText:
                        text: "Enregistrer le choix des SIM"
                        theme_text_color: "Custom"
                        text_color: "white"

            CarteKela:
                TitreCarte:
                    icon: "counter"
                    text: "Solde SMS"
                MDLabel:
                    text: "Code de solde : le code que vous tapez pour voir vos SMS restants (exemple *123#). Forfait : le nombre de SMS achetés ; « Rechargé » démarre le décompte à partir d'aujourd'hui."
                    font_style: "Body"
                    role: "small"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(6)
                    MDTextField:
                        id: sol_op1
                        mode: "outlined"
                        size_hint_x: .3
                        MDTextFieldHintText:
                            text: "Opérateur"
                    MDTextField:
                        id: sol_code1
                        mode: "outlined"
                        size_hint_x: .35
                        MDTextFieldHintText:
                            text: "Code de solde"
                    MDTextField:
                        id: sol_forfait1
                        mode: "outlined"
                        input_filter: "int"
                        size_hint_x: .35
                        MDTextFieldHintText:
                            text: "Forfait (SMS)"
                MDButton:
                    style: "text"
                    pos_hint: {{"right": 1}}
                    on_release: app.recharge_sim(1)
                    MDButtonIcon:
                        icon: "battery-charging-high"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDButtonText:
                        text: "Rechargé aujourd'hui"
                        theme_text_color: "Custom"
                        text_color: "{t.VIOLET}"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(6)
                    MDTextField:
                        id: sol_op2
                        mode: "outlined"
                        size_hint_x: .3
                        MDTextFieldHintText:
                            text: "Opérateur"
                    MDTextField:
                        id: sol_code2
                        mode: "outlined"
                        size_hint_x: .35
                        MDTextFieldHintText:
                            text: "Code de solde"
                    MDTextField:
                        id: sol_forfait2
                        mode: "outlined"
                        input_filter: "int"
                        size_hint_x: .35
                        MDTextFieldHintText:
                            text: "Forfait (SMS)"
                MDButton:
                    style: "text"
                    pos_hint: {{"right": 1}}
                    on_release: app.recharge_sim(2)
                    MDButtonIcon:
                        icon: "battery-charging-high"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDButtonText:
                        text: "Rechargé aujourd'hui"
                        theme_text_color: "Custom"
                        text_color: "{t.VIOLET}"
                MDBoxLayout:
                    adaptive_height: True
                    spacing: dp(6)
                    MDTextField:
                        id: sol_seuil
                        mode: "outlined"
                        input_filter: "int"
                        MDTextFieldHintText:
                            text: "Alerte sous (SMS)"
                    MDTextField:
                        id: sol_auto
                        mode: "outlined"
                        input_filter: "int"
                        MDTextFieldHintText:
                            text: "Vérifier toutes les (heures)"
                MDButton:
                    theme_bg_color: "Custom"
                    md_bg_color: "{t.VIOLET}"
                    pos_hint: {{"center_x": .5}}
                    on_release: app.enregistrer_soldes()
                    MDButtonIcon:
                        icon: "content-save-outline"
                        theme_icon_color: "Custom"
                        icon_color: "white"
                    MDButtonText:
                        text: "Enregistrer le solde SMS"
                        theme_text_color: "Custom"
                        text_color: "white"


    MDBoxLayout:
        orientation: "horizontal"
        adaptive_height: True
        spacing: dp(10)
        padding: dp(4), 0

        MDButton:
            theme_bg_color: "Custom"
            md_bg_color: "{t.VIOLET}"
            size_hint_x: 1
            on_release: app.save_settings(self)
            MDButtonIcon:
                icon: "content-save-outline"
                theme_icon_color: "Custom"
                icon_color: "white"
            MDButtonText:
                text: "Enregistrer"
                theme_text_color: "Custom"
                text_color: "white"

        MDButton:
            style: "outlined"
            size_hint_x: 1
            on_release: app.reset_settings(self)
            MDButtonIcon:
                icon: "undo"
                theme_icon_color: "Custom"
                icon_color: "{t.GRIS}"
            MDButtonText:
                text: "Remettre à zéro"
                theme_text_color: "Custom"
                text_color: "{t.GRIS}"
''')


class SettingsBox(MDBoxLayout):
    pass


class ApiKeyTxtbox(MDTextField):
    pass
