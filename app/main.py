import os
os.environ['KIVY_GL_BACKEND'] = 'sdl2'
#from kivy.config import Config
#Config.set("graphics", "multisamples", "0")
import sys
import json
from threading import Thread

from kivy.uix.widget import Widget
from kivy.core.clipboard import Clipboard
from kivy.lang import Builder
from kivy.core.window import Window
from kivy.utils import platform
from kivy.metrics import dp, sp
from kivy.clock import Clock
from kivy.properties import StringProperty, NumericProperty, ObjectProperty, BooleanProperty, ColorProperty

# debug
try:
    from kivy.graphics.opengl import glGetString, GL_VENDOR, GL_RENDERER, GL_VERSION
    print("GL_VENDOR:", glGetString(GL_VENDOR))
    print("GL_RENDERER:", glGetString(GL_RENDERER))
    print("GL_VERSION:", glGetString(GL_VERSION))
except Exception as e:
    print(f"OpenGL query error: {e}")

from kivymd.uix.widget import MDWidget
from kivymd.app import MDApp
from kivymd.uix.navigationbar import MDNavigationBar, MDNavigationItem
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDButton, MDButtonIcon, MDButtonText
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.label import MDLabel
from kivymd.uix.dialog import MDDialog, MDDialogHeadlineText, MDDialogSupportingText, MDDialogButtonContainer, MDDialogContentContainer

# import screens (else pyinstaller may ignore it)
from screens.mainScr import ButtonControl, EndPointUrl, DocButton, SerialCard, LigneSolde
from screens.settings import SettingsBox, ApiKeyTxtbox
from screens.historiqueScr import HistoriqueBox
from screens import theme as t

# import services
from services.postApi import get_api_keys, generate_new_api_key
from services import pairing
from services import historique
from services import simRouting
from services import soldeSms
import time
from services.netSvc import get_network_ips
from services.config import __version__, app_name

# IMPORTANT: Set this property for keyboard behaviour
Window.softinput_mode = "below_target"

# import platform specific modules
if platform == "android":
    from jnius import autoclass, cast
    from android.permissions import check_permission, request_permissions, Permission
    from screens.kivymd_patch import disable_gpu_ripple, disable_hover
    from services.android_env import on_android
    disable_gpu_ripple()
    if on_android():
        disable_hover()
else:
    from services.appSvc import app_service_thread
    from services.pathMgr import get_user_data_dir
    from services.serialMgr import get_com_ports

# Local classes
class BaseMDNavigationItem(MDNavigationItem):
    icon = StringProperty()
    text = StringProperty()

class MainScreenBox(MDBoxLayout):
    top_pad = NumericProperty(0)
    bottom_pad = NumericProperty(0)
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if platform == "android":
            try:
                from android.display_cutout import get_height_of_bar
                self.top_pad = int(get_height_of_bar('status'))
                self.bottom_pad = int(get_height_of_bar('navigation'))
            except Exception as e:
                print(f"Failed android 15 padding: {e}")
                self.top_pad = 32
                self.bottom_pad = 48

## Global definitions

# Determine the base path for your application's resources
if getattr(sys, 'frozen', False):
    # Running as a PyInstaller bundle
    base_path = sys._MEIPASS
else:
    # Running in a normal Python environment
    base_path = os.path.dirname(os.path.abspath(__file__))
kv_file_path = os.path.join(base_path, 'main_layout.kv')

