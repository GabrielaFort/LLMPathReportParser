import io
import json
import os
import re
import tempfile
from pathlib import Path

import ollama

PATH_REPORT_PROMPT = """
You are a medical expert that extracts relevant information from pathology reports.
Return only a JSON object that follows the provided schema.
Do not use markdown fences.
Do not rename, omit, or add keys.
Use exactly these JSON keys: test_order_id, sample_site, sample_type, diagnosis, icd_code_descriptions, comments.
Use JSON null for unknown values. Do not use the string "null".
There may be incorrect spelling or grammer due to OCR or text extraction errors. Try your best to correct these errors and extract the relevant information.
Do NOT hallucinate any information. If the information is not present in the report, return null for that field.
Please extract the following information from the pathology report:

1) test_order_id (Optional - random ID will be generated if null): Example: 12345. If not clearly specified, just return null - do not make up an ID.
2) sample_site (Optional): Where the tumor sample was collected. Example: Lung, lower lobe
3) sample_type (Optional): Primary, Metastasis. Grade and/or stage if available. Example: Primary tumor, Grade 3
4) diagnosis (Optional): Short description. Example: Squamous cell carcinoma
5) icd_code_descriptions (Optional): If available, descriptive text associated with ICD code(s). Example: Carcinoma, Squamous cell, NOS
6) comments (Optional): Long description, often with IHC results. Example: Invasive, poorly differentiated squamous cell carcinoma with cellular and nuclear atypia. p40 positive by IHC.

The response MUST contain at least one of the following fields: diagnosis, icd_code_descriptions, or comments.
"""

PATH_REPORT_FIELDS = [
    "test_order_id",
    "sample_site",
    "sample_type",
    "diagnosis",
    "icd_code_descriptions",
    "comments",
]

REQUIRED_ONCOTREE_FIELDS = [
    "icd_code_descriptions",
    "path_lab_info",
    "test_order_id",
    "sample_site",
]

IMAGE_ONLY_MARKDOWN_RE = re.compile(r"<!--\s*image\s*-->", re.IGNORECASE)
INVALID_JSON_ESCAPE_RE = re.compile(r'\\(?!["\\/bfnrtu])')
DEFAULT_OLLAMA_HOST = "http://localhost:11434"

PATH_REPORT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "test_order_id": {
            "type": ["string", "null"],
            "description": "Patient/report/test order ID if present. Use null if not found."
        },
        "sample_site": {
            "type": ["string", "null"],
            "description": "Where the tumor sample was collected, e.g. Liver, lung lower lobe."
        },
        "sample_type": {
            "type": ["string", "null"],
            "description": "Primary/metastatic status, grade, stage, or specimen type if stated."
        },
        "diagnosis": {
            "type": ["string", "null"],
            "description": "Short diagnostic phrase, e.g. Squamous cell carcinoma."
        },
        "icd_code_descriptions": {
            "type": ["string", "null"],
            "description": "ICD-linked or other classification terms useful for tumor typing."
        },
        "comments": {
            "type": ["string", "null"],
            "description": "Longer pathology details, IHC results, morphology, or relevant comments."
        }
    },
    "required": PATH_REPORT_FIELDS
}


def get_model_source(model):
    return "cloud" if "cloud" in str(model).lower() else "local"


def get_ollama_base_url():
    base_url = (
        os.environ.get("OLLAMA_BASE_URL")
        or os.environ.get("OLLAMA_HOST")
        or DEFAULT_OLLAMA_HOST
    ).strip()
    if not base_url:
        base_url = DEFAULT_OLLAMA_HOST
    if not base_url.startswith(("http://", "https://")):
        base_url = f"http://{base_url}"
    return base_url


def build_oncotree_input_json(
    icd_code_descriptions="",
    path_lab_info="",
    test_order_id="",
    sample_site="",
):
    return {
        "icd_code_descriptions": icd_code_descriptions,
        "path_lab_info": path_lab_info,
        "test_order_id": test_order_id,
        "sample_site": sample_site,
    }


def clean_null_string(value):
    if isinstance(value, str) and value.strip().lower() == "null":
        return None
    return value


