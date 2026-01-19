#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Generateur Swift SEEV.001.001.12
Usage: python seev001.py
"""

import re
import random
from datetime import datetime, timedelta


def extraire_isin(txt):
    patterns = [
        r"ISIN\s*:?\s*([A-Z]{2}[A-Z0-9]{9}[0-9])",
        r"\b(LU[0-9]{10})\b",
        r"\b(XS[0-9]{10})\b",
        r"\b(FR[0-9]{10})\b",
        r"\b(DE[0-9]{10})\b",
    ]
    for p in patterns:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            return m.group(1).upper().replace(" ", "")
    return ""


def extraire_emetteur(txt):
    patterns = [
        r"convened by ([A-Z][A-Z\s,.]+(?:SE|SA|S\.A\.|LTD|GMBH|INC|CORP))",
        r"Meeting of ([A-Z][A-Z\s,.]+(?:SE|SA|S\.A\.|LTD|GMBH|INC|CORP))",
        r"\b([A-Z][A-Z\s]+(?:SE|SA|S\.A\.))\b",
    ]
    for p in patterns:
        m = re.search(p, txt, re.MULTILINE | re.IGNORECASE)
        if m:
            return m.group(1).strip().upper()
    return ""


def extraire_balance(txt):
    patterns = [
        r"([0-9,]+)\s*shares",
        r"([0-9,]+)\s*(?:shares|actions|obligations)",
    ]
    for p in patterns:
        m = re.search(p, txt, re.IGNORECASE)
        if m:
            return m.group(1).replace(",", "")
    return "0"


def extraire_dates(txt):
    mois = {
        "january": "01", "february": "02", "march": "03",
        "april": "04", "may": "05", "june": "06",
        "july": "07", "august": "08", "september": "09",
        "october": "10", "november": "11", "december": "12"
    }

    dates = {"mtg": "", "rec": "", "vote": ""}

    m = re.search(
        r"held on (\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+at\s+(\d{1,2}):(\d{2})",
        txt, re.IGNORECASE
    )
    if m:
        mo = mois.get(m.group(2).lower(), "01")
        dates["mtg"] = f"{m.group(3)}-{mo}-{m.group(1).zfill(2)}T{m.group(4).zfill(2)}:{m.group(5)}:00Z"

    m = re.search(
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+\(midnight\)",
        txt, re.IGNORECASE
    )
    if m:
        mo = mois.get(m.group(2).lower(), "01")
        dates["rec"] = f"{m.group(3)}-{mo}-{m.group(1).zfill(2)}"

    m = re.search(
        r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})\s+at\s+(\d{1,2}):(\d{2})\s+p\.?m",
        txt, re.IGNORECASE
    )
    if m:
        mo = mois.get(m.group(2).lower(), "01")
        h = int(m.group(4)) + 12
        dates["vote"] = f"{m.group(3)}-{mo}-{m.group(1).zfill(2)}T{str(h).zfill(2)}:{m.group(5)}:00Z"

    return dates


def extraire_adresse(txt):
    m = re.search(
        r"at\s+(\d+[A-Z]?),\s+([^,]*?(?:Avenue|Street|Route|Rue|Boulevard|Place|Quai)[^,]*),\s+(L-?\d{4})",
        txt, re.IGNORECASE
    )
    if m:
        return {"bn": m.group(1), "st": m.group(2).strip().upper(), "pc": m.group(3)}
    return {"bn": "", "st": "", "pc": ""}


def extraire_url(txt):
    m = re.search(r'(https?://[^\s<>"’]+)', txt)
    return m.group(1) if m else ""


def resume_resolution(t):
    t = t.strip()
    if re.match(r"^Presentation of", t, re.IGNORECASE):
        return "Presentation of reports"

    if re.search(r"Approval of the annual", t, re.IGNORECASE):
        y = re.search(r"(\d{4})", t)
        return f"Approval of annual accounts {y.group(1) if y else ''}"

    if re.search(r"Approval of the consolidated", t, re.IGNORECASE):
        y = re.search(r"(\d{4})", t)
        return f"Approval of consolidated accounts {y.group(1) if y else ''}"

    return t[:97] + "…" if len(t) > 100 else t


def extraire_resolutions(txt):
    resolutions = []
    lines = txt.split("\n")
    in_agenda = False
    current_num = None
    current_text = ""

    for line in lines:
        line = line.strip()

        if re.search(r"AGENDA|ORDER OF BUSINESS", line, re.IGNORECASE):
            in_agenda = True
            continue

        if not in_agenda:
            continue

        m = re.match(r"^\s*(\d{1,2})[\.\)]\s+(.+)", line)
        if m:
            if current_num and current_text:
                resolutions.append({
                    "n": current_num,
                    "t": resume_resolution(current_text),
                    "f": False
                })
            current_num = m.group(1)
            current_text = m.group(2)
        elif current_num and len(line) > 5 and not re.match(r"Thank you|Yours|Sincerely", line, re.I):
            current_text += " " + line

    if current_num and current_text:
        resolutions.append({
            "n": current_num,
            "t": resume_resolution(current_text),
            "f": False
        })

    return resolutions


def esc(t):
    if not t:
        return ""
    return (
        t.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
         .replace('"', "&quot;")
    )


def generer_xml(data):
    mid = f"GMET{random.randint(100000000, 999999999)}"
    now = datetime.now()

    mtg_dt = data.get("mtg") or (now + timedelta(days=30)).strftime("%Y-%m-%dT10:00:00Z")
    rec_dt = data.get("rec") or (now + timedelta(days=14)).strftime("%Y-%m-%d")
    vote_dt = data.get("vote") or mtg_dt

    iss = esc(data.get("iss", "ISSUER"))
    isin = data.get("isin", "LU0000000000")
    bal = data.get("bal", "0")
    url = esc(data.get("url", ""))

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Document xmlns="urn:iso:std:iso:20022:tech:xsd:seev.001.001.12">
 <MtgNtfctn>
  <NtfctnGnlInf>
   <NtfctnTp>NEWM</NtfctnTp>
  </NtfctnGnlInf>
  <Mtg>
   <MtgId>{mid}</MtgId>
   <IssrMtgId>{mid}</IssrMtgId>
   <Tp>GMET</Tp>
   <AnncmntDt>
    <DtTm>{now.strftime("%Y-%m-%dT%H:%M:%SZ")}</DtTm>
   </AnncmntDt>
   <Prtcptn>
    <IssrDdlnForVtng>
     <DtOrDtTm>
      <DtTm>{vote_dt}</DtTm>
     </DtOrDtTm>
    </IssrDdlnForVtng>
   </Prtcptn>
   {"<AddtlDcmnttnURLAdr>" + url + "</AddtlDcmnttnURLAdr>" if url else ""}
   <EntitlmntFxgDt>
    <Dt>
     <Dt>{rec_dt}</Dt>
    </Dt>
   </EntitlmntFxgDt>
  </Mtg>
  <MtgDtls>
   <DtAndTm>
    <DtOrDtTm>
     <DtTm>{mtg_dt}</DtTm>
    </DtOrDtTm>
   </DtAndTm>
   <Lctn>
    <Adr>
     <StrtNm>{esc(data.get("st", ""))}</StrtNm>
     <BldgNb>{esc(data.get("bn", ""))}</BldgNb>
     <PstCd>{esc(data.get("pc", ""))}</PstCd>
     <TwnNm>LUXEMBOURG</TwnNm>
     <Ctry>LU</Ctry>
    </Adr>
   </Lctn>
  </MtgDtls>
  <Issr>
   <Id>
    <NmAndAdr>
     <Nm>{iss}</Nm>
    </NmAndAdr>
   </Id>
  </Issr>
  <Scty>
   <FinInstrmId>
    <ISIN>{isin}</ISIN>
   </FinInstrmId>
   <Pos>
    <HldgBal>
     <Bal>
      <Qty>
       <Unit>{bal}</Unit>
      </Qty>
     </Bal>
    </HldgBal>
   </Pos>
  </Scty>
"""
    for r in data.get("resolutions", []):
        xml += f"""  <Rsltn>
   <IssrLabl>{r['n']}</IssrLabl>
   <Desc>
    <Lang>en</Lang>
    <Titl>{esc(r['t'])}</Titl>
   </Desc>
   <ForInfOnly>{"true" if r.get('f') else "false"}</ForInfOnly>
  </Rsltn>
"""

    xml += """ </MtgNtfctn>
</Document>"""
    return xml


def main():
    print("=" * 60)
    print("GENERATEUR SWIFT SEEV.001.001.12")
    print("=" * 60)
    print("Collez le texte de la notice, puis terminez par deux lignes vides (ou Ctrl-D) :")

    lines = []
    empty = 0
    while True:
        try:
            line = input()
            if line == "":
                empty += 1
                if empty >= 2:
                    break
            else:
                empty = 0
            lines.append(line)
        except EOFError:
            break

    txt = "\n".join(lines)
    if not txt.strip():
        print("Erreur : Aucun texte saisi.")
        return

    data = {}

    data["isin"] = extraire_isin(txt)
    data["iss"] = extraire_emetteur(txt)
    data["bal"] = extraire_balance(txt)
    data.update(extraire_dates(txt))
    data.update(extraire_adresse(txt))
    data["url"] = extraire_url(txt)
    data["resolutions"] = extraire_resolutions(txt)

    xml = generer_xml(data)
    print("\n--- XML GENERE ---\n")
    print(xml)


if __name__ == "__main__":
    main()