## Main App Class
class OpenSmsApp(MDApp):
    # Dégradé de la marque Kelaplus (bandeau du haut), voir screens/theme.py.
    degrade_marque = ObjectProperty(None, allownone=True)


    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        Window.bind(on_keyboard=self.events)
        self.resp_thred = None
        self.txt_dialog = None
        self.wake_lock = None
        self.service_stat = False
        self.api_started = False
        self.key_exists = False
        self.api_key = None
        self.serial_started = False
        self.serial_dropdown_menu = None
        self.pair_dialog = None  # fenêtre « Autoriser Kelaplus ? » (jumelage, voir services/pairing.py)
        self.pair_id_vu = None  # dernière demande de connexion montrée (pour ne pas la rouvrir)
        self.config_template = {
            "app": app_name,
            "port": 9292,
            "boot": True,  # Kelaplus : le serveur démarre tout seul, pour que l'ordinateur trouve le téléphone sans toucher à « Start Server »
            "permissions": False,
        }
        self.req_template = {
            "port": 9292,
            "server": "stop",
            "serial_port": "none",
            "baudrate": 115200,
        }

    def build(self):
        # Couleurs de Kelaplus : violet et magenta sur fond clair.
        self.theme_cls.theme_style = "Light"
        self.theme_cls.primary_palette = "Purple"
        self.degrade_marque = t.degrade()
        return Builder.load_file(kv_file_path)

    ## App logics
    def on_start(self):
        # paths setup
        self.api_started = False
        file_m_height = 1
        # for android
        if platform == "android":
            file_m_height = 0.9
            self.root.ids.home_scr.ids.serial_card.opacity = 0
            from android.storage import app_storage_path
            sdk_version = 33
            try:
                VERSION = autoclass('android.os.Build$VERSION')
                sdk_version = VERSION.SDK_INT
                print(f"Android SDK: {sdk_version}")
                #self.show_toast_msg(f"Android SDK: {sdk_version}")
            except Exception as e:
                print(f"Could not check the android SDK version: {e}")
                #self.show_toast_msg(f"Error checking SDK: {e}", is_error=True)
            # Kelaplus : « Téléphone » (READ_PHONE_STATE) pour connaître les SIM d'un téléphone double SIM (choix de la SIM par opérateur).
            self.android_permissions = [Permission.WAKE_LOCK, Permission.SEND_SMS, Permission.READ_PHONE_STATE, Permission.CALL_PHONE]
            if sdk_version >= 33:
                self.android_permissions.extend([Permission.POST_NOTIFICATIONS])
            request_permissions(self.android_permissions)
            self.internal_storage = app_storage_path()
            self.config_dir = os.path.join(self.internal_storage, 'config')
            os.makedirs(self.config_dir, exist_ok=True)
            self.request_path = os.path.join(self.config_dir, "request.json")
            self.resp_path = os.path.join(self.config_dir, "resp.json")
            svc_running = False
            # start the listner service on Android
            try:
                svc_running = self.is_service_running()
                if not svc_running:
                    self.write_request() # cleans the request file
                    self.start_service()
                else:
                    self.service_stat = True
            except Exception as e:
                print(f"Error while starting android service: {e}")
        # non android platforms
        else:
            self.service_stat = True
            # Path related set up
            self.internal_storage = get_user_data_dir(self.config_template["app"])
            self.config_dir = os.path.join(self.internal_storage, 'config')
            os.makedirs(self.config_dir, exist_ok=True)
            self.request_path = os.path.join(self.config_dir, "request.json")
            self.resp_path = os.path.join(self.config_dir, "resp.json")
            self.write_request()
            # Serial setup
            ports = get_com_ports()
            if len(ports) >= 1:
                serial_card = self.root.ids.home_scr.ids.serial_card
                serial_card.disabled = False
                menu_items = [
                    {
                        "text": f"{port}",
                        "on_release": lambda x=f"{port}": self.serial_port_select(x),
                    } for port in ports
                ]
                self.serial_dropdown_menu = MDDropdownMenu(
                    caller=serial_card, items=menu_items, position="center"
                )
            # Start the app service
            Thread(target=app_service_thread, daemon=True).start()
        # All generic things
        self.app_config = os.path.join(self.config_dir, "config.json")
        auto_start_sw = self.root.ids.settings_scr.ids.auto_start_sw
        port_no_inp = self.root.ids.settings_scr.ids.port_no_inp
        if os.path.exists(self.app_config):
            with open(self.app_config, "r", encoding="utf-8") as cf:
                saved_config = json.load(cf)
            self.config_template["port"] = int(saved_config["port"])
            self.config_template["boot"] = saved_config["boot"]
            self.config_template["permissions"] = saved_config.get("permissions", False)
            print(f"start config check: {self.config_template}")
            self.req_template["port"] = int(self.config_template["port"])
            start_on_launch = self.config_template["boot"]
            if start_on_launch:
                self.req_template["server"] = "start"
                auto_start_sw.active = True
                Thread(target=self.write_request, daemon=True).start()
            else:
                auto_start_sw.active = False
        else:
            self.write_app_conf()
            # Première ouverture : on démarre le serveur tout de suite (réglage « démarrer à l'ouverture » activé par défaut).
            self.req_template["server"] = "start"
            auto_start_sw.active = True
            Thread(target=self.write_request, daemon=True).start()
        port_no_inp.text = str(self.config_template["port"])
        api_keys = get_api_keys()
        if len(api_keys) >= 1:
            self.key_exists = True
        self.stop_resp_loop()
        self.resp_thred = Thread(target=self.resp_check_loop, daemon=True)
        self.resp_thred.start()
        # Kelaplus : une demande de connexion de l'ordinateur s'affiche ici dès qu'elle arrive (l'application doit être ouverte).
        Clock.schedule_interval(self.verifier_jumelage, 1)
        # Accueil : chiffres du jour et ordinateurs connectés, tenus à jour.
        Clock.schedule_interval(self.rafraichir_accueil, 3)
        # Solde SMS : vérification automatique (réglable) pendant que l'application est ouverte.
        self.lignes_solde = {}
        self.solde_en_cours = None
        Clock.schedule_interval(self.verifier_soldes_auto, 600)
        Clock.schedule_once(self.verifier_soldes_auto, 20)
        Clock.schedule_once(self.rafraichir_accueil, 1)
        print("Init success...")

    def is_service_running(self):
        if platform == "android":
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Context = autoclass('android.content.Context')
            ActivityManager = autoclass('android.app.ActivityManager')
            activity = PythonActivity.mActivity
            manager = activity.getSystemService(
                Context.ACTIVITY_SERVICE
            )
            services = manager.getRunningServices(1000)
            for service_info in services.toArray():
                if str(service_info.service.getClassName()) == (
                    'com.greatfy.kelaplussms.ServiceOpensmssvc'
                ):
                    return True
            return False
        else:
            return False

    def start_service(self):
        if platform == "android":
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            mActivity = PythonActivity.mActivity
            service = autoclass('com.greatfy.kelaplussms.ServiceOpensmssvc')
            #argument = ''
            argument = os.environ.get('PYTHON_SERVICE_ARGUMENT', '')
            print(f"PYTHON_SERVICE_ARGUMENT: {argument}")
            #service.start(mActivity, argument)
            service.start(mActivity, 'icon', 'OpenSMS API', 'Service Running' , argument)
        self.service_stat = True

    def stop_service(self):
        if platform == "android":
            service = autoclass('com.greatfy.kelaplussms.ServiceOpensmssvc')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            mActivity = PythonActivity.mActivity
            service.stop(mActivity)
            self.service_stat = False

    def resp_check_loop(self):
        self.api_started = False
        self.serial_started = False
        import time
        api_srv_btn = self.root.ids.home_scr.ids.api_srv_btn
        api_srv_lbl = self.root.ids.home_scr.ids.api_srv_lbl
        serial_btn = self.root.ids.home_scr.ids.serial_btn
        serial_stat_lbl = self.root.ids.home_scr.ids.serial_stat_lbl
        time.sleep(0.5) # A delay for the android service to kick in
        # debug
        print_path = os.path.abspath(self.resp_path)
        print(f"RESP Path: {print_path}")
        while True:
            resp = None
            if os.path.exists(self.resp_path):
                try:
                    with open(self.resp_path, "r", encoding="utf-8") as rf:
                        resp = json.load(rf)
                    if resp:
                        # server status
                        server_stat = resp.get("server", "unknown")
                        if server_stat == "started":
                            if not self.api_started:
                                self.api_started = True
                                Clock.schedule_once(lambda dt: self.afficher_etat_serveur(True))
                                Clock.schedule_once(lambda dt: self.update_api_details())
                                #Clock.schedule_once(lambda dt: self.show_toast_msg("API Server Started"))
                        elif server_stat == "stopped":
                            if self.api_started:
                                self.api_started = False
                                Clock.schedule_once(lambda dt: self.afficher_etat_serveur(False))
                                Clock.schedule_once(lambda dt: self.clear_api_details())
                                #Clock.schedule_once(lambda dt: self.show_toast_msg("API Server Stopped"))

                        # serial status
                        if platform != "android":
                            ser_stat = resp.get("serial", "none")
                            provider = resp.get("provider", "unknown")
                            if not self.serial_started:
                                if ser_stat == "ok":
                                    stat_text = f"Modem connecté au réseau : {provider}"
                                    serial_stat_lbl.text = stat_text
                                    serial_btn.btn_txt = "Modem connecté"
                                    serial_btn.md_bg_color = t.VERT
                    else:
                        api_srv_lbl.text = "Le service du téléphone ne répond pas encore, patientez…"
                except Exception as e:
                    print(f"Error while reading resp: {e}")
            else:
                api_srv_lbl.text = "Démarrage du service du téléphone…"
            time.sleep(2)

    def afficher_etat_serveur(self, en_marche: bool):
        """ La carte « Passerelle SMS » de l'accueil : pastille, phrase et bouton selon l'état du serveur. """
        ids = self.root.ids.home_scr.ids
        if en_marche:
            ids.etat_pastille.text = "En marche"
            ids.etat_pastille.couleur = t.VERT
            ids.etat_pastille.fond = t.VERT_PALE
            ids.api_srv_lbl.text = "Le téléphone est prêt : Kelaplus peut envoyer ses SMS par ce téléphone."
            ids.api_srv_btn.btn_icon = "stop"
            ids.api_srv_btn.btn_txt = "Arrêter le serveur"
            ids.api_srv_btn.md_bg_color = t.ROUGE
        else:
            ids.etat_pastille.text = "Arrêtée"
            ids.etat_pastille.couleur = t.ROUGE
            ids.etat_pastille.fond = t.ROUGE_PALE
            ids.api_srv_lbl.text = "Le serveur est arrêté : Kelaplus ne peut pas envoyer de SMS par ce téléphone."
            ids.api_srv_btn.btn_icon = "play"
            ids.api_srv_btn.btn_txt = "Démarrer le serveur"
            ids.api_srv_btn.md_bg_color = t.VIOLET

    def rafraichir_accueil(self, dt=None):
        """ Chiffres des SMS (aujourd'hui, envoyés, échecs) et ordinateurs Kelaplus connectés. """
        try:
            ids = self.root.ids.home_scr.ids
            r = historique.resume()
            ids.chiffre_jour.valeur = str(r["aujourdhui"])
            ids.chiffre_envoyes.valeur = str(r["envoyes"])
            ids.chiffre_echecs.valeur = str(r["echecs"])
            self.afficher_soldes()
            postes = pairing.ordinateurs_connectes()
            ids.ordinateurs_lbl.text = (
                "\n".join(f"•  {p}" for p in postes)
                if postes
                else "Aucun ordinateur connecté. Dans Kelaplus : Communication › Passerelles SMS › Rechercher mon téléphone."
            )
        except Exception as e:
            print(f"Accueil : rafraîchissement impossible : {e}")

    def vider_historique(self, instance=None):
        buttons = MDDialogButtonContainer(
            Widget(),
            MDButton(MDButtonText(text="Annuler"), style="text", on_release=self.txt_dialog_closer),
            MDButton(
                MDButtonText(text="Vider", theme_text_color="Custom", text_color=t.ROUGE),
                style="text",
                on_release=self.confirmer_vider_historique,
            ),
            spacing="8dp",
        )
        self.show_text_dialog("Vider l'historique ?", "Tous les SMS de la liste seront effacés de ce téléphone (pas des téléphones des parents).", None, buttons)

    def confirmer_vider_historique(self, instance=None):
        self.txt_dialog_closer()
        try:
            historique.vider()
            self.root.ids.hist_scr._signature = None
            self.root.ids.hist_scr.actualiser()
            self.rafraichir_accueil()
            self.show_toast_msg("Historique vidé.")
        except Exception as e:
            print(f"Historique : impossible de vider : {e}")
            self.show_toast_msg("Impossible de vider l'historique.", is_error=True)

    def write_app_conf(self):
        with open(self.app_config, "w") as cf:
            json.dump(self.config_template, cf)

    def write_request(self):
        with open(self.request_path, "w") as rf:
            json.dump(self.req_template, rf)

    def clear_api_details(self):
        endpoint_box = self.root.ids.home_scr.ids.endpoint_box
        endpoint_box.clear_widgets()

    def update_api_details(self):
        self.clear_api_details()
        ip_map = get_network_ips()
        port_no = self.config_template["port"]
        endpoint_box = self.root.ids.home_scr.ids.endpoint_box
        # WiFi interfaces
        for wifi_iface in ip_map["wifi"]:
            iface_name = wifi_iface.get("interface", "")
            ip_addr = wifi_iface["ip"]
            url = f"http://{ip_addr}:{port_no}/sms"
            iface_widget = EndPointUrl()
            iface_widget.url = f"{ip_addr}:{port_no}"
            iface_widget.iface_name = f"Wi-Fi ({iface_name})" if iface_name else "Wi-Fi"
            endpoint_box.add_widget(iface_widget)
        # Ethernet interfaces
        for eth_iface in ip_map["ethernet"]:
            iface_name = eth_iface.get("interface", "")
            ip_addr = eth_iface["ip"]
            url = f"http://{ip_addr}:{port_no}/sms"
            iface_widget = EndPointUrl()
            iface_widget.url = f"{ip_addr}:{port_no}"
            iface_widget.iface_name = f"Câble réseau ({iface_name})" if iface_name else "Câble réseau"
            endpoint_box.add_widget(iface_widget)

    def api_server_mgr(self, instance=None):
        permissions_ok = self.check_request_android_permission()
        if not permissions_ok:
            return
        key_ok = self.check_if_key_exists()
        if key_ok:
            if not self.service_stat:
                self.start_service()
            if not self.api_started:
                self.req_template["server"] = "start"
                self.write_request()
            else:
                self.req_template["server"] = "stop"
                self.write_request()
        else:
            self.new_api_key_pop()

    def check_request_android_permission(self):
        if platform == "android" and not self.config_template["permissions"]:
            permission_flag = True
            for permission in self.android_permissions:
                # « Téléphone » sert seulement au choix de la SIM : refusée, les SMS partent par la SIM par défaut, le serveur démarre quand même.
                if permission in (Permission.READ_PHONE_STATE, Permission.CALL_PHONE):
                    continue
                tmp_flag = check_permission(permission)
                if not tmp_flag:
                    permission_flag = False
                    break
            if not permission_flag:
                request_permissions(self.android_permissions, self.permission_callback)
            return permission_flag
        else:
            return True

    def permission_callback(self, permissions, results):
        # results is a list of booleans corresponding to requested permissions
        usr_deny_flag = False
        if False in results:
            # the user checked "Don't ask again" or denied it twice.
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            current_activity = PythonActivity.mActivity
            # Check rationale status via Android API
            for permission in permissions:
                should_show = current_activity.shouldShowRequestPermissionRationale(permission)
                if not should_show:
                    usr_deny_flag = True
                    break
            if usr_deny_flag:
                # User denied twice / blocked permanently! Show redirect popup.
                print("Permission is denied by user!")
                Clock.schedule_once(lambda dt: self.show_settings_popup())

    def show_settings_popup(self):
        buttons = MDDialogButtonContainer(
            Widget(),
            MDButton(
                MDButtonText(
                    text="Annuler"
                ),
                style="text",
                on_release=self.txt_dialog_closer
            ),
            MDButton(
                MDButtonText(
                    text="Déjà accordée",
                    theme_text_color= "Custom",
                    text_color= t.GRIS
                ),
                style="text",
                on_release=self.confirm_android_permissions
            ),
            MDButton(
                MDButtonText(
                    text="Ouvrir les paramètres",
                    theme_text_color= "Custom",
                    text_color= t.VIOLET
                ),
                style="text",
                on_release=self.open_android_settings
            ),
            spacing="8dp",
        )
        self.show_text_dialog(
            "Permissions manquantes",
            "Accordez les permissions SMS et Notifications dans les paramètres du téléphone (si Android les bloque : menu ⋮ › « Autoriser les paramètres restreints »).",
            None,
            buttons
        )

    def confirm_android_permissions(self, instnce=None):
        self.config_template["permissions"] = True
        Thread(target=self.write_app_conf, daemon=True).start()

    def open_android_settings(self, instance=None):
        self.txt_dialog_closer()
        # Target Android Native Intents
        Intent = autoclass('android.content.Intent')
        Settings = autoclass('android.provider.Settings')
        Uri = autoclass('android.net.Uri')
        PythonActivity = autoclass('org.kivy.android.PythonActivity')
        # Create intent to open this specific app's settings details
        activity = PythonActivity.mActivity
        intent = Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS)
        uri = Uri.fromParts("package", activity.getPackageName(), None)
        intent.setData(uri)
        # Launch settings
        activity.startActivity(intent)

    def check_if_key_exists(self):
        api_keys = get_api_keys()
        if len(api_keys) >= 1:
            self.key_exists = True
        else:
            self.key_exists = False
        return self.key_exists

    def new_api_key_pop(self):
        buttons = MDDialogButtonContainer(
            Widget(),
            MDButton(
                MDButtonText(
                    text="Annuler"
                ),
                style="text",
                on_release=self.txt_dialog_closer
            ),
            MDButton(
                MDButtonText(
                    text="Générer",
                    theme_text_color= "Custom",
                    text_color= t.VIOLET
                ),
                style="text",
                on_release=self.create_new_api_key
            ),
            spacing="8dp",
        )
        self.show_text_dialog(
            "Générer une clé API",
            "Générer une nouvelle clé API ? Les anciennes clés, et les ordinateurs Kelaplus déjà connectés, ne fonctionneront plus : il faudra les reconnecter.",
            None,
            buttons
        )

    def create_new_api_key(self, instance=None):
        self.txt_dialog_closer()
        self.api_key = generate_new_api_key()
        if self.api_key:
            Clipboard.copy(self.api_key)
            custom = MDDialogContentContainer(
                ApiKeyTxtbox(
                    text = self.api_key
                )
            )
            buttons = MDDialogButtonContainer(
                Widget(),
                MDButton(
                    MDButtonText(
                        text="Annuler"
                    ),
                    style="text",
                    on_release=self.txt_dialog_closer
                ),
                MDButton(
                    MDButtonText(
                        text="Copier",
                        theme_text_color= "Custom",
                        text_color= t.VIOLET
                    ),
                    style="text",
                    on_release=self.copy_api_key
                ),
                spacing="8dp",
            )
            self.show_text_dialog(
                "Votre nouvelle clé API",
                "La clé est déjà copiée. Cet écran ne s'affiche qu'une fois : gardez-la en lieu sûr.",
                custom,
                buttons
            )
        else:
            Clock.schedule_once(lambda dt: self.show_toast_msg("La clé n'a pas pu être créée, réessayez.", is_error=True))

    def copy_api_key(self, instance=None):
        if self.api_key:
            Clipboard.copy(self.api_key)
        self.txt_dialog_closer()
        Clock.schedule_once(lambda dt: self.show_toast_msg("Clé API copiée : gardez-la en lieu sûr."))

    ## Connexion de Kelaplus (jumelage) : l'ordinateur demande, l'utilisateur autorise sur le téléphone

    def verifier_jumelage(self, dt=None):
        """ Toutes les secondes : y a-t-il une demande de connexion de Kelaplus à montrer ? """
        if self.pair_dialog:
            return
        try:
            demande = pairing.demande_en_attente()
        except Exception as e:
            print(f"Jumelage : lecture impossible : {e}")
            return
        if demande and demande["id"] != self.pair_id_vu:
            self.pair_id_vu = demande["id"]
            self.fenetre_jumelage(demande)

    def fenetre_jumelage(self, demande):
        poste = demande.get("poste", "Ordinateur")
        ecole = demande.get("ecole", "")
        qui = f"« {poste} »" + (f" ({ecole})" if ecole else "")
        buttons = MDDialogButtonContainer(
            Widget(),
            MDButton(
                MDButtonText(text="Refuser"),
                style="text",
                on_release=lambda *_: self.repondre_jumelage(demande["id"], False)
            ),
            MDButton(
                MDButtonText(text="Autoriser", theme_text_color="Custom", text_color=t.VIOLET),
                style="text",
                on_release=lambda *_: self.repondre_jumelage(demande["id"], True)
            ),
            spacing="8dp",
        )
        self.pair_dialog = MDDialog(
            MDDialogHeadlineText(text="Autoriser Kelaplus ?"),
            MDDialogSupportingText(
                text=(
                    f"L'ordinateur {qui} demande à se connecter à ce téléphone pour envoyer des SMS (paiements, absences, rappels...). "
                    "N'autorisez que si c'est bien vous qui venez de cliquer sur « Connexion » dans Kelaplus."
                )
            ),
            buttons,
            auto_dismiss=False,
        )
        self.pair_dialog.open()

    def repondre_jumelage(self, id_demande, accepte):
        if self.pair_dialog:
            self.pair_dialog.dismiss()
            self.pair_dialog = None
        try:
            if accepte:
                ok = pairing.accepter(id_demande)
                message = "Kelaplus est connecté : il enverra ses SMS par ce téléphone." if ok else "La demande a expiré : recommencez depuis Kelaplus."
                Clock.schedule_once(lambda dt: self.show_toast_msg(message, is_error=not ok))
            else:
                pairing.refuser(id_demande)
                Clock.schedule_once(lambda dt: self.show_toast_msg("Connexion refusée."))
        except Exception as e:
            print(f"Jumelage : réponse impossible : {e}")
            Clock.schedule_once(lambda dt: self.show_toast_msg("Impossible d'enregistrer la réponse, réessayez.", is_error=True))

    def api_doc_link(self, instance=None):
        port_no = self.config_template["port"]
        self.open_link(instance, f"http://127.0.0.1:{port_no}/docs")

    def open_link(self, instance=None, url=None):
        if url:
            import webbrowser
            webbrowser.open(url)

    ## Desktop specific setups

    def open_serial_menu(self, instance=None):
        if self.serial_dropdown_menu:
            self.serial_dropdown_menu.open()

    def serial_port_select(self, port:str):
        self.req_template["serial_port"] = port
        self.serial_dropdown_menu.dismiss()
        port_dropdown = self.root.ids.home_scr.ids.port_dropdown
        port_dropdown.text = port

    def start_serial_connection(self, instance=None):
        if self.serial_started:
            self.show_toast_msg("Le modem est déjà connecté.")
            return
        port = self.req_template["serial_port"]
        if port == "none":
            self.show_toast_msg("Choisissez d'abord le port série.", is_error=True)
            return
        baud_rate = self.root.ids.home_scr.ids.baud_rate.text
        baud_int = self.req_template["baudrate"]
        if len(baud_rate) >= 4:
            try:
                baud_int = int(baud_rate)
                self.req_template["baudrate"] = baud_int
            finally:
                print(f"Using baud rate: {baud_int}")
        Thread(target=self.write_request, daemon=True).start()

    ## Settings sections
    def save_settings(self, instance=None, control_txt="none"):
        port_no_inp = self.root.ids.settings_scr.ids.port_no_inp
        flag = False
        if control_txt == "switch":
            if self.config_template["boot"]:
                self.config_template["boot"] = False
                flag = True
            else:
                self.config_template["boot"] = True
                flag = True
        if port_no_inp.text != "":
            port_no = int(port_no_inp.text)
            if port_no >= 1025:
                self.config_template["port"] = port_no
                self.req_template["port"] = port_no
        print(f"Service on start: {self.config_template["boot"]}, port: {self.config_template["port"]}")
        Thread(target=self.write_app_conf, daemon=True).start()
        Clock.schedule_once(lambda dt: self.show_toast_msg("Réglages enregistrés."))

    def refresh_settings_view(self):
        auto_start_sw = self.root.ids.settings_scr.ids.auto_start_sw
        port_no_inp = self.root.ids.settings_scr.ids.port_no_inp
        if self.config_template["boot"]:
            auto_start_sw.active = True
        else:
            auto_start_sw.active = False
        port_no_inp.text = str(self.config_template["port"])

    def reset_settings(self, instance=None):
        self.config_template = {
            "port": 9292,
            "boot": True,
        }
        self.req_template["port"] = 9292
        print("Réglages remis à zéro.")
        self.refresh_settings_view()
        Thread(target=self.write_app_conf, daemon=True).start()
        Clock.schedule_once(lambda dt: self.show_toast_msg("Réglages remis à zéro."))

    ## App or UI related things
    def acquire_wakelock(self):
        if self.wake_lock:
            return  # already acquired
        try:
            PythonActivity = autoclass("org.kivy.android.PythonActivity")
            Context = autoclass("android.content.Context")
            activity = PythonActivity.mActivity
            PowerManager = autoclass("android.os.PowerManager")
            power_manager = cast(PowerManager, activity.getSystemService(Context.POWER_SERVICE))
            # Create wakelock (use PowerManager.FULL_WAKE_LOCK for full wakelock)
            self.wake_lock = power_manager.newWakeLock(
                PowerManager.FULL_WAKE_LOCK, "OpenSmsApp::WakeLockTag"
            )
            self.wake_lock.acquire()
            print("WakeLock acquired")
        except Exception as e:
            print(f"Wake lock aquire error: {e}")

    def release_wakelock(self):
        if self.wake_lock and self.wake_lock.isHeld():
            self.wake_lock.release()
            self.wake_lock = None
            print("WakeLock released")

    def show_toast_msg(self, message, is_error=False, duration=3):
        from kivymd.uix.snackbar import MDSnackbar, MDSnackbarText, MDSnackbarSupportingText
        # Couleurs de Kelaplus : violet pour une information, rouge pour une erreur.
        bg_color = (0.576, 0.02, 0.827, 1) if not is_error else (0.863, 0.149, 0.149, 1)
        MDSnackbar(
            MDSnackbarText(
                text=message,
            ),
            y=dp(24),
            orientation="horizontal",
            pos_hint={"center_x": 0.5},
            background_color=bg_color,
        ).open()

    def show_text_dialog(
            self, 
            title, 
            text="", 
            custom_content:MDDialogContentContainer|None = None, 
            buttons:MDDialogButtonContainer|None = None
        ):
        self.txt_dialog = MDDialog(
            MDDialogHeadlineText(
                text = title
            ),
            MDDialogSupportingText(
                text = text
            ),
            custom_content,
            buttons
        )
        self.txt_dialog.open()

    def txt_dialog_closer(self, instance=None):
        if self.txt_dialog:
            self.txt_dialog.dismiss()

    def goto_app_settings(self, instance=None):
        self.txt_dialog_closer()
        self.go_to_screen("Réglages")

    def goto_logs_screen(self, instance=None):
        self.root.ids.nav_drawer.set_state("close")
        self.go_to_screen("Journal")

    def go_to_screen(self, screen:str):
        self.root.ids.screen_manager.current = screen

    def on_main_screen_entry(self, instance=None):
        self.root.ids.top_back_btn.opacity = 0
        self.root.ids.top_back_btn.disabled = True

    def on_settings_entry(self, instance=None):
        self.root.ids.top_back_btn.opacity = 1
        self.root.ids.top_back_btn.disabled = False
        self.charger_choix_sim()
        self.charger_soldes_ui()

    ## Choix de la SIM selon l'opérateur du destinataire (services/simRouting.py)

    def charger_choix_sim(self):
        """ Remplit la carte « Choix de la SIM » : interrupteur, SIM détectées, opérateurs et préfixes des deux règles. """
        try:
            ids = self.root.ids.settings_scr.ids
            r = simRouting.lire_reglages()
            ids.sim_actif.active = bool(r.get("actif"))
            regles = (r.get("regles") or []) + [{"operateur": "", "prefixes": []}] * 2
            ids.op1.text = regles[0]["operateur"]
            ids.pref1.text = ", ".join(regles[0]["prefixes"])
            ids.op2.text = regles[1]["operateur"]
            ids.pref2.text = ", ".join(regles[1]["prefixes"])
            sims = simRouting.sims_actives()
            if sims:
                ids.sims_lbl.text = "SIM détectées : " + "  ·  ".join(f"SIM {x['emplacement'] + 1} : {x['operateur'] or 'inconnu'}" for x in sims)
                if len(sims) < 2:
                    ids.sims_lbl.text += "  (une seule SIM : tous les SMS partent par elle)"
            else:
                ids.sims_lbl.text = "SIM détectées : aucune (autorisez « Téléphone » dans les permissions de l'application)" if platform == "android" else "SIM détectées : aucune (ordinateur)"
        except Exception as e:
            print(f"Choix de la SIM : affichage impossible : {e}")

    ## Solde SMS des SIM (services/soldeSms.py ; Java : UssdHelper)

    def afficher_soldes(self):
        """ La carte « Solde SMS des SIM » de l'accueil : une ligne par opérateur réglé. """
        ids = self.root.ids.home_scr.ids
        r = soldeSms.lire()
        envois = historique.envois(historique.MAX_ENVOIS)
        noms = [o["operateur"] for o in r["operateurs"]]
        if list(self.lignes_solde.keys()) != noms:
            ids.soldes_box.clear_widgets()
            self.lignes_solde = {}
            for nom in noms:
                ligne = LigneSolde(operateur=nom)
                self.lignes_solde[nom] = ligne
                ids.soldes_box.add_widget(ligne)
        sans_code = [o["operateur"] for o in r["operateurs"] if not o.get("code")]
        ids.soldes_aide.text = ("Code de solde à saisir dans Réglages › Solde SMS : " + ", ".join(sans_code) + ".") if sans_code else f"Alerte en rouge sous {r['seuil']} SMS."
        for o in r["operateurs"]:
            ligne = self.lignes_solde.get(o["operateur"])
            if not ligne:
                continue
            e = soldeSms.etat(o, envois, r["seuil"])
            ligne.en_cours = self.solde_en_cours == o["operateur"]
            if e["restants"] is None:
                ligne.valeur = "—"
                ligne.couleur = t.GRIS
                ligne.detail = (e["texte"][:90] + "…") if len(e["texte"] or "") > 90 else (e["texte"] or "Pas encore consulté.")
            else:
                ligne.valeur = f"{'≈ ' if e['estimation'] else ''}{e['restants']} SMS"
                ligne.couleur = t.ROUGE if e["bas"] else t.VERT
                quand = ""
                if e["date"]:
                    minutes = int((time.time() - e["date"]) / 60)
                    quand = "à l'instant" if minutes < 1 else f"il y a {minutes} min" if minutes < 60 else f"il y a {minutes // 60} h" if minutes < 1440 else f"il y a {minutes // 1440} j"
                source = "estimation d'après les SMS envoyés" if e["estimation"] else "réponse de l'opérateur"
                ligne.detail = source + (f", {quand}" if quand else "") + ("  ·  solde bas : rechargez" if e["bas"] else "")

    def consulter_solde(self, nom_operateur, silencieux=False):
        """ Envoie le code de solde sur la SIM de cet opérateur et attend la réponse (30 secondes au plus). """
        if self.solde_en_cours:
            return
        r = soldeSms.lire()
        o = soldeSms.operateur(r, nom_operateur)
        if not o or not o.get("code"):
            if not silencieux:
                self.show_toast_msg(f"Saisissez d'abord le code de solde {nom_operateur} dans Réglages › Solde SMS.", is_error=True)
            return
        sims = simRouting.sims_actives()
        sim = next((x for x in sims if soldeSms._norm(nom_operateur) in soldeSms._norm(x.get("operateur", ""))), None)
        if sims and not sim:
            if not silencieux:
                self.show_toast_msg(f"Aucune SIM {nom_operateur} détectée dans le téléphone.", is_error=True)
            return
        erreur = soldeSms.envoyer_ussd(sim["id"] if sim else None, o["code"])
        if erreur:
            if not silencieux:
                self.show_toast_msg(erreur, is_error=True)
            return
        self.solde_en_cours = nom_operateur
        self.afficher_soldes()
        debut = time.time()

        def attendre(dt):
            etat, texte = soldeSms.reponse_ussd()
            if etat == 0 and time.time() - debut < 30:
                return True
            ok = etat == 1
            if etat == 0:
                texte = "Pas de réponse de l'opérateur (30 s)."
            dernier = soldeSms.enregistrer_reponse(nom_operateur, texte, ok)
            self.solde_en_cours = None
            self.afficher_soldes()
            if not silencieux:
                if ok and dernier.get("restants") is not None:
                    self.show_toast_msg(f"{nom_operateur} : {dernier['restants']} SMS restants.")
                else:
                    self.show_toast_msg(f"{nom_operateur} : {texte[:120]}", is_error=not ok)
            elif ok and dernier.get("restants") is not None and dernier["restants"] <= soldeSms.lire()["seuil"]:
                self.show_toast_msg(f"Solde SMS bas sur la SIM {nom_operateur} : {dernier['restants']} SMS. Rechargez.", is_error=True)
            return False

        Clock.schedule_interval(attendre, 0.5)

    def verifier_soldes_auto(self, dt=None):
        """ Toutes les N heures (réglable), consulte le solde des opérateurs qui ont un code, l'un après l'autre. """
        r = soldeSms.lire()
        if not r.get("auto_heures") or platform != "android":
            return
        maintenant = time.time()
        for o in r["operateurs"]:
            dernier = (o.get("dernier") or {}).get("date") or 0
            if o.get("code") and maintenant - dernier > r["auto_heures"] * 3600:
                self.consulter_solde(o["operateur"], silencieux=True)
                return  # un seul à la fois ; le suivant au prochain passage

    def charger_soldes_ui(self):
        try:
            ids = self.root.ids.settings_scr.ids
            r = soldeSms.lire()
            ops = r["operateurs"] + [{"operateur": "", "code": "", "forfait": 0}] * 2
            for n, o in ((1, ops[0]), (2, ops[1])):
                ids[f"sol_op{n}"].text = o["operateur"]
                ids[f"sol_code{n}"].text = o.get("code", "")
                ids[f"sol_forfait{n}"].text = str(o.get("forfait") or "") if o.get("forfait") else ""
            ids.sol_seuil.text = str(r["seuil"])
            ids.sol_auto.text = str(r["auto_heures"])
        except Exception as e:
            print(f"Solde SMS : affichage des réglages impossible : {e}")

    def enregistrer_soldes(self, instance=None, afficher=True):
        ids = self.root.ids.settings_scr.ids
        ancien = soldeSms.lire()
        operateurs = []
        for n in (1, 2):
            nom = ids[f"sol_op{n}"].text.strip()
            if not nom:
                continue
            code = ids[f"sol_code{n}"].text.strip()
            if code and not soldeSms.code_valide(code):
                self.show_toast_msg(f"Code de solde invalide pour {nom} (exemple : *123#).", is_error=True)
                return False
            avant = soldeSms.operateur(ancien, nom) or {}
            forfait = ids[f"sol_forfait{n}"].text.strip()
            operateurs.append({
                "operateur": nom[:30],
                "code": code,
                "forfait": int(forfait) if forfait.isdigit() else 0,
                "depuis": avant.get("depuis", 0),
                "dernier": avant.get("dernier"),
            })
        seuil = ids.sol_seuil.text.strip()
        auto = ids.sol_auto.text.strip()
        soldeSms.ecrire({
            "seuil": int(seuil) if seuil.isdigit() else 50,
            "auto_heures": int(auto) if auto.isdigit() else 6,
            "operateurs": operateurs,
        })
        self.lignes_solde = {}
        self.rafraichir_accueil()
        if afficher:
            self.show_toast_msg("Réglages du solde SMS enregistrés.")
        return True

    def recharge_sim(self, n):
        ids = self.root.ids.settings_scr.ids
        nom = ids[f"sol_op{n}"].text.strip()
        forfait = ids[f"sol_forfait{n}"].text.strip()
        if not nom or not forfait.isdigit() or int(forfait) <= 0:
            self.show_toast_msg("Indiquez l'opérateur et le nombre de SMS du forfait acheté.", is_error=True)
            return
        if not self.enregistrer_soldes(afficher=False):
            return
        soldeSms.recharge(nom, int(forfait))
        self.rafraichir_accueil()
        self.show_toast_msg(f"Recharge {nom} notée : {forfait} SMS à partir d'aujourd'hui.")

    def enregistrer_sim(self, instance=None):
        ids = self.root.ids.settings_scr.ids
        regles = []
        for op, pref in ((ids.op1.text, ids.pref1.text), (ids.op2.text, ids.pref2.text)):
            nom = op.strip()
            prefixes = simRouting.normaliser_prefixes(pref)
            if nom and prefixes:
                regles.append({"operateur": nom[:30], "prefixes": prefixes})
        try:
            simRouting.ecrire_reglages({"actif": bool(ids.sim_actif.active), "regles": regles})
            self.charger_choix_sim()
            self.show_toast_msg("Choix des SIM enregistré.")
        except Exception as e:
            print(f"Choix de la SIM : enregistrement impossible : {e}")
            self.show_toast_msg("Impossible d'enregistrer le choix des SIM.", is_error=True)

    def back_button_action(self, instance=None):
        if self.root.ids.screen_manager.current in ["Réglages", "Journal", "Historique"]:
           self.go_to_screen("Accueil")

    def events(self, instance, keyboard, keycode, text, modifiers):
        """Handle mobile device button presses (e.g., Android back button)."""
        if keyboard in (1001, 27):
            self.back_button_action()
            return True
        # exits from app
        return False

    def stop_resp_loop(self):
        if self.resp_thred:
            self.resp_thred.join(timeout=5)
        self.resp_thred = None

    def on_pause(self):
        self.stop_resp_loop()
        return True

    def on_resume(self):
        self.stop_resp_loop()
        self.resp_thred = Thread(target=self.resp_check_loop, daemon=True)
        self.resp_thred.start()

    # run on app exit
    def on_stop(self):
        print("Exiting the app...")
        if platform == "android":
            #self.stop_service()
            self.release_wakelock()

    # on bottom navigation
    def on_switch_tabs(
            self,
            bar: MDNavigationBar,
            item: MDNavigationItem,
            item_icon: str,
            item_text: str,
        ):
            self.root.ids.screen_manager.current = item_text


if __name__ == '__main__':
    OpenSmsApp().run()
