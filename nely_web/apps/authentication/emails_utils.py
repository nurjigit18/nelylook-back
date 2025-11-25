import logging
import resend
from django.conf import settings

logger = logging.getLogger(__name__)

# Initialize Resend with API key
resend.api_key = settings.RESEND_API_KEY


def send_verification_email_sendgrid(user_email, user_name, verification_url):
    """
    Send verification email using Resend API
    (Function name kept for backward compatibility)
    """
    try:
        logger.info(f"Sending verification email to {user_email} via Resend API")

        # HTML content
        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Подтвердите ваш email</h2>
        <p>Здравствуйте, {user_name or user_email}!</p>
        <p>Спасибо за регистрацию в NelyLook! Пожалуйста, подтвердите ваш email, нажав на кнопку ниже:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{verification_url}"
               style="background-color: #000; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Подтвердить email
            </a>
        </div>
        <p>Или скопируйте и вставьте эту ссылку в браузер:</p>
        <p style="word-break: break-all; color: #7f8c8d;">{verification_url}</p>
        <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
            Если вы не создавали аккаунт, просто проигнорируйте это письмо.
        </p>
    </div>
</body>
</html>
        """

        # Send via Resend API
        params = {
            "from": "NelyLook <noreply@nelylook.com>",
            "to": [user_email],
            "subject": "Подтвердите ваш email - NelyLook",
            "html": html_content,
        }

        response = resend.Emails.send(params)

        logger.info(f"✅ Verification email sent successfully. Response: {response}")
        return True, response.get('id', 'sent')

    except Exception as e:
        logger.error(f"❌ Failed to send verification email via Resend API: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False, str(e)


def send_password_reset_email_sendgrid(user_email, user_name, reset_url):
    """
    Send password reset email using Resend API.
    (Function name kept for backward compatibility)
    Returns (True, email_id) on success or (False, error_str) on failure.
    """
    try:
        logger.info(f"Sending password reset email to {user_email} via Resend API")

        html_content = f"""
<html>
<body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50;">Сброс пароля</h2>
        <p>Здравствуйте, {user_name or user_email}!</p>
        <p>Вы запросили сброс пароля. Нажмите на кнопку ниже, чтобы установить новый пароль:</p>
        <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}"
               style="background-color: #000; color: white; padding: 12px 30px;
                      text-decoration: none; border-radius: 5px; display: inline-block;">
                Сбросить пароль
            </a>
        </div>
        <p>Или скопируйте и вставьте эту ссылку в браузер:</p>
        <p style="word-break: break-all; color: #7f8c8d;">{reset_url}</p>
        <p style="margin-top: 30px; font-size: 12px; color: #7f8c8d;">
            Ссылка действительна 24 часа. Если вы не запрашивали сброс пароля, просто проигнорируйте это письмо.
        </p>
    </div>
</body>
</html>
        """

        params = {
            "from": "NelyLook <noreply@nelylook.com>",
            "to": [user_email],
            "subject": "Сброс пароля - NelyLook",
            "html": html_content,
        }

        response = resend.Emails.send(params)

        logger.info(f"✅ Password reset email sent. Response: {response}")
        return True, response.get('id', 'sent')

    except Exception as e:
        logger.error(f"❌ Failed to send password reset email via Resend API: {str(e)}")
        logger.error(f"Error type: {type(e).__name__}")
        import traceback
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        return False, str(e)
