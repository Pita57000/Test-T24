"""
Générateur SEEV.001 - Application Streamlit
Extracteur automatique d'informations de convocations et générateur de messages Swift SEEV.001.001.12
"""

import streamlit as st
import re
from datetime import datetime, timedelta
from io import BytesIO
import xml.etree.ElementTree as ET
from xml.dom import minidom

# Configuration de la page
st.set_page_config(
    page_title="Générateur SEEV.001",
    page_icon="🏦",
    layout="wide"
)

# Titre
st.title("🏦 Générateur de Messages SEEV.001.001.12")
st.markdown("**Extracteur automatique pour convocations d'assemblées (PDF, Word, TXT)**")

# Initialisation de la session
if 'extracted_data' not in st.session_state:
    st.session_state.extracted_data = {}
if 'file_processed' not in st.session_state:
    st.session_state.file_processed = False


def extract_text_from_file(uploaded_file):
    """Extrait le texte selon le type de fichier"""
    file_type = uploaded_file.type
    filename = uploaded_file.name.lower()

    if file_type == "text/plain" or filename.endswith('.txt'):
        return uploaded_file.read().decode('utf-8', errors='ignore')

    elif file_type == "application/pdf" or filename.endswith('.pdf'):
        try:
            import pdfplumber
            with pdfplumber.open(uploaded_file) as pdf:
                text = ""
                for page in pdf.pages:
                    text += (page.extract_text() or "") + "\n"
            return text
        except ImportError:
            st.error("pdfplumber n'est pas installé. Utilisez: pip install pdfplumber")
            return None
        except Exception as e:
            st.error(f"Erreur lors de la lecture du PDF: {e}")
            return None

    elif filename.endswith('.docx'):
        try:
            from docx import Document
            doc = Document(uploaded_file)
            text = "\n".join([para.text for para in doc.paragraphs])
            return text
        except ImportError:
            st.error("python-docx n'est pas installé. Utilisez: pip install python-docx")
            return None
        except Exception as e:
            st.error(f"Erreur lors de la lecture du DOCX: {e}")
            return None

    else:
        st.warning(f"Type de fichier non supporté: {file_type}")
        return None


def resume(t):
    """Standardise les titres des résolutions"""
    t = t.strip()
    if not t: return ""
    if re.match(r'^Presentation of|^Présentation des', t, re.I): return 'Presentation of reports'

    match = re.search(r'(?:Approval of the annual|Approbation des comptes).*?(\d{4})', t, re.I)
    if match: return f'Approval of annual accounts {match.group(1)}'
    if re.search(r'Approval of the annual|Approbation des comptes', t, re.I): return 'Approval of annual accounts'

    match = re.search(r'(?:Approval of the consolidated|Approbation des comptes consolidés).*?(\d{4})', t, re.I)
    if match: return f'Approval of consolidated accounts {match.group(1)}'

    if re.search(r'Acknowledgement of the results|Affectation du résultat', t, re.I): return 'Acknowledgement and allocation of results'

    if re.search(r'advisory vote.*remuneration|vote consultatif.*rémunération', t, re.I):
        return 'Advisory vote on remuneration policy' if re.search(r'policy|politique', t, re.I) else 'Advisory vote on remuneration report'

    if re.search(r'discharge|quitus', t, re.I):
        n = re.search(r'(?:to|à)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)', t)
        return f'Discharge to {n.group(1)}' if n else 'Granting of discharge'

    if re.search(r'Renewal|Renouvellement', t, re.I):
        c = re.search(r'(?:of|de)\s+([A-Z][A-Za-z\s\.]+S\.A\.)', t)
        return f'Renewal of auditor {c.group(1)}' if c else 'Renewal of auditor'

    if re.search(r'resignation|démission', t, re.I):
        n = re.search(r'(?:Mr\.|M\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', t)
        return f'Resignation of {n.group(1)}' if n else 'Resignation'

    if re.search(r'Appointment|Nomination', t, re.I):
        n = re.search(r'(?:Mr\.|M\.)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', t)
        return f'Appointment of {n.group(1)}' if n else 'Appointment'

    return t[:100] + '...' if len(t) > 100 else t


