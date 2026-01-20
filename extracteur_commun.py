import re

MO_EN = ['january','february','march','april','may','june','july','august','september','october','november','december']
MO_FR = ['janvier','février','mars','avril','mai','juin','juillet','août','septembre','octobre','novembre','décembre']

def extraire_nom_societe(texte):
    issMatch = re.search(r'\*\*([A-Z][A-Za-z\s]+(?:SE|SA|S\.A\.))\*\*', texte)
    if not issMatch:
        issMatch = re.search(r'^([A-Z][A-Za-z\s]+(?:SE|SA))\s*$', texte, re.M)
    if not issMatch:
        issMatch = re.search(r'convened by ([A-Z][A-Za-z\s,\.]+(?:SE|SA|Ltd|GmbH))', texte, re.I)

    if issMatch:
        return issMatch.group(1).strip().upper()
    return "ISSUER"

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
            if len(val) == 12:
                return val
    return None

def extraire_rcs(texte):
    m = re.search(r'R\.?C\.?S\.?\s*([A-Z0-9\s-]+)', texte, re.I)
    if m:
        return m.group(1).strip()
    return None

def parse_date(day, month_str, year):
    mo_str = month_str.lower()
    if mo_str in MO_EN:
        mo = str(MO_EN.index(mo_str) + 1).zfill(2)
    elif mo_str in MO_FR:
        mo = str(MO_FR.index(mo_str) + 1).zfill(2)
    else:
        mo = "01"
    return f"{year}-{mo}-{day.zfill(2)}"

def extraire_dates(texte):
    res = {}
    months_regex = '|'.join(MO_EN + MO_FR)

    # Meeting date
    mtgMatch = re.search(rf'held on (\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+at\s+(\d{{1,2}}):(\d{{2}})', texte, re.I)
    if mtgMatch:
        res['meeting_date'] = parse_date(mtgMatch.group(1), mtgMatch.group(2), mtgMatch.group(3))
        res['meeting_time'] = f"{mtgMatch.group(4).zfill(2)}:{mtgMatch.group(5)}"

    # Record date
    recMatch = re.search(rf'(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+\(midnight\)', texte, re.I)
    if not recMatch:
        recMatch = re.search(rf'record date\s*[:\s]\s*(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})', texte, re.I)
    if recMatch:
        res['record_date'] = parse_date(recMatch.group(1), recMatch.group(2), recMatch.group(3))

    # Deadline
    dlMatch = re.search(rf'(\d{{1,2}})\s+({months_regex})\s+(\d{{4}})\s+at\s+(\d{{1,2}}):(\d{{2}})\s*p\.?m', texte, re.I)
    if dlMatch:
        res['deadline'] = parse_date(dlMatch.group(1), dlMatch.group(2), dlMatch.group(3)) + f"T{str(int(dlMatch.group(4)) + 12).zfill(2)}:{dlMatch.group(5)}"

    return res

def extraire_heure(texte):
    m = re.search(r'at\s+(\d{1,2}):(\d{2})', texte, re.I)
    if m:
        return f"{m.group(1).zfill(2)}:{m.group(2)}"
    return None

def extraire_lieu(texte):
    addrMatch = re.search(r'at\s+(\d+[A-Z]?),\s+([A-Za-z\s\.]+(?:Avenue|Street|Route|Rue|Boulevard)[^,]*),\s+(L-?\d{4})', texte, re.I)
    if addrMatch:
        return f"{addrMatch.group(1)}, {addrMatch.group(2).strip()}, {addrMatch.group(3)} LUXEMBOURG"
    return None

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
            inAgenda = True
            continue
        if not inAgenda: continue
        if re.search(r'^II\.|^PARTICIPATION|^III\.|^IV\.|^VOTING|^PROXY|^VOTE', line, re.I):
            break

        if re.search(rf'^\d{{1,2}}\s+({months_regex})\s+\d{{4}}', line, re.I):
            continue

        resMatch = re.match(r'^\s*(\d{1,2})[\.\)]\s+(.+)', line)
        if resMatch:
            if currentNum and currentText:
                resols.append({'n': currentNum, 't': resume(currentText), 'f': bool(re.search(r'^Presentation', currentText, re.I))})
            currentNum = resMatch.group(1)
            currentText = resMatch.group(2)
        elif currentNum and len(line) > 5 and not re.match(r'^[A-Z]{3,}$', line):
            currentText += ' ' + line

    if currentNum and currentText:
        resols.append({'n': currentNum, 't': resume(currentText), 'f': bool(re.search(r'^Presentation', currentText, re.I))})

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
    if re.search(r'no quorum|without quorum|sans quorum', texte, re.I):
        return "No quorum required"
    return None
