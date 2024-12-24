import os
import requests
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse

from helpers import create_pdf_directory
from helpers import pdf_to_images_by_toc
from helpers import PDF_BASE_DIR

# Initialize FastAPI app
app = FastAPI()


# Load Gemini API key from environment variables
API_KEY = os.getenv("GENERATIVE_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"


# FastAPI Endpoint: Process PDF and organize images by TOC
@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF."
        )

    pdf_path = f"temp_{file.filename}"
    try:
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        pdf_dir = create_pdf_directory(file.filename)

        image_paths, toc = pdf_to_images_by_toc(pdf_path, pdf_dir)

        os.remove(pdf_path)

        return {"pdf_directory": pdf_dir, "toc": toc}
    except Exception as e:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


# FastAPI Endpoint: Get Image URIs for a Specific TOC Section
@app.get("/images/toc/{pdf_dir}/{toc_section}")
async def get_toc_images(pdf_dir: str, toc_section: str):
    section_dir = os.path.join(PDF_BASE_DIR, pdf_dir, toc_section)
    if not os.path.exists(section_dir):
        raise HTTPException(
            status_code=404,
            detail=f"TOC section '{toc_section}' not found in PDF directory '{pdf_dir}'",
        )

    image_files = [
        f for f in os.listdir(section_dir) if f.endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        raise HTTPException(status_code=404, detail="No images found in section")

    image_uris = [
        f"/images/{pdf_dir}/{toc_section}/{image_file}" for image_file in image_files
    ]

    return {"toc_section": toc_section, "images": image_uris}


# FastAPI Endpoint: Get Image URI for a Specific Page
@app.get("/images/page/{pdf_dir}/{page_number}")
async def get_page_image(pdf_dir: str, page_number: int):
    # Find the image corresponding to the page number
    for root, _, files in os.walk(os.path.join(PDF_BASE_DIR, pdf_dir)):
        for file in files:
            if file == f"page_{page_number}.jpg":
                return {
                    "page": page_number,
                    "uri": f"/images/{os.path.relpath(root, PDF_BASE_DIR)}/{file}",
                }

    raise HTTPException(
        status_code=404,
        detail=f"Page {page_number} not found in PDF directory '{pdf_dir}'",
    )


# FastAPI Endpoint: Get All Image URIs for a PDF
@app.get("/images/{pdf_dir}")
async def get_document_images(pdf_dir: str):
    pdf_full_path = os.path.join(PDF_BASE_DIR, pdf_dir)

    # Verify if the PDF directory exists
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=404, detail=f"PDF directory '{pdf_dir}' not found"
        )

    images = []
    for root, _, files in os.walk(pdf_full_path):
        # Get the relative folder path from the PDF directory
        rel_path = os.path.relpath(root, pdf_full_path)

        for file in files:
            if file.endswith((".jpg", ".jpeg", ".png")):
                # Construct URI based on whether we're in the root or a subfolder
                if rel_path == ".":
                    # File is in the root PDF directory
                    image_uri = f"/images/{pdf_dir}/{file}"
                else:
                    # File is in a subfolder
                    image_uri = f"/images/{pdf_dir}/{rel_path}/{file}"
                images.append(image_uri)

    if not images:
        raise HTTPException(
            status_code=404, detail=f"No images found in directory '{pdf_dir}'"
        )

    return {"pdf_directory": pdf_dir, "images": images, "total_images": len(images)}


# FastAPI Endpoint: Serve an Image
@app.get("/images/{pdf_dir}/{folder}/{image_name}")
async def get_image(pdf_dir: str, folder: str, image_name: str):
    image_path = os.path.join(PDF_BASE_DIR, pdf_dir, folder, image_name)
    if not os.path.exists(image_path):
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(image_path)


