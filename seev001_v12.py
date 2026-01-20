#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Générateur SEEV.001.001.12 - Version Simple
Pas besoin d'installation compliquée, juste Python de base !
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime

def generer_seev001(donnees):
    """
    Génère un message Swift SEEV.001.001.12

    Args:
        donnees (dict): Dictionnaire contenant toutes les informations

    Returns:
        str: Le XML formaté
    """

    # Créer la racine du document
    root = ET.Element('Document')
    root.set('xmlns', 'urn:iso:std:iso:20022:tech:xsd:seev.001.001.12')

    # Message Meeting Notification
    mtg_notif = ET.SubElement(root, 'MtgNtfctn')

    # 1. Notification General Information
    notif_gen_info = ET.SubElement(mtg_notif, 'NtfctnGnlInf')

    notif_id = ET.SubElement(notif_gen_info, 'NtfctnId')
    notif_id.text = donnees.get('notification_id', 'NOTIF001')

    notif_tp = ET.SubElement(notif_gen_info, 'NtfctnTp')
    notif_tp.text = 'NEWM'

    notif_sts = ET.SubElement(notif_gen_info, 'NtfctnSts')
    evt_cmpltns_sts = ET.SubElement(notif_sts, 'EvtCmpltnsSts')
    evt_cmpltns_sts.text = 'COMP'
    evt_conf_sts = ET.SubElement(notif_sts, 'EvtConfSts')
    evt_conf_sts.text = 'CONF'

    # 2. Meeting (Mtg)
    mtg = ET.SubElement(mtg_notif, 'Mtg')

    mtg_id = ET.SubElement(mtg, 'MtgId')
    mtg_id.text = donnees.get('meeting_id', 'MTG001')

    issuer_mtg_id = ET.SubElement(mtg, 'IssrMtgId')
    issuer_mtg_id.text = donnees.get('issuer_meeting_id', 'ISS001')

    mtg_tp = ET.SubElement(mtg, 'Tp')
    mtg_tp.text = donnees.get('meeting_type', 'XMET')

    clssfctn = ET.SubElement(mtg, 'Clssfctn')
    clssfctn_cd = ET.SubElement(clssfctn, 'Cd')
    clssfctn_cd.text = 'ISSU'

    # 3. Meeting Details
    mtg_dtls = ET.SubElement(mtg_notif, 'MtgDtls')
    dt_and_tm = ET.SubElement(mtg_dtls, 'DtAndTm')
    dt_or_dt_tm = ET.SubElement(dt_and_tm, 'DtOrDtTm')
    dt_tm = ET.SubElement(dt_or_dt_tm, 'DtTm')

    meeting_date = donnees.get('meeting_date', '')
    if meeting_date and 'T' not in meeting_date:
        meeting_date += 'T09:00:00Z'
    dt_tm.text = meeting_date

    if donnees.get('location'):
        lctn = ET.SubElement(mtg_dtls, 'Lctn')
        adr = ET.SubElement(lctn, 'Adr')
        twn_nm = ET.SubElement(adr, 'TwnNm')
        twn_nm.text = donnees['location']
        ctry = ET.SubElement(adr, 'Ctry')
        ctry.text = donnees.get('country_code', 'ZZ')  # Use country_code if available

    # 4. Issuer
    issr = ET.SubElement(mtg_notif, 'Issr')
    issr_id = ET.SubElement(issr, 'Id')
    nm_and_adr = ET.SubElement(issr_id, 'NmAndAdr')
    nm = ET.SubElement(nm_and_adr, 'Nm')
    nm.text = donnees.get('company_name', '')

    # 5. Security (Scty)
    scty = ET.SubElement(mtg_notif, 'Scty')
    fin_instrm_id = ET.SubElement(scty, 'FinInstrmId')
    isin = ET.SubElement(fin_instrm_id, 'ISIN')
    isin.text = donnees.get('isin', '')

    if donnees.get('security_description'):
        desc = ET.SubElement(scty, 'Desc')
        desc.text = donnees['security_description']

    # 6. Resolutions
    for idx, resolution in enumerate(donnees.get('resolutions', []), 1):
        rsltn = ET.SubElement(mtg_notif, 'Rsltn')

        issr_labl = ET.SubElement(rsltn, 'IssrLabl')
        issr_labl.text = str(idx)

        desc_node = ET.SubElement(rsltn, 'Desc')
        lang = ET.SubElement(desc_node, 'Lang')
        lang.text = donnees.get('language', 'en')
        titl = ET.SubElement(desc_node, 'Titl')
        titl.text = resolution

        for_inf_only = ET.SubElement(rsltn, 'ForInfOnly')
        for_inf_only.text = 'false'

        sts = ET.SubElement(rsltn, 'Sts')
        sts.text = 'ACTV'

    # 7. Contact Details
    if any(donnees.get(k) for k in ['contact_name', 'contact_email', 'contact_phone']):
        mtg_cntct_prsn = ET.SubElement(mtg_notif, 'MtgCntctPrsn')
        cntct_dtls = ET.SubElement(mtg_cntct_prsn, 'CntctDtls')

        if donnees.get('contact_name'):
            nm_prfx = ET.SubElement(cntct_dtls, 'NmPrfx')
            nm_prfx.text = donnees['contact_name']

        if donnees.get('contact_email'):
            email = ET.SubElement(cntct_dtls, 'EmailAdr')
            email.text = donnees['contact_email']

        if donnees.get('contact_phone'):
            phne = ET.SubElement(cntct_dtls, 'PhneNb')
            phne.text = donnees['contact_phone']

    # 8. Additional Information
    if donnees.get('additional_info'):
        addtl_inf = ET.SubElement(mtg_notif, 'AddtlInf')
        dsclmr = ET.SubElement(addtl_inf, 'Dsclmr')
        lang = ET.SubElement(dsclmr, 'Lang')
        lang.text = donnees.get('language', 'en')
        inf = ET.SubElement(dsclmr, 'AddtlInf')
        inf.text = donnees['additional_info']

    # Formater le XML
    xml_str = ET.tostring(root, encoding='utf-8')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent="  ", encoding='utf-8').decode('utf-8')

    # Enlever la ligne vide après la déclaration XML
    lines = pretty_xml.split('\n')
    pretty_xml = '\n'.join([line for line in lines if line.strip()])

    return pretty_xml

