from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText
from kivymd.uix.list import MDListItem
from kivymd.uix.dropdownitem import MDDropDownItem, MDDropDownItemText
from kivymd.uix.textfield import MDTextField

from kivy.lang import Builder
from kivy.core.clipboard import Clipboard
from kivy.properties import StringProperty

from screens import theme as t

# Accueil de Kelaplus SMS : état du serveur, chiffres du jour, ordinateurs Kelaplus connectés, adresse du téléphone sur le Wi-Fi.
Builder.load_string(f'''
<EndPointUrl>
    padding: dp(4), dp(2)
    theme_bg_color: "Custom"
    md_bg_color: "{t.FOND}"
    radius: [dp(12)]
    MDListItemLeadingIcon:
        icon: "wifi"
        theme_icon_color: "Custom"
        icon_color: "{t.VIOLET}"
    MDListItemHeadlineText:
        text: root.url
        theme_text_color: "Custom"
        text_color: "{t.TEXTE}"
    MDListItemSupportingText:
        text: root.iface_name
        theme_text_color: "Custom"
        text_color: "{t.GRIS}"
    MDIconButton:
        icon: "content-copy"
        theme_icon_color: "Custom"
        icon_color: "{t.VIOLET}"
        pos_hint: {{'center_y': 0.5}}
        on_release: root.copy_url(root.url)

<ButtonControl>
    pos_hint: {{"center_x": .5}}
    theme_bg_color: "Custom"
    md_bg_color: self.btn_colour
    radius: [dp(14)]
    MDButtonIcon:
        icon: root.btn_icon
        theme_icon_color: "Custom"
        icon_color: "white"
    MDButtonText:
        text: root.btn_txt
        theme_text_color: "Custom"
        text_color: "white"
        bold: True

<DocButton>
    pos_hint: {{"center_x": .5}}
    style: "text"
    on_release: app.api_doc_link()
    MDButtonIcon:
        icon: root.btn_icon
        theme_icon_color: "Custom"
        icon_color: "{t.VIOLET}"
    MDButtonText:
        text: root.btn_txt
        theme_text_color: "Custom"
        text_color: "{t.VIOLET}"

<SerialBtn>
    pos_hint: {{"center_x": .5}}
    theme_bg_color: "Custom"
    md_bg_color: "{t.TEXTE}"
    MDButtonIcon:
        icon: root.btn_icon
        theme_icon_color: "Custom"
        icon_color: "white"
    MDButtonText:
        text: root.btn_txt
        theme_text_color: "Custom"
        text_color: "white"

<AppHomeBox>:
    orientation: 'vertical'

    MDScrollView:
        do_scroll_x: False
        bar_width: 0

        MDBoxLayout:
            id: home_scr_main_box
            orientation: "vertical"
            adaptive_height: True
            padding: dp(4), dp(12), dp(4), dp(12)
            spacing: dp(12)

            CarteKela:
                MDBoxLayout:
                    adaptive_height: True
                    TitreCarte:
                        icon: "cellphone-message"
                        text: "Passerelle SMS"
                    Pastille:
                        id: etat_pastille
                        text: "Arrêtée"
                        couleur: "{t.ROUGE}"
                        fond: "{t.ROUGE_PALE}"
                        pos_hint: {{"center_y": .5}}
                MDLabel:
                    id: api_srv_lbl
                    text: "Le serveur est arrêté : Kelaplus ne peut pas envoyer de SMS par ce téléphone."
                    font_style: "Body"
                    role: "medium"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                ButtonControl:
                    id: api_srv_btn
                    btn_colour: "{t.VIOLET}"
                    style: "filled"
                    on_release: app.api_server_mgr(self)

            MDBoxLayout:
                adaptive_height: True
                spacing: dp(10)
                ChiffreKela:
                    id: chiffre_jour
                    valeur: "0"
                    libelle: "Aujourd'hui"
                    couleur: "{t.VIOLET}"
                ChiffreKela:
                    id: chiffre_envoyes
                    valeur: "0"
                    libelle: "Envoyés"
                    couleur: "{t.VERT}"
                ChiffreKela:
                    id: chiffre_echecs
                    valeur: "0"
                    libelle: "Échecs"
                    couleur: "{t.ROUGE}"

            CarteKela:
                TitreCarte:
                    icon: "laptop"
                    text: "Ordinateurs Kelaplus connectés"
                MDLabel:
                    id: ordinateurs_lbl
                    text: "Aucun ordinateur connecté. Dans Kelaplus : Communication › Passerelles SMS › Rechercher mon téléphone."
                    font_style: "Body"
                    role: "medium"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True

            CarteKela:
                TitreCarte:
                    icon: "access-point-network"
                    text: "Adresse du téléphone sur le Wi-Fi"
                MDLabel:
                    text: "Kelaplus trouve ce téléphone tout seul. Cette adresse sert seulement à le chercher à la main."
                    font_style: "Body"
                    role: "small"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                MDBoxLayout:
                    id: endpoint_box
                    orientation: "vertical"
                    adaptive_height: True
                    spacing: dp(8)

            CarteKela:
                id: serial_card
                disabled: True
                TitreCarte:
                    icon: "serial-port"
                    text: "Modem GSM (port série)"
                MDLabel:
                    id: serial_stat_lbl
                    text: "Le modem n'est pas encore connecté."
                    font_style: "Body"
                    role: "medium"
                    theme_text_color: "Custom"
                    text_color: "{t.GRIS}"
                    adaptive_height: True
                MDListItem:
                    on_release: app.open_serial_menu()
                    MDListItemLeadingIcon:
                        icon: "serial-port"
                    MDListItemHeadlineText:
                        text: "Port série"
                    MDListItemSupportingText:
                        text: "Pour les commandes AT"
                    MDDropDownItem:
                        id: serial_dropdwn
                        pos_hint: {{"center_y": .5}}
                        on_release: app.open_serial_menu()
                        MDDropDownItemText:
                            id: port_dropdown
                            text: "Choisir"
                MDListItem:
                    MDListItemLeadingIcon:
                        icon: "speedometer"
                    MDListItemHeadlineText:
                        text: "Vitesse (bauds)"
                    MDListItemSupportingText:
                        text: "Par défaut : 115200"
                    MDTextField:
                        id: baud_rate
                        text: "115200"
                        mode: "outlined"
                        input_filter: 'int'
                SerialBtn:
                    id: serial_btn
                    on_release: app.start_serial_connection()
''')


class AppHomeBox(MDBoxLayout):
    pass


class ButtonControl(MDButton):
    btn_icon = StringProperty("play")
    btn_txt = StringProperty("Démarrer le serveur")
    btn_colour = t.VIOLET


class SerialBtn(MDButton):
    btn_icon = StringProperty("serial-port")
    btn_txt = StringProperty("Connecter le modem")
    btn_colour = t.TEXTE


class DocButton(MDButton):
    btn_icon = StringProperty("file-document-outline")
    btn_txt = StringProperty("Documentation de l'API")
    btn_colour = t.VIOLET_PALE


class EndPointUrl(MDListItem):
    url = StringProperty("")
    iface_name = StringProperty("")

    def copy_url(self, instance=None):
        Clipboard.copy(self.url)


class SerialCard(MDListItem):
    pass
