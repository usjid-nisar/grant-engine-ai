
# Project - Grant Engine AI

This project leverages **models** and other tools to process and analyze documents, such as grant proposals, with specific functionalities like converting PDFs to images, extracting structured data, and verifying document conditions.

---

## Features

### 1. **PDF Processing**
- Converts PDF files into images organized by Table of Contents (TOC).
- Supports generation of unique URIs for images of specific sections or pages.

### 2. **Condition Checking**
- Verifies specific conditions such as:
  - Sequential numbering of figures and tables.
  - Adherence to formatting guidelines.
- Uses the **Gemini model** to process extracted data and validate conditions.

### 3. **API Endpoints**
- Provides RESTful endpoints for:
  - PDF processing and organization by TOC.
  - Retrieving image URIs for specific TOC sections, pages, or entire documents.
  - Condition checking for individual sections, pages, or entire documents using APIs.

---

## Setup

### Prerequisites
- Python 3.8+
- Virtual Environment (optional but recommended)

### Installation

1. **Clone the Repository**:
   ```bash
   git clone git@github.com:username/grant-engine-ai.git
   cd grant-engine-ai
   ```

2. **Set Up Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Create a `.env` file to store sensitive information:
   ```plaintext
   GENERATIVE_API_KEY=your_api_key
   ```

5. **Run the Application**:
   ```bash
   uvicorn main:app --reload
   ```
   The app will be available at `http://127.0.0.1:8000`.

---

## Usage

### Key Endpoints

#### 1. **Process PDF**
**Endpoint**: `POST /process-pdf/`

- Uploads a PDF file and organizes images by TOC.
- **Response**:
  ```json
  {
      "pdf_directory": "unique_pdf_folder",
      "toc": [[1, "Introduction", 1], [1, "Methodology", 3]]
  }
  ```

#### 2. **Retrieve Image URIs**
- **TOC Section**: `GET /images/toc/{pdf_dir}/{toc_section}`
- **Specific Page**: `GET /images/page/{pdf_dir}/{page_number}`
- **Entire Document**: `GET /images/document/{pdf_dir}`

#### 3. **Condition Checking**
- **TOC Section**: `POST /check-condition/toc/`
- **Specific Page**: `POST /check-condition/page/`
- **Entire Document**: `POST /check-condition/document/`

---

## Contributing

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature-name`.
3. Commit your changes: `git commit -m "Add some feature"`.
4. Push to the branch: `git push origin feature-name`.
5. Open a pull request.

---

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.