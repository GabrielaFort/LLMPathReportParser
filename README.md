# LLM Path Report Parser

Prepare pathology reports for the OncoTree classifier.

This repository converts `.pdf`, `.txt`, and `.docx` pathology reports into the JSON input format expected by the OncoTree classifier. It does not run the classifier.

## Output Format

Each output file is one JSON record:

```json
{
  "icd_code_descriptions": "",
  "path_lab_info": "",
  "test_order_id": "",
  "sample_site": ""
}
```

## Install

```bash
python -m pip install -r requirements.txt
```

You also need Ollama running locally for local models, or an Ollama Cloud API key for cloud models.

## PHI Warning

Pathology reports may contain protected health information (PHI). Do not upload PHI or other sensitive patient data to cloud LLM models. For PHI-containing reports, use an approved local model or de-identify the reports before processing.

## Usage

Print classifier input JSON to the terminal:

```bash
python prepare_oncotree_input.py report.pdf -m gemma4:e4b
```

Write classifier input JSON to a file:

```bash
python prepare_oncotree_input.py report.pdf -m gemma4:e4b -o input_json/report.json
```

TXT and DOCX reports use the same command:

```bash
python prepare_oncotree_input.py report.txt -m gemma4:e4b -o input_json/report.json
python prepare_oncotree_input.py report.docx -m gemma4:e4b -o input_json/report.json
```

For Ollama Cloud models, pass the cloud model name and API key. Any model name containing `cloud` is treated as a cloud model:

Warning: this sends report content to Ollama Cloud. Do not use cloud models with PHI-containing reports.

```bash
python prepare_oncotree_input.py report.pdf \
  -m gemma4:31b-cloud \
  --api-key-file key.txt \
  -o input_json/report.json
```

## Files

- `report_input_parser.py`: shared parser logic for PDF/TXT/DOCX to classifier input JSON
- `prepare_oncotree_input.py`: command-line entry point
