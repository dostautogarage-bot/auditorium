from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from io import BytesIO
from django.utils import timezone


def generate_bookings_pdf(bookings, filters=None, auditorium=None):
    """
    Generate a PDF report of bookings
    
    Args:
        bookings: QuerySet of Booking objects
        filters: Dictionary containing filter information (optional)
        auditorium: Auditorium object (optional)
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=30, leftMargin=30,
                           topMargin=30, bottomMargin=18)
    
    # Container for the 'Flowable' objects
    elements = []
    
    # Determine auditorium name
    auditorium_name = "Auditorium"
    if auditorium and auditorium.name:
        auditorium_name = auditorium.name
    elif bookings:
        first_b = bookings.first()
        if first_b and first_b.auditorium and first_b.auditorium.name:
            auditorium_name = first_b.auditorium.name

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#14B8A6'),
        spaceAfter=30,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#0F766E'),
        spaceAfter=12,
        fontName='Helvetica-Bold'
    )
    
    normal_style = styles['Normal']
    
    # Add title
    title = Paragraph(f"{auditorium_name} - Booking Report", title_style)
    elements.append(title)
    
    # Add generation date
    date_text = f"Generated on: {timezone.now().strftime('%B %d, %Y at %I:%M %p')}"
    date_para = Paragraph(date_text, normal_style)
    elements.append(date_para)
    elements.append(Spacer(1, 12))
    
    # Add filter information if provided
    if filters:
        filter_text = "<b>Filters Applied:</b><br/>"
        if filters.get('month'):
            filter_text += f"Month: {filters['month']}<br/>"
        if filters.get('start_date'):
            filter_text += f"Start Date: {filters['start_date']}<br/>"
        if filters.get('end_date'):
            filter_text += f"End Date: {filters['end_date']}<br/>"
        if filters.get('admin_name'):
            filter_text += f"Admin: {filters['admin_name']}<br/>"
        
        filter_para = Paragraph(filter_text, normal_style)
        elements.append(filter_para)
        elements.append(Spacer(1, 12))
    
    # Add summary statistics
    total_bookings = bookings.count()
    total_amount = sum(b.total_amount for b in bookings)
    total_advance = sum(b.advance_received for b in bookings)
    total_pending = total_amount - total_advance
    
    summary_text = f"""
    <b>Summary:</b><br/>
    Total Bookings: {total_bookings}<br/>
    Total Amount: Rs {total_amount:,.2f}<br/>
    Advance Received: Rs {total_advance:,.2f}<br/>
    Pending Amount: Rs {total_pending:,.2f}
    """
    summary_para = Paragraph(summary_text, normal_style)
    elements.append(summary_para)
    elements.append(Spacer(1, 20))
    
    # Create table data
    data = [['#', 'Event Title', 'Contact', 'Mobile', 'Date & Time', 'Amount', 'Advance', 'Pending', 'Created By']]
    
    for idx, booking in enumerate(bookings, 1):
        start_time = timezone.localtime(booking.start_time)
        end_time = timezone.localtime(booking.end_time)
        
        date_str = start_time.strftime('%b %d, %Y')
        time_str = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')}"
        
        data.append([
            str(idx),
            booking.title[:20] + '...' if len(booking.title) > 20 else booking.title,
            booking.contact_person[:15] + '...' if len(booking.contact_person) > 15 else booking.contact_person,
            booking.mobile_number,
            f"{date_str}\n{time_str}",
            f"Rs {booking.total_amount:,.0f}",
            f"Rs {booking.advance_received:,.0f}",
            f"Rs {booking.pending_amount:,.0f}",
            booking.created_by.username[:10]
        ])
    
    # Create table
    table = Table(data, colWidths=[0.4*inch, 1.2*inch, 1*inch, 0.9*inch, 1.3*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch])
    
    # Add style to table
    table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#14B8A6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        
        # Data rows
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (0, -1), 'CENTER'),  # First column centered
        ('ALIGN', (5, 1), (-1, -1), 'RIGHT'),  # Amount columns right-aligned
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        
        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F0FDFA')]),
    ]))
    
    elements.append(table)
    
    # Add footer
    elements.append(Spacer(1, 30))
    footer_text = f"{auditorium_name} Booking System | Generated automatically"
    footer_para = Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=TA_CENTER
    ))
    elements.append(footer_para)
    
    # Build PDF
    doc.build(elements)
    
    # Get the value of the BytesIO buffer and return it
    pdf = buffer.getvalue()
    buffer.close()
    return pdf


def num_to_words_indian(num):
    """Converts a number to Indian currency words representation (Rupees)"""
    try:
        num = int(num)
    except (ValueError, TypeError):
        return ""
    if num == 0:
        return "Zero"

    units = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
             "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]

    def convert_below_thousand(n):
        if n < 20:
            return units[n]
        elif n < 100:
            return tens[n // 10] + (" " + units[n % 10] if n % 10 != 0 else "")
        else:
            return units[n // 100] + " Hundred" + (" and " + convert_below_thousand(n % 100) if n % 100 != 0 else "")

    parts = []
    # Crores
    if num >= 10000000:
        parts.append(convert_below_thousand(num // 10000000) + " Crore")
        num %= 10000000
    # Lakhs
    if num >= 100000:
        parts.append(convert_below_thousand(num // 100000) + " Lakh")
        num %= 100000
    # Thousands
    if num >= 1000:
        parts.append(convert_below_thousand(num // 1000) + " Thousand")
        num %= 1000
    # Remaining
    if num > 0:
        parts.append(convert_below_thousand(num))

    return " ".join(parts)


def generate_single_booking_pdf(booking):
    """
    Generate a professional PDF receipt/invoice for a single booking that acts as
    an official AUDITORIUM BOOKING PAYMENT RECEIPT with optional digital signature.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=40, leftMargin=40,
                           topMargin=35, bottomMargin=35)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Base details
    auditorium = getattr(booking, 'auditorium', None)
    aud_name = auditorium.name if auditorium and auditorium.name else "Auditorium"
    aud_phone = auditorium.contact_phone if auditorium and auditorium.contact_phone else "N/A"
    aud_email = auditorium.contact_email if auditorium and auditorium.contact_email else "N/A"
    aud_owner_name = auditorium.owner.username if auditorium and auditorium.owner else "Administrator"
    
    receipt_no = f"{booking.serial_number}" if booking.serial_number else f"BK{10000 + booking.pk}"
    issue_date = timezone.now().strftime("%d %B, %Y")
    
    # Times & Shift
    start_time = timezone.localtime(booking.start_time)
    end_time = timezone.localtime(booking.end_time)
    
    if auditorium:
        day_start_str = auditorium.day_shift_start.strftime("%I:%M %p").lstrip('0').replace(' 0', ' ')
        day_end_str = auditorium.day_shift_end.strftime("%I:%M %p").lstrip('0').replace(' 0', ' ')
        night_start_str = auditorium.night_shift_start.strftime("%I:%M %p").lstrip('0').replace(' 0', ' ')
        night_end_str = auditorium.night_shift_end.strftime("%I:%M %p").lstrip('0').replace(' 0', ' ')
        
        booking_start_time_of_day = start_time.time()
        
        if auditorium.day_shift_start <= booking_start_time_of_day <= auditorium.day_shift_end:
            shift = f"Day Shift ({day_start_str} - {day_end_str})"
        elif auditorium.night_shift_start <= booking_start_time_of_day <= auditorium.night_shift_end:
            shift = f"Night Shift ({night_start_str} - {night_end_str})"
        else:
            shift = "Custom Time"
    else:
        shift = "Custom Time"
        
    booking_period = f"{start_time.strftime('%I:%M %p')} - {end_time.strftime('%I:%M %p')} ({shift})"
    event_date_str = start_time.strftime("%d %B, %Y")
    
    # Financial details
    advance_amount = booking.advance_received or 0
    rupees_in_words = num_to_words_indian(advance_amount)
    
    # Custom paragraph styles
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#1E293B'),
        alignment=TA_CENTER,
        spaceAfter=15
    )
    
    meta_style = ParagraphStyle(
        'ReceiptMeta',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#475569')
    )
    
    body_style = ParagraphStyle(
        'ReceiptBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=16,
        textColor=colors.HexColor('#1E293B'),
        spaceAfter=15,
        alignment=TA_LEFT
    )
    
    grid_label_style = ParagraphStyle(
        'GridLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )
    
    grid_value_style = ParagraphStyle(
        'GridValue',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#1E293B')
    )

    # ===== HEADER LOGO & NAME SIDE-BY-SIDE =====
    has_logo = False
    logo_img = None
    if auditorium and auditorium.logo:
        try:
            from reportlab.platypus import Image as RLImage
            logo_path = auditorium.logo.path
            logo_img = RLImage(logo_path, width=1.1*inch, height=1.1*inch)
            logo_img.hAlign = 'LEFT'
            has_logo = True
        except Exception:
            has_logo = False

    aud_name_style = ParagraphStyle(
        'HeaderAudName',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F776E')
    )
    
    aud_sub_style = ParagraphStyle(
        'HeaderAudSub',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13,
        textColor=colors.HexColor('#475569')
    )

    p_aud_name = Paragraph(aud_name.upper(), aud_name_style)
    p_aud_sub = Paragraph(f"Phone: {aud_phone} &bull; Email: {aud_email}", aud_sub_style)
    
    text_flow = [p_aud_name, Spacer(1, 4), p_aud_sub]

    if has_logo:
        header_table = Table([[logo_img, text_flow]], colWidths=[1.4*inch, 5.6*inch])
    else:
        header_table = Table([[text_flow]], colWidths=[7.0*inch])
        
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
    ]))
    
    elements.append(header_table)
    
    # Draw thin horizontal line
    line_table = Table([['']], colWidths=[7.0*inch])
    line_table.setStyle(TableStyle([
        ('LINEBELOW', (0,0), (-1,-1), 1.5, colors.HexColor('#E2E8F0')),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 10))

    # ===== TITLE =====
    title_style = ParagraphStyle(
        'ReceiptTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        textColor=colors.HexColor('#1E293B'),
        alignment=TA_CENTER,
        spaceAfter=15
    )
    elements.append(Paragraph("AUDITORIUM BOOKING PAYMENT RECEIPT", title_style))
    elements.append(Spacer(1, 5))
    
    # ===== METADATA BAR =====
    meta_data = [
        [
            Paragraph(f"<b>Receipt No.:</b> {receipt_no}", meta_style),
            Paragraph(f"<b>Date of Issue:</b> {issue_date}", ParagraphStyle('RightMeta', parent=meta_style, alignment=TA_RIGHT))
        ]
    ]
    meta_table = Table(meta_data, colWidths=[3.5*inch, 3.5*inch])
    meta_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 10),
    ]))
    elements.append(meta_table)
    elements.append(Spacer(1, 5))
    
    # ===== ACKNOWLEDGMENT BODY =====
    ack_text = (
        f"This is to acknowledge that we have received an amount of <b>RS.{advance_amount:,.2f}</b> "
        f"(<b>Rupees {rupees_in_words} only</b>) from <b>{booking.contact_person}</b> towards the booking and "
        f"use of <b>{aud_name}</b> for the event held on <b>{event_date_str}</b>."
    )
    elements.append(Paragraph(ack_text, body_style))
    elements.append(Spacer(1, 5))
    
    # ===== EVENT DETAILS TITLE =====
    elements.append(Paragraph("<b>EVENT DETAILS</b>", ParagraphStyle('SectionHeader', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14, textColor=colors.HexColor('#0F776E'), spaceAfter=8)))
    
    # ===== EVENT DETAILS GRID =====
    grid_data = [
        [Paragraph("Event Name:", grid_label_style), Paragraph(booking.title, grid_value_style)],
        [Paragraph("Event Date:", grid_label_style), Paragraph(event_date_str, grid_value_style)],
        [Paragraph("Auditorium / Venue:", grid_label_style), Paragraph(aud_name, grid_value_style)],
        [Paragraph("Booking Period:", grid_label_style), Paragraph(booking_period, grid_value_style)],
        [Paragraph("Amount Received:", grid_label_style), Paragraph(f"<b>RS.{advance_amount:,.2f}</b>", grid_value_style)],
    ]
    
    grid_table = Table(grid_data, colWidths=[2.2*inch, 4.8*inch])
    grid_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 12),
        ('RIGHTPADDING', (0,0), (-1,-1), 12),
    ]))
    elements.append(grid_table)
    elements.append(Spacer(1, 12))
    
    # ===== DECLARATIONS =====
    note_text = "The above-mentioned amount has been duly received against the auditorium booking and related venue charges for the event conducted on the date stated above."
    official_text = "This receipt is issued as an official acknowledgment of the payment received."
    elements.append(Paragraph(note_text, ParagraphStyle('NoteStyle', parent=body_style, fontSize=9.5, leading=14, textColor=colors.HexColor('#475569'))))
    elements.append(Paragraph(official_text, ParagraphStyle('OfficialStyle', parent=body_style, fontSize=9.5, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=20)))
    
    # ===== SIGNATURE BLOCK (SIMPLIFIED) =====
    sig_elements = []
    sig_elements.append(Paragraph(f"<b>For {aud_name}</b>", ParagraphStyle('ForCompany', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=14, alignment=TA_RIGHT, spaceAfter=8)))
    
    if auditorium and auditorium.digital_signature:
        try:
            from reportlab.platypus import Image as RLImage
            sig_path = auditorium.digital_signature.path
            sig_img = RLImage(sig_path, width=1.5*inch, height=0.6*inch)
            sig_img.hAlign = 'RIGHT'
            sig_elements.append(sig_img)
            sig_elements.append(Spacer(1, 4))
        except Exception as e:
            sig_elements.append(Spacer(1, 20))
    else:
        sig_elements.append(Spacer(1, 30))
        
    sig_text_style = ParagraphStyle('SigText', parent=styles['Normal'], fontName='Helvetica', fontSize=8.5, leading=12, alignment=TA_RIGHT, textColor=colors.HexColor('#475569'))
    sig_elements.append(Paragraph(f"___________________________", sig_text_style))
    
    processed_by = booking.created_by.username if booking.created_by else "Authorized Signatory"
    sig_elements.append(Paragraph(f"Processed By: <b>{processed_by}</b>", sig_text_style))
    
    # Wrap signature block in a right aligned Table
    sig_table_data = [['', sig_elements]]
    sig_table = Table(sig_table_data, colWidths=[3.2*inch, 3.8*inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'BOTTOM'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (1,0), (1,-1), 0),
    ]))
    elements.append(sig_table)
    
    # Build PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Made with Bob
