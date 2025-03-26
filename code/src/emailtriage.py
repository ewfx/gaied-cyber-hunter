import os
import email
import base64
import pandas as pd
import google.generativeai as genai
from bs4 import BeautifulSoup
import chromadb
import chromadb.utils.embedding_functions as embedding_functions
import logging
import uuid #Import UUID to generate unique IDs.

#pip install chromadb
#pip install sentence_transformers


# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Replace with your actual configurations
EMAIL_FOLDER = "samples-data"
API_KEY = "XXXXXXXXXXXXXXXXXXX"
MODEL_NAME = "google/gemini-2.0-pro-exp-02-05:free"
EMBEDDING_MODEL = "all-MiniLM-L6-v2" # Sentence Transformers model.
GUIDELINE_FOLDER = "guidelines"


# Initialize LLM and Embedding Model
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL_NAME)
embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)

# Initialize ChromaDB
client = chromadb.Client()
collection = client.create_collection("email_categories", embedding_function=embedding_function)


# Function to extract guidelines containing the request and subrequest types and definitions
def extract_guidelines(guideline_file):
    try:
        with open(guideline_file, 'r', encoding='utf-8') as f:
            content = f.read()

        parts = content.split("~~~~~~~~~~~~~~")
        guidelines = parts[0].strip() if len(parts) > 0 else "Unknown guideline"
        print("guidelines is :{}".format(guidelines))


        return guidelines

    except FileNotFoundError:
        logging.error(f"File not found: {guideline_file}")
        return "", "File Not Found", "File Not Found"
    except Exception as e:
        logging.error(f"Error processing file {guideline_file}: {e}")
        return "", "Error", "Error"





# Function to extract email text from a text file, and category and subcategory
def extract_email_text(email_file):
    try:
        with open(email_file, 'r', encoding='utf-8') as f:
            content = f.read()

        parts = content.split("~~~~~~~~~~~~~~")
        category = parts[1].strip() if len(parts) > 0 else "Unknown Category"
        print("category is : {}".format(category))

        sub_parts = parts[2].split("~~~~~~~~~~~~~~") if len(parts) > 1 else ["Unknown Subcategory",""]
        subcategory = sub_parts[0].strip() if len(sub_parts) > 0 else "Unknown Subcategory"
        print("subcategory is : {}".format(subcategory))

        sub_parts = parts[3].split("~~~~~~~~~~~~~~") if len(parts) > 1 else ["Unknown mainask",""]
        mainask = sub_parts[0].strip() if len(sub_parts) > 0 else "Unknown mainask"
        print("mainask is : {}".format(mainask))

        email_text = parts[0].strip() if len(parts) > 0 else "Unknown email body text"
        print("email_text is :{}".format(email_text))


        return email_text, category, subcategory, mainask

    except FileNotFoundError:
        logging.error(f"File not found: {email_file}")
        return "", "File Not Found", "File Not Found"
    except Exception as e:
        logging.error(f"Error processing file {email_file}: {e}")
        return "", "Error", "Error"

# Function to chunk text
def chunk_text(text, chunk_size=512, chunk_overlap=100):
    chunks = []
    for i in range(0, len(text), chunk_size - chunk_overlap):
        chunks.append(text[i:i + chunk_size])
    return chunks

# Populate the vector database with existing emails
def populate_vector_db_with_samples():
    for filename in os.listdir(EMAIL_FOLDER):
        if filename.endswith(".txt"):
            email_file = os.path.join(EMAIL_FOLDER, filename)
            text, category, subcategory, mainask = extract_email_text(email_file)
            chunks = chunk_text(text)

            for chunk in chunks:
                chunk_id = str(uuid.uuid4())  # Generate unique ID for each chunk.
                collection.add(
                    documents=[chunk],
                    metadatas=[{"category": category, "subcategory": subcategory, "mainask": mainask, "filename": filename}],
                    ids = [chunk_id]  # Add the unique ID
                )


# Populate the vector database with guidelines
def populate_vector_db_with_guidelines():
    for filename in os.listdir(GUIDELINE_FOLDER):
        if filename.endswith(".txt"):
            guideline_file = os.path.join(GUIDELINE_FOLDER, filename)
            guideline = extract_guidelines(guideline_file)
            chunks = chunk_text(guideline)

            for chunk in chunks:
                chunk_id = str(uuid.uuid4())  # Generate unique ID for each chunk.
                collection.add(
                    documents=[chunk],
                    #metadatas=[{"category": category, "subcategory": subcategory, "mainask": mainask, "filename": filename}],
                    ids = [chunk_id]  # Add the unique ID
                )

def gen_prompts(email_info, context):
    prompts = [
        {
            "role": "system",
            "context": context,
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



def llm_request(new_prompt_msg):
    import requests
    import json
    response = requests.post(
        url="XXXXXXXXXXX",
        headers={
            "Authorization": "XXXXXXXXXXXXXXX",
            "Content-Type": "application/json",
        },
        data=json.dumps({
            "model": "google/gemini-2.0-pro-exp-02-05:free",
            "messages": new_prompt_msg,

        })
    )
    response_json = response.json()
    print("llm response is :{}".format(response_json))
    llm_response = response_json["choices"][0]["message"]["content"]
    print(llm_response)
    return llm_response

# Function to categorize a new email
def categorize_email(new_email_file):
    new_email_text, category, subcategory, mainask = extract_email_text(new_email_file)
    #new_email_text = extract_email_text(new_email_file)

    results = collection.query(
        query_texts=[new_email_text],
        n_results=5  # Retrieve top 5 relevant chunks
    )

    context = ""
    # for document, metadata in zip(results["documents"][0], results["metadatas"][0]):
    #     context += f"Document: {document}\nCategory: {metadata['category']}\nSubcategory: {metadata['subcategory']}\n\n"

    for document in results["documents"][0]:
        context += document
    print("The context is :{}".format(context))
    prompt = f"""
    Given the following email: {new_email_text}

    And the following relevant documents:
    {context}

    Categorize the email into a category and subcategory.
    """
    new_prompt_msg = gen_prompts(new_email_text, context)

    #response = model.generate_content(prompt)
    response = llm_request(new_prompt_msg)
    #return response.text
    return response

# Main execution
if __name__ == "__main__":
    # populate_vector_db_with_guidelines()
    # populate_vector_db_with_samples()
    new_email_file = "<email which needs to be identified>"
    category_result = categorize_email(new_email_file)
    print("Final output is :{}".format(category_result))
