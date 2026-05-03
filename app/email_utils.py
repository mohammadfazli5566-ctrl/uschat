import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail


def send_reset_code(to_email, code):
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    from_email = os.environ.get("FROM_EMAIL")

    if not sendgrid_key or not from_email:
        print("SENDGRID_API_KEY oder FROM_EMAIL fehlt.")
        print("CODE:", code)
        return False

    message = Mail(
        from_email=from_email,
        to_emails=to_email,
        subject="UsChatSecure Passwort zurücksetzen",
        html_content=f"""
        <h2>UsChatSecure</h2>
        <p>Dein Bestätigungscode lautet:</p>
        <h1 style="font-size:32px;">{code}</h1>
        <p>Dieser Code ist nur für das Zurücksetzen deines Passworts.</p>
        <p>Wenn du das nicht warst, ignoriere diese E-Mail.</p>
        """
    )

    try:
        sg = SendGridAPIClient(sendgrid_key)
        sg.send(message)
        return True
    except Exception as e:
        print("SendGrid Fehler:", e)
        print("CODE:", code)
        return False