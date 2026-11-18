"""
ScamTrace Forensic Reports Module - ReportLab PDF generation
"""
import io
import logging
from datetime import datetime
from typing import Dict, List

logger = logging.getLogger(__name__)

DISCLAIMER = "SYNTHETIC DATA — FOR DEMONSTRATION PURPOSES ONLY. NOT REAL FINANCIAL RECORDS."
RISK_DISCLAIMER = (
    "Risk scores are heuristic behavioral indicators ONLY. "
    "They are NOT evidence of criminality and require human investigation."
)


def generate_pdf_report(case_data: dict) -> bytes:
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.lib.colors import HexColor, black, white
        from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                         TableStyle, PageBreak, HRFlowable)
        from reportlab.lib.enums import TA_CENTER, TA_LEFT

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
            rightMargin=2*cm, leftMargin=2*cm, topMargin=2.5*cm, bottomMargin=2.5*cm)

        BLUE = HexColor('#1f6feb')
        TEAL = HexColor('#2ea8a5')
        RED = HexColor('#f85149')
        ORANGE = HexColor('#d29922')
        BORDER = HexColor('#21262d')
        SECONDARY = HexColor('#8b949e')
        LIGHT_ROW = HexColor('#f8f9fa')

        styles = getSampleStyleSheet()
        title_st = ParagraphStyle('T', parent=styles['Title'], fontSize=24, textColor=BLUE, alignment=TA_CENTER, spaceAfter=4)
        sub_st = ParagraphStyle('S', parent=styles['Normal'], fontSize=11, textColor=SECONDARY, alignment=TA_CENTER, spaceAfter=16)
        h1_st = ParagraphStyle('H1', parent=styles['Heading1'], fontSize=13, textColor=BLUE, spaceBefore=14, spaceAfter=6)
        body_st = ParagraphStyle('B', parent=styles['Normal'], fontSize=9, spaceAfter=4)
        disc_st = ParagraphStyle('D', parent=styles['Normal'], fontSize=7, textColor=ORANGE, alignment=TA_CENTER)
        mono_st = ParagraphStyle('M', parent=styles['Code'], fontSize=7, fontName='Courier')

        story = []
        case_id = case_data.get('case_id', 'CASE-UNKNOWN')
        investigator = case_data.get('investigator', 'System')
        report_date = case_data.get('date', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        # Cover
        story += [Spacer(1, 2*cm), Paragraph("SCAMTRACE", title_st),
                  Paragraph("Financial Crime Intelligence & Investigation Platform", sub_st),
                  HRFlowable(width="100%", thickness=2, color=BLUE), Spacer(1, 0.4*cm),
                  Paragraph("FORENSIC INVESTIGATION REPORT",
                      ParagraphStyle('RT', parent=styles['Heading1'], fontSize=16, alignment=TA_CENTER)), Spacer(1, 0.8*cm)]

        ci_data = [['Case ID', case_id], ['Investigator', investigator],
                   ['Report Date', report_date], ['Classification', 'SYNTHETIC DEMONSTRATION']]
        ci_tbl = Table(ci_data, colWidths=[4*cm, 13*cm])
        ci_tbl.setStyle(TableStyle([
            ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'), ('TEXTCOLOR', (0,0), (0,-1), BLUE),
            ('FONTSIZE', (0,0), (-1,-1), 9), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ]))
        story += [ci_tbl, Spacer(1, 0.8*cm), HRFlowable(width="100%", thickness=1, color=BORDER),
                  Spacer(1, 0.3*cm), Paragraph(DISCLAIMER, disc_st), PageBreak()]

        # 1. Evidence Inventory
        story.append(Paragraph("1. Evidence Inventory", h1_st))
        ev = case_data.get('evidence_hashes', [])
        if ev:
            ev_data = [['Evidence ID', 'Filename', 'SHA-256 (truncated)', 'Upload Time', 'Size']]
            for e in ev:
                h = str(e.get('sha256_hash', ''))
                ev_data.append([str(e.get('evidence_id', '')), str(e.get('filename', '')),
                                 h[:24]+'...' if len(h) > 24 else h,
                                 str(e.get('upload_timestamp', ''))[:19],
                                 f"{e.get('file_size', 0):,} B"])
            ev_tbl = Table(ev_data, colWidths=[2.5*cm, 4*cm, 5*cm, 3.5*cm, 2*cm])
            ev_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), BLUE), ('TEXTCOLOR', (0,0), (-1,0), white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.3, BORDER), ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_ROW]),
                ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(ev_tbl)
        else:
            story.append(Paragraph("No evidence files registered for this case.", body_st))
        story.append(Spacer(1, 0.4*cm))

        # 2. Transaction Summary
        story.append(Paragraph("2. Transaction Summary", h1_st))
        tx = case_data.get('transactions_summary', {})
        if tx:
            sum_data = [['Metric', 'Value'],
                        ['Total Transactions', str(tx.get('total', 0))],
                        ['Total Amount', f"₹{float(tx.get('total_amount', 0)):,.2f}"],
                        ['Date Range', f"{tx.get('date_from', 'N/A')} to {tx.get('date_to', 'N/A')}"],
                        ['Flagged Transactions', str(tx.get('flagged', 0))],
                        ['Unique Accounts', str(tx.get('unique_accounts', 0))]]
            sum_tbl = Table(sum_data, colWidths=[8*cm, 9*cm])
            sum_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), TEAL), ('TEXTCOLOR', (0,0), (-1,0), white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,-1), 9), ('GRID', (0,0), (-1,-1), 0.3, BORDER),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_ROW]),
                ('TOPPADDING', (0,0), (-1,-1), 4), ('BOTTOMPADDING', (0,0), (-1,-1), 4),
            ]))
            story.append(sum_tbl)
        story.append(Spacer(1, 0.4*cm))

        # 3. Suspicious Accounts
        story.append(Paragraph("3. Suspicious Accounts", h1_st))
        sus = case_data.get('suspicious_accounts', [])
        if sus:
            sa_data = [['Account ID', 'Holder', 'Risk Score', 'Level', 'Primary Factor']]
            for a in sus[:20]:
                cf = str(a.get('contributing_factors', ''))
                sa_data.append([str(a.get('account_id', '')), str(a.get('account_holder', ''))[:18],
                                 str(a.get('risk_score', 0)), str(a.get('risk_level', '')),
                                 cf[:55]+'...' if len(cf) > 55 else cf])
            sa_tbl = Table(sa_data, colWidths=[3*cm, 3.5*cm, 2*cm, 2*cm, 6.5*cm])
            sa_tbl.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), RED), ('TEXTCOLOR', (0,0), (-1,0), white),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 7),
                ('GRID', (0,0), (-1,-1), 0.3, BORDER), ('ROWBACKGROUNDS', (0,1), (-1,-1), [white, LIGHT_ROW]),
                ('TOPPADDING', (0,0), (-1,-1), 3), ('BOTTOMPADDING', (0,0), (-1,-1), 3),
            ]))
            story.append(sa_tbl)
        else:
            story.append(Paragraph("No suspicious accounts identified.", body_st))
        story.append(Spacer(1, 0.4*cm))

        # 4. Money Trails
        story.append(Paragraph("4. Money Trail Analysis", h1_st))
        trails = case_data.get('money_trails', [])
        if trails:
            for i, trail in enumerate(trails[:5]):
                path_str = ' → '.join(trail.get('path', []))
                story.append(Paragraph(f"<b>Trail {i+1}:</b> {path_str}", body_st))
                edges = trail.get('edges', [])
                if edges:
                    ed = [['From', 'To', 'Amount (₹)', 'Timestamp']]
                    for e in edges:
                        ed.append([str(e.get('from', '')), str(e.get('to', '')),
                                   f"{float(e.get('amount', 0)):,.2f}", str(e.get('timestamp', ''))[:19]])
                    et = Table(ed, colWidths=[4*cm, 4*cm, 3.5*cm, 5.5*cm])
                    et.setStyle(TableStyle([
                        ('BACKGROUND', (0,0), (-1,0), ORANGE), ('TEXTCOLOR', (0,0), (-1,0), white),
                        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'), ('FONTSIZE', (0,0), (-1,-1), 7),
                        ('GRID', (0,0), (-1,-1), 0.3, BORDER), ('TOPPADDING', (0,0), (-1,-1), 2),
                    ]))
                    story.append(et)
                story.append(Spacer(1, 0.2*cm))
        else:
            story.append(Paragraph("No money trails traced.", body_st))
        story.append(Spacer(1, 0.4*cm))

        # 5. Risk Explanations
        story.append(Paragraph("5. Risk Score Explanations", h1_st))
        for acc in case_data.get('risk_explanations', [])[:10]:
            story.append(Paragraph(
                f"<b>{acc.get('account_id', '')} — {acc.get('account_holder', '')}</b>: "
                f"Score {acc.get('risk_score', 0)}/100 ({acc.get('risk_level', '')})", body_st))
            for f in str(acc.get('contributing_factors', '')).split(';'):
                if f.strip():
                    story.append(Paragraph(f"  • {f.strip()}",
                        ParagraphStyle('F', parent=body_st, leftIndent=15, fontSize=8)))
            story.append(Spacer(1, 0.15*cm))
        story.append(Paragraph(f"<i>{RISK_DISCLAIMER}</i>",
            ParagraphStyle('RD', parent=body_st, fontSize=7, textColor=ORANGE)))
        story.append(Spacer(1, 0.4*cm))

        # 6. Processing Logs
        story.append(Paragraph("6. Processing Logs", h1_st))
        logs = case_data.get('processing_logs', [])
        if logs:
            log_text = '<br/>'.join(str(l) for l in logs[-20:])
            story.append(Paragraph(log_text, ParagraphStyle('L', parent=mono_st, fontSize=7)))
        story.append(Spacer(1, 0.4*cm))

        # Footer
        story += [HRFlowable(width="100%", thickness=1, color=BORDER), Spacer(1, 0.2*cm),
                  Paragraph(DISCLAIMER, disc_st),
                  Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | ScamTrace v1.0.0 | Case: {case_id}",
                      ParagraphStyle('Ft', parent=styles['Normal'], fontSize=6, textColor=SECONDARY, alignment=TA_CENTER))]

        doc.build(story)
        pdf = buffer.getvalue()
        buffer.close()
        return pdf

    except ImportError as e:
        logger.error(f"ReportLab not available: {e}")
        content = (f"SCAMTRACE FORENSIC REPORT\n{'='*50}\n"
                   f"Case: {case_data.get('case_id', 'N/A')}\n"
                   f"NOTE: Install reportlab for PDF output: pip install reportlab\n"
                   f"{DISCLAIMER}\n")
        return content.encode('utf-8')
    except Exception as e:
        logger.error(f"PDF error: {e}")
        raise
