import email
from email.parser import Parser
from email.header import decode_header
import os
import docx
from PyPDF2 import PdfReader
import openpyxl
import pytesseract
from PIL import Image
import io

def extract_text_from_eml(eml_file_path):
    """
    Extracts text content and attachments from an email file.
    """

    with open(eml_file_path, 'r', encoding='utf-8', errors='ignore') as f:
        msg = Parser().parse(f)

    text_data = ""

    # Extract email header information
    text_data += f"Subject: {msg['Subject']}\n"
    # text_data += f"From: {msg['From']}\n"
    # text_data += f"To: {msg['To']}\n"
    # text_data += f"Date: {msg['Date']}\n\n"

    # Extract email body content
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))

            if content_type == "text/plain" and "attachment" not in content_disposition:
                text_data += part.get_payload(decode=True).decode(part.get_content_charset() or 'utf-8',
                                                                  errors='ignore') + "\n"

            elif "attachment" in content_disposition:
                filename = part.get_filename()
                if filename:
                    text_data += "Below are the attachment details in text format.\n"
                    try:
                        attachment_data = part.get_payload(decode=True)
                        if content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
                            doc = docx.Document(io.BytesIO(attachment_data))
                            for paragraph in doc.paragraphs:
                                text_data += paragraph.text + "\n"

                        elif content_type == 'application/pdf':
                            pdf_reader = PdfReader(io.BytesIO(attachment_data))
                            for page in pdf_reader.pages:
                                text_data += page.extract_text()

                        elif content_type == 'application/vnd.ms-excel' or content_type == 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet':
                            workbook = openpyxl.load_workbook(io.BytesIO(attachment_data), read_only=True)
                            for sheet_name in workbook.sheetnames:
                                sheet = workbook[sheet_name]
                                for row in sheet.rows:
                                    for cell in row:
                                        text_data += str(cell.value) + " "
                                    text_data += "\n"

                        elif content_type.startswith('image/'):
                            image = Image.open(io.BytesIO(attachment_data))
                            text = pytesseract.image_to_string(image, lang='eng')
                            text_data += text + "\n"

                        else:
                            text_data += f"Attachment: {filename}\n"

                    except Exception as e:
                        text_data += f"Error processing attachment {filename}: {e}\n"
    else:
        text_data += msg.get_payload(decode=True).decode(msg.get_content_charset() or 'utf-8', errors='ignore')

    return text_data


from openai import OpenAI
from google.colab import userdata