def sauvegarder_xml(xml_content, nom_fichier=None):
    """Sauvegarde le XML dans un fichier"""
    if nom_fichier is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        nom_fichier = f'SEEV001_{timestamp}.xml'

    with open(nom_fichier, 'w', encoding='utf-8') as f:
        f.write(xml_content)

    print(f"✅ Fichier sauvegardé : {nom_fichier}")
    return nom_fichier

if __name__ == '__main__':
    # EXEMPLE D'UTILISATION
    mes_donnees = {
        'notification_id': 'NOTIF20250120001',
        'meeting_id': 'MTG20250215001',
        'issuer_meeting_id': 'BIGREP2025001',

        'isin': 'DE000A2G9LL1',
        'company_name': 'BIGREP SE',
        'security_description': 'Bond 5.5% 2026',

        'meeting_date': '2025-02-15',
        'location': 'Berlin',
        'country_code': 'DE',
        'language': 'fr',
        'meeting_type': 'XMET',

        'resolutions': [
            "Approbation de la modification des conditions d'émission relatives au taux d'intérêt, portant le taux de 5,5% à 6,0% par an.",
            "Approbation du report de la date d'échéance finale du 31 décembre 2026 au 31 décembre 2027.",
            "Approbation de la nomination d'un nouveau représentant des obligataires pour la durée restante de l'emprunt.",
            "Pouvoirs à donner au représentant des obligataires pour accomplir toutes formalités nécessaires."
        ],

        'contact_name': 'Bondholder Relations',
        'contact_email': 'bondholder.relations@bigrep.com',
        'contact_phone': '+49 30 1234 5678',

        'additional_info': 'Record Date: 2025-02-05. Deadline pour réponses: 2025-02-10.'
    }

    print("="*60)
    print("GÉNÉRATION DU MESSAGE SEEV.001.001.12")
    print("="*60)
    print()

    # Générer le XML
    xml_genere = generer_seev001(mes_donnees)

    # Afficher le résultat
    print(xml_genere)
    print()

    # Sauvegarder dans un fichier
    # fichier = sauvegarder_xml(xml_genere) # Commented out to avoid polluting repo during tests

    print()
    print("="*60)
    print("✅ GÉNÉRATION TERMINÉE")
    print("="*60)
