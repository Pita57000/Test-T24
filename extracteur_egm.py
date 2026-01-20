import re

def extraire_donnees_egm(texte):
    res = {}
    purposes = []
    if re.search(r'amendment of the articles', texte, re.I):
        purposes.append("Articles Amendment")
    if re.search(r'capital increase', texte, re.I):
        purposes.append("Capital Increase")
    res['egm_purpose'] = purposes

    if re.search(r'liquidation|winding up', texte, re.I):
        res['liquidation'] = True
    return res