gemini_via_openai_client = OpenAI(
    api_key=userdata.get("GOOGLE_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
)


def email_ocr(message):
    response = gemini_via_openai_client.chat.completions.create(
        model="gemini-2.0-flash-exp",
        messages=message,
    )
    return response.choices[0].message.content


def gen_prompts(email_info):
  prompts = [
      {
          "role": "system",
          "content": """You are a highly intelligent AI assistant specializing in analyzing email content (provided in text format) and extracting key information for triage. Your task is to meticulously examine the provided email, including attachment details, and identify:
**Guidelines:**
**1. Sender:** Extract the sender's email address.
**2. Subject:** Extract the email subject.
**3. Identify Priority:** Determine the email's priority (e.g., High, Medium, Low) based on keywords in the subject or body. Consider factors such as "urgent," "important," "kindly note","penalty" or deadlines mentioned.
**4. Identify Primary Request Type:** Analyze the email's body and subject line for a primary request. Consider verbs like "please review,"urgent," "important," "kindly note","penalty","action needed,","authorize","disburse","numerical in terms of money" or "verify" for your approval and finally summarize the request"
**5. Extract Sub-Requests:**  Look for secondary actions, tasks, or information needed to fulfill the main request. These could be nested within the main request or mentioned separately.
**6. Request type if any from attachment:** Incase of attachment , List all attachments and their types (e.g., .jpeg, .jpg, .doc, .pdf files).Extract relevant information from the attachments, such as document titles or key data points. Consider verbs like "please review," "action needed," "authorize," "disburse," or "verify" for your approval.Identify any primary request type within the attachment.


**Output Structure:**

Present your findings in a structured format using Markdown or JSON, clearly labeling each piece of information.

  **Example:**
  **Email:**
  "Loan disbursement information"
  "Attachments have all the required doucuments to disburse the loan"

**Input:** (Email content with attachments)

**Output:**

json {"Subject": "Urgent Request": "Project Update", "Priority": "High", "Primary Request Type": "Mention the primary requests on the mail","Sub-Requests":"check if any subrequest","Request type if any from attachment:"verify"}

**Important:**

*   Prioritize accuracy and conciseness in your analysis.
*   If information is missing or unclear, indicate it as "Not Found" or "Unknown."
*   Focus on extracting information relevant for triage and prioritization.

Reasoning:

Sender, Subject, and Priority: Identifying these elements quickly allows for initial assessment and routing of the email.
Action Required: Understanding the desired action helps determine the appropriate next steps for the email recipient.
Summary: A concise summary provides context without requiring the recipient to read the entire email.
Attachments: Analyzing attachments allows for a more comprehensive understanding of the email's purpose and content, especially if relevant information is included within them. By listing attachments and summarizing their content (if possible), you can further inform the triage process.
This prompt focuses on extracting key information for email triage, including handling attachments to help you prioritize and route emails effectively. Let me know if you'd like any modifications or if you have another question!
  """
      },
      {"role": "user", "content": email_info},
  ]

  return prompts




def gen_prompts(email_info):
  prompts = [
      {
          "role": "system",
          "content": """You are a highly intelligent AI assistant specializing in analyzing email content (provided in text format) and extracting key information for triage. Your task is to meticulously examine the provided email, including attachment details, and identify:
**Guidelines:**
**1. Sender:** Extract the sender's email address.
**2. Subject:** Extract the email subject.
**3. Identify Priority:** Determine the email's priority (e.g., High, Medium, Low) based on keywords in the subject or body. Consider factors such as "urgent," "important," "kindly note","penalty" or deadlines mentioned.
**4. Identify Primary Request Type:** Analyze the email's body and subject line for a primary request. Consider verbs like "please review,"urgent," "important," "kindly note","penalty","action needed,","authorize","disburse","numerical in terms of money" or "verify" for your approval and finally summarize the request"
**5. Extract Sub-Requests:**  Look for secondary actions, tasks, or information needed to fulfill the main request. These could be nested within the main request or mentioned separately.
**6. Request type if any from attachment:** List all attachments.Extract relevant information from the attachments, such as document titles or key data points like Consider verbs like "please review," "action needed,","authorize","disburse" or "verify" for your approval.Please find any primary request type in the attachment.

**Output Structure:**

Present your findings in a structured format using Markdown or JSON, clearly labeling each piece of information.

  **Example:**
  **Email:**
  "Loan disbursement information"
  "Attachments have all the required doucuments to disburse the loan"

**Input:** (Email content with attachments)

**Output:**

json {"Subject": "Urgent Request": "Project Update", "Priority": "High", "Primary Request Type": "Mention the primary requests on the mail","Sub-Requests":"check if any subrequest","Request type if any from attachment:"verify"}

**Important:**

*   Prioritize accuracy and conciseness in your analysis.
*   If information is missing or unclear, indicate it as "Not Found" or "Unknown."
*   Focus on extracting information relevant for triage and prioritization.

Reasoning:

Sender, Subject, and Priority: Identifying these elements quickly allows for initial assessment and routing of the email.
Action Required: Understanding the desired action helps determine the appropriate next steps for the email recipient.
Summary: A concise summary provides context without requiring the recipient to read the entire email.
Attachments: Analyzing attachments allows for a more comprehensive understanding of the email's purpose and content, especially if relevant information is included within them. By listing attachments and summarizing their content (if possible), you can further inform the triage process.
This prompt focuses on extracting key information for email triage, including handling attachments to help you prioritize and route emails effectively. Let me know if you'd like any modifications or if you have another question!
  """
      },
      {"role": "user", "content": email_info},
  ]

  return prompts



import gradio as gr
import email
from email.parser import Parser
from email.header import decode_header
import os
import docx
from PyPDF2 import PdfReader
import openpyxl
from PIL import Image
import io
from openai import OpenAI
from google.colab import userdata
from IPython.display import display, Markdown, update_display


def process_eml(eml_file):
    if not eml_file:
        return "Please upload an email file."
    output_text = ""
    # for eml_file_path in eml_file_paths:
    try:
        email_data = extract_text_from_eml(eml_file)
        prompts = gen_prompts(email_data)
        # output_text += f"**Email: {eml_file}**\n"
        output_text += email_ocr(prompts) + "\n\n"
    except Exception as e:
        output_text += f"Error processing {eml_file}: {e}\n\n"

    return output_text


iface = gr.Interface(
    fn=process_eml,
    inputs=gr.File(label='Upload eml file'),
    outputs=[gr.Markdown(label="Response:")],
    title="Email Request Extractor",
    description="Upload one or more .eml files to extract requests and sub-requests.",
    flagging_mode="never",
)

iface.launch(debug=True)