def extract_isin(text):
    """Extrait l'ISIN du texte avec plusieurs patterns"""
    isin_patterns = [
        r'ISIN\s*[:\s]\s*([A-Z]{2}[A-Z0-9]{9}[0-9])',
        r'\b(LU[0-9]{10})\b',
        r'\b(XS[0-9]{10})\b',
        r'\b(FR[0-9]{10})\b',
        r'\b(DE[0-9]{10})\b',
        r'\b(BE[0-9]{10})\b',
        r'\b([A-Z]{2}[A-Z0-9]{9}[0-9])\b'
    ]
    for pattern in isin_patterns:
        match = re.search(pattern, text, re.I)
        if match:
            return match.group(1).upper()
    return ""


def extract_company_name(text):
    """Extrait le nom de l'émetteur"""
    # Patterns spécifiques
    patterns = [
        r'\*\*([A-Z][A-Za-z\s]+(?:SE|SA|S\.A\.))\*\*',
        r'^([A-Z][A-Za-z\s]+(?:SE|SA))\s*$',
        r'convened by ([A-Z][A-Za-z\s,\.]+(?:SE|SA|Ltd|GmbH|S\.A\.))'
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.M | re.I)
        if match:
            return match.group(1).strip().upper()

    # Fallback sur les premières lignes
    lines = text.split('\n')[:10]
    for line in lines:
        line = line.strip()
        if 5 < len(line) < 100 and any(keyword in line for keyword in ['SE', 'SA', 'S.A.', 'LTD', 'CORP', 'AG']):
            clean_line = re.sub(r'[^a-zA-Z0-9\s\.\-&]', '', line)
            return clean_line.strip().upper()
    return ""


def parse_date_with_month_name(day, month_name, year):
    """Convertit une date avec nom de mois en YYYY-MM-DD"""
    months_en = ['january','february','march','april','may','june','july','august','september','october','november','december']
    months_fr = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']

    m_name = month_name.lower()
    try:
        if m_name in months_en:
            m = months_en.index(m_name) + 1
        elif m_name in months_fr:
            m = months_fr.index(m_name) + 1
        else:
            return None
        return f"{year}-{str(m).zfill(2)}-{str(day).zfill(2)}"
    except:
        return None

def extract_dates(text):
    """Extrait les dates importantes avec support FR/EN"""
    dates = {}

    # Pattern générique pour les dates avec noms de mois
    month_pattern = r'(\d{1,2})\s+(janvier|février|mars|avril|mai|juin|juillet|août|septembre|octobre|novembre|décembre|january|february|march|april|may|june|july|august|september|october|november|december)\s+(\d{4})'

    # Meeting date
    mtg_match = re.search(r'(?:held on|se tiendra le|réunion le)\s+' + month_pattern, text, re.I)
    if mtg_match:
        d = parse_date_with_month_name(mtg_match.group(1), mtg_match.group(2), mtg_match.group(3))
        if d: dates['meeting_date'] = d

    # Record date
    rec_match = re.search(r'(?:record date|date d\'enregistrement).*?' + month_pattern, text, re.I)
    if not rec_match:
        rec_match = re.search(month_pattern + r'.*?\(midnight\)', text, re.I)
    if rec_match:
        d = parse_date_with_month_name(rec_match.group(1), rec_match.group(2), rec_match.group(3))
        if d: dates['record_date'] = d

    # Deadline
    dl_match = re.search(r'(?:deadline|date limite|au plus tard).*?' + month_pattern, text, re.I)
    if dl_match:
        d = parse_date_with_month_name(dl_match.group(1), dl_match.group(2), dl_match.group(3))
        if d: dates['deadline'] = d

    # Pattern numérique DD/MM/YYYY
    numeric_date = r'(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})'
    if 'meeting_date' not in dates:
        m = re.search(r'(?:meeting|assemblée|réunion).*?(' + numeric_date + r')', text, re.I)
        if m:
            # On suppose DD/MM/YYYY pour l'Europe
            dates['meeting_date'] = f"{m.group(4)}-{m.group(3).zfill(2)}-{m.group(2).zfill(2)}"

    return dates


