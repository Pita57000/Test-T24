import datetime
import xml.etree.ElementTree as ET
from xml.dom import minidom

def esc(t):
    if not t: return ""
    return str(t).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;').replace("'", '&apos;')

def dt(d):
    if not d: return "2024-01-01T00:00:00Z"
    if 'T' in d:
        if len(d) == 16: return d + ":00Z"
        return d
    return d + "T00:00:00Z"

def generer_seev001(donnees, meeting_type):
    mid = "GMET" + datetime.datetime.now().strftime("%f")

    # Root
    root = ET.Element("Document", {
        "xmlns": "urn:iso:std:iso:20022:tech:xsd:seev.001.001.12"
    })

    mtg_ntfctn = ET.SubElement(root, "MtgNtfctn")

    # General Info
    inf = ET.SubElement(mtg_ntfctn, "NtfctnGnlInf")
    ET.SubElement(inf, "NtfctnTp").text = "NEWM"
    sts = ET.SubElement(inf, "NtfctnSts")
    ET.SubElement(sts, "EvtCmpltnsSts").text = "COMP"
    ET.SubElement(sts, "EvtConfSts").text = "CONF"

    # Meeting
    mtg = ET.SubElement(mtg_ntfctn, "Mtg")
    ET.SubElement(mtg, "MtgId").text = mid
    ET.SubElement(mtg, "IssrMtgId").text = mid
    ET.SubElement(mtg, "Tp").text = "GMET"
    clssf = ET.SubElement(mtg, "Clssfctn")
    ET.SubElement(clssf, "Cd").text = "ISSU"

    ann = ET.SubElement(mtg, "AnncmntDt")
    ET.SubElement(ann, "DtTm").text = dt(donnees.get("announcement_date"))

    prtc = ET.SubElement(mtg, "Prtcptn")
    mtd = ET.SubElement(prtc, "PrtcptnMtd")
    ET.SubElement(mtd, "Cd").text = "PHYS"
    ddln = ET.SubElement(prtc, "IssrDdlnForVtng")
    dt_or_dttm = ET.SubElement(ddln, "DtOrDtTm")
    ET.SubElement(dt_or_dttm, "DtTm").text = dt(donnees.get("deadline"))

    ent = ET.SubElement(mtg, "EntitlmntFxgDt")
    dt_el = ET.SubElement(ent, "Dt")
    ET.SubElement(dt_el, "Dt").text = donnees.get("record_date", "2024-01-01")
    ET.SubElement(ent, "DtMd").text = "EODY"

    # Meeting Details
    dtls = ET.SubElement(mtg_ntfctn, "MtgDtls")
    dt_tm = ET.SubElement(dtls, "DtAndTm")
    dt_or_dttm_2 = ET.SubElement(dt_tm, "DtOrDtTm")
    mtg_dt = donnees.get("meeting_date", "2024-01-01") or "2024-01-01"
    mtg_tm = donnees.get("meeting_time", "00:00") or "00:00"
    ET.SubElement(dt_or_dttm_2, "DtTm").text = dt(mtg_dt + "T" + mtg_tm)

    lctn = ET.SubElement(dtls, "Lctn")
    adr = ET.SubElement(lctn, "Adr")
    loc = donnees.get("location", "LUXEMBOURG") or "LUXEMBOURG"
    ET.SubElement(adr, "TwnNm").text = loc[:35]
    ET.SubElement(adr, "Ctry").text = "LU"

    # Issuer
    issr = ET.SubElement(mtg_ntfctn, "Issr")
    issr_id = ET.SubElement(issr, "Id")
    nm_adr = ET.SubElement(issr_id, "NmAndAdr")
    name = donnees.get("company_name", "ISSUER") or "ISSUER"
    ET.SubElement(nm_adr, "Nm").text = name[:140]

    # Security
    scty = ET.SubElement(mtg_ntfctn, "Scty")
    fin = ET.SubElement(scty, "FinInstrmId")
    isin = donnees.get("isin", "LU0000000000") or "LU0000000000"
    ET.SubElement(fin, "ISIN").text = isin

    # Resolutions
    for r in donnees.get('resolutions', []):
        rsltn = ET.SubElement(mtg_ntfctn, "Rsltn")
        ET.SubElement(rsltn, "IssrLabl").text = str(r.get("n"))
        desc = ET.SubElement(rsltn, "Desc")
        ET.SubElement(desc, "Lang").text = "en"
        ET.SubElement(desc, "Titl").text = (r.get("t") or "Resolution")[:250]
        ET.SubElement(rsltn, "ForInfOnly").text = "true" if r.get("f") else "false"
        ET.SubElement(rsltn, "Sts").text = "ACTV"

    # Return as string
    xml_str = ET.tostring(root, encoding='utf-8')
    parsed = minidom.parseString(xml_str)
    return parsed.toprettyxml(indent=" ")
