# Στέλνει στους recipients ξεχωριστά το εμαιλ μέσω του csv αρχείου και κάνει και έλεγχο.
# Στο sender_password μπαίνει ο κωδικός από το App Password της Google 
# και χρειάζεται το email να έχει 2FA

import smtplib
import csv
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

def query_ollama(prompt):
    url = "http://localhost:11434/api/generate"
    payload = {
        "model": "hf.co/gawyria/model:Q4_K_M",  
        "prompt": prompt,
        "stream": False
    }

    response = requests.post(url, json=payload)
    data = response.json()

    # Extract the response based on the actual structure
    if "response" in data:
        return data["response"]
    else:
        # If the response is the entire text
        return data.get("text", data.get("output", str(data)))
    
# Extracts the body and subject from the output
def extract_subject_and_body(text):
    subject_match = re.search(r"Subject:\s*(.+)", text)
    body_match = re.search(r"Body:\s*(.+)", text, re.DOTALL)

    if subject_match and body_match:
        subject = subject_match.group(1).strip()
        body = body_match.group(1).strip()
        return subject, body
    else:
        raise ValueError("Couldn't extract subject and body from the text.")

# Email credentials
sender_email = "krisakik6@gmail.com"
sender_password = "fymaqrhjrxxorich"  # Use your Gmail App Password

# SMTP Server
smtp_server = "smtp.gmail.com"
smtp_port = 587

# CSV file path
csv_filename = "contacts.csv"

# Email validation regex
email_regex = r"^[a-zA-Z0-9._]+@[a-zA-Z0-9]+\.[a-zA-Z]{2,}$"

def validate_csv(csv_filename):
    try:
        with open(csv_filename, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            headers = next(reader, None)  # Read the first row as headers

            # Check if headers match the required format
            if headers != ["name", "email"]:
                raise ValueError("Invalid CSV format. Expected headers: 'name,email'.")

            # Read and validate each row
            contacts = []
            for row in reader:
                if len(row) != 2:
                    raise ValueError(f"Invalid row: {row}. Each row must have exactly 2 columns (name, email).")

                name, email = row[0].strip(), row[1].strip()

                if not name or not email:
                    raise ValueError(f"Missing data in row: {row}. Name and email cannot be empty.")

                if not re.match(email_regex, email):
                    raise ValueError(f"Invalid email format: {email} in row: {row}")

                contacts.append((name, email))

            return contacts

    except Exception as e:
        print(f"CSV Validation Error: {e}")
        return None  # Return None if validation fails

try:
    # Validate CSV file
    contacts = validate_csv(csv_filename)
    if contacts is None:
        raise Exception("Fix the CSV file and try again.")

    # Start SMTP session
    server = smtplib.SMTP(smtp_server, smtp_port)
    server.starttls()  # Secure connection
    server.login(sender_email, sender_password)  # Login

    # Ask user for prompt
    user_prompt = input("Enter the prompt for the email: ").strip()
    confirmed = False

    while not confirmed:
        # Generate email with LLM
        llm_output = query_ollama(user_prompt)

        try:
            # Extract subject and body
            subject, body_template = extract_subject_and_body(llm_output)

            # Show result to user
            print("\n--- Generated Email ---")
            print(f"Subject: {subject}")
            print(f"Body:\n{body_template}")
            print("------------------------\n")

            # Ask for confirmation
            user_input = input("Do you want to send this email? (yes/no): ").strip().lower()
            if user_input in ['yes', 'y']:
                confirmed = True
            else:
                print("Regenerating...\n")
        except Exception as e:
            print(f"Failed to extract subject/body: {e}")
            print("Trying again...\n")

    
    for name, recipient_email in contacts:
        # Ask if the user wants HTML formatting
        use_html = input("Do you want to send the email as HTML? (yes/no): ").strip().lower()
        send_as_html = use_html in ['yes', 'y']

        # Create a new email message for each recipient
        msg = MIMEMultipart("alternative")
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject

        # Personalize the body
        personalized_plain = body_template.replace("[Name]", name).replace("[Insert Call-to-Action button or link]", "link")

        # HTML version
        html_body = personalized_plain.replace('\n', '<br>')
        with open("email_template.html", "r", encoding="utf-8") as file:
            html_template = file.read()
        
        personalized_html = html_template.format(subject=subject, html_body=html_body)

        # Attach only the one the user chose
        if send_as_html:
            msg.attach(MIMEText(personalized_html, 'html'))
        else:
            msg.attach(MIMEText(personalized_plain, 'plain'))

        # Send the email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email sent to {name} ({recipient_email})")

    # Close connection
    server.quit()
    print("All emails sent successfully!")

except Exception as e:
    print(f"Error: {e}")