def extract_address(text):
    """Extrait l'adresse de réunion"""
    addr_match = re.search(r'at\s+(\d+[A-Z]?),\s+([A-Za-z\s\.]+(?:Avenue|Street|Route|Rue|Boulevard)[^,]*),\s+(L-?\d{4})', text, re.I)
    if addr_match:
        return {
            'building_number': addr_match.group(1),
            'street': addr_match.group(2).strip().upper(),
            'post_code': addr_match.group(3)
        }
    return {}


def extract_url(text):
    """Extrait l'URL de documentation"""
    url_match = re.search(r'(https?://[^\s<>"]+)', text, re.I)
    return url_match.group(1) if url_match else ""


def extract_resolutions(text):
    """Extrait les résolutions de l'agenda"""
    resolutions = []

    # Tentative de trouver le début de l'agenda
    agenda_start = re.search(r'AGENDA FOR THE ANNUAL|^I\.\s*AGENDA|AGENDA|ORDER OF BUSINESS|ORDRE DU JOUR', text, re.I | re.M)
    if agenda_start:
        content = text[agenda_start.end():]
        # Tentative de trouver la fin
        agenda_end = re.search(r'^II\.|^PARTICIPATION|^III\.|^IV\.|^VOTING|^PROXY', content, re.I | re.M)
        if agenda_end:
            content = content[:agenda_end.start()]

        # Extraction par numérotation
        matches = re.finditer(r'^\s*(\d{1,2})[\.\)]\s+(.+)', content, re.M)
        for match in matches:
            num = match.group(1)
            raw_text = match.group(2).strip()
            resolutions.append({
                'id': num,
                'text': resume(raw_text),
                'info_only': True if re.search(r'^Presentation|^Présentation', raw_text, re.I) else False
            })

    if not resolutions:
        # Fallback patterns
        patterns = [
            r'(?:Résolution|Resolution)\s+(?:n°|No\.|#)?\s*(\d+)\s*[:–-]\s*(.+?)(?=(?:Résolution|Resolution)|\n\n|$)',
        ]
        for pattern in patterns:
            matches = re.finditer(pattern, text, re.I | re.S)
            for match in matches:
                resolutions.append({
                    'id': match.group(1),
                    'text': resume(match.group(2)),
                    'info_only': False
                })

    return resolutions if resolutions else [{'id': '1', 'text': 'À extraire manuellement', 'info_only': False}]


def auto_extract_data(text):
    """Extraction automatique de toutes les données avec valeurs par défaut"""
    data = {
        'isin': extract_isin(text),
        'company_name': extract_company_name(text),
        'url': extract_url(text),
        'meeting_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
        'record_date': (datetime.now() + timedelta(days=14)).strftime('%Y-%m-%d'),
        'deadline': (datetime.now() + timedelta(days=28)).strftime('%Y-%m-%d'),
        'holding_balance': '0',
        'street': '',
        'building_number': '',
        'post_code': '',
        'town': 'LUXEMBOURG'
    }

    # Dates extraites
    extracted_dates = extract_dates(text)
    data.update({k: v for k, v in extracted_dates.items() if v})

    # Adresse
    addr = extract_address(text)
    data.update({k: v for k, v in addr.items() if v})

    # Résolutions
    data['resolutions_list'] = extract_resolutions(text)

    # Balance (Holding)
    bal_match = re.search(r'([0-9,]+)\s*(?:shares|actions|obligations)', text, re.I)
    if bal_match:
        data['holding_balance'] = bal_match.group(1).replace(',', '')

    return data


