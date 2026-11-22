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
                        text: "Démarrer le serveur à l'ouverture"
                    MDListItemSupportingText:
                        text: "Conseillé : Kelaplus trouve le téléphone tout seul"
                    MDSwitch:
                        id: auto_start_sw
                        pos_hint: {{"center_y": 0.5}}
                        icon_active: "check"
                        icon_inactive: "close"
                        on_release: app.save_settings(self, "switch")

                LigneReglage:
                    MDListItemLeadingIcon:
                        icon: "server-network"
                        theme_icon_color: "Custom"
                        icon_color: "{t.VIOLET}"
                    MDListItemHeadlineText:
                        text: "Port du serveur"
                    MDListItemSupportingText:
                        text: "9292 par défaut (1025 à 65535)"
                    MDListItemTertiaryText:
                        text: "Redémarrez le serveur après un changement"
                    MDTextField:
                        id: port_no_inp
                        mode: "outlined"
                        input_filter: 'int'

            CarteKela:
                TitreCarte:
                    icon: "key-outline"
                    text: "Clé API"
                MDLabel:
                    text: "Inutile avec Kelaplus : la connexion par autorisation crée une clé pour chaque ordinateur. Générer une nouvelle clé déconnecte tous les ordinateurs."
                    font_style: "Body"
                    role: "small"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                MDButton:
                    style: "outlined"
                    pos_hint: {{"center_x": .5}}
                    on_release: app.new_api_key_pop()
                    MDButtonIcon:
                        icon: "autorenew"
                        theme_icon_color: "Custom"
                        icon_color: "{t.ORANGE}"
                    MDButtonText:
                        text: "Générer une nouvelle clé"
                        theme_text_color: "Custom"
                        text_color: "{t.ORANGE}"

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
