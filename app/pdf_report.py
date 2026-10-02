from __future__ import annotations
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle

def fmt(v,d=3): return "–" if v is None else f"{v:.{d}f}"
def build_report(campaigns,analytics):
    buf=BytesIO(); doc=SimpleDocTemplate(buf,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm)
    s=getSampleStyleSheet(); story=[Paragraph("Hausmonitor – Nivellement-Bericht",s["Title"]),Paragraph("Automatisch erzeugte technische Dokumentation. Statistische Beziehungen sind keine geotechnischen Kausalnachweise.",s["BodyText"]),Spacer(1,5*mm)]
    latest=campaigns[-1] if campaigns else None
    if latest:
        h=latest["stats"]["house"]
        story += [Paragraph("Aktueller Stand",s["Heading2"]),Table([["Letzte Messung",latest["measured_at"]],["Hausdifferenz SO−SW",fmt(h["value"])+" mm"],["Änderung seit Start",fmt(h["delta"])+" mm"],["Komb. Standardfehler",fmt(h["se"])+" mm"],["Bewertung",h["quality"]]],colWidths=[65*mm,100*mm])]
    story += [Spacer(1,4*mm),Paragraph("Messkampagnen",s["Heading2"])]
    rows=[["Datum","Haus mm","Δ mm","SE mm","Terrasse mm","GW m","Luft °C"]]
    for c in campaigns:
        rows.append([c["measured_at"].replace("T"," "),fmt(c["stats"]["house"]["value"]),fmt(c["stats"]["house"]["delta"]),fmt(c["stats"]["house"]["se"]),fmt(c["stats"]["terrace"]["value"]),fmt(c["groundwater"]),fmt(c["air_temp"],1)])
    table=Table(rows,repeatRows=1,colWidths=[35*mm,22*mm,20*mm,20*mm,25*mm,20*mm,18*mm]); table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#17365d')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('FONTSIZE',(0,0),(-1,-1),8),('GRID',(0,0),(-1,-1),.25,colors.grey),('VALIGN',(0,0),(-1,-1),'TOP')]))
    story.append(table); story += [Spacer(1,4*mm),Paragraph("Trend- und Korrelationsanalyse",s["Heading2"])]
    for label,key in [("Zeittrend",'time'),("Grundwasser",'groundwater'),("Lufttemperatur",'air_temp'),("Wandtemperaturdifferenz",'wall_delta')]:
        a=analytics.get(key)
        text="nicht auswertbar" if not a else f"n={a['n']}, Steigung={fmt(a['slope'],4)}, R²={fmt(a['r2'],3)}"
        story.append(Paragraph(f"<b>{label}:</b> {text}",s["BodyText"]))
    story += [Spacer(1,3*mm),Paragraph("Hinweis: Prognosen sind lineare Extrapolationen aus der Messreihe. Saisonale Effekte, Grundwasserregime und Änderungen des Messaufbaus können die Ergebnisse beeinflussen.",s["BodyText"])]
    doc.build(story); buf.seek(0); return buf