def generate_seev001_xml(data):
    """Génère le XML SEEV.001.001.12 complet"""

    # Namespace
    ns = "urn:iso:std:iso:20022:tech:xsd:seev.001.001.12"
    ET.register_namespace('', ns)

    root = ET.Element('Document', xmlns=ns)
    mtg_ntfctn = ET.SubElement(root, 'MtgNtfctn')

    # NtfctnGnlInf
    ntfctn_gnl_inf = ET.SubElement(mtg_ntfctn, 'NtfctnGnlInf')
    ET.SubElement(ntfctn_gnl_inf, 'NtfctnTp').text = 'NEWM'
    ntfctn_sts = ET.SubElement(ntfctn_gnl_inf, 'NtfctnSts')
    ET.SubElement(ntfctn_sts, 'EvtCmpltnsSts').text = 'COMP'
    ET.SubElement(ntfctn_sts, 'EvtConfSts').text = 'CONF'

    # Mtg
    mtg = ET.SubElement(mtg_ntfctn, 'Mtg')
    ET.SubElement(mtg, 'MtgId').text = data.get('notification_id', 'GMET000000000')
    ET.SubElement(mtg, 'IssrMtgId').text = data.get('issuer_meeting_id', data.get('notification_id', 'GMET000000000'))
    ET.SubElement(mtg, 'Tp').text = 'GMET'
    clssfctn = ET.SubElement(mtg, 'Clssfctn')
    ET.SubElement(clssfctn, 'Cd').text = 'ISSU'

    anncmnt_dt = ET.SubElement(mtg, 'AnncmntDt')
    ann_val = data.get('announcement_date', datetime.now().strftime('%Y-%m-%d'))
    ET.SubElement(anncmnt_dt, 'DtTm').text = f"{ann_val}T09:00:00Z"

    # Participation Methods
    dl_val = data.get('deadline', '2026-01-01')
    for method in ['PHYS', 'PRXY', 'EVOT']:
        prtcptn = ET.SubElement(mtg, 'Prtcptn')
        prtcptn_mtd = ET.SubElement(prtcptn, 'PrtcptnMtd')
        ET.SubElement(prtcptn_mtd, 'Cd').text = method
        issr_ddln = ET.SubElement(prtcptn, 'IssrDdlnForVtng')
        dt_or_dt_tm = ET.SubElement(issr_ddln, 'DtOrDtTm')
        ET.SubElement(dt_or_dt_tm, 'DtTm').text = f"{dl_val}T17:00:00Z"
        if method == 'PHYS':
            ET.SubElement(prtcptn, 'SpprtdByAcctSvcr').text = 'false'

    # Attendance
    attndnc = ET.SubElement(mtg, 'Attndnc')
    ET.SubElement(attndnc, 'ConfInf').text = data.get('attendance_info', "To attend to the meeting the shareholder need to provide : ID and proof holding of shares")
    conf_mkt_ddln = ET.SubElement(attndnc, 'ConfMktDdln')
    dt_or_dt_tm = ET.SubElement(conf_mkt_ddln, 'DtOrDtTm')
    conf_dl_val = data.get('confirmation_deadline', data.get('deadline', '2026-01-01'))
    ET.SubElement(dt_or_dt_tm, 'DtTm').text = f"{conf_dl_val}T17:00:00Z"

    if data.get('url'):
        ET.SubElement(mtg, 'AddtlDcmnttnURLAdr').text = data.get('url')

    sbped = ET.SubElement(mtg, 'SctiesBlckgPrdEndDt')
    dt_cd = ET.SubElement(sbped, 'DtCd')
    ET.SubElement(dt_cd, 'Cd').text = 'MEET'

    entitlmnt = ET.SubElement(mtg, 'EntitlmntFxgDt')
    dt_elem = ET.SubElement(entitlmnt, 'Dt')
    rec_val = data.get('record_date', '2026-01-01')
    ET.SubElement(dt_elem, 'Dt').text = rec_val
    ET.SubElement(entitlmnt, 'DtMd').text = 'EODY'

    # MtgDtls
    mtg_dtls = ET.SubElement(mtg_ntfctn, 'MtgDtls')
    dt_and_tm = ET.SubElement(mtg_dtls, 'DtAndTm')
    dt_or_dt_tm = ET.SubElement(dt_and_tm, 'DtOrDtTm')
    mtg_dt_val = data.get('meeting_date', '2026-01-01')
    ET.SubElement(dt_or_dt_tm, 'DtTm').text = f"{mtg_dt_val}T10:00:00Z"

    lctn = ET.SubElement(mtg_dtls, 'Lctn')
    adr = ET.SubElement(lctn, 'Adr')
    if data.get('street'): ET.SubElement(adr, 'StrtNm').text = data.get('street')
    if data.get('building_number'): ET.SubElement(adr, 'BldgNb').text = data.get('building_number')
    if data.get('post_code'): ET.SubElement(adr, 'PstCd').text = data.get('post_code')
    ET.SubElement(adr, 'TwnNm').text = data.get('town', 'LUXEMBOURG')
    ET.SubElement(adr, 'Ctry').text = 'LU'

    # Issr
    issr = ET.SubElement(mtg_ntfctn, 'Issr')
    issr_id = ET.SubElement(issr, 'Id')
    nm_and_adr = ET.SubElement(issr_id, 'NmAndAdr')
    ET.SubElement(nm_and_adr, 'Nm').text = data.get('company_name', 'ISSUER')

    # IssrAgt
    issr_agt = ET.SubElement(mtg_ntfctn, 'IssrAgt')
    agt_id = ET.SubElement(issr_agt, 'Id')
    ET.SubElement(agt_id, 'AnyBIC').text = data.get('bic_code', 'XXXXXXXXXXX')
    ET.SubElement(issr_agt, 'Role').text = 'PRIN'

    # Scty
    scty = ET.SubElement(mtg_ntfctn, 'Scty')
    fin_instrm_id = ET.SubElement(scty, 'FinInstrmId')
    ET.SubElement(fin_instrm_id, 'ISIN').text = data.get('isin', 'LU0000000000')
    pos = ET.SubElement(scty, 'Pos')
    ET.SubElement(pos, 'AcctId').text = data.get('account_id', '000000000')
    hldg_bal = ET.SubElement(pos, 'HldgBal')
    bal = ET.SubElement(hldg_bal, 'Bal')
    ET.SubElement(bal, 'ShrtLngPos').text = 'LONG'
    qty = ET.SubElement(bal, 'Qty')
    ET.SubElement(qty, 'Unit').text = str(data.get('holding_balance', '0')) + '.'
    ET.SubElement(hldg_bal, 'BalTp').text = 'ELIG'

    # Resolutions
    for res in data.get('resolutions_data', []):
        res_elem = ET.SubElement(mtg_ntfctn, 'Rsltn')
        ET.SubElement(res_elem, 'IssrLabl').text = str(res['id'])
        desc = ET.SubElement(res_elem, 'Desc')
        ET.SubElement(desc, 'Lang').text = 'en'
        ET.SubElement(desc, 'Titl').text = res['text']
        ET.SubElement(res_elem, 'ForInfOnly').text = 'true' if res['info_only'] else 'false'
        ET.SubElement(res_elem, 'Sts').text = 'ACTV'

        if not res['info_only']:
            for vtp in ['CFOR', 'CAGS', 'ABST']:
                vit = ET.SubElement(res_elem, 'VoteInstrTp')
                vitc = ET.SubElement(vit, 'VoteInstrTpCd')
                ET.SubElement(vitc, 'Tp').text = vtp

    # Vote
    vote = ET.SubElement(mtg_ntfctn, 'Vote')
    ET.SubElement(vote, 'PrtlVoteAllwd').text = 'false'
    ET.SubElement(vote, 'SpltVoteAllwd').text = 'true'
    mthds = ET.SubElement(vote, 'VoteMthds')
    mail = ET.SubElement(mthds, 'VoteByMail')
    for line in data.get('vote_address', ["Institution Name", "Address Line 1", "Address Line 2"]):
        ET.SubElement(mail, 'EmailAdr').text = line
    if data.get('vote_tel'):
        ET.SubElement(mthds, 'VoteByTel').text = data.get('vote_tel')

    rvc = ET.SubElement(vote, 'RvcbltyMktDdln')
    dt_or_dt_tm = ET.SubElement(rvc, 'DtOrDtTm')
    ET.SubElement(dt_or_dt_tm, 'DtTm').text = f"{dl_val}T17:00:00Z"
    ET.SubElement(vote, 'BnfclOwnrDsclsr').text = 'true'

    # AddtlInf
    add_inf = ET.SubElement(mtg_ntfctn, 'AddtlInf')
    if data.get('contact_info'):
        dsclmr1 = ET.SubElement(add_inf, 'Dsclmr')
        ET.SubElement(dsclmr1, 'Lang').text = 'en'
        ET.SubElement(dsclmr1, 'AddtlInf').text = data.get('contact_info')

    dsclmr2 = ET.SubElement(add_inf, 'Dsclmr')
    ET.SubElement(dsclmr2, 'Lang').text = 'en'
    ET.SubElement(dsclmr2, 'AddtlInf').text = data.get('general_info', "The noteholder can vote by proxy, voting form, physically during the meeting or by electronic instruction.")

    # Formatting XML
    xml_bytes = ET.tostring(root, encoding='utf-8')
    xml_str = minidom.parseString(xml_bytes).toprettyxml(indent="  ")
    return xml_str


