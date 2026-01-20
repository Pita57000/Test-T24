import re

def extraire_donnees_agm(texte):
    res = {}
    div = re.search(r'dividend of EUR\s*([0-9\.]+)', texte, re.I)
    if div:
        res['dividend'] = div.group(1)

    fy = re.search(r'fiscal year ended ([^,\.]+)', texte, re.I)
    if fy:
        res['fiscal_year_end'] = fy.group(1).strip()

    auditor = re.search(r'auditor\s+([A-Z][A-Za-z\s\.]+S\.A\.)', texte, re.I)
    if auditor:
        res['auditor'] = auditor.group(1).strip()

    return res
