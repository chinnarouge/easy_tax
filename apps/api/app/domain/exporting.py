from __future__ import annotations

import csv
from io import BytesIO, StringIO

from apps.api.app.domain.field_catalog import get_field_mapping, load_field_catalog
from apps.api.app.domain.store import TaxReturnRecord, calculate_completion


def build_csv_export(record: TaxReturnRecord) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["field_id", "form", "line", "value"])

    for section, values in record.sections.items():
        for field_name, value in values.items():
            mapping = get_field_mapping(f"{section}.{field_name}")
            form = mapping["elster_form"] if mapping else section
            line = mapping["elster_line"] if mapping else "manual review"
            writer.writerow([f"{section}.{field_name}", form, line, value])

    return buffer.getvalue()


def _pdf_escape(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf_export(record: TaxReturnRecord) -> bytes:
    lines = [
        f"SteuerHelfer export for tax year {record.tax_year}",
        f"Status: {record.status}",
        f"Completion: {calculate_completion(record)}%",
        "",
        "Required Anlagen:",
    ]
    lines.extend(f"- {anlage}" for anlage in record.required_anlagen)
    lines.append("")
    lines.append("Field mapping overview:")

    for catalog_entry in load_field_catalog():
        lines.append(
            f"- {catalog_entry['internal_id']}: {catalog_entry['elster_form']} / {catalog_entry['elster_line']}"
        )

    content_lines = [f"({_pdf_escape(line)}) Tj" for line in lines]
    stream_text = "BT /F1 11 Tf 72 760 Td " + " T* ".join(content_lines) + " ET"
    stream_bytes = stream_text.encode("latin-1", errors="ignore")

    pdf = BytesIO()
    offsets: list[int] = []

    def write(chunk: bytes) -> None:
        pdf.write(chunk)

    write(b"%PDF-1.4\n")

    def add_object(obj_num: int, body: bytes) -> None:
        offsets.append(pdf.tell())
        write(f"{obj_num} 0 obj\n".encode())
        write(body)
        write(b"\nendobj\n")

    add_object(1, b"<< /Type /Catalog /Pages 2 0 R >>")
    add_object(2, b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    add_object(
        3,
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
    )
    add_object(4, b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    add_object(5, f"<< /Length {len(stream_bytes)} >>\nstream\n".encode() + stream_bytes + b"\nendstream")

    xref_offset = pdf.tell()
    write(f"xref\n0 {len(offsets) + 1}\n".encode())
    write(b"0000000000 65535 f \n")
    for offset in offsets:
        write(f"{offset:010d} 00000 n \n".encode())
    write(
        (
            "trailer\n"
            f"<< /Size {len(offsets) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF"
        ).encode()
    )
    return pdf.getvalue()