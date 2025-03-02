# Στέλνει στους recipients ξεχωριστά το εμαιλ μέσω του csv αρχείου και κάνει και έλεγχο.
# Στο sender_password μπαίνει ο κωδικός από το App Password της Google 
# και χρειάζεται το email να έχει 2FA

import smtplib
import csv
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# Email credentials
sender_email = "AUTHORIZED EMAIL"
sender_password = "GMAIL APP PASSWORD"  # Use your Gmail App Password

# SMTP Server
smtp_server = "smtp.gmail.com"
smtp_port = 587

# CSV file path
csv_filename = "contacts.csv"

# Email validation regex
email_regex = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"

def validate_csv(csv_filename):
    """Validates the CSV file format and data."""
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

    for name, recipient_email in contacts:
        # Create a new email message for each recipient
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = "Personalized Greeting"

        # Email body with dynamic name
        body = f"Hello {name},\n\nThis is a personalized email just for you!\n\nBest regards,\nYour Name"
        msg.attach(MIMEText(body, 'plain'))

        # Send email
        server.sendmail(sender_email, recipient_email, msg.as_string())
        print(f"Email sent to {name} ({recipient_email})")

    # Close connection
    server.quit()
    print("All emails sent successfully!")

except Exception as e:
    print(f"Error: {e}")
