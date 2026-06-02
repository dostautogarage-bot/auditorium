# 📧 Email Notification Setup Guide

This guide will help you set up FREE email notifications for your ABC Auditorium booking system using Gmail.

## 🎯 What You'll Get

Once configured, the system will automatically send:
- ✅ **Booking Confirmation** emails with PDF receipt attached
- ✅ **Booking Update** notifications
- ✅ **Payment Reminder** emails
- ✅ **Cancellation** notifications

---

## 📋 Prerequisites

- A Gmail account (free)
- 5 minutes of your time

---

## 🚀 Step-by-Step Setup

### Step 1: Enable 2-Step Verification on Gmail

1. Go to your Google Account: https://myaccount.google.com/
2. Click on **Security** in the left sidebar
3. Under "Signing in to Google", click on **2-Step Verification**
4. Follow the prompts to enable it (you'll need your phone)

### Step 2: Generate App Password

1. After enabling 2-Step Verification, go back to **Security**
2. Under "Signing in to Google", click on **App passwords**
3. Select app: Choose **Mail**
4. Select device: Choose **Other (Custom name)**
5. Enter name: Type "ABC Auditorium Booking System"
6. Click **Generate**
7. **IMPORTANT**: Copy the 16-character password (it looks like: `xxxx xxxx xxxx xxxx`)
8. Save this password securely - you'll need it in the next step

### Step 3: Configure Django Settings

Open your `core/settings.py` file and add these lines at the end:

```python
# Email Configuration
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'your-email@gmail.com'  # Replace with your Gmail address
EMAIL_HOST_PASSWORD = 'xxxx xxxx xxxx xxxx'  # Replace with the App Password from Step 2
DEFAULT_FROM_EMAIL = 'ABC Auditorium <your-email@gmail.com>'
```

**Replace:**
- `your-email@gmail.com` with your actual Gmail address
- `xxxx xxxx xxxx xxxx` with the App Password you generated

### Step 4: Test the Configuration

Run this command in your terminal to test if emails work:

```bash
python manage.py shell
```

Then paste this code:

```python
from django.core.mail import send_mail

send_mail(
    'Test Email',
    'If you receive this, email is working!',
    'your-email@gmail.com',
    ['your-email@gmail.com'],
    fail_silently=False,
)
```

Check your inbox - you should receive a test email!

---

## 🔒 Security Best Practices

### Option 1: Use Environment Variables (Recommended)

Instead of hardcoding your email password in settings.py, use environment variables:

1. Install python-decouple:
```bash
pip install python-decouple
```

2. Create a `.env` file in your project root:
```
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=xxxx xxxx xxxx xxxx
```

3. Update `core/settings.py`:
```python
from decouple import config

EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

4. Add `.env` to your `.gitignore` file

### Option 2: Use Django's Secret Key Management

Store sensitive data in a separate file that's not committed to version control.

---

## 📧 How Emails Work

### Automatic Emails

The system automatically sends emails when:

1. **New Booking Created** → Confirmation email with PDF receipt
2. **Booking Updated** → Update notification
3. **Booking Deleted** → Cancellation notification

### Email Recipients

Emails are sent to:
- The contact person's email (if provided in the contact_person field)
- OR the booking creator's email (if contact person doesn't have email)

**Note**: Make sure to collect customer email addresses in the contact_person field!

---

## 🎨 Customizing Emails

### Change Auditorium Name

Edit `booking/email_utils.py` and update:
```python
'auditorium_name': 'ABC Auditorium',  # Change this
'contact_phone': '+91 808 983 3403',  # Change this
```

### Customize Email Templates

Email templates are located in:
- `booking/templates/booking/emails/booking_confirmation.html`
- `booking/templates/booking/emails/booking_update.html`
- `booking/templates/booking/emails/payment_reminder.html`
- `booking/templates/booking/emails/booking_cancellation.html`

You can edit these HTML files to change colors, text, or layout.

---

## 🐛 Troubleshooting

### Problem: Emails not sending

**Solution 1**: Check your Gmail settings
- Make sure 2-Step Verification is enabled
- Verify the App Password is correct (no spaces)

**Solution 2**: Check Django logs
```bash
python manage.py runserver
```
Look for error messages in the console

**Solution 3**: Test SMTP connection
```python
python manage.py shell

from django.core.mail import get_connection
connection = get_connection()
connection.open()  # Should return True if working
```

### Problem: Emails going to spam

**Solution**: 
- Ask recipients to mark your emails as "Not Spam"
- Add a proper sender name in DEFAULT_FROM_EMAIL
- Consider using a custom domain email (advanced)

### Problem: Gmail blocking sign-in

**Solution**:
- Make sure you're using an App Password, not your regular Gmail password
- Check if "Less secure app access" needs to be enabled (older accounts)

---

## 📊 Email Limits

Gmail free account limits:
- **500 emails per day**
- **100 recipients per email**

This is more than enough for most auditorium businesses!

---

## 🔄 Manual Email Sending

You can also manually send emails from Django admin or shell:

```python
from booking.models import Booking
from booking.email_utils import send_booking_confirmation_email, send_payment_reminder_email

# Send confirmation for a specific booking
booking = Booking.objects.get(pk=1)
send_booking_confirmation_email(booking)

# Send payment reminder
send_payment_reminder_email(booking)
```

---

## ✅ Verification Checklist

- [ ] 2-Step Verification enabled on Gmail
- [ ] App Password generated
- [ ] settings.py configured with email settings
- [ ] Test email sent successfully
- [ ] .env file created (if using environment variables)
- [ ] .env added to .gitignore
- [ ] Email templates customized (optional)

---

## 💡 Tips

1. **Use a dedicated Gmail account** for your auditorium (e.g., bookings@yourdomain.com)
2. **Keep the App Password secure** - treat it like a regular password
3. **Test emails regularly** to ensure they're working
4. **Monitor your Gmail quota** - you get 500 emails/day for free
5. **Collect customer emails** - add email field to booking form if needed

---

## 🆘 Need Help?

If you encounter issues:
1. Check the troubleshooting section above
2. Review Django logs for error messages
3. Verify your Gmail App Password is correct
4. Make sure your internet connection is working

---

## 🎉 You're Done!

Your email notification system is now set up! Customers will automatically receive professional emails for all their bookings.

**Next Steps:**
- Create a test booking to see the email in action
- Customize email templates with your branding
- Consider adding more email types (e.g., event reminders)

---

*Last Updated: June 2026*
*ABC Auditorium Booking System*