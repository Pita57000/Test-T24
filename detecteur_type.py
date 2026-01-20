import re

def detecter_type_event(texte):
    """Détecte si c'est une AGM, EGM ou BONDHOLDER meeting"""
    if re.search(r'bondholder|noteholder|obligataire', texte, re.I):
        return 'BONDHOLDER'
    if re.search(r'extraordinary|extraordinaire|EGM', texte, re.I):
        return 'EGM'
    return 'AGM'

def detecter_document_type(texte):
    """Détecte le type de document"""
    if re.search(r'notice|avis|convocation', texte, re.I):
        return 'Notice of Meeting'
    return 'Document'

def detecter_langue(texte):
    """Détecte la langue (FR ou EN)"""
    if re.search(r'\bthe\b|\band\b|\bof\b', texte, re.I):
        return 'EN'
    if re.search(r'\ble\b|\bla\b|\bet\b', texte, re.I):
        return 'FR'
    return 'EN'