def is_oncotree_input_json(parsed):
    return isinstance(parsed, dict) and all(field in parsed for field in REQUIRED_ONCOTREE_FIELDS)


def normalize_oncotree_input_json(parsed, filename):
    parsed = {key: clean_null_string(value) for key, value in parsed.items()}
    return build_oncotree_input_json(
        icd_code_descriptions=parsed.get("icd_code_descriptions") or "",
        path_lab_info=parsed.get("path_lab_info") or "",
        test_order_id=parsed.get("test_order_id") or Path(filename).stem,
        sample_site=parsed.get("sample_site") or "",
    )


def parse_json_object(content):
    def loads_json_object(text):
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            cleaned = INVALID_JSON_ESCAPE_RE.sub("", text)
            return json.loads(cleaned)

    try:
        return loads_json_object(content)
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise
        return loads_json_object(content[start:end + 1])


def validate_path_report_fields(data):
    if data.get("null") is None:
        data.pop("null", None)

    expected_fields = set(PATH_REPORT_FIELDS)
    actual_fields = set(data)
    missing_fields = sorted(expected_fields - actual_fields)
    extra_fields = sorted(actual_fields - expected_fields)

    if missing_fields or extra_fields:
        raise ValueError(
            "Path report parser returned invalid JSON keys. "
            f"Missing keys: {missing_fields or 'none'}. "
            f"Extra keys: {extra_fields or 'none'}."
        )


def is_empty_or_image_only_markdown(markdown):
    text = markdown.strip()
    if not text:
        return True

    return not IMAGE_ONLY_MARKDOWN_RE.sub("", text).strip()


def convert_pdf_to_md(pdf_path, force_full_page_ocr=False):
    """
    Convert a PDF pathology report to MD format using docling
    """
    from docling.datamodel.base_models import InputFormat
    from docling.document_converter import DocumentConverter, PdfFormatOption
    from docling.datamodel.pipeline_options import PdfPipelineOptions, RapidOcrOptions


    pipeline_options = PdfPipelineOptions(do_table_structure=True)
    pipeline_options.do_ocr = True
    if force_full_page_ocr:
        pipeline_options.ocr_options = RapidOcrOptions(force_full_page_ocr=True)
    else:
        pipeline_options.ocr_options = RapidOcrOptions()
    # pipeline_options.ocr_options = TesseractOcrOptions()

    converter = DocumentConverter(
        allowed_formats=[InputFormat.PDF],
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        },
    )

    result = converter.convert(pdf_path)
    doc = result.document
    md = doc.export_to_markdown()

    if (
        not force_full_page_ocr
        and is_empty_or_image_only_markdown(md)
    ):
        return convert_pdf_to_md(pdf_path, force_full_page_ocr=True)

    return md


def convert_pdf_bytes_to_md(pdf_bytes):
    with tempfile.TemporaryDirectory() as temp_dir:
        pdf_path = Path(temp_dir) / "report.pdf"
        pdf_path.write_bytes(pdf_bytes)
        return convert_pdf_to_md(pdf_path)


def extract_docx_text(docx_bytes):
    from docx import Document

    doc = Document(io.BytesIO(docx_bytes))
    paragraphs = [
        paragraph.text
        for paragraph in doc.paragraphs
        if paragraph.text.strip()
    ]
    return "\n\n".join(paragraphs)


