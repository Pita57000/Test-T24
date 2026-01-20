#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur SEEV.001 Universel
Gère AGM, EGM et Bondholder Meetings
"""

import os
import sys
from datetime import datetime

# Import des modules
import detecteur_type
import extracteur_commun
import extracteur_agm
import extracteur_egm
import extracteur_bondholder
import generateur_xml


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
    meeting_type = detecteur_type.detecter_type_event(texte)
    document_type = detecteur_type.detecter_document_type(texte)
    langue = detecteur_type.detecter_langue(texte)

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

    donnees['company_name'] = extracteur_commun.extraire_nom_societe(texte)
    print(f"  ✅ Société: {donnees['company_name']}")

    donnees['isin'] = extracteur_commun.extraire_isin(texte)
    if donnees['isin']:
        print(f"  ✅ ISIN: {donnees['isin']}")

    donnees['rcs'] = extracteur_commun.extraire_rcs(texte)
    if donnees['rcs']:
        print(f"  ✅ RCS: {donnees['rcs']}")

    # Dates
    dates = extracteur_commun.extraire_dates(texte)
    donnees.update(dates)
    if dates.get('meeting_date'):
        print(f"  ✅ Date meeting: {dates['meeting_date']}")
    if dates.get('record_date'):
        print(f"  ✅ Record date: {dates['record_date']}")
    if dates.get('deadline'):
        print(f"  ✅ Deadline: {dates['deadline']}")

    # Heure
    donnees['meeting_time'] = extracteur_commun.extraire_heure(texte)
    if donnees['meeting_time']:
        print(f"  ✅ Heure: {donnees['meeting_time']}")

    # Lieu
    donnees['location'] = extracteur_commun.extraire_lieu(texte)
    if donnees['location']:
        print(f"  ✅ Lieu: {donnees['location'][:50]}...")

    # Contact
    donnees['contact'] = extracteur_commun.extraire_contact(texte)
    if donnees['contact'].get('email'):
        print(f"  ✅ Email: {donnees['contact']['email']}")

    # Résolutions
    donnees['resolutions'] = extracteur_commun.extraire_resolutions(texte)
    if donnees['resolutions']:
        print(f"  ✅ Résolutions: {len(donnees['resolutions'])} trouvée(s)")

    # Quorum
    donnees['quorum'] = extracteur_commun.extraire_quorum(texte)

    print()

    # 3. Extraction spécifique selon le type
    if meeting_type == 'AGM':
        print("📈 Extraction données AGM...")
        donnees_agm = extracteur_agm.extraire_donnees_agm(texte)
        donnees.update(donnees_agm)

        if donnees_agm.get('dividend'):
            print(f"  ✅ Dividende: {donnees_agm['dividend']}")
        if donnees_agm.get('fiscal_year_end'):
            print(f"  ✅ Exercice fiscal: {donnees_agm['fiscal_year_end']}")
        if donnees_agm.get('auditor'):
            print(f"  ✅ Auditeur: {donnees_agm['auditor'][:50]}...")

    elif meeting_type == 'EGM':
        print("⚡ Extraction données EGM...")
        donnees_egm = extracteur_egm.extraire_donnees_egm(texte)
        donnees.update(donnees_egm)

        if donnees_egm.get('egm_purpose'):
            purposes = ', '.join(donnees_egm['egm_purpose'])
            print(f"  ✅ Objectif: {purposes}")
        if donnees_egm.get('liquidation'):
            print(f"  ⚠️  Liquidation détectée")

    elif meeting_type == 'BONDHOLDER':
        print("💰 Extraction données Bondholder...")
        donnees_bond = extracteur_bondholder.extraire_donnees_bondholder(texte)
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

    chemin_fichier = input("Chemin: ").strip().strip('"')

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
    reponse = input("Réponse: ").strip().upper()

    if reponse != 'O':
        print("❌ Génération annulée.")
        return

    print()
    print("🚀 Génération du XML SEEV.001...")

    # 6. Générer le XML
    try:
        xml_content = generateur_xml.generer_seev001(donnees, meeting_type)

        # 7. Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        company_short = donnees.get('company_name', 'Company')[:20].replace(' ', '_')
        nom_fichier = f'SEEV001_{company_short}_{timestamp}.xml'

        with open(nom_fichier, 'w', encoding='utf-8') as f:
            f.write(xml_content)

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
        input("\nAppuyez sur Entrée pour quitter...")