# Interface principale
st.markdown("---")

# Zone de téléchargement
uploaded_file = st.file_uploader(
    "📎 Glissez-déposez votre convocation (PDF, Word, ou TXT)",
    type=['pdf', 'docx', 'txt'],
    help="Formats acceptés: PDF, DOCX, TXT"
)

if uploaded_file:
    st.success(f"✅ Fichier chargé: {uploaded_file.name}")

    # Bouton d'extraction
    if st.button("🔍 Extraire les données", type="primary"):
        with st.spinner("Extraction en cours..."):
            # Extraire le texte
            text = extract_text_from_file(uploaded_file)

            if text:
                # Afficher un aperçu du texte
                with st.expander("📄 Aperçu du texte extrait"):
                    st.text_area("Texte brut", text[:2000], height=200)

                # Extraction automatique
                st.session_state.extracted_data = auto_extract_data(text)
                st.session_state.file_processed = True
                st.rerun()

# Affichage et édition des données extraites
if st.session_state.file_processed:
    st.markdown("---")
    st.subheader("✏️ Données extraites - Vérifiez et modifiez si nécessaire")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Informations de base**")
        notification_id = st.text_input(
            "Meeting ID",
            value=st.session_state.extracted_data.get('notification_id', f"GMET{datetime.now().strftime('%Y%m%d%H%M')}")
        )

        isin = st.text_input(
            "ISIN",
            value=st.session_state.extracted_data.get('isin', ''),
            max_chars=12
        )

        company_name = st.text_input(
            "Nom de l'émetteur",
            value=st.session_state.extracted_data.get('company_name', '')
        )

        holding_balance = st.text_input(
            "Holding Balance",
            value=st.session_state.extracted_data.get('holding_balance', '0')
        )

        url = st.text_input(
            "URL Documentation",
            value=st.session_state.extracted_data.get('url', '')
        )

    with col2:
        st.markdown("**Dates**")
        announcement_date = st.date_input(
            "Date d'annonce",
            value=datetime.now()
        )

        # Helper to safely parse dates from session state
        def safe_parse_date(key, default_days=0):
            val = st.session_state.extracted_data.get(key)
            try:
                return datetime.strptime(val, '%Y-%m-%d')
            except:
                return datetime.now() + timedelta(days=default_days)

        meeting_date = st.date_input(
            "Date de l'assemblée",
            value=safe_parse_date('meeting_date', 30)
        )

        record_date = st.date_input(
            "Record Date",
            value=safe_parse_date('record_date', 14)
        )

        deadline = st.date_input(
            "Voting Deadline",
            value=safe_parse_date('deadline', 28)
        )

        confirmation_deadline = st.date_input(
            "Confirmation Deadline",
            value=safe_parse_date('deadline', 28)
        )

    st.markdown("**Lieu de réunion**")
    c3, c4, c5, c6 = st.columns([2, 1, 1, 2])
    with c3:
        street = st.text_input("Rue", value=st.session_state.extracted_data.get('street', ''))
    with c4:
        bldg_nb = st.text_input("N°", value=st.session_state.extracted_data.get('building_number', ''))
    with c5:
        post_code = st.text_input("Code Postal", value=st.session_state.extracted_data.get('post_code', ''))
    with c6:
        town = st.text_input("Ville", value=st.session_state.extracted_data.get('town', 'LUXEMBOURG'))

    st.markdown("**Institution & Contact**")
    exp_inst = st.expander("Configuration de l'Institution", expanded=False)
    with exp_inst:
        bic_code = st.text_input("BIC Code", value="XXXXXXXXXXX")
        account_id = st.text_input("Account ID", value="000000000")
        vote_address = st.text_area("Adresse de vote (une ligne par entrée)", value="Institution Name\nAddress Line 1\nAddress Line 2")
        vote_tel = st.text_input("Téléphone de vote", value="")
        contact_info = st.text_area("Contact Info (Additional Info)", value="CONTACT:\nemail: contact@institution.com")
        attendance_info = st.text_area("Information de participation", value="To attend to the meeting the shareholder need to provide : ID and proof holding of shares")
        general_info = st.text_area("Informations générales", value="The noteholder can vote by proxy, voting form, physically during the meeting or by electronic instruction.")

    st.markdown("**Résolutions**")

    # Gestion des résolutions
    res_list = st.session_state.extracted_data.get('resolutions_list', [])
    updated_resolutions = []

    for i, res in enumerate(res_list):
        with st.expander(f"Résolution {res['id']}: {res['text'][:50]}...", expanded=True):
            r_col1, r_col2 = st.columns([4, 1])
            with r_col1:
                r_text = st.text_area(f"Texte Rés. {res['id']}", value=res['text'], key=f"res_text_{i}")
            with r_col2:
                r_info = st.checkbox("Info seule", value=res['info_only'], key=f"res_info_{i}")
            updated_resolutions.append({'id': res['id'], 'text': r_text, 'info_only': r_info})

    if st.button("➕ Ajouter une résolution"):
        new_id = str(len(res_list) + 1)
        st.session_state.extracted_data['resolutions_list'].append({'id': new_id, 'text': '', 'info_only': False})
        st.rerun()

    # Préparer les données finales
    final_data = {
        'notification_id': notification_id,
        'isin': isin,
        'company_name': company_name,
        'holding_balance': holding_balance,
        'url': url,
        'announcement_date': announcement_date.strftime('%Y-%m-%d'),
        'meeting_date': meeting_date.strftime('%Y-%m-%d'),
        'record_date': record_date.strftime('%Y-%m-%d'),
        'deadline': deadline.strftime('%Y-%m-%d'),
        'confirmation_deadline': confirmation_deadline.strftime('%Y-%m-%d'),
        'street': street,
        'building_number': bldg_nb,
        'post_code': post_code,
        'town': town,
        'bic_code': bic_code,
        'account_id': account_id,
        'vote_address': [line.strip() for line in vote_address.split('\n') if line.strip()],
        'vote_tel': vote_tel,
        'contact_info': contact_info,
        'attendance_info': attendance_info,
        'general_info': general_info,
        'resolutions_data': updated_resolutions
    }

    # Génération du XML
    st.markdown("---")
    if st.button("🚀 Générer le message SEEV.001", type="primary"):
        xml_output = generate_seev001_xml(final_data)

        st.success("✅ Message SEEV.001 généré avec succès!")

        # Affichage du XML
        st.code(xml_output, language='xml')

        # Téléchargement
        st.download_button(
            label="📥 Télécharger le XML",
            data=xml_output,
            file_name=f"SEEV001_{final_data['isin']}_{datetime.now().strftime('%Y%m%d')}.xml",
            mime="application/xml"
        )

# Sidebar avec informations
with st.sidebar:
    st.markdown("### 📋 Guide d'utilisation")
    st.markdown("""
    1. **Téléchargez** votre convocation
    2. **Extrayez** les données automatiquement
    3. **Vérifiez** et modifiez si nécessaire
    4. **Générez** le message SEEV.001
    5. **Téléchargez** le fichier XML
    """)

    st.markdown("---")
    st.markdown("### ℹ️ Informations")
    st.info("Application de génération automatique de messages Swift SEEV.001.001.12 pour convocations d'assemblées")

    st.markdown("**Formats supportés:**")
    st.markdown("- PDF (.pdf)")
    st.markdown("- Word (.docx)")
    st.markdown("- Texte (.txt)")