def parse_path_report_text(report_text, model, model_source=None, api_key=None):
    """
    Parse a pathology report using a specified ollama LLM and return the extracted information.
    """
    model_source = model_source or get_model_source(model)

    if model_source == "cloud":
        if not api_key:
            raise ValueError("Ollama Cloud API key is required for parsing with cloud models.")

        client = ollama.Client(
            host="https://ollama.com",
            headers={"Authorization": f"Bearer {api_key}"},
        )
    else:
        client = ollama.Client(host=get_ollama_base_url())

    response = client.chat(
        model = model, 
        messages = [
            {"role": "system", "content": PATH_REPORT_PROMPT},
            {"role": "user", "content": report_text}
        ],
        format = PATH_REPORT_SCHEMA,
        options={'temperature': 0.0},
    )
    content = response['message']['content']
    # print("Path report parser raw model response:")
    # print(content)
    try:
        data = parse_json_object(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse JSON from model response: {content}") from e

    validate_path_report_fields(data)
    
    diagnosis_parts = []
    if data.get("diagnosis"):
        diagnosis_parts.append(data["diagnosis"])
    if data.get("comments"):
        diagnosis_parts.append(data["comments"])
    if data.get("sample_type"):
        diagnosis_parts.append(data["sample_type"])

    if not (
        data.get("diagnosis") 
        or data.get("icd_code_descriptions")
        or data.get("comments")
    ):
        raise ValueError("The model response must contain at least one of the following fields: diagnosis, icd_code_descriptions, or comments.")
    
    input_record = build_oncotree_input_json(
        test_order_id=data.get("test_order_id"),
        sample_site=data.get("sample_site"),
        icd_code_descriptions=data.get("icd_code_descriptions"),
        path_lab_info="; ".join(diagnosis_parts) if diagnosis_parts else None,
    )
   
    return input_record


def report_text_to_oncotree_input(
    report_text,
    filename,
    parser_model,
    model_source=None,
    api_key=None,
):
    try:
        parsed = json.loads(report_text)
    except json.JSONDecodeError:
        parsed = None

    if is_oncotree_input_json(parsed):
        return normalize_oncotree_input_json(parsed, filename)

    parsed_report = parse_path_report_text(report_text, parser_model, model_source, api_key)

    return build_oncotree_input_json(
        icd_code_descriptions=parsed_report.get("icd_code_descriptions") or "",
        path_lab_info=parsed_report.get("path_lab_info") or "",
        test_order_id=Path(filename).stem,
        sample_site=parsed_report.get("sample_site") or "",
    )


def json_bytes_to_oncotree_input(file_bytes, filename):
    parsed = json.loads(file_bytes.decode("utf-8"))

    if is_oncotree_input_json(parsed):
        return normalize_oncotree_input_json(parsed, filename)

    raise ValueError("JSON must already match the OncoTree classifier input schema.")


def bytes_to_oncotree_input(
    filename,
    file_bytes,
    parser_model,
    model_source=None,
    api_key=None,
    pdf_text_getter=None,
):
    suffix = Path(filename).suffix.lower()

    if suffix == ".json":
        return json_bytes_to_oncotree_input(file_bytes, filename)

    if suffix == ".txt":
        report_text = file_bytes.decode("utf-8", errors="replace")
        return report_text_to_oncotree_input(
            report_text,
            filename,
            parser_model,
            model_source,
            api_key,
        )

    if suffix == ".docx":
        report_text = extract_docx_text(file_bytes)
        if not report_text.strip():
            raise ValueError("No readable text found in the DOCX file.")
        return report_text_to_oncotree_input(
            report_text,
            filename,
            parser_model,
            model_source,
            api_key,
        )

    if suffix == ".pdf":
        report_text = pdf_text_getter() if pdf_text_getter else convert_pdf_bytes_to_md(file_bytes)
        if is_empty_or_image_only_markdown(report_text):
            raise ValueError("No readable text extracted from the PDF.")
        return report_text_to_oncotree_input(
            report_text,
            filename,
            parser_model,
            model_source,
            api_key,
        )

    raise ValueError("Supported input types are .pdf, .txt, .docx, and classifier-ready .json.")


def file_path_to_oncotree_input(path, parser_model, model_source=None, api_key=None):
    path = Path(path)
    return bytes_to_oncotree_input(
        path.name,
        path.read_bytes(),
        parser_model,
        model_source,
        api_key,
    )


def uploaded_file_to_oncotree_input(
    uploaded_file,
    parser_model,
    model_source=None,
    api_key=None,
    pdf_text_getter=None,
):
    cached_pdf_text_getter = None
    if pdf_text_getter:
        cached_pdf_text_getter = lambda: pdf_text_getter(uploaded_file)

    return bytes_to_oncotree_input(
        uploaded_file.name,
        uploaded_file.getvalue(),
        parser_model,
        model_source,
        api_key,
        pdf_text_getter=cached_pdf_text_getter,
    )
