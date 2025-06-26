from fastapi import FastAPI, Depends, HTTPException, Header, Form
from pydantic import EmailStr
import ollama
import os
import smtplib
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv
import datetime

load_dotenv()  # Loads a value from our environment variable file

API_KEY_CREDITS = {os.getenv("API_KEY"): 5}  # List of valid API keys
print("Loaded API Keys with credits:",
      API_KEY_CREDITS)  # the "5" means that the user has only 5 requests that they can send to the model

# My fastAPI application (app is the name)
app = FastAPI()

# Email credentials
SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_USER = os.getenv("EMAIL_USER")  # the email address
EMAIL_PASS = os.getenv("EMAIL_PASS")  # the app password

def create_html_email(body: str, recipient_name: str, subject: str, link: str) -> str:
    """Create a luxurious HTML email template with lilac header"""
    # Replace newlines in the body with <br> tags
    formatted_body = body.replace('\n', '<br>')

    # Create premium template with lilac header
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
                position: relative;
                border: 12px solid #f5f0e6;
                background-color: #ffffff;
                box-shadow: 0 5px 25px rgba(0, 0, 0, 0.08);
                overflow: hidden;
            }}
            .header {{
                background: linear-gradient(to right, #d8bfd8, #e6e6fa);
                color: #000000;
                padding: 30px 20px;
                text-align: center;
                margin-bottom: 0;
                border-bottom: 1px solid #d8bfd8;
            }}
            .header h1 {{
                font-family: 'Cormorant Garamond', serif;
                font-size: 32px;
                font-weight: 600;
                letter-spacing: 0.5px;
                margin: 0;
                padding: 0;
                line-height: 1.3;
                color: #000000;
                text-shadow: 1px 1px 2px rgba(255,255,255,0.3);
            }}
            .content {{
                padding: 30px 40px;
                position: relative;
            }}
            .message {{
                margin-bottom: 30px;
                font-size: 16px;
                color: #555;
                line-height: 1.8;
            }}
            .footer {{
                margin-top: 30px;
                font-size: 12px;
                color: #999;
                text-align: center;
                padding: 20px;
                border-top: 1px solid #f0f0f0;
                background-color: #fafafa;
            }}
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .button {{
                display: inline-block;
                padding: 14px 35px;
                background: linear-gradient(to right, #a38b5e, #d4c29c);
                color: #2c3e50;
                text-decoration: none;
                border-radius: 2px;
                font-weight: 500;
                box-shadow: 0 3px 10px rgba(163, 139, 94, 0.2);
                transition: all 0.3s ease;
                font-family: 'Cormorant Garamond', serif;
                font-size: 17px;
                letter-spacing: 0.8px;
            }}
            .button:hover {{
                transform: translateY(-2px);
                box-shadow: 0 5px 15px rgba(163, 139, 94, 0.3);
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
            .divider {{
                height: 1px;
                background: linear-gradient(to right, transparent, #e0d6c0, transparent);
                margin: 25px 0;
            }}
            @media (max-width: 600px) {{
                .email-container {{
                    border-width: 8px;
                }}
                .content {{
                    padding: 25px;
                }}
                .header h1 {{
                    font-size: 26px;
                }}
            }}
        </style>
    </head>
    <body>
        <div class="email-container">
            <div class="header">
                <h1>{subject}</h1>
            </div>
            
            <div class="content">
                <div class="message">
                    {formatted_body}
                </div>
                
                <div class="divider"></div>
                
                <div class="button-container">
                    <a href="{link}" class="button">Continue Reading</a>
                </div>
                
                <div class="signature">
                    Warm regards,<br>
                    <span style="font-weight: 600;">The Team</span>
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

# It looks in the headers of our request for a variable called x_api_key
def verify_api_key(x_api_key: str = Header(None)):
    credits = API_KEY_CREDITS.get(x_api_key, 0)
    if credits <= 0:
        raise HTTPException(status_code=401, detail="Invalid API Key, or no credits left")
    return x_api_key


def extract_subject_and_body(text):
    """Remove Subject: line if present, and extract body."""
    text = re.sub(r"Subject:.*\n?", "", text)
    body_match = re.search(r"Body:\s*(.+)", text, re.DOTALL)
    if body_match:
        return body_match.group(1).strip()
    else:
        return text.strip()


def personalize_body(body_template, recipient_name, link):
    print("\n[DEBUG] Raw Template:\n", body_template)

    # Replace name placeholders
    name_pattern = re.compile(r"\[?(Recipient|Name|Your Name|Employee|User)\]?", flags=re.IGNORECASE)
    body_template = name_pattern.sub(recipient_name, body_template)

    # Replace link placeholders
    link_placeholder_pattern = re.compile(
        r"\[?(Insert\s+(phishing\s+)?URL|Insert\s+Call-to-Action\s+button\s+or\s+link|Insert\s+link|Insert\s+URL|phishing\s+URL|click\s+here\s+link|CTA|Click here|insert website URL|Insert link button: Shop Now|Insert link button or link|Insert malicious link|Insert link button: Update My Plan Now|Insert Call-to-Action button: Upgrade Now|Insert Call-to-Action button: Shop Now|Insert Call-to-Action button: Shop Now or Start Saving)\]?",
        flags=re.IGNORECASE
    )

    # Cleaned version of the link for comparison
    link_clean = re.escape(link)

    # Step 1: Replace placeholder if it exists
    if link_placeholder_pattern.search(body_template):
        body_with_link = link_placeholder_pattern.sub(link, body_template)
    else:
        body_with_link = body_template.strip()

    # Step 2: Only append if the link is NOT already present anywhere
    if not re.search(link_clean, body_with_link, re.IGNORECASE):
        body_with_link += f"\n\n{link}"

    return body_with_link


# Sends a post request(an HTTP type request) to this URL
# Generates and returns the email content without sending it
@app.post("/generate")
def generate(
        prompt: str = Form(...),
        recipient_name: str = Form(...),
        link: str = Form(...),
        x_api_key: str = Depends(verify_api_key)
):
    # Subtract one credit because the user has successfully been verified
    # and used this function(they passed the API key)
    API_KEY_CREDITS[x_api_key] -= 1

    try:
        # Generate phishing text
        response = ollama.chat(
            model="JoannaF/phishing_email_generator",
            messages=[{"role": "user", "content": prompt}]
        )
        llm_text = response["message"]["content"]
        print("LLM OUTPUT:\n", llm_text)

        # Extract body
        body_template = extract_subject_and_body(llm_text)
        print("Body template:\n", body_template)

        # Personalize body
        body = personalize_body(body_template, recipient_name, link)

        # Remove "Best regards" and everything after
        body = re.sub(
            r"(?i)(Best regards,.*?$|Best,\s*\[Company\].*?$|Warm regards,\s*\[Company\s*\[Your Name].*?$|Best,\s*\[Your Name].*?$|Warm regards,\s*\[Your Name].*?$|Best,\s*\[Name].*?$|Happy shopping,\s*\[The [Company [Name] Team.*?$)",
            "",
            body,
            flags=re.DOTALL
        ).strip()

        # Also remove any P.S. section (and everything after it)
        body = re.sub(
            r"(?i)P\.S\..*$",
            "",
            body,
            flags=re.DOTALL
        ).strip()

        body = re.sub(
            r"(?i)(Here's an example of a phishing email:.*?$|Here is a sample phishing email:.*?$)",
            "",
            body,
            flags=re.DOTALL
        ).strip()

        return {
            "message": "Preview generated. Use this body for approval.",
            "body": body
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating or parsing content: {str(e)}")


# Sends the previously previewed email after user approves
@app.post("/send_email")
def send_email(
        body: str = Form(...),
        email: EmailStr = Form(...),
        subject: str = Form(...),
        recipient_name: str = Form(None),  # Make it optional
        use_html_ui: bool = Form(False),  # New parameter to control UI choice
        link: str = Form(...),
):
    # Prepare and send the email
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = email
        msg["Subject"] = subject

        # If recipient_name wasn't provided, use a default or extract from email
        if not recipient_name:
            recipient_name = "Valued Customer"  # Default value

        if use_html_ui:
            # Only include HTML version
            html_body = create_html_email(body, recipient_name, subject, link)
            msg.attach(MIMEText(html_body, "html"))
        else:
            # Only include plain text version
            msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        return {
            "message": f"Email sent to {email}",
            "subject": subject,
            "body": body,
            "html_ui_used": use_html_ui
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to send email: {str(e)}")
