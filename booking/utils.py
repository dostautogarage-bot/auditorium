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


def generate_single_booking_pdf(booking):
    """
    Generate a professional PDF receipt/invoice for a single booking
    
    Args:
        booking: Booking object
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=35, leftMargin=35,
                           topMargin=30, bottomMargin=25)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Determine auditorium details
    auditorium = getattr(booking, 'auditorium', None)
    aud_name = auditorium.name if auditorium and auditorium.name else "Auditorium"
    aud_phone = auditorium.contact_phone if auditorium and auditorium.contact_phone else ""
    aud_email = auditorium.contact_email if auditorium and auditorium.contact_email else ""

    contact_parts = []
    if aud_phone:
        contact_parts.append(f"<b>Phone:</b> {aud_phone}")
    if aud_email:
        contact_parts.append(f"<b>Email:</b> {aud_email}")

    # ===== HEADER SECTION =====
    # Company name with decorative border
    header_data = [[Paragraph(
        f'<font size="24" color="#14B8A6"><b>{aud_name.upper()}</b></font>',
        ParagraphStyle('HeaderTitle', parent=styles['Normal'], alignment=TA_CENTER)
    )]]
    
    header_table = Table(header_data, colWidths=[7.2*inch])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDFA')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#14B8A6')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(header_table)
    elements.append(Spacer(1, 8))
    
    # Contact info bar (separate from header)
    if contact_parts:
        contact_text = f'<font size="8" color="#0F766E">{" | ".join(contact_parts)}</font>'
        contact_info = Paragraph(
            contact_text,
            ParagraphStyle('ContactInfo', parent=styles['Normal'], alignment=TA_CENTER)
        )
        elements.append(contact_info)
        elements.append(Spacer(1, 10))
    
    # ===== BOOKING CONFIRMATION BANNER =====
    booking_serial = f"#{booking.serial_number}" if booking.serial_number else f"#BK{booking.pk}"
    
    banner_data = [[
        Paragraph(
            f'<font size="15" color="white"><b>BOOKING CONFIRMATION</b></font>',
            ParagraphStyle('BannerLeft', parent=styles['Normal'], alignment=TA_LEFT)
        ),
        Paragraph(
            f'<font size="14" color="white"><b>{booking_serial}</b></font>',
            ParagraphStyle('BannerRight', parent=styles['Normal'], alignment=TA_RIGHT)
        )
    ]]
    
    banner_table = Table(banner_data, colWidths=[4.7*inch, 2.5*inch])
    banner_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#14B8A6')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (0, -1), 12),
        ('RIGHTPADDING', (1, 0), (1, -1), 12),
    ]))
    elements.append(banner_table)
    elements.append(Spacer(1, 12))
    
    # ===== CUSTOMER & EVENT DETAILS SECTION =====
    start_time = timezone.localtime(booking.start_time)
    end_time = timezone.localtime(booking.end_time)
    
    # Determine shift
    start_hour = start_time.hour
    if 9 <= start_hour < 16:
        shift = "Day Shift (9 AM - 4 PM)"
    elif 17 <= start_hour < 21:
        shift = "Night Shift (5 PM - 9 PM)"
    else:
        shift = "Custom Time"
    
    # Customer details box
    customer_data = [
        [Paragraph('<font size="10" color="#0F766E"><b>CUSTOMER DETAILS</b></font>',
                   ParagraphStyle('SectionHeader', parent=styles['Normal']))],
        [Paragraph(f'<font size="9"><b>Name:</b> {booking.contact_person}</font>', styles['Normal'])],
        [Paragraph(f'<font size="9"><b>Mobile:</b> {booking.mobile_number}</font>', styles['Normal'])],
        [Paragraph(f'<font size="9"><b>Event:</b> {booking.title}</font>', styles['Normal'])],
    ]
    
    customer_table = Table(customer_data, colWidths=[7.2*inch])
    customer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0F2F1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#14B8A6')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#14B8A6')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(customer_table)
    elements.append(Spacer(1, 8))
    
    # Event schedule box
    schedule_data = [
        [Paragraph('<font size="10" color="#0F766E"><b>EVENT SCHEDULE</b></font>',
                   ParagraphStyle('SectionHeader', parent=styles['Normal']))],
        [Paragraph(f'<font size="9"><b>Date:</b> {start_time.strftime("%A, %B %d, %Y")}</font>', styles['Normal'])],
        [Paragraph(f'<font size="9"><b>Shift:</b> {shift}</font>', styles['Normal'])],
        [Paragraph(f'<font size="9"><b>Time:</b> {start_time.strftime("%I:%M %p")} - {end_time.strftime("%I:%M %p")}</font>', styles['Normal'])],
    ]
    
    schedule_table = Table(schedule_data, colWidths=[7.2*inch])
    schedule_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0F2F1')),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#14B8A6')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#14B8A6')),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(schedule_table)
    elements.append(Spacer(1, 10))
    
    # ===== PAYMENT DETAILS SECTION =====
    payment_status_color = '#10B981' if not booking.payment_pending else '#EF4444'
    payment_status_text = '✓ FULLY PAID' if not booking.payment_pending else '⚠ PAYMENT PENDING'
    
    payment_data = [
        [Paragraph('<font size="10" color="#0F766E"><b>PAYMENT DETAILS</b></font>',
                   ParagraphStyle('SectionHeader', parent=styles['Normal'])), ''],
        ['', ''],
        [Paragraph('<font size="9"><b>Total Amount:</b></font>', styles['Normal']),
         Paragraph(f'<font size="9"><b>Rs {booking.total_amount:,.2f}</b></font>',
                   ParagraphStyle('AmountRight', parent=styles['Normal'], alignment=TA_RIGHT))],
        [Paragraph('<font size="9"><b>Advance Paid:</b></font>', styles['Normal']),
         Paragraph(f'<font size="9" color="#10B981">Rs {booking.advance_received:,.2f}</font>',
                   ParagraphStyle('AmountRight', parent=styles['Normal'], alignment=TA_RIGHT))],
        [Paragraph('<font size="9"><b>Balance Due:</b></font>', styles['Normal']),
         Paragraph(f'<font size="9" color="#EF4444"><b>Rs {booking.pending_amount:,.2f}</b></font>',
                   ParagraphStyle('AmountRight', parent=styles['Normal'], alignment=TA_RIGHT))],
        ['', ''],
        [Paragraph(f'<font size="9" color="{payment_status_color}"><b>{payment_status_text}</b></font>',
                   ParagraphStyle('StatusCenter', parent=styles['Normal'], alignment=TA_CENTER)), ''],
    ]
    
    payment_table = Table(payment_data, colWidths=[4.2*inch, 3*inch])
    payment_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#E0F2F1')),
        ('BACKGROUND', (0, 2), (-1, 4), colors.HexColor('#FAFAFA')),
        ('BACKGROUND', (0, 6), (-1, 6), colors.HexColor('#F0FDFA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#14B8A6')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#14B8A6')),
        ('LINEABOVE', (0, 2), (-1, 2), 0.5, colors.grey),
        ('LINEBELOW', (0, 4), (-1, 4), 0.5, colors.grey),
        ('SPAN', (0, 0), (-1, 0)),
        ('SPAN', (0, 6), (-1, 6)),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 10),
        ('RIGHTPADDING', (0, 0), (-1, -1), 10),
    ]))
    elements.append(payment_table)
    elements.append(Spacer(1, 10))
    
    # ===== BOOKING INFO =====
    booking_info = Paragraph(
        f'<font size="8" color="grey">Booked by: {booking.created_by.username} | '
        f'Booking Date: {booking.created_at.strftime("%B %d, %Y at %I:%M %p")}</font>',
        ParagraphStyle('BookingInfo', parent=styles['Normal'], alignment=TA_CENTER)
    )
    elements.append(booking_info)
    elements.append(Spacer(1, 10))
    
    # ===== TERMS & CONDITIONS =====
    terms_data = [[Paragraph('<font size="9" color="#0F766E"><b>TERMS & CONDITIONS</b></font>',
                             ParagraphStyle('TermsHeader', parent=styles['Normal']))]]
    
    terms_list = [
        "• Arrive 30 minutes before scheduled time.",
        "• Cancellations must be made 48 hours in advance.",
        "• Damage to property will be charged separately.",
        "• Outside food/beverages not permitted without approval.",
    ]
    
    for term in terms_list:
        terms_data.append([Paragraph(f'<font size="7" color="grey">{term}</font>', styles['Normal'])])
    
    terms_table = Table(terms_data, colWidths=[7.2*inch])
    terms_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F0FDFA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#B0BEC5')),
        ('LINEBELOW', (0, 0), (-1, 0), 1, colors.HexColor('#B0BEC5')),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(terms_table)
    elements.append(Spacer(1, 10))
    
    # ===== FOOTER =====
    footer_data = [[
        Paragraph(
            f'<font size="10" color="#14B8A6"><b>Thank you for choosing {aud_name}!</b></font><br/>'
            '<font size="7" color="grey">This is a computer-generated document and does not require a signature.</font>',
            ParagraphStyle('Footer', parent=styles['Normal'], alignment=TA_CENTER)
        )
    ]]
    
    footer_table = Table(footer_data, colWidths=[7.2*inch])
    footer_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F0FDFA')),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#14B8A6')),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    elements.append(footer_table)
    
    # Build PDF
    doc.build(elements)
    
    pdf = buffer.getvalue()
    buffer.close()
    return pdf

# Made with Bob
