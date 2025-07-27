import requests
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# User's inputs
sender_email = input("Enter your email address: ")
sender_password = input("Enter your app password: ")
email = input("Enter the recipient email(s) separated by commas: ")
recipient_name = input("Enter the recipient's name: ")
link = input("Enter the link: ")
prompt = input("Enter the prompt for the model: ")
subject = input("Enter the subject for the email: ")

headers = {
    "x-api-key": os.getenv("API_KEY"),
    "Content-Type": "application/x-www-form-urlencoded"
}

# Step 1: Generate preview
preview_data = {
    "prompt": prompt,
    "recipient_name": recipient_name,
    "link": link
}

preview_response = requests.post("http://localhost:8000/generate", headers=headers, data=preview_data)

if preview_response.status_code != 200:
    print("Failed to generate preview.")
    print("Error:", preview_response.text)
    exit()

body = preview_response.json()["body"]
print("\n=== EMAIL PREVIEW ===")
print("Subject:", subject)
print("Body:\n", body)
print("=====================\n")

choice = input("Do you want to send this email? (yes or no): ").strip().lower()
if choice != "yes":
    print("Email not sent.")
    exit()

# Ask user if they want to use HTML UI
use_ui = input("Do you want to send the email with an UI? (yes or no): ").strip().lower()
if choice != "yes":
    print("Email sent without a ui.")
    exit()

# Step 2: Send email
send_data = {
    "email": email,
    "subject": subject,
    "body": body,
    "recipient_name": recipient_name,
    "link": link,
    "use_html_ui": str(use_ui),
    "sender_email": sender_email,
    "sender_password": sender_password
}

send_response = requests.post("http://localhost:8000/send_email", headers=headers, data=send_data)

print("Status Code:", send_response.status_code)
try:
    print("Response:", send_response.json())
except Exception as e:
    print("Failed to parse JSON:", e)
    print("Raw response:", send_response.text)
