# LLM Path Report Parser

Prepare pathology reports or molecular testing results for the [OncoTree classifier](https://github.com/HuntsmanCancerInstitute/OncoTree/tree/master).

This repository converts pathology reports or test results into the JSON input format expected by the OncoTree classifier. It accepts `.pdf`, `.txt`, and `.docx` inputs. A local or cloud-hosted Ollama LLM is utilized to parse the input files.

**Warning: Do not upload any PHI/PII to cloud-hosted AI models or unapproved systems. To run the application using local models, read the instructions below.**

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

Pathology/testing reports may contain protected health information (PHI). Do not upload PHI or other sensitive patient data to cloud LLM models. For PHI-containing reports, use an approved local model or de-identify the reports before processing.

## Usage

```text
usage: python prepare_oncotree_input.py INPUT -m MODEL [options]

Convert a report into OncoTree classifier input JSON.

positional arguments:
  INPUT                 Input report file: .pdf, .txt, or .docx.

required arguments:
  -m, --model MODEL     Ollama model for report parsing.

options:
  --model-source {local,cloud} Where to run the model. Default: local.
  --api-key API_KEY            Ollama Cloud API key.
  --api-key-file FILE          File containing the Ollama Cloud API key.
  --ollama-host URL            Optional local Ollama host URL, e.g. http://127.0.0.1:11434. Ignored for cloud models.
  --pdf-page-limit N           Only process the first N pages of PDF inputs. Default: process all pages.
  -o, --output FILE            Output JSON file. If omitted, JSON is printed to stdout.
  -h, --help                   Show the command help message and exit.
```

Print classifier input JSON to the terminal:

```bash
python prepare_oncotree_input.py report.pdf -m gemma4:e4b
```

Write classifier input JSON to a file:

```bash
python prepare_oncotree_input.py report.pdf -m gemma4:e4b -o input_json/report.json
```

Only process the first N pages of a PDF:

```bash
python prepare_oncotree_input.py report.pdf \
  -m gemma4:e4b \
  --pdf-page-limit 5 \
  -o input_json/report.json
```

If `--pdf-page-limit` is omitted, the full PDF is processed. Setting a page limit for long reports where the majority of diagnosis information is within the first few pages can reduce processing time.

TXT and DOCX reports use the same command:

```bash
python prepare_oncotree_input.py report.txt -m gemma4:e4b -o input_json/report.json
python prepare_oncotree_input.py report.docx -m gemma4:e4b -o input_json/report.json
```

By default, the parser uses Ollama's default local host. If Ollama is running on a non-default host or port, pass it explicitly:

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

For Ollama Cloud models, explicitly set `--model-source cloud` and pass an API key:

Warning: this sends report content to Ollama Cloud. Do not use cloud models with PHI-containing reports.

```bash
python prepare_oncotree_input.py report.pdf \
  -m glm-5.2:cloud \
  --model-source cloud \
  --api-key-file key.txt \
  -o input_json/report.json
```

Local is the default model source. 

## Files

- `report_input_parser.py`: shared parser logic for PDF/TXT/DOCX to classifier input JSON
- `prepare_oncotree_input.py`: command-line entry point
