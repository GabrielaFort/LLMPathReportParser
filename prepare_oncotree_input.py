import argparse
import json
from pathlib import Path

from report_input_parser import file_path_to_oncotree_input, normalize_model_source


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert a pathology report into OncoTree classifier input JSON."
    )
    parser.add_argument("input", help="Input report file: .pdf, .txt, or .docx.")
    parser.add_argument("-m", "--model", required=True, help="Ollama model for report parsing.")
    parser.add_argument(
        "--model-source",
        choices=["local", "cloud"],
        default="local",
        help="Where to run the model. Default: local.",
    )
    parser.add_argument("--api-key", help="Ollama Cloud API key.")
    parser.add_argument("--api-key-file", help="File containing the Ollama Cloud API key.")
    parser.add_argument(
        "--ollama-host",
        help="Local Ollama host URL, e.g. http://127.0.0.1:11434. Ignored for cloud models.",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Output JSON file. If omitted, JSON is printed to stdout.",
    )
    return parser.parse_args()


def get_api_key(args):
    if args.api_key:
        return args.api_key

    if args.api_key_file:
        return Path(args.api_key_file).read_text(encoding="utf-8").strip()

    return None


def main():
    args = parse_args()
    input_path = Path(args.input)
    api_key = get_api_key(args)
    model_source = normalize_model_source(args.model_source)

    if model_source == "cloud" and not api_key:
        raise SystemExit("Cloud models require --api-key or --api-key-file.")

    input_record = file_path_to_oncotree_input(
        input_path,
        args.model,
        model_source,
        api_key,
        ollama_host=args.ollama_host,
    )
    output_json = json.dumps(input_record, indent=2)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json + "\n", encoding="utf-8")
    else:
        print(output_json)


if __name__ == "__main__":
    main()
