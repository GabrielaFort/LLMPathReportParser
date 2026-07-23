# LLM Path Report Parser

Prepare pathology reports for the [OncoTree classifier](https://github.com/HuntsmanCancerInstitute/OncoTree/tree/master).

This repository converts pathology reports into the JSON input format expected by the OncoTree classifier. It accepts `.pdf`, `.txt`, and `.docx` inputs. A local or cloud-hosted Ollama LLM is utilized to parse the input files.

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

Clone this repository and enter the project directory:
```bash
git clone https://github.com/GabrielaFort/LLMPathReportParser.git
cd LLMPathReportParser
```

Install required libraries:
```bash
python -m pip install -r requirements.txt
```

You also need Ollama running locally for local models, or an Ollama Cloud API key for cloud models.

## PHI Warning

Pathology reports may contain protected health information (PHI). Do not upload PHI or other sensitive patient data to cloud LLM models. For PHI-containing reports, use an approved local model or de-identify the reports before processing.

## Usage

```text
usage: python prepare_oncotree_input.py INPUT -m MODEL [options]

Convert a pathology report into OncoTree classifier input JSON.

positional arguments:
  INPUT                 Input report file: .pdf, .txt, or .docx.

required arguments:
  -m, --model MODEL     Ollama model for report parsing.

options:
  --api-key API_KEY     Ollama Cloud API key.
  --api-key-file FILE   File containing the Ollama Cloud API key.
  --ollama-host URL     Local Ollama host URL, e.g. http://127.0.0.1:11434.
                        Ignored for cloud models.
  -o, --output FILE     Output JSON file. If omitted, JSON is printed to stdout.
  -h, --help            Show the command help message and exit.
```

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

If local Ollama is running on a non-default host or port, pass it explicitly:

```bash
python prepare_oncotree_input.py report.pdf \
  -m gemma4:e4b \
  --ollama-host http://127.0.0.1:46021 \
  -o input_json/report.json
```

You can also set `OLLAMA_HOST` instead of passing `--ollama-host` each time:

```bash
export OLLAMA_HOST=http://127.0.0.1:46021
python prepare_oncotree_input.py report.pdf -m gemma4:e4b -o input_json/report.json
```

For local models, host resolution uses this order:

```text
--ollama-host argument -> OLLAMA_HOST environment variable -> http://localhost:11434
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
