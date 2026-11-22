package com.greatfy.kelaplussms;

import android.content.Context;
import android.os.Handler;
import android.os.Looper;
import android.telephony.TelephonyManager;

/**
 * Kelaplus SMS : demande du solde de SMS à l'opérateur par un code USSD, sur une SIM précise (Android 8 et plus).
 * Python (services/soldeSms.py) lance la demande avec envoyer(), puis lit etat() et reponse() jusqu'à la réponse de l'opérateur.
 * etat : 0 en attente, 1 réponse reçue, 2 échec.
 */
public class UssdHelper {
    private static volatile String reponse = null;
    private static volatile int etat = 0;

    public static String reponse() {
        return reponse;
    }

    public static int etat() {
        return etat;
    }

    public static void envoyer(Context contexte, int subId, String code) {
        reponse = null;
        etat = 0;
        try {
            TelephonyManager tm = (TelephonyManager) contexte.getSystemService(Context.TELEPHONY_SERVICE);
            if (subId >= 0) {
                tm = tm.createForSubscriptionId(subId);
            }
            tm.sendUssdRequest(code, new TelephonyManager.UssdResponseCallback() {
                @Override
                public void onReceiveUssdResponse(TelephonyManager t, String requete, CharSequence texte) {
                    reponse = texte != null ? texte.toString() : "";
                    etat = 1;
                }

                @Override
                public void onReceiveUssdResponseFailed(TelephonyManager t, String requete, int codeEchec) {
                    reponse = "L'opérateur n'a pas répondu (code " + codeEchec + "). Vérifiez le code USSD.";
                    etat = 2;
                }
            }, new Handler(Looper.getMainLooper()));
        } catch (SecurityException e) {
            reponse = "Permission « Appels téléphoniques » refusée : autorisez-la dans les paramètres de l'application.";
            etat = 2;
        } catch (Exception e) {
            reponse = "Demande impossible : " + e.getMessage();
            etat = 2;
        }
    }
}
