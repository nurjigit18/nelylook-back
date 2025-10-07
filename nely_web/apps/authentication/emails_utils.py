import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from django.conf import settings

logger = logging.getLogger(__name__)

def send_verification_email_sendgrid(user_email, user_name, verification_url):
    """
    Send verification email using SendGrid HTTP API
    More reliable than SMTP, especially on cloud platforms
    """
    try:
        logger.info(f"Sending verification email to {user_email} via SendGrid HTTP API")
        
        # Create email message
        from_email = Email("noreply@nelylook.com", "NelyLook")
        to_email = To(user_email)
        subject = "Verify your NelyLook account"
        
        # Plain text content
        plain_content = f"""
Hello {user_name or user_email},

Please verify your email address by clicking the link below:

{verification_url}

If you did not create an account, please ignore this email.

Best regards,
The NelyLook Team
        """
        
        # HTML content
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Verify Your Email Address</h2>
        <p>Hello {user_name or user_email},</p>
        <p>Thank you for signing up with NelyLook! Please verify your email address by clicking the button below:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}" 
               style="background-color: #3498db; color: white; padding: 12px 30px; 
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Verify Email
            </a>
        </div>
        <p>Or copy and paste this link into your browser:</p>
        <p style="word-break: break-all; color: #7f8c8d;">{verification_url}</p>
        <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
            If you did not create an account, please ignore this email.
        </p>
    </div>
</body>
</html>
        """
        
        # Create Mail object
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject=subject,
            plain_text_content=plain_content,
            html_content=html_content
        )
        
        # Send via SendGrid API
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✅ Email sent successfully. Status: {response.status_code}")
        logger.info(f"Response headers: {response.headers}")
        
        return True, response.status_code
        
    except Exception as e:
        logger.error(f"❌ Failed to send email via SendGrid API: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False, str(e)
