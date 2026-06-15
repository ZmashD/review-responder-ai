import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from dotenv import load_dotenv

# Load environmental variables from the .env file
load_dotenv()

def send_escalation_email(review_text: str, reason: str, brand_profile: str) -> bool:
    """
    Sends a real-time email alert via SendGrid API when a high-risk review is detected.
    Returns True if sent successfully, False otherwise.
    """
    # Retrieve the API key securely from the environment
    api_key = os.environ.get('SENDGRID_API_KEY')
    
    if not api_key:
        print("Error: SENDGRID_API_KEY not found in environment variables.")
        return False

    # This email address MUST match the Single Sender Identity you verified in SendGrid
    sender_email = 'zmash5d@gmail.com'
    
    # For testing purposes, you will send the alert to your own inbox
    recipient_email = 'zmash5d@gmail.com'

    # Construct the rich HTML email layout
    subject = f"🚨 Escalation Alert: {brand_profile}"
    
    html_body = f"""
    <div style="font-family: Arial, sans-serif; line-height: 1.6; max-width: 600px; border: 1px solid #e0e0e0; padding: 20px; border-radius: 5px;">
        <h2 style="color: #d9534f; margin-top: 0;">⚠️ Urgent Escalation Required</h2>
        <p>A high-risk customer review has been flagged by the system and requires manual manager review.</p>
        <hr style="border: 0; border-top: 1px solid #eeeeee;">
        <p><strong>Brand Profile:</strong> {brand_profile}</p>
        <p><strong>Reason for Escalation:</strong> <span style="color: #d9534f; font-weight: bold;">{reason}</span></p>
        <hr style="border: 0; border-top: 1px solid #eeeeee;">
        <div style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #d9534f; font-style: italic;">
            "{review_text}"
        </div>
        <hr style="border: 0; border-top: 1px solid #eeeeee;">
        <p style="font-size: 0.9em; color: #666;">This is an automated notification from your Reputation Management Engine.</p>
    </div>
    """

    message = Mail(
        from_email=sender_email,
        to_emails=recipient_email,
        subject=subject,
        html_content=html_body
    )

    try:
        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        # A 202 status code indicates SendGrid successfully accepted the email for delivery
        if response.status_code == 202:
            print(f"Success: Escalation email sent for {brand_profile}.")
            return True
        else:
            print(f"Warning: SendGrid responded with status code {response.status_code}")
            return False
    except Exception as e:
        print(f"Failed to send email via SendGrid: {str(e)}")
        return False