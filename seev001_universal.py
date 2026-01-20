#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur SEEV.001 Universel Standalone
Gère AGM, EGM et Bondholder Meetings
"""

import os
import sys
import re
import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom
from datetime import datetime as dt_obj

# --- MODULES INTEGRATED ---

# 1. detecteur_type
def detecter_type_event(texte):
    if re.search(r'bondholder|noteholder|obligataire', texte, re.I):
        return 'BONDHOLDER'
    if re.search(r'extraordinary|extraordinaire|EGM', texte, re.I):
        return 'EGM'
    return 'AGM'

def detecter_document_type(texte):
    if re.search(r'notice|avis|convocation', texte, re.I):
        return 'Notice of Meeting'
    return 'Document'

def detecter_langue(texte):
    if re.search(r'\bthe\b|\band\b|\bof\b', texte, re.I):
        return 'EN'
    if re.search(r'\ble\b|\bla\b|\bet\b', texte, re.I):
        return 'FR'
    return 'EN'

# 2. extracteur_commun
MO_EN = ['january','february','march','april','may','june','july','august','september','october','november','december']
MO_FR = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']

def extraire_nom_societe(texte):
    issMatch = re.search(r'\*\*([A-Z][A-Za-z\s]+(?:SE|SA|S\.A\.))\*\*', texte)
    if not issMatch:
        issMatch = re.search(r'^([A-Z][A-Za-z\s]+(?:SE|SA))\s*$', texte, re.M)
    if not issMatch:
        issMatch = re.search(r'convened by ([A-Z][A-Za-z\s,\.]+(?:SE|SA|Ltd|GmbH))', texte, re.I)
    return issMatch.group(1).strip().upper() if issMatch else "ISSUER"

def extraire_isin(texte):
    isinPatterns = [
        r'ISIN\s*[:\s]\s*([A-Z]{2}[A-Z0-9]{9}[0-9])',
        r'\b(LU[0-9]{10})\b',
        r'\b(XS[0-9]{10})\b',
        r'\b(FR[0-9]{10})\b',
        r'\b(DE[0-9]{10})\b',
        r'\b(BE[0-9]{10})\b',
        r'(LU|XS)\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]\s?[0-9]'
    ]
    for pattern in isinPatterns:
        m = re.search(pattern, texte, re.I)
        if m:
            val = m.group(1) if m.groups() else m.group(0)
            val = re.sub(r'\s', '', val).upper()
            if len(val) == 12: return val
    return None

def extraire_rcs(texte):
    m = re.search(r'R\.?C\.?S\.?\s*([A-Z0-9\s-]+)', texte, re.I)
    return m.group(1).strip() if m else None

def parse_date(day, month_str, year):
    mo_str = month_str.lower()
    if mo_str in MO_EN: mo = str(MO_EN.index(mo_str) + 1).zfill(2)
    elif mo_str in MO_FR: mo = str(MO_FR.index(mo_str) + 1).zfill(2)
    else: mo = "01"
    return f"{year}-{mo}-{day.zfill(2)}"

def extraire_dates(texte):
    res = {}
    months_regex = '|'.join(MO_EN + MO_FR)
    mtgMatch = re.search(rf'held on (\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+at\s+(\d{{1,2}}):(\d{{2}})', texte, re.I)
    if mtgMatch:
        res['meeting_date'] = parse_date(mtgMatch.group(1), mtgMatch.group(2), mtgMatch.group(3))
        res['meeting_time'] = f"{mtgMatch.group(4).zfill(2)}:{mtgMatch.group(5)}"
    recMatch = re.search(rf'(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+\(midnight\)', texte, re.I)
    if not recMatch: recMatch = re.search(rf'record date\s*[:\s]\s*(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})', texte, re.I)
    if recMatch: res['record_date'] = parse_date(recMatch.group(1), recMatch.group(2), recMatch.group(3))
    # Handling AM/PM and potential 12:00 edge cases
    dlMatch = re.search(rf'(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+at\s+(\d{{1,2}}):(\d{{2}})\s*(p\.?m|a\.?m)?', texte, re.I)
    if dlMatch:
        h = int(dlMatch.group(4))
        ampm = dlMatch.group(6).lower() if dlMatch.group(6) else ""
        if 'p' in ampm and h < 12: h += 12
        elif 'a' in ampm and h == 12: h = 0
        res['deadline'] = parse_date(dlMatch.group(1), dlMatch.group(2), dlMatch.group(3)) + f"T{str(h).zfill(2)}:{dlMatch.group(5)}"
    return res

def extraire_heure(texte):
    m = re.search(r'at\s+(\d{1,2}):(\d{2})', texte, re.I)
    return f"{m.group(1).zfill(2)}:{m.group(2)}" if m else None

def extraire_lieu(texte):
    addrMatch = re.search(r'at\s+(\d+[A-Z]?),\s+([A-Za-z\s\.]+(?:Avenue|Street|Route|Rue|Boulevard)[^,]*),\s+(L-?\d{4})', texte, re.I)
    return f"{addrMatch.group(1)}, {addrMatch.group(2).strip()}, {addrMatch.group(3)} LUXEMBOURG" if addrMatch else None

def extraire_contact(texte):
    email = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', texte)
    return {'email': email.group(0) if email else None}

def extraire_resolutions(texte):
    resols = []
    lines = texte.split('\n')
    inAgenda = False
    currentNum = None
    currentText = ''
    months_regex = '|'.join(MO_EN + MO_FR)
    for line in lines:
        line = line.strip()
        if re.search(r'AGENDA FOR THE ANNUAL|^I\.\s*AGENDA|AGENDA|ORDER OF BUSINESS|ORDRE DU JOUR', line, re.I):
            inAgenda = True; continue
        if not inAgenda: continue
        if re.search(r'^II\.|^PARTICIPATION|^III\.|^IV\.|^VOTING|^PROXY|^VOTE', line, re.I): break
        if re.search(rf'^\d{{1,2}}\s+({months_regex})\s+\d{{4}}', line, re.I): continue
        resMatch = re.match(r'^\s*(\d{1,2})[\.\)]\s+(.+)', line)
        if resMatch:
            if currentNum and currentText: resols.append({'n': currentNum, 't': resume(currentText), 'f': bool(re.search(r'^Presentation', currentText, re.I))})
            currentNum, currentText = resMatch.group(1), resMatch.group(2)
        elif currentNum and len(line) > 5 and not re.match(r'^[A-Z]{3,}$', line):
            currentText += ' ' + line
    if currentNum and currentText: resols.append({'n': currentNum, 't': resume(currentText), 'f': bool(re.search(r'^Presentation', currentText, re.I))})
    return resols

def resume(t):
    t = t.strip()
    if re.search(r'^Presentation of', t, re.I): return 'Presentation of reports'
    m = re.search(r'Approval of the annual', t, re.I)
    if m:
        year = re.search(r'(\d{4})', t)
        return f"Approval of annual accounts {year.group(1) if year else ''}"
    return t[:250]

def extraire_quorum(texte):
    return "No quorum required" if re.search(r'no quorum|without quorum|sans quorum', texte, re.I) else None

# 3. extracteur_agm
def extraire_donnees_agm(texte):
    res = {}
    div = re.search(r'dividend of EUR\s*([0-9\.]+)', texte, re.I)
    if div: res['dividend'] = div.group(1)
    fy = re.search(r'fiscal year ended ([^,\.]+)', texte, re.I)
    if fy: res['fiscal_year_end'] = fy.group(1).strip()
    auditor = re.search(r'auditor\s+([A-Z][A-Za-z\s\.]+S\.A\.)', texte, re.I)
    if auditor: res['auditor'] = auditor.group(1).strip()
    return res

# 4. extracteur_egm
def extraire_donnees_egm(texte):
    res = {'egm_purpose': []}
    if re.search(r'amendment of the articles', texte, re.I): res['egm_purpose'].append("Articles Amendment")
    if re.search(r'capital increase', texte, re.I): res['egm_purpose'].append("Capital Increase")
    if re.search(r'liquidation|winding up', texte, re.I): res['liquidation'] = True
    return res

# 5. extracteur_bondholder
def extraire_donnees_bondholder(texte):
    res = {'clearing_systems': []}
    bond_type = re.search(r'(Notes|Bonds|Obligations)\s+due\s+(\d{4})', texte, re.I)
    if bond_type: res['bond_type'] = bond_type.group(0)
    if re.search(r'Euroclear', texte, re.I): res['clearing_systems'].append('Euroclear')
    if re.search(r'Clearstream', texte, re.I): res['clearing_systems'].append('Clearstream')
    if re.search(r'deemed consent', texte, re.I): res['deemed_consent'] = True
    res['meeting_calls'] = re.findall(r'(\d+)(?:st|nd|rd|th)\s+meeting', texte, re.I)
    return res

# 6. generateur_xml
def dt_iso(d):
    if not d: return "2024-01-01T00:00:00Z"
    return (d + ":00Z") if 'T' in d and len(d) == 16 else (d + "T00:00:00Z" if 'T' not in d else d)

def generer_seev001(donnees, meeting_type):
    mid = "GMET" + dt_obj.now().strftime("%f")
    root = ET.Element("Document", {"xmlns": "urn:iso:std:iso:20022:tech:xsd:seev.001.001.12"})
    mtg_ntfctn = ET.SubElement(root, "MtgNtfctn")
    inf = ET.SubElement(mtg_ntfctn, "NtfctnGnlInf")
    ET.SubElement(inf, "NtfctnTp").text = "NEWM"
    sts = ET.SubElement(inf, "NtfctnSts")
    ET.SubElement(sts, "EvtCmpltnsSts").text = "COMP"
    ET.SubElement(sts, "EvtConfSts").text = "CONF"
    mtg = ET.SubElement(mtg_ntfctn, "Mtg")
    ET.SubElement(mtg, "MtgId").text = mid
    ET.SubElement(mtg, "IssrMtgId").text = mid
    ET.SubElement(mtg, "Tp").text = "GMET"
    clssf = ET.SubElement(mtg, "Clssfctn")
    ET.SubElement(clssf, "Cd").text = "ISSU"
    ann = ET.SubElement(mtg, "AnncmntDt")
    ET.SubElement(ann, "DtTm").text = dt_iso(donnees.get("announcement_date"))
    prtc = ET.SubElement(mtg, "Prtcptn")
    ET.SubElement(ET.SubElement(prtc, "PrtcptnMtd"), "Cd").text = "PHYS"
    ddln = ET.SubElement(prtc, "IssrDdlnForVtng")
    ET.SubElement(ET.SubElement(ddln, "DtOrDtTm"), "DtTm").text = dt_iso(donnees.get("deadline"))
    ent = ET.SubElement(mtg, "EntitlmntFxgDt")
    ET.SubElement(ET.SubElement(ent, "Dt"), "Dt").text = donnees.get("record_date", "2024-01-01")
    ET.SubElement(ent, "DtMd").text = "EODY"
    dtls = ET.SubElement(mtg_ntfctn, "MtgDtls")
    mtg_dt = donnees.get("meeting_date") or "2024-01-01"
    mtg_tm = donnees.get("meeting_time") or "00:00"
    ET.SubElement(ET.SubElement(ET.SubElement(dtls, "DtAndTm"), "DtOrDtTm"), "DtTm").text = dt_iso(mtg_dt + "T" + mtg_tm)
    adr = ET.SubElement(ET.SubElement(dtls, "Lctn"), "Adr")
    ET.SubElement(adr, "TwnNm").text = (donnees.get("location") or "LUXEMBOURG")[:35]
    ET.SubElement(adr, "Ctry").text = "LU"
    issr = ET.SubElement(mtg_ntfctn, "Issr")
    ET.SubElement(ET.SubElement(ET.SubElement(issr, "Id"), "NmAndAdr"), "Nm").text = (donnees.get("company_name") or "ISSUER")[:140]
    scty = ET.SubElement(mtg_ntfctn, "Scty")
    ET.SubElement(ET.SubElement(scty, "FinInstrmId"), "ISIN").text = donnees.get("isin") or "LU0000000000"
    for r in donnees.get('resolutions', []):
        rsltn = ET.SubElement(mtg_ntfctn, "Rsltn")
        ET.SubElement(rsltn, "IssrLabl").text = str(r.get("n"))
        desc = ET.SubElement(rsltn, "Desc")
        ET.SubElement(desc, "Lang").text = "en"
        ET.SubElement(desc, "Titl").text = (r.get("t") or "Resolution")[:250]
        ET.SubElement(rsltn, "ForInfOnly").text = "true" if r.get("f") else "false"
        ET.SubElement(rsltn, "Sts").text = "ACTV"
    xml_str = ET.tostring(root, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent=" ")


# --- ORIGINAL MAIN LOGIC ---

def lire_fichier(chemin):
    """Lit un fichier texte"""
    try:
        with open(chemin, 'r', encoding='utf-8') as f:
            return f.read()
    except:
        try:
            with open(chemin, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            print(f"❌ Erreur lecture: {e}")
            return None


def extraire_toutes_donnees(texte):
    """Extrait toutes les données selon le type d'événement"""
    print("🔍 Analyse du document...")
    print()

    # 1. Détecter le type
    meeting_type = detecter_type_event(texte)
    document_type = detecter_document_type(texte)
    langue = detecter_langue(texte)

    print(f"  📋 Type d'événement: {meeting_type}")
    print(f"  📄 Type de document: {document_type}")
    print(f"  🌍 Langue: {langue}")
    print()

    # 2. Extraction données communes
    print("📊 Extraction des données communes...")
    donnees = {}

    donnees['meeting_type'] = meeting_type
    donnees['document_type'] = document_type
    donnees['langue'] = langue

    donnees['company_name'] = extraire_nom_societe(texte)
    print(f"  ✅ Société: {donnees['company_name']}")

    donnees['isin'] = extraire_isin(texte)
    if donnees['isin']:
        print(f"  ✅ ISIN: {donnees['isin']}")

    donnees['rcs'] = extraire_rcs(texte)
    if donnees['rcs']:
        print(f"  ✅ RCS: {donnees['rcs']}")

    # Dates
    dates = extraire_dates(texte)
    donnees.update(dates)
    if dates.get('meeting_date'):
        print(f"  ✅ Date meeting: {dates['meeting_date']}")
    if dates.get('record_date'):
        print(f"  ✅ Record date: {dates['record_date']}")
    if dates.get('deadline'):
        print(f"  ✅ Deadline: {dates['deadline']}")

    # Heure
    donnees['meeting_time'] = extraire_heure(texte)
    if donnees['meeting_time']:
        print(f"  ✅ Heure: {donnees['meeting_time']}")

    # Lieu
    donnees['location'] = extraire_lieu(texte)
    if donnees['location']:
        print(f"  ✅ Lieu: {donnees['location'][:50]}...")

    # Contact
    donnees['contact'] = extraire_contact(texte)
    if donnees['contact'].get('email'):
        print(f"  ✅ Email: {donnees['contact']['email']}")

    # Résolutions
    donnees['resolutions'] = extraire_resolutions(texte)
    if donnees['resolutions']:
        print(f"  ✅ Résolutions: {len(donnees['resolutions'])} trouvée(s)")

    # Quorum
    donnees['quorum'] = extraire_quorum(texte)

    print()

    # 3. Extraction spécifique selon le type
    if meeting_type == 'AGM':
        print("📈 Extraction données AGM...")
        donnees_agm = extraire_donnees_agm(texte)
        donnees.update(donnees_agm)

        if donnees_agm.get('dividend'):
            print(f"  ✅ Dividende: {donnees_agm['dividend']}")
        if donnees_agm.get('fiscal_year_end'):
            print(f"  ✅ Exercice fiscal: {donnees_agm['fiscal_year_end']}")
        if donnees_agm.get('auditor'):
            print(f"  ✅ Auditeur: {donnees_agm['auditor'][:50]}...")

    elif meeting_type == 'EGM':
        print("⚡ Extraction données EGM...")
        donnees_egm = extraire_donnees_egm(texte)
        donnees.update(donnees_egm)

        if donnees_egm.get('egm_purpose'):
            purposes = ', '.join(donnees_egm['egm_purpose'])
            print(f"  ✅ Objectif: {purposes}")
        if donnees_egm.get('liquidation'):
            print(f"  ⚠️  Liquidation détectée")

    elif meeting_type == 'BONDHOLDER':
        print("💰 Extraction données Bondholder...")
        donnees_bond = extraire_donnees_bondholder(texte)
        donnees.update(donnees_bond)

        if donnees_bond.get('bond_type'):
            print(f"  ✅ Type de bonds: {donnees_bond['bond_type']}")
        if donnees_bond.get('clearing_systems'):
            systems = ', '.join(donnees_bond['clearing_systems'])
            print(f"  ✅ Clearing: {systems}")
        if donnees_bond.get('deemed_consent'):
            print(f"  ⚠️  Deemed consent: OUI")
        if donnees_bond.get('meeting_calls'):
            print(f"  ✅ Meeting calls: {len(donnees_bond['meeting_calls'])}")

    print()
    return donnees, meeting_type


