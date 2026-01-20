#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Générateur SEEV.001.001.12 avec Extraction Automatique
Lit un fichier TXT et génère automatiquement le message Swift
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime
import re
import os

def lire_fichier_txt(chemin_fichier):
    """Lit le contenu d’un fichier TXT"""
    try:
        with open(chemin_fichier, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        # Essayer avec un autre encodage si UTF-8 échoue
        try:
            with open(chemin_fichier, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Erreur lors de la lecture du fichier: {e}")
            return None

def extraire_isin(texte):
    """Extrait l’ISIN du texte"""
    # Pattern ISIN: 2 lettres pays + 9 alphanumériques + 1 chiffre de contrôle
    pattern = r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b'
    match = re.search(pattern, texte)
    if match:
        return match.group(1)
    return ""

def extraire_nom_emetteur(texte):
    """Extrait le nom de l’émetteur"""
    # Chercher dans les premières lignes
    lignes = texte.split('\n')[:20]
    # Mots à ignorer
    mots_ignores = ['CONVOCATION', 'ASSEMBLÉE', 'ASSEMBLY', 'MEETING', 'BONDHOLDER',
    'OBLIGATAIRE', 'ISIN', 'DATE', 'LIEU', 'PLACE']

    for ligne in lignes:
        ligne_clean = ligne.strip()
        # Ligne entre 5 et 100 caractères
        if 5 < len(ligne_clean) < 100:
            # Ne contient pas de mots à ignorer
            if not any(mot in ligne_clean.upper() for mot in mots_ignores):
                # Contient des lettres
                if re.search(r'[A-Za-z]', ligne_clean):
                    return ligne_clean
    return ""

def extraire_dates(texte):
    """Extrait les dates importantes"""
    dates = {}

    # Date de meeting
    patterns_meeting = [
        r'(?:meeting|assemblée|réunion|se tiendra).*?(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
        r'(?:meeting|assemblée|réunion|se tiendra).*?(\d{1,2}\s+\w+\s+\d{4})',
        r'Date\s*:\s*(\d{1,2}\s+\w+\s+\d{4})',
        r'Date\s*:\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
    ]

    for pattern in patterns_meeting:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            dates['meeting_date'] = match.group(1)
            break

    # Deadline
    patterns_deadline = [
        r'(?:deadline|date limite|au plus tard|avant le|before).*?(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
        r'(?:deadline|date limite|au plus tard|avant le|before).*?(\d{1,2}\s+\w+\s+\d{4})',
    ]

    for pattern in patterns_deadline:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            dates['deadline'] = match.group(1)
            break

    # Record Date
    patterns_record = [
        r'Record\s+Date\s*:\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})',
        r'Record\s+Date\s*:\s*(\d{1,2}\s+\w+\s+\d{4})',
    ]

    for pattern in patterns_record:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            dates['record_date'] = match.group(1)
            break

    return dates

def convertir_date_iso(date_str):
    """Convertit une date en format ISO (YYYY-MM-DD)"""
    if not date_str:
        return ""

    # Dictionnaire des mois
    mois_fr = {
        'janvier': '01', 'février': '02', 'mars': '03', 'avril': '04',
        'mai': '05', 'juin': '06', 'juillet': '07', 'août': '08',
        'septembre': '09', 'octobre': '10', 'novembre': '11', 'décembre': '12'
    }

    mois_en = {
        'january': '01', 'february': '02', 'march': '03', 'april': '04',
        'may': '05', 'june': '06', 'july': '07', 'august': '08',
        'september': '09', 'october': '10', 'november': '11', 'december': '12'
    }

    # Format: 15 février 2025
    match = re.match(r'(\d{1,2})\s+(\w+)\s+(\d{4})', date_str)
    if match:
        jour, mois, annee = match.groups()
        mois_lower = mois.lower()
        if mois_lower in mois_fr:
            return f"{annee}-{mois_fr[mois_lower]}-{jour.zfill(2)}"
        elif mois_lower in mois_en:
            return f"{annee}-{mois_en[mois_lower]}-{jour.zfill(2)}"

    # Format: 15/02/2025
    match = re.match(r'(\d{1,2})[\/\-\.](\d{1,2})[\/\-\.](\d{4})', date_str)
    if match:
        jour, mois, annee = match.groups()
        return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"

    # Format: 2025-02-15 (déjà en ISO)
    match = re.match(r'(\d{4})[\/\-\.](\d{1,2})[\/\-\.](\d{1,2})', date_str)
    if match:
        annee, mois, jour = match.groups()
        return f"{annee}-{mois.zfill(2)}-{jour.zfill(2)}"

    return date_str

def extraire_lieu(texte):
    """Extrait le lieu du meeting"""
    patterns_lieu = [
        r'Lieu\s*:\s*(.+?)(?=\n|$)',
        r'Place\s*:\s*(.+?)(?=\n|$)',
        r'Location\s*:\s*(.+?)(?=\n|$)',
        r'(?:se tiendra|will be held).*?(?:à|at)\s+(.+?)(?=\n|$)',
    ]

    for pattern in patterns_lieu:
        match = re.search(pattern, texte, re.IGNORECASE)
        if match:
            lieu = match.group(1).strip()
            # Nettoyer
            lieu = re.sub(r'\s+', ' ', lieu)
            if len(lieu) > 10 and len(lieu) < 200:
                return lieu
    return ""

def extraire_resolutions(texte):
    """Extrait les résolutions"""
    resolutions = []

    # Pattern pour résolutions numérotées
    patterns = [
        # Résolution n°1: texte
        r'Résolution\s+n°\s*(\d+)\s*:\s*(.+?)(?=\n\nRésolution|\n\n[A-Z]{3,}|$)',
        # Resolution No. 1: texte
        r'Resolution\s+(?:No\.|#)?\s*(\d+)\s*:\s*(.+?)(?=\n\nResolution|\n\n[A-Z]{3,}|$)',
        # 1. texte
        r'^(\d+)\.\s+(.+?)(?=\n\d+\.|\n\n|$)',
    ]

    for pattern in patterns:
        matches = re.finditer(pattern, texte, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        for match in matches:
            num = match.group(1)
            texte_res = match.group(2).strip()
            # Nettoyer le texte
            texte_res = re.sub(r'\s+', ' ', texte_res)
            # Limiter à 500 caractères
            if len(texte_res) > 500:
                texte_res = texte_res[:497] + "..."

            if texte_res and len(texte_res) > 10:
                resolutions.append(f"Résolution {num}: {texte_res}")

        if resolutions:
            break

    # Si aucune résolution trouvée, chercher dans la section ORDRE DU JOUR
    if not resolutions:
        match_agenda = re.search(r'(?:ORDRE DU JOUR|AGENDA)(.*?)(?=\n\n[A-Z]{3,}|$)',
        texte, re.IGNORECASE | re.DOTALL)
        if match_agenda:
            agenda_text = match_agenda.group(1)
            # Chercher les lignes numérotées
            lignes = agenda_text.split('\n')
            for ligne in lignes:
                match_num = re.match(r'^\s*(\d+)\.\s+(.+)', ligne)
                if match_num:
                    num = match_num.group(1)
                    texte_res = match_num.group(2).strip()
                    if len(texte_res) > 10:
                        resolutions.append(f"Résolution {num}: {texte_res}")

    return resolutions if resolutions else ["Résolution 1: À extraire manuellement"]

def extraire_contact(texte):
    """Extrait les informations de contact"""
    contact = {}

    # Email
    pattern_email = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    match = re.search(pattern_email, texte)
    if match:
        contact['email'] = match.group(0)

    # Téléphone
    pattern_tel = r'(?:\+|00)\d{1,3}[\s\-]?\d{1,4}[\s\-]?\d{1,4}[\s\-]?\d{1,4}'
    match = re.search(pattern_tel, texte)
    if match:
        contact['phone'] = match.group(0)

    return contact

def extraire_bic(texte):
    """Extrait le code BIC"""
    # Pattern BIC: 8 ou 11 caractères
    pattern = r'\b([A-Z]{6}[A-Z0-9]{2}(?:[A-Z0-9]{3})?)\b'
    matches = re.findall(pattern, texte)

    # Mots à exclure
    exclusions = ['CONVOCATION', 'ASSEMBLÉE', 'ASSEMBLY', 'BONDHOLDER',
    'OBLIGATAIRE', 'MEETING', 'BIGREP']

    # Filtrer pour éviter les faux positifs
    for match in matches:
        if len(match) in [8, 11] and match not in exclusions:
            # Un vrai BIC se termine souvent par XXX ou un code pays
            if match.endswith('XXX') or match.endswith('LUX'):
                return match

    return ""

def extraction_automatique(texte):
    """Extrait toutes les données du texte"""
    print("🔍 Extraction des données en cours…")
    print()

    donnees = {}

    # ISIN
    donnees['isin'] = extraire_isin(texte)
    print(f" 📋 ISIN: {donnees['isin'] or '❌ Non trouvé'}")

    # Émetteur
    donnees['company_name'] = extraire_nom_emetteur(texte)
    print(f" 🏢 Émetteur: {donnees['company_name'] or '❌ Non trouvé'}")

    # Dates
    dates = extraire_dates(texte)
    donnees['meeting_date'] = convertir_date_iso(dates.get('meeting_date', ''))
    donnees['deadline'] = convertir_date_iso(dates.get('deadline', ''))
    donnees['record_date'] = convertir_date_iso(dates.get('record_date', ''))

    print(f" 📅 Date meeting: {donnees['meeting_date'] or '❌ Non trouvé'}")
    print(f" ⏰ Deadline: {donnees['deadline'] or '❌ Non trouvé'}")
    print(f" 📌 Record date: {donnees['record_date'] or '❌ Non trouvé'}")

    # Lieu
    donnees['location'] = extraire_lieu(texte)
    print(f" 📍 Lieu: {donnees['location'] or '❌ Non trouvé'}")

    # Résolutions
    donnees['resolutions'] = extraire_resolutions(texte)
    print(f" 📝 Résolutions: {len(donnees['resolutions'])} trouvée(s)")

    # Contact
    contact = extraire_contact(texte)
    donnees['contact_email'] = contact.get('email', '')
    donnees['contact_phone'] = contact.get('phone', '')
    print(f" 📧 Email: {donnees['contact_email'] or '❌ Non trouvé'}")
    print(f" 📞 Téléphone: {donnees['contact_phone'] or '❌ Non trouvé'}")

    # BIC
    donnees['bic'] = extraire_bic(texte)
    print(f" 🏦 BIC: {donnees['bic'] or '❌ Non trouvé'}")

    print()
    return donnees

def generer_seev001(donnees):
    """Génère le message Swift SEEV.001.001.12"""

    # Créer la racine
    root = ET.Element('Document')
    root.set('xmlns', 'urn:iso:std:iso:20022:tech:xsd:seev.001.001.12')

    # Meeting Notification
    mtg_notif = ET.SubElement(root, 'MtgNtfctn')

    # 1. Notification General Information
    notif_gen_info = ET.SubElement(mtg_notif, 'NtfctnGnlInf')
    notif_id = ET.SubElement(notif_gen_info, 'NtfctnId')
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    notif_id.text = donnees.get('notification_id', f'NOTIF{timestamp}')

    # 2. Meeting Reference
    mtg_ref = ET.SubElement(mtg_notif, 'MtgRef')
    mtg_id = ET.SubElement(mtg_ref, 'MtgId')
    mtg_id.text = donnees.get('meeting_id', f'MTG{timestamp}')

    issuer_mtg_id = ET.SubElement(mtg_ref, 'IssrMtgId')
    issuer_mtg_id.text = donnees.get('issuer_meeting_id', f'ISS{timestamp}')

    # 3. Financial Instrument (ISIN)
    if donnees.get('isin'):
        fin_instrm_id = ET.SubElement(mtg_notif, 'FinInstrmId')
        isin = ET.SubElement(fin_instrm_id, 'ISIN')
        isin.text = donnees['isin']

    # 4. Meeting Details
    mtg_dtl = ET.SubElement(mtg_notif, 'MtgDtls')

    if donnees.get('meeting_date'):
        dt_and_tm = ET.SubElement(mtg_dtl, 'DtAndTm')
        dt = ET.SubElement(dt_and_tm, 'Dt')
        dt.text = donnees['meeting_date']

    if donnees.get('location'):
        lctn = ET.SubElement(mtg_dtl, 'Lctn')
        lctn_desc = ET.SubElement(lctn, 'Desc')
        lctn_desc.text = donnees['location']

    mtg_tp = ET.SubElement(mtg_dtl, 'MtgTp')
    mtg_tp.text = donnees.get('meeting_type', 'XMET')

    # 5. Issuer
    if donnees.get('company_name'):
        issr = ET.SubElement(mtg_notif, 'Issr')
        issr_id = ET.SubElement(issr, 'Id')
        nm_and_adr = ET.SubElement(issr_id, 'NmAndAdr')
        nm = ET.SubElement(nm_and_adr, 'Nm')
        nm.text = donnees['company_name']

    # 6. Resolutions
    for idx, resolution in enumerate(donnees.get('resolutions', []), 1):
        rsltn = ET.SubElement(mtg_notif, 'Rsltn')

        rsltn_id = ET.SubElement(rsltn, 'Id')
        rsltn_id.text = str(idx)

        rsltn_desc = ET.SubElement(rsltn, 'Desc')
        rsltn_desc.text = resolution

        tp = ET.SubElement(rsltn, 'Tp')
        tp.text = 'EXTR'

        vt_mthd = ET.SubElement(rsltn, 'VtMthd')
        vt_mthd.text = 'POLL'

    # 7. Contact
    if donnees.get('contact_email') or donnees.get('contact_phone'):
        mtg_cntct = ET.SubElement(mtg_notif, 'MtgCntctPrsn')
        cntct_dtls = ET.SubElement(mtg_cntct, 'CntctDtls')

        if donnees.get('contact_email'):
            email = ET.SubElement(cntct_dtls, 'EmailAdr')
            email.text = donnees['contact_email']

        if donnees.get('contact_phone'):
            phne = ET.SubElement(cntct_dtls, 'PhneNb')
            phne.text = donnees['contact_phone']

    # 8. Additional Info
    addtl_info_parts = []
    if donnees.get('record_date'):
        addtl_info_parts.append(f"Record Date: {donnees['record_date']}")
    if donnees.get('deadline'):
        addtl_info_parts.append(f"Deadline: {donnees['deadline']}")
    if donnees.get('bic'):
        addtl_info_parts.append(f"BIC: {donnees['bic']}")

    if addtl_info_parts:
        addtl_inf = ET.SubElement(mtg_notif, 'AddtlInf')
        addtl_inf.text = ". ".join(addtl_info_parts) + "."

    # Formater
    xml_str = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent=" ", encoding='utf-8').decode('utf-8')

    # Nettoyer
    lines = pretty_xml.split('\n')
    pretty_xml = '\n'.join([line for line in lines if line.strip()])

    return pretty_xml

def sauvegarder_xml(xml_content, nom_fichier=None):
    """Sauvegarde le XML"""
    if nom_fichier is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom_fichier = f'SEEV001_{timestamp}.xml'

    with open(nom_fichier, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    return nom_fichier

# =============================================================================
# PROGRAMME PRINCIPAL
# =============================================================================

if __name__ == '__main__':
    print("=" * 70)
    print(" " * 15 + "GÉNÉRATEUR SEEV.001.001.12")
    print(" " * 10 + "avec Extraction Automatique depuis TXT")
    print("=" * 70)
    print()

    # Demander le fichier
    print("📁 Quel fichier TXT voulez-vous traiter ?")
    print()
    print("Options :")
    print(" 1. Tapez le chemin complet (ex: C:\\Documents\\convocation.txt)")
    print(" 2. Si le fichier est dans le même dossier, tapez juste son nom")
    print(" 3. Ou glissez-déposez le fichier ici")
    print()

    chemin_fichier = input("Chemin du fichier: ").strip().strip('"')

    if not chemin_fichier:
        print("❌ Aucun fichier spécifié!")
        input("Appuyez sur Entrée pour quitter...")
        exit(1)

    # Vérifier que le fichier existe
    if not os.path.exists(chemin_fichier):
        print(f"❌ Fichier introuvable: {chemin_fichier}")
        input("Appuyez sur Entrée pour quitter...")
        exit(1)

    print()
    print("=" * 70)

    # Lire le fichier
    texte = lire_fichier_txt(chemin_fichier)

    if not texte:
        print("❌ Impossible de lire le fichier!")
        input("Appuyez sur Entrée pour quitter...")
        exit(1)

    print(f"✅ Fichier lu: {len(texte)} caractères")
    print()

    # Extraction
    donnees_extraites = extraction_automatique(texte)

    print("=" * 70)
    print()

    # Demander confirmation
    print("Les données extraites vous conviennent-elles ? (O/N)")
    reponse = input("Votre réponse: ").strip().upper()

    if reponse != 'O':
        print()
        print("💡 Vous pouvez modifier les données extraites dans le code")
        print(" ou améliorer le fichier TXT source.")
        input("Appuyez sur Entrée pour quitter...")
        exit(0)

    print()
    print("🚀 Génération du XML SEEV.001...")

    # Générer le XML
    xml_genere = generer_seev001(donnees_extraites)

    # Sauvegarder
    nom_fichier = sauvegarder_xml(xml_genere)

    print()
    print("=" * 70)
    print("✅ GÉNÉRATION TERMINÉE !")
    print("=" * 70)
    print()
    print(f"📄 Fichier créé: {nom_fichier}")
    print()
    print("Vous pouvez maintenant :")
    print(" 1. Ouvrir le fichier XML avec un éditeur")
    print(" 2. Vérifier son contenu")
    print(" 3. L'envoyer via Swift")
    print()

    input("Appuyez sur Entrée pour quitter...")
