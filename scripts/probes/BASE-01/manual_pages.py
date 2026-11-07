import sys
from pathlib import Path
_workspace=next(p for p in Path(__file__).resolve().parents if (p/"pyproject.toml").is_file())
sys.path[:0]=[str(_workspace),str(_workspace/"src")]
"""Extract selected installed manual pages into development evidence (zero-based indices)."""
import argparse
import json
from pathlib import Path

import pypdfium2
from zemax_mcp.config import Config


def extract(indices, output):
    source = Config.from_env().install_dir/'OpticStudio_UserManual_en.pdf'
    document = pypdfium2.PdfDocument(str(source))
    pages = []
    try:
        for index in indices:
            if not 0 <= index < len(document):
                raise ValueError(f'Page index outside manual: {index}')
            page = document[index]
            try:
                text = page.get_textpage()
                try:
                    pages.append(dict(page_index=index, text=text.get_text_range()))
                finally:
                    text.close()
            finally:
                page.close()
    finally:
        document.close()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(source=str(source), page_index_base=0, pages=pages),
        ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), page_indices=indices)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--page-index', type=int, action='append', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    extract(args.page_index, args.output)
