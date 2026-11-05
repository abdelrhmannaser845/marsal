from pathlib import Path
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
from src.core.models import StudentGradeRecord


class TemplateEngine:
    """Renders WhatsApp and Email templates using Jinja2."""

    def __init__(self, template_dir: Optional[Path] = None):
        if template_dir is None:
            template_dir = Path(__file__).resolve().parent.parent / "templates"
        self.template_dir = Path(template_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(["html", "xml"]),
            trim_blocks=True,
            lstrip_blocks=True
        )

    def render_whatsapp(
        self,
        student: StudentGradeRecord,
        template_name: str = "wa_grade_report.txt.j2",
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render WhatsApp text notification."""
        template = self.env.get_template(template_name)
        ctx = {"student": student}
        if extra_context:
            ctx.update(extra_context)
        return template.render(**ctx).strip()

    def render_email_html(
        self,
        student: StudentGradeRecord,
        template_name: str = "email_grade_report.html.j2",
        extra_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Render HTML email body."""
        template = self.env.get_template(template_name)
        ctx = {"student": student}
        if extra_context:
            ctx.update(extra_context)
        return template.render(**ctx)

    def render_email_plain(
        self,
        student: StudentGradeRecord,
        template_name: str = "wa_grade_report.txt.j2"
    ) -> str:
        """Render plain text fallback for email."""
        return self.render_whatsapp(student, template_name=template_name)
