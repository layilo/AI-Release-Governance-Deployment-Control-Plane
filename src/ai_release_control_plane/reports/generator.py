from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any


class ReportGenerator:
    def __init__(self, output_dir: Path) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write_json(self, name: str, payload: Any) -> Path:
        path = self.output_dir / f"{name}.json"
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, default=self._json_default)
            f.write("\n")
        return path

    def write_csv(self, name: str, rows: list[dict[str, Any]]) -> Path:
        path = self.output_dir / f"{name}.csv"
        headers: list[str] = []
        for row in rows:
            for key in row:
                if key not in headers:
                    headers.append(key)
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            if headers:
                writer.writeheader()
                for row in rows:
                    writer.writerow({key: self._stringify_csv_value(row.get(key)) for key in headers})
        return path

    def write_markdown(self, name: str, title: str, payload: Any) -> Path:
        path = self.output_dir / f"{name}.md"
        body = json.dumps(payload, indent=2, default=self._json_default)
        with path.open("w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n```json\n{body}\n```\n")
        return path

    def write_html(self, name: str, title: str, payload: Any) -> Path:
        path = self.output_dir / f"{name}.html"
        body = html.escape(json.dumps(payload, indent=2, default=self._json_default))
        with path.open("w", encoding="utf-8") as f:
            f.write(
                "<!DOCTYPE html>\n"
                "<html lang=\"en\">\n"
                "<head>\n"
                f"<meta charset=\"utf-8\">\n<title>{html.escape(title)}</title>\n"
                "</head>\n"
                "<body>\n"
                f"<h1>{html.escape(title)}</h1>\n"
                f"<pre>{body}</pre>\n"
                "</body>\n"
                "</html>\n"
            )
        return path

    @staticmethod
    def _json_default(value: Any) -> Any:
        if hasattr(value, "model_dump"):
            return value.model_dump(mode="json")
        if isinstance(value, Path):
            return str(value)
        return str(value)

    @classmethod
    def _stringify_csv_value(cls, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, default=cls._json_default)
        return str(value)
