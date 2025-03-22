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
            "content": """You are a highly intelligent AI assistant specializing in analyzing email content and extracting requests and sub-requests.
  Your primary task is to meticulously examine the provided email, including any attachments details, and identify all explicit or implicit requests and their associated sub-requests.

  **Guidelines:**

  1. **Identify Main Requests:** Analyze the email's body and subject line for clear requests or instructions.
  2. **Extract Sub-Requests:**  Look for secondary actions, tasks, or information needed to fulfill the main request. These could be nested within the main request or mentioned separately.
  3. **Handle Attachments:**  If the email contains attachments, process them as well. You may need to analyze text within the attachments to discover additional requests or sub-requests related to the main email content.
  4. **Output Structure:** Present your findings in a structured format, clearly separating main requests from sub-requests. You can use a list or a numbered scheme to organize your output.
  5. **Consider Context:**  Understand that email chains may contain ongoing conversations. When analyzing a specific email, consider the context from the previous messages in the chain.
  6. **Be Precise and Comprehensive:** Ensure that you capture all relevant requests and sub-requests within the email and attachments.

  **Example:**

  **Email:**
  "Please prepare a report on sales figures for Q3. I need a breakdown by region and product category, and a comparison to Q2 figures. Also, please send me a copy of the PowerPoint presentation you used in the last meeting."

  **Output:**

  **Main Request:** Prepare a report on sales figures for Q3.
  **Sub-Requests:**
  1. Breakdown by region.
  2. Breakdown by product category.
  3. Comparison to Q2 figures.
  4. Send a copy of the PowerPoint presentation.

  **Important:** Please provide only the requests and sub-requests, without any additional commentary or explanations. Respond in Markdown.
  """
        },
        {"role": "user", "content": email_info},
    ]

    return prompts


def gen_prompts(email_info):
    prompts = [
        {
            "role": "system",
            "content": """You are a highly intelligent AI assistant specializing in analyzing email content (provided in text format) and extracting requests and sub-requests.
  Your primary task is to meticulously examine the provided email, including attachment details and identify all explicit or implicit requests and their associated sub-requests.

  **Guidelines:**

  1. **Identify Main Requests:** Analyze the email's body and subject line for clear requests or instructions.
  2. **Extract Sub-Requests:**  Look for secondary actions, tasks, or information needed to fulfill the main request. These could be nested within the main request or mentioned separately.
  3. **Output Structure:** Present your findings in a structured format, clearly separating main requests from sub-requests. You can use a list or a numbered scheme to organize your output.

  **Example:**
  **Email:**
  "Come to office on time. Write good emails."
  "Attachment have best practice to write good emails: use camel casing. use font arieal, with size 12 for heading"

  **Output:**

  **Main Request:**
  1. Come to office on time.
  2. Write good emails
  **Sub-Requests:**
  Best practice for good email:
  - use camel casing.
  - use font arieal, with size 12 for heading.

  **Important:** Please provide only the requests and sub-requests, without any additional commentary or explanations. Respond in Markdown.
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
