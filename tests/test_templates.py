import pytest
from src.core.models import StudentGradeRecord
from src.services.templating import TemplateEngine


@pytest.fixture
def sample_student():
    return StudentGradeRecord(
        student_id="220769",
        name="عبدالرحمن خالد سعد الدين",
        phone="+201120844781",
        email="abdelrhmannaser06@gmail.com",
        course="Comp 304 Compiler Design - Spring",
        midterm=12.0,
        lab=15.0,
        oral=5.0,
        bonus=0.0,
        total=32.0,
        notes="Score after adding extra bonus"
    )


def test_render_whatsapp_original_style(sample_student):
    engine = TemplateEngine()
    rendered = engine.render_whatsapp(sample_student, "wa_grade_report.txt.j2")
    assert "عبدالرحمن خالد سعد الدين" in rendered
    assert "220769" in rendered
    assert "12/15, 15/37, 5/8, 32/60." in rendered
    assert "Good luck ^_^" in rendered


def test_render_whatsapp_styled(sample_student):
    engine = TemplateEngine()
    rendered = engine.render_whatsapp(sample_student, "wa_grade_report_styled.txt.j2")
    assert "Academic Performance Notification" in rendered
    assert "220769" in rendered
    assert "Midterm: 12.0 / 15" in rendered


def test_render_email_html(sample_student):
    engine = TemplateEngine()
    rendered = engine.render_email_html(sample_student, "email_grade_report.html.j2")
    assert "Comp 304 Compiler Design" in rendered
    assert "عبدالرحمن خالد سعد الدين" in rendered
    assert "32.0" in rendered


def test_render_email_retro(sample_student):
    engine = TemplateEngine()
    rendered = engine.render_email_html(sample_student, "email_retro_alert.html.j2")
    assert "SYSTEM — ACADEMIC DISPATCH" in rendered
    assert "220769" in rendered
