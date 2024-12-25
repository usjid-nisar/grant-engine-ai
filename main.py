import os
import requests
import base64
from fastapi import FastAPI, File, UploadFile, HTTPException, APIRouter
from fastapi.responses import FileResponse
from fastapi.responses import JSONResponse
from helpers import create_pdf_directory
from helpers import pdf_to_images_by_toc
from helpers import PDF_BASE_DIR

# Define the standard sections to check
STANDARD_SECTIONS = [
    "Research Strategy",
    "Specific Aims",
    "Commercialization Plan",
    "Facilities",
    "Vertebrate Animals",
    "Introduction",
    "Authentication of Key",
    "Inclusion of Individuals Across the Lifespan",
    "Inclusion of Women and Minorities",
    "Recruitment and Retention Plan",
    "Study Timeline",
    "Protection of Human Subjects",
    "Data and Safety Monitoring Plan",
    "Overall structure of the study team",
    "Statistical Design and Power",
    "Investigational Product",
]


# Initialize FastAPI app
app = FastAPI()

# Load Gemini API key from environment variables
API_KEY = os.getenv("GENERATIVE_API_KEY")
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# Organize endpoints under proper router prefixes
pdf_router = APIRouter(prefix="/pdf", tags=["PDF Operations"])
image_router = APIRouter(prefix="/images", tags=["Image Operations"])
analysis_router = APIRouter(prefix="/analysis", tags=["Analysis Operations"])


# Move PDF processing endpoint
@pdf_router.post("/process/")
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


# Update image endpoints
@image_router.get("/{pdf_dir}/toc/{toc_section}")
async def get_toc_images(pdf_dir: str, toc_section: str):
    # Verify if the PDF directory exists first
    pdf_full_path = os.path.join(PDF_BASE_DIR, pdf_dir)
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=404, detail=f"PDF directory '{pdf_dir}' not found"
        )

    # Clean the TOC section name to match the directory naming convention
    toc_section_clean = "".join(
        c for c in toc_section if c.isalnum() or c in " _-"
    ).strip()
    section_dir = os.path.join(pdf_full_path, toc_section_clean)

    if not os.path.exists(section_dir):
        raise HTTPException(
            status_code=404,
            detail=f"TOC section '{toc_section}' not found in PDF directory '{pdf_dir}'",
        )

    # Get all images in the TOC section folder
    try:
        image_files = [
            f for f in os.listdir(section_dir) if f.endswith((".jpg", ".jpeg", ".png"))
        ]

        # Sort image files by page number
        image_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error reading TOC section directory: {str(e)}"
        )

    if not image_files:
        raise HTTPException(
            status_code=404, detail=f"No images found in TOC section '{toc_section}'"
        )

    # Construct image URIs
    image_uris = [
        f"/images/{pdf_dir}/{toc_section_clean}/{image_file}"
        for image_file in image_files
    ]

    return {
        "pdf_directory": pdf_dir,
        "toc_section": toc_section,
        "toc_section_clean": toc_section_clean,
        "images": image_uris,
        "total_images": len(image_uris),
    }


@image_router.get("/{pdf_dir}/page/{page_number}")
async def get_page_image(pdf_dir: str, page_number: int):
    # Verify if the PDF directory exists first
    pdf_full_path = os.path.join(PDF_BASE_DIR, pdf_dir)
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=404, detail=f"PDF directory '{pdf_dir}' not found"
        )

    try:
        # Find the image corresponding to the page number
        for root, _, files in os.walk(pdf_full_path):
            for file in files:
                if file == f"page_{page_number}.jpg":
                    # Get relative path from the PDF directory for consistent URI structure
                    rel_path = os.path.relpath(root, pdf_full_path)

                    # Construct URI based on whether we're in the root or a subfolder
                    if rel_path == ".":
                        image_uri = f"/images/{pdf_dir}/{file}"
                    else:
                        image_uri = f"/images/{pdf_dir}/{rel_path}/{file}"

                    return {
                        "pdf_directory": pdf_dir,
                        "page_number": page_number,
                        "section": os.path.basename(root),
                        "uri": image_uri,
                    }

        raise HTTPException(
            status_code=404,
            detail=f"Page {page_number} not found in PDF directory '{pdf_dir}'",
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error searching for page: {str(e)}"
        )


@image_router.get("/{pdf_dir}")
async def get_document_images(pdf_dir: str):
    pdf_full_path = os.path.join(PDF_BASE_DIR, pdf_dir)
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=404, detail=f"PDF directory '{pdf_dir}' not found"
        )

    images = []
    for root, dirs, files in os.walk(pdf_full_path):
        # Get the relative folder path from the PDF directory
        rel_path = os.path.relpath(root, pdf_full_path)

        for file in files:
            if file.endswith((".jpg", ".jpeg", ".png")):
                if rel_path == ".":
                    # For files in root directory, use a placeholder folder name
                    image_uri = f"/images/{pdf_dir}/root/{file}"
                else:
                    # For files in subfolders, use the actual folder path
                    image_uri = f"/images/{pdf_dir}/{rel_path}/{file}"
                images.append(
                    {
                        "uri": image_uri,
                        "folder": "root" if rel_path == "." else rel_path,
                        "filename": file,
                    }
                )

    if not images:
        raise HTTPException(
            status_code=404, detail=f"No images found in directory '{pdf_dir}'"
        )

    # Sort images by filename to maintain consistent order
    images.sort(key=lambda x: x["filename"])

    return {
        "pdf_directory": pdf_dir,
        "images": [img["uri"] for img in images],
        "total_images": len(images),
        "image_details": images,
    }


