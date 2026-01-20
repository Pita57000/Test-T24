import re

def extraire_donnees_bondholder(texte):
    res = {}
    bond_type = re.search(r'(Notes|Bonds|Obligations)\s+due\s+(\d{4})', texte, re.I)
    if bond_type:
        res['bond_type'] = bond_type.group(0)

    res['clearing_systems'] = []
    if re.search(r'Euroclear', texte, re.I): res['clearing_systems'].append('Euroclear')
    if re.search(r'Clearstream', texte, re.I): res['clearing_systems'].append('Clearstream')

    if re.search(r'deemed consent', texte, re.I):
        res['deemed_consent'] = True

    res['meeting_calls'] = re.findall(r'(\d+)(?:st|nd|rd|th)\s+meeting', texte, re.I)

    return res
