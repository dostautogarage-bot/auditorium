from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from .utils import generate_single_booking_pdf
import logging

logger = logging.getLogger(__name__)


def is_email_configured():
    """Check if email is properly configured"""
    return (
        hasattr(settings, 'EMAIL_HOST_USER') and
        settings.EMAIL_HOST_USER and
        hasattr(settings, 'EMAIL_HOST_PASSWORD') and
        settings.EMAIL_HOST_PASSWORD and
        getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', True)
    )


def send_booking_confirmation_email(booking):
    """
    Send booking confirmation email to customer with PDF attachment
    
    Args:
        booking: Booking object
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Check if email is configured
        if not is_email_configured():
            logger.warning("Email not configured. Skipping email notification. See EMAIL_SETUP_GUIDE.md")
            return False
        
        # Prepare email context
        context = {
            'booking': booking,
            'auditorium_name': 'ABC Auditorium',
            'contact_phone': '+91 808 983 3403',
        }
        
        # Render HTML email
        html_content = render_to_string('booking/emails/booking_confirmation.html', context)
        text_content = strip_tags(html_content)
        
        # Create email
        subject = f'Booking Confirmation - {booking.title}'
        from_email = settings.EMAIL_HOST_USER
        
        # Send email to admin who created the booking
        to_email = []
        if hasattr(booking.created_by, 'email') and booking.created_by.email:
            to_email = [booking.created_by.email]
        
        if not to_email:
            logger.warning(f"No valid email address for booking {booking.pk}")
            return False
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        
        # Attach PDF receipt
        try:
            pdf_content = generate_single_booking_pdf(booking)
            email.attach(
                f'booking_{booking.pk}_receipt.pdf',
                pdf_content,
                'application/pdf'
            )
        except Exception as e:
            logger.error(f"Failed to attach PDF: {str(e)}")
        
        # Send email
        email.send(fail_silently=False)
        logger.info(f"Booking confirmation email sent for booking {booking.pk}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking confirmation email: {str(e)}")
        return False


def send_booking_update_email(booking, changes=None):
    """
    Send booking update notification email
    
    Args:
        booking: Booking object
        changes: Dictionary of changes made (optional)
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not is_email_configured():
            return False
        
        context = {
            'booking': booking,
            'changes': changes,
            'auditorium_name': 'ABC Auditorium',
            'contact_phone': '+91 808 983 3403',
        }
        
        html_content = render_to_string('booking/emails/booking_update.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'Booking Updated - {booking.title}'
        from_email = settings.EMAIL_HOST_USER
        
        # Send email to admin who created the booking
        to_email = []
        if hasattr(booking.created_by, 'email') and booking.created_by.email:
            to_email = [booking.created_by.email]
        
        if not to_email:
            return False
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Booking update email sent for booking {booking.pk}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send booking update email: {str(e)}")
        return False


def send_payment_reminder_email(booking):
    """
    Send payment reminder email for pending payments
    
    Args:
        booking: Booking object
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not is_email_configured():
            return False
        
        if not booking.payment_pending:
            return False
        
        context = {
            'booking': booking,
            'pending_amount': booking.pending_amount,
            'auditorium_name': 'ABC Auditorium',
            'contact_phone': '+91 808 983 3403',
        }
        
        html_content = render_to_string('booking/emails/payment_reminder.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'Payment Reminder - {booking.title}'
        from_email = settings.EMAIL_HOST_USER
        
        # Send email to admin who created the booking
        to_email = []
        if hasattr(booking.created_by, 'email') and booking.created_by.email:
            to_email = [booking.created_by.email]
        
        if not to_email:
            return False
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Payment reminder email sent for booking {booking.pk}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send payment reminder email: {str(e)}")
        return False


def send_cancellation_email(booking):
    """
    Send booking cancellation notification email
    
    Args:
        booking: Booking object
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        if not is_email_configured():
            return False
        
        context = {
            'booking': booking,
            'auditorium_name': 'ABC Auditorium',
            'contact_phone': '+91 808 983 3403',
        }
        
        html_content = render_to_string('booking/emails/booking_cancellation.html', context)
        text_content = strip_tags(html_content)
        
        subject = f'Booking Cancelled - {booking.title}'
        from_email = settings.EMAIL_HOST_USER
        
        # Send email to admin who created the booking
        to_email = []
        if hasattr(booking.created_by, 'email') and booking.created_by.email:
            to_email = [booking.created_by.email]
        
        if not to_email:
            return False
        
        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=from_email,
            to=to_email
        )
        
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)
        
        logger.info(f"Cancellation email sent for booking {booking.pk}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to send cancellation email: {str(e)}")
        return False

# Made with Bob