@image_router.get("/{pdf_dir}/{folder}/{image_name}")
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
                    {  "text": (

                            f"Please analyze the '{toc_section}' section of the document for the following conditions:\n"
                            "1. Verify if all figure numbers are sequential and unique.\n"
                            "2. Verify if all table numbers are sequential and unique.\n"
                            "3. Give an error if there are any figures or tables that are not sequential or not unique.\n"
                            "Just give me the error message and figure numbers and table numbers that are not sequential or not unique along with the page number and section name, no other text.\n"
                            "4. If there are no errors, just say 'No errors found'.\n"
                            f"Document Images: {', '.join(image_uris)}"
                        ),
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


# Function to send condition check request to Gemini with image data
def check_figure_sequence_with_images(toc_section, image_uris):
    headers = {
        "Content-Type": "application/json",
    }

    # Load images and encode them as Base64
    image_data = []
    for image_uri in image_uris:
        image_path = image_uri.lstrip(
            "/"
        )  # Remove leading slash to get the correct file path
        try:
            with open(image_path, "rb") as image_file:
                encoded_image = base64.b64encode(image_file.read()).decode("utf-8")
                image_data.append(
                    {
                        "filename": image_path.split("/")[-1],
                        "data": encoded_image,
                    }
                )
        except Exception as e:
            return JSONResponse(
                status_code=500,
                content={"detail": f"Error reading image '{image_path}': {str(e)}"},
            )

    data = {
        "contents": [
            {
                "parts": [
                    {
                        "text": (
                            f"Please analyze the '{toc_section}' section of the document for the following conditions:\n"
                            "1. Verify if all figure numbers are sequential and unique.\n"
                            "2. Verify if all table numbers are sequential and unique.\n"
                            "3. Give an error if there are any figures or tables that are not sequential or not unique.\n"
                            "Just give me the error message and figure numbers and table numbers that are not sequential or not unique along with the page number and section name, no other text.\n"
                            "4. If there are no errors, just say 'No errors found'.\n"
                        ),
                        "images": image_data,
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


@analysis_router.post("/check-figure-sequence-sections/")
async def check_figure_sequence_sections(pdf_dir: str):
    pdf_full_path = os.path.join(PDF_BASE_DIR, pdf_dir)
    if not os.path.exists(pdf_full_path):
        raise HTTPException(
            status_code=404, detail=f"PDF directory '{pdf_dir}' not found"
        )

    # Get existing directories in the PDF folder
    existing_sections = [
        d
        for d in os.listdir(pdf_full_path)
        if os.path.isdir(os.path.join(pdf_full_path, d))
    ]

    results = []
    for section in STANDARD_SECTIONS:
        # Clean the section name to match directory naming convention
        section_clean = "".join(c for c in section if c.isalnum() or c in " _-").strip()

        # Check if this section exists in the PDF directory
        if section_clean in existing_sections:
            section_dir = os.path.join(pdf_full_path, section_clean)

            # Get all images in the section folder
            image_files = [
                f
                for f in os.listdir(section_dir)
                if f.endswith((".jpg", ".jpeg", ".png"))
            ]

            if image_files:
                # Sort images by page number
                image_files.sort(key=lambda x: int(x.split("_")[1].split(".")[0]))

                image_uris = [
                    f"/images/{pdf_dir}/{section_clean}/{image_file}"
                    for image_file in image_files
                ]

                try:
                    gemini_response = check_figure_sequence(section, image_uris)
                    results.append(
                        {
                            "section": section,
                            "section_clean": section_clean,
                            "status": "checked",
                            "image_count": len(image_files),
                            "gemini_response": gemini_response,
                        }
                    )
                except Exception as e:
                    results.append(
                        {
                            "section": section,
                            "section_clean": section_clean,
                            "status": "error",
                            "error": str(e),
                        }
                    )
            else:
                results.append(
                    {
                        "section": section,
                        "section_clean": section_clean,
                        "status": "no_images",
                    }
                )
        else:
            results.append(
                {
                    "section": section,
                    "section_clean": section_clean,
                    "status": "section_not_found",
                }
            )

    return {
        "pdf_directory": pdf_dir,
        "sections_analyzed": len(results),
        "sections_found": len(
            [r for r in results if r["status"] != "section_not_found"]
        ),
        "sections_with_images": len([r for r in results if r["status"] == "checked"]),
        "results": results,
    }


# Include routers in the main app
app.include_router(pdf_router)
app.include_router(image_router)
app.include_router(analysis_router)