def afficher_resume(donnees, meeting_type):
    """Affiche un résumé des données extraites"""
    print("=" * 70)
    print(" " * 25 + "RÉSUMÉ")
    print("=" * 70)
    print()
    print(f"Type: {meeting_type}")
    print(f"Société: {donnees.get('company_name', 'Non trouvé')}")

    if donnees.get('isin'):
        print(f"ISIN: {donnees['isin']}")

    print(f"Date: {donnees.get('meeting_date', 'Non trouvé')}")
    print(f"Heure: {donnees.get('meeting_time', 'Non trouvé')}")
    print(f"Résolutions: {len(donnees.get('resolutions', []))}")
    print()
    print("=" * 70)
    print()


def main():
    """Fonction principale"""
    print("=" * 70)
    print(" " * 15 + "GÉNÉRATEUR SEEV.001 UNIVERSEL")
    print(" " * 10 + "AGM • EGM • BONDHOLDER MEETINGS")
    print("=" * 70)
    print()

    # 1. Demander le fichier
    print("📁 Fichier à traiter:")
    print("  - Tapez le chemin complet")
    print("  - Ou glissez-déposez le fichier")
    print()

    try:
        chemin_fichier = input("Chemin: ").strip().strip('"')
    except EOFError:
        return

    if not chemin_fichier:
        print("❌ Aucun fichier spécifié!")
        return

    if not os.path.exists(chemin_fichier):
        print(f"❌ Fichier introuvable: {chemin_fichier}")
        return

    print()
    print("=" * 70)
    print()

    # 2. Lire le fichier
    texte = lire_fichier(chemin_fichier)
    if not texte:
        print("❌ Impossible de lire le fichier!")
        return

    print(f"✅ Fichier lu: {len(texte)} caractères")
    print()

    # 3. Extraire les données
    donnees, meeting_type = extraire_toutes_donnees(texte)

    # 4. Afficher le résumé
    afficher_resume(donnees, meeting_type)

    # 5. Demander confirmation
    print("Voulez-vous générer le XML SEEV.001 ? (O/N)")
    try:
        reponse = input("Réponse: ").strip().upper()
    except EOFError:
        reponse = 'N'

    if reponse != 'O':
        print("❌ Génération annulée.")
        return

    print()
    print("🚀 Génération du XML SEEV.001...")

    # 6. Générer le XML
    try:
        xml_content = generer_seev001(donnees, meeting_type)

        # 7. Sauvegarder
        timestamp = dt_obj.now().strftime('%Y%m%d_%H%M%S')
        company_raw = donnees.get('company_name', 'Company')
        # Sanitize filename for Windows
        company_short = re.sub(r'[<>:"/\\|?*]', '', company_raw)[:20].strip().replace(' ', '_')
        nom_fichier = f'SEEV001_{company_short}_{timestamp}.xml'

        try:
            with open(nom_fichier, 'w', encoding='utf-8') as f:
                f.write(xml_content)
        except PermissionError:
            # Fallback to home directory
            home = os.path.expanduser("~")
            fallback_path = os.path.join(home, nom_fichier)
            print(f"⚠️  Permission refusée dans le dossier local. Tentative de sauvegarde dans : {home}")
            with open(fallback_path, 'w', encoding='utf-8') as f:
                f.write(xml_content)
            nom_fichier = fallback_path

        print()
        print("=" * 70)
        print("✅ GÉNÉRATION TERMINÉE !")
        print("=" * 70)
        print()
        print(f"📄 Fichier créé: {nom_fichier}")
        print()
        print("Le fichier XML SEEV.001 est prêt à être utilisé.")
        print()

    except Exception as e:
        print(f"❌ Erreur lors de la génération: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Interrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
    finally:
        try:
            input("\nAppuyez sur Entrée pour quitter...")
        except EOFError:
            pass
