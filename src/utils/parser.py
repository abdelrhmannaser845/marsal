import csv
from pathlib import Path
from typing import List, Dict, Any, Tuple, Optional
import openpyxl
from src.core.models import StudentGradeRecord
from src.utils.phone import normalize_phone


# Column alias mapping for resilient ingestion
COLUMN_ALIASES = {
    "student_id": ["student_id", "student id", "id", "code", "registration_no", "كود الطالب", "رقم القيد", "الرقم التعريفي"],
    "name": ["name", "student_name", "student name", "full_name", "اسم الطالب", "الاسم"],
    "phone": ["phone", "phone_number", "mobile", "cell", "whatsapp", "wa_number", "رقم الهاتف", "الموبايل", "تليفون", "الواتساب"],
    "email": ["email", "student_email", "mail", "البريد", "البريد الإلكتروني", "ايميل"],
    "course": ["course", "course_name", "subject", "module", "المادة", "المقرر"],
    "midterm": ["midterm", "mid", "نصفي", "أعمال سنة"],
    "midterm_max": ["midterm_max", "max_midterm"],
    "lab": ["lab", "practical", "عملي", "المختبر"],
    "lab_max": ["lab_max", "max_lab"],
    "oral": ["oral", "شفوي", "الشفهي"],
    "oral_max": ["oral_max", "max_oral"],
    "bonus": ["bonus", "extra", "بونص", "إضافي"],
    "total": ["total", "score", "grade", "المجموع", "الدرجة النهائية"],
    "total_max": ["total_max", "max_total"],
    "notes": ["notes", "remarks", "comments", "ملاحظات"]
}


def _match_column(col_name: str) -> Optional[str]:
    """Match a raw header string to a canonical field name."""
    clean = str(col_name).strip().lower().replace("-", "_").replace(" ", "_")
    for canonical, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            if clean == alias.lower().replace("-", "_").replace(" ", "_"):
                return canonical
    return None


def _to_float(val: Any) -> Optional[float]:
    """Safely convert value to float or return None."""
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_csv_file(file_path: Path) -> List[Dict[str, Any]]:
    """Reads a CSV file trying utf-8-sig, utf-8, and cp1256 encodings."""
    path = Path(file_path)
    encodings = ["utf-8-sig", "utf-8", "cp1256", "latin-1"]
    
    for enc in encodings:
        try:
            with open(path, mode="r", encoding=enc) as f:
                reader = csv.DictReader(f)
                rows = [dict(row) for row in reader]
                return rows
        except (UnicodeDecodeError, csv.Error):
            continue
            
    raise ValueError(f"Could not decode CSV file '{file_path}' with supported encodings.")


def parse_excel_file(file_path: Path) -> List[Dict[str, Any]]:
    """Reads an Excel (.xlsx) file into a list of row dictionaries."""
    wb = openpyxl.load_workbook(filename=str(file_path), data_only=True)
    sheet = wb.active
    
    rows = list(sheet.iter_rows(values_only=True))
    if not rows:
        return []
        
    headers = [str(h).strip() if h is not None else f"col_{idx}" for idx, h in enumerate(rows[0])]
    data_rows = []
    
    for row in rows[1:]:
        if not any(row):  # skip empty lines
            continue
        row_dict = {}
        for header, val in zip(headers, row):
            row_dict[header] = val
        data_rows.append(row_dict)
        
    return data_rows


def ingest_records(
    file_path: Path,
    default_course: str = "Comp 304 Compiler Design - Spring",
    default_region: str = "EG"
) -> Tuple[List[StudentGradeRecord], List[Dict[str, Any]]]:
    """
    Ingests student records from either CSV or Excel file.
    
    Returns:
        (valid_records, errors)
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if path.suffix.lower() == ".csv":
        raw_rows = parse_csv_file(path)
    elif path.suffix.lower() in [".xlsx", ".xlsm", ".xltx"]:
        raw_rows = parse_excel_file(path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}. Please provide .csv or .xlsx")

    valid_records: List[StudentGradeRecord] = []
    errors: List[Dict[str, Any]] = []

    for index, row in enumerate(raw_rows, start=2):
        try:
            mapped_data: Dict[str, Any] = {}
            extra_data: Dict[str, Any] = {}

            for col_raw, val in row.items():
                canonical = _match_column(col_raw)
                if canonical:
                    mapped_data[canonical] = val
                else:
                    extra_data[str(col_raw).strip()] = val

            # Required field checks
            raw_id = mapped_data.get("student_id")
            raw_name = mapped_data.get("name")
            raw_phone = mapped_data.get("phone")

            if not raw_id or not raw_name or not raw_phone:
                missing = []
                if not raw_id: missing.append("student_id")
                if not raw_name: missing.append("name")
                if not raw_phone: missing.append("phone")
                errors.append({
                    "row": index,
                    "student_id": raw_id or "UNKNOWN",
                    "error": f"Missing mandatory field(s): {', '.join(missing)}"
                })
                continue

            normalized_phone = normalize_phone(raw_phone, default_region=default_region)
            course_name = mapped_data.get("course") or default_course

            # Numerical conversions
            midterm = _to_float(mapped_data.get("midterm"))
            midterm_max = _to_float(mapped_data.get("midterm_max")) or 15.0
            lab = _to_float(mapped_data.get("lab"))
            lab_max = _to_float(mapped_data.get("lab_max")) or 37.0
            oral = _to_float(mapped_data.get("oral"))
            oral_max = _to_float(mapped_data.get("oral_max")) or 8.0
            bonus = _to_float(mapped_data.get("bonus")) or 0.0
            total = _to_float(mapped_data.get("total"))
            total_max = _to_float(mapped_data.get("total_max")) or 60.0

            # If total is not provided in sheet, compute automatically
            if total is None and any(v is not None for v in [midterm, lab, oral]):
                total = (midterm or 0.0) + (lab or 0.0) + (oral or 0.0) + bonus

            record = StudentGradeRecord(
                student_id=str(raw_id).strip(),
                name=str(raw_name).strip(),
                phone=normalized_phone,
                email=str(mapped_data.get("email")).strip() if mapped_data.get("email") else None,
                course=str(course_name).strip(),
                midterm=midterm,
                midterm_max=midterm_max,
                lab=lab,
                lab_max=lab_max,
                oral=oral,
                oral_max=oral_max,
                bonus=bonus,
                total=total,
                total_max=total_max,
                notes=str(mapped_data.get("notes")).strip() if mapped_data.get("notes") else None,
                extra_fields=extra_data
            )
            valid_records.append(record)

        except Exception as e:
            errors.append({
                "row": index,
                "student_id": str(row.get("student_id") or row.get("id") or "UNKNOWN"),
                "error": str(e)
            })

    return valid_records, errors