# Function to send condition check request to Gemini
def check_figure_sequence(toc_section, image_uris):
    headers = {
        "Content-Type": "application/json",
    }
    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"Please analyze the '{toc_section}' section of the document for the following conditions:\n"
                            "1. Verify if all figure numbers are sequential and unique.\n"
                            "2. Verify if all table numbers are sequential and unique.\n"
                            f"Document Images: {', '.join(image_uris)}"
                        )
                    }
                ]
            }
        ]
    }
    url = f"{BASE_URL}?key={API_KEY}"

    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            return response.json()
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Gemini API Error: {response.text}",
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error sending data to Gemini: {str(e)}"
        )


# FastAPI Endpoint: Process PDF and organize images by TOC
@app.post("/process-pdf/")
async def process_pdf(file: UploadFile = File(...)):
    if file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400, detail="Invalid file type. Please upload a PDF."
        )

    pdf_path = f"temp_{file.filename}"
    try:
        with open(pdf_path, "wb") as f:
            f.write(await file.read())

        pdf_dir = create_pdf_directory(file.filename)

        image_paths, toc = pdf_to_images_by_toc(pdf_path, pdf_dir)

        os.remove(pdf_path)

        return {"pdf_directory": pdf_dir, "toc": toc}
    except Exception as e:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
        raise HTTPException(status_code=500, detail=f"Error processing PDF: {str(e)}")


# FastAPI Endpoint: Check conditions for a specific TOC section
@app.post("/check-condition/toc/")
async def check_condition_toc(pdf_dir: str, toc_section: str):
    section_dir = os.path.join(PDF_BASE_DIR, pdf_dir, toc_section)
    if not os.path.exists(section_dir):
        raise HTTPException(
            status_code=404,
            detail=f"TOC section '{toc_section}' not found in PDF directory '{pdf_dir}'",
        )

    # Get all images in the TOC section folder
    image_files = [
        f for f in os.listdir(section_dir) if f.endswith((".jpg", ".jpeg", ".png"))
    ]
    if not image_files:
        raise HTTPException(status_code=404, detail="No images found in section")

    image_uris = [
        f"/images/{pdf_dir}/{toc_section}/{image_file}" for image_file in image_files
    ]

    # Check conditions with Gemini
    gemini_response = check_figure_sequence(toc_section, image_uris)

    return {
        "toc_section": toc_section,
        "image_uris": image_uris,
        "gemini_response": gemini_response,
    }


# FastAPI Endpoint: Check conditions for a specific page
@app.post("/check-condition/page/")
async def check_condition_page(pdf_dir: str, page_number: int):
    # Find the image corresponding to the page number
    for root, _, files in os.walk(os.path.join(PDF_BASE_DIR, pdf_dir)):
        for file in files:
            if file == f"page_{page_number}.jpg":
                image_uri = f"/images/{os.path.relpath(root, PDF_BASE_DIR)}/{file}"

                # Check conditions with Gemini
                gemini_response = check_figure_sequence(
                    f"Page {page_number}", [image_uri]
                )

                return {
                    "page_number": page_number,
                    "image_uri": image_uri,
                    "gemini_response": gemini_response,
                }

    raise HTTPException(
        status_code=404,
        detail=f"Page {page_number} not found in PDF directory '{pdf_dir}'",
    )


# FastAPI Endpoint: Check conditions for the entire document
@app.post("/check-condition/document/")
async def check_condition_document(pdf_dir: str):
    images = []
    for root, _, files in os.walk(os.path.join(PDF_BASE_DIR, pdf_dir)):
        for file in files:
            if file.endswith((".jpg", ".jpeg", ".png")):
                images.append(f"/images/{os.path.relpath(root, PDF_BASE_DIR)}/{file}")

    if not images:
        raise HTTPException(status_code=404, detail="No images found for document")

    # Check conditions with Gemini
    gemini_response = check_figure_sequence("Entire Document", images)

    return {
        "pdf_directory": pdf_dir,
        "image_uris": images,
        "gemini_response": gemini_response,
    }
