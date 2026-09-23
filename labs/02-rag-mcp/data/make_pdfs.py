"""Regenerates the three Lab 2 sample PDFs (fictional company, invented facts — so a model cannot know the answers
without retrieval). Needs: pip install reportlab. The PDFs are committed; you only need this to change the content."""
from pathlib import Path

from reportlab import rl_config
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

rl_config.invariant = 1          # byte-identical PDFs on every run (no timestamps / random ids)
HERE = Path(__file__).resolve().parent
S = getSampleStyleSheet()
FOOTER = "Kestrel Drone Logistics GmbH (fictional company for the Building Stuff with GenAI workshop)"


def build(name: str, title: str, blocks: list) -> None:
    story = [Paragraph(title, S["Title"]), Spacer(1, 6)]
    for kind, content in blocks:
        if kind == "h":
            story += [Spacer(1, 8), Paragraph(content, S["Heading2"])]
        elif kind == "p":
            story.append(Paragraph(content, S["BodyText"]))
        elif kind == "table":
            t = Table(content, hAlign="LEFT")
            t.setStyle(TableStyle([("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
                                   ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2A446F")),
                                   ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                                   ("FONTSIZE", (0, 0), (-1, -1), 8.5)]))
            story += [Spacer(1, 4), t, Spacer(1, 4)]
    def footer(canvas, doc):
        canvas.setFont("Helvetica", 7)
        canvas.drawString(40, 20, f"{FOOTER} · page {doc.page}")
    SimpleDocTemplate(str(HERE / name), pagesize=A4, title=title, author="Kestrel Drone Logistics (fictional)").build(
        story, onFirstPage=footer, onLaterPages=footer)


build("kestrel_operations_handbook.pdf", "Kestrel Operations Handbook v4.2 (2026)", [
    ("p", "This handbook is binding for all flight operations staff. It replaces version 4.1 from November 2025."),
    ("h", "1. Fleet overview"),
    ("p", "Kestrel operates three drone models. Payload limits drop in rain because wet propellers lose lift; "
          "the rain limit applies whenever precipitation is reported at the launch or drop site."),
    ("table", [["Model", "Max payload (dry)", "Max payload (rain)", "Range", "Max wind", "Battery swap"],
               ["K-2 Sparrow", "1.2 kg", "0.9 kg", "12 km", "28 km/h", "every 40 cycles"],
               ["K-4 Kestrel", "2.5 kg", "1.8 kg", "18 km", "35 km/h", "every 60 cycles"],
               ["K-7 Heron", "6.0 kg", "4.2 kg", "25 km", "42 km/h", "every 80 cycles"]]),
    ("h", "2. Weather rules"),
    ("p", "No flight may start when the forecast wind at flight altitude exceeds the model's maximum wind rating. "
          "Lightning: if a strike is detected within 15 km of the route, all drones on that route are grounded until "
          "30 minutes after the last strike (the 15/30 rule). Below -10 degrees Celsius batteries must be pre-warmed "
          "to at least 15 degrees before launch."),
    ("h", "3. Night operations"),
    ("p", "Night flights (sunset to sunrise) require form NW-17, signed by the shift lead before the first launch of "
          "the night. The maximum altitude at night is 90 m above ground; during the day it is 120 m."),
    ("h", "4. Battery policy"),
    ("p", "A battery whose state of health falls below 82 % is retired and sent to recycling. Batteries in storage "
          "are kept at a 55 % charge. Every battery carries a QR label with its cycle count."),
    ("h", "5. Incident codes and escalation"),
    ("table", [["Code", "Meaning", "Escalate to", "Within"],
               ["KX-1", "Minor deviation, no damage", "Shift lead", "end of shift"],
               ["KX-2", "Payload lost or damaged", "Operations manager + customer service", "1 hour"],
               ["KX-3", "Injury or third-party damage", "Managing director + authority (LBA)", "15 minutes"]]),
])

build("kestrel_customer_service_policy.pdf", "Kestrel Customer Service Policy (March 2026)", [
    ("h", "1. Delivery windows"),
    ("p", "Standard deliveries are promised within a 2-hour window. Express deliveries are promised within a "
          "30-minute window and cost a surcharge of EUR 4.90."),
    ("h", "2. Refunds"),
    ("p", "If a delivery arrives more than 20 minutes after the end of its window, the customer receives a refund of "
          "50 % of the delivery fee. If the payload is lost (incident code KX-2), the customer receives a full refund "
          "plus a EUR 15 voucher. Refunds are issued automatically within 5 business days."),
    ("h", "3. Customer contact after incidents"),
    ("p", "After a KX-2 incident, customer service contacts the customer within 4 hours. After a KX-3 incident, "
          "only the managing director's office contacts the customer."),
    ("h", "4. Restricted items"),
    ("p", "We do not carry lithium batteries above 100 Wh, liquids above 1 litre, living animals, or anything "
          "classified as dangerous goods. Medication is accepted only from registered pharmacies."),
    ("h", "5. Photos and data"),
    ("p", "Proof-of-delivery photos are kept for 30 days and then deleted. Flight logs are kept for 2 years."),
])

build("kestrel_incident_review_q3_2026.pdf", "Incident Review Q3 2026", [
    ("p", "Prepared by the operations team. Three incidents in the quarter, no injuries."),
    ("h", "Incident 1 - 14 July 2026, Mannheim (KX-1)"),
    ("p", "A K-4 Kestrel was grounded mid-route after a lightning strike 9 km away; the 15/30 rule was applied and "
          "the drone waited at a safe landing point. The parcel arrived 41 minutes after the end of its Standard "
          "window, so the late-delivery refund applied."),
    ("h", "Incident 2 - 2 August 2026, Rhine crossing near Ludwigshafen (KX-2)"),
    ("p", "A K-7 Heron released its payload early over the river bank. Root cause: a timing bug in latch firmware "
          "3.1.4. The payload was recovered, but damaged. The fleet was updated to latch firmware 3.1.6 within 48 hours; "
          "no repeat since."),
    ("h", "Incident 3 - 3 September 2026, Heidelberg (near miss)"),
    ("p", "A K-2 Sparrow came within 20 m of a newly erected construction crane that was missing from the map. New "
          "rule: construction-zone geofences are refreshed every Monday from the city's permit feed."),
    ("h", "Actions"),
    ("table", [["Action", "Owner", "Due"],
               ["Weekly geofence refresh automated", "M. Okafor", "2026-10-15"],
               ["Latch firmware canary rollout process", "J. Lindqvist", "2026-10-31"],
               ["Lightning-hold waiting points added to all routes", "A. Brandt", "2026-11-30"]]),
])
print("written:", sorted(p.name for p in HERE.glob("*.pdf")))
