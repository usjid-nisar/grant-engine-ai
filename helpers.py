import os
import fitz
from uuid import uuid4
from pdf2image import convert_from_path
from fastapi import HTTPException

# Update directory structure constants
PDF_BASE_DIR = "images"  # Base directory for all PDFs
os.makedirs(PDF_BASE_DIR, exist_ok=True)


# Extract TOC from PDF
def get_toc_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    toc = doc.get_toc()  # Returns a list of [level, title, page number]
    return toc


# Utility function to create PDF-specific directory
def create_pdf_directory(pdf_filename):
    pdf_id = uuid4().hex
    pdf_dir = os.path.join(
        PDF_BASE_DIR, f"{pdf_id}_{os.path.splitext(pdf_filename)[0]}"
    )
    os.makedirs(pdf_dir, exist_ok=True)
    return pdf_dir


# Convert PDF to images and organize by TOC
def pdf_to_images_by_toc(pdf_path, pdf_dir):
    try:
        toc = get_toc_from_pdf(pdf_path)
        if not toc:
            toc = [[1, "general", 1]]  # Default TOC entry if none is found

        images = convert_from_path(pdf_path)
        image_paths = []

        # Process TOC structure
        for entry in toc:
            level, title, page_number = entry
            title_clean = "".join(c for c in title if c.isalnum() or c in " _-").strip()
            section_dir = os.path.join(pdf_dir, title_clean)
            os.makedirs(section_dir, exist_ok=True)

            # Save images for the TOC section
            image_index = page_number - 1  # Page numbers are 1-based
            if image_index < len(images):  # Check for valid page
                image_filename = f"page_{page_number}.jpg"
                image_path = os.path.join(section_dir, image_filename)
                images[image_index].save(image_path, "JPEG")
                image_paths.append(image_path)

        return image_paths, toc
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error converting PDF to images: {str(e)}"
        )
