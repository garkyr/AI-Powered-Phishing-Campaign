from fastapi import FastAPI, Depends, HTTPException, Header, Form
from pydantic import EmailStr, ValidationError, BaseModel
import ollama
import os
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import datetime

load_dotenv()  # Loads values from .env file

API_KEY_CREDITS = {os.getenv("API_KEY"): 5}
print("Loaded API Keys with credits:", API_KEY_CREDITS)

app = FastAPI()

# Email credentials
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_PASS = os.getenv("EMAIL_PASS")

def create_html_email(body: str, subject: str, link: str) -> str:
    formatted_body = body.replace('\n', '<br>')

    html_template = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{subject}</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600&family=Raleway:wght@300;400;500&display=swap');
            body {{
                font-family: 'Raleway', sans-serif;
                line-height: 1.7;
                color: #555;
                background-color: #f9f7f5;
                margin: 0;
                padding: 0;
            }}
            .email-container {{
                max-width: 600px;
                margin: 0 auto;
                border: 12px solid #f5f0e6;
                background-color: #ffffff;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.08);
            }}
            .header {{
                background: linear-gradient(to right, #d8bfd8, #e6e6fa);
                color: #000;
                padding: 30px 20px;
                text-align: center;
                border-bottom: 1px solid #d8bfd8;
            }}
            .header h1 {{
                font-family: 'Cormorant Garamond', serif;
                font-size: 32px;
                font-weight: 600;
                margin: 0;
            }}
            .content {{
                padding: 30px 40px;
            }}
            .message {{
                margin-bottom: 30px;
                font-size: 16px;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #999;
                text-align: center;
                padding: 20px;
                background-color: #fafafa;
                border-top: 1px solid #f0f0f0;
            }}
            .signature {{
                font-family: 'Cormorant Garamond', serif;
                font-size: 18px;
                color: #3a4a5e;
                margin-top: 30px;
                text-align: right;
                font-style: italic;
                font-weight: 500;
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>{subject}</h1>
            </div>
            <div class="content">
                <div class="message">{formatted_body}</div>
                <div class="signature">
                    Warm regards,<br>
                    <strong>The Team</strong>
                </div>
            </div>
            <div class="footer">
                <p>© {datetime.datetime.now().year} All Rights Reserved</p>
                <p>This is an automated message - please do not reply directly</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html_template

def verify_api_key(x_api_key: str = Header(None)):
    credits = API_KEY_CREDITS.get(x_api_key, 0)
    if credits <= 0:
        raise HTTPException(status_code=401, detail="Invalid API Key, or no credits left")
    return x_api_key

def extract_subject_and_body(text):
    subject_match = re.search(r"Subject:\s*(.+)", text)
    body_match = re.search(r"Body:\s*(.+)", text, re.DOTALL)

    if subject_match and body_match:
        subject = subject_match.group(1).strip()
        body = body_match.group(1).strip()
        return subject, body
    else:
        raise ValueError("Couldn't extract subject and body from the text.")

@app.post("/generate")
def generate(
        prompt: str = Form(...),
        recipient_name: str = Form(...),
        link: str = Form(...),
        x_api_key: str = Depends(verify_api_key)
):
    API_KEY_CREDITS[x_api_key] -= 1

    MAX_ATTEMPTS = 5
    placeholder = "[Insert Call-to-Action button or link]"

    for attempt in range(MAX_ATTEMPTS):
        try:
            response = ollama.chat(
                model="gawyria/demo-model",
                messages=[{"role": "user", "content": prompt}]
            )
            llm_output = response["message"]["content"]
            print(f"Attempt {attempt + 1} LLM OUTPUT:\n", llm_output)

            # Ensure the placeholder exists before proceeding
            if placeholder not in llm_output:
                print(f"Placeholder '{placeholder}' not found. Retrying...")
                continue

            # Extract subject and body
            subject, body = extract_subject_and_body(llm_output)

            # Replace placeholders
            body = re.sub(r"\[Name\]", recipient_name, body, flags=re.IGNORECASE)
            body = re.sub(re.escape(placeholder), link, body, flags=re.IGNORECASE)

            return {
                "message": "Preview generated. Use this subject and body for approval.",
                "subject": subject,
                "body": body
            }

        except Exception as e:
            if attempt == MAX_ATTEMPTS - 1:
                raise HTTPException(status_code=500, detail=f"Final attempt failed: {str(e)}")

    raise HTTPException(status_code=500, detail=f"Failed to generate content with required placeholder after {MAX_ATTEMPTS} attempts.")


# Sends the previously previewed email after user approves
@app.post("/send_email")
def send_email(
        body: str = Form(...),
        email: str = Form(...),
        subject: str = Form(...),
        use_html_ui: bool = Form(False),
        link: str = Form(...),
        sender_email: EmailStr = Form(...),
        sender_password: str = Form(...)
):
    try:
        # Split and validate emails
        raw_emails = [e.strip() for e in email.split(",")]

        # Helper to validate a single email using Pydantic model
        class EmailModel(BaseModel):
            email: EmailStr

        recipients = []
        for e in raw_emails:
            try:
                validated = EmailModel(email=e)
                recipients.append(validated.email)
            except ValidationError:
                raise HTTPException(status_code=400, detail=f"Invalid email: {e}")

        msg = MIMEMultipart("alternative")
        msg["From"] = sender_email
        msg["To"] = email
        msg["Subject"] = subject

        if use_html_ui:
            html_body = create_html_email(body, subject, link)
            msg.attach(MIMEText(html_body, "html"))
        else:
            msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)

        return {
            "message": f"Email sent to {email}",
            "subject": subject,
            "body": body,
            "html_ui_used": use_html_ui
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
