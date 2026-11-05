import pytest
from pathlib import Path
from src.core.config import AppConfig
from src.core.models import StudentGradeRecord, DispatchChannel, DispatchStatus
from src.core.database import DispatchDatabase
from src.services.whatsapp_service import MockWhatsAppProvider
from src.services.dispatcher import NotificationDispatcher


def test_dispatcher_dry_run(tmp_path):
    test_db_path = tmp_path / "test_dispatch.db"
    config = AppConfig()
    config.db_path = test_db_path
    
    mock_wa = MockWhatsAppProvider()
    db = DispatchDatabase(test_db_path)
    
    dispatcher = NotificationDispatcher(
        config=config,
        database=db,
        wa_provider=mock_wa,
        dry_run=True
    )
    
    student = StudentGradeRecord(
        student_id="220769",
        name="عبدالرحمن خالد سعد الدين",
        phone="+201120844781",
        email="test@example.com",
        course="Comp 304",
        midterm=12.0,
        lab=15.0,
        oral=5.0,
        total=32.0
    )
    
    results = dispatcher.dispatch_single_student(student, channel=DispatchChannel.BOTH)
    assert len(results) == 2
    assert all(r.status == DispatchStatus.SUCCESS for r in results)
    
    # Check SQLite audit log
    history = db.get_history()
    assert len(history) == 2
    assert history[0]["student_id"] == "220769"


def test_dispatcher_skipped_email(tmp_path):
    test_db_path = tmp_path / "test_dispatch2.db"
    config = AppConfig()
    config.db_path = test_db_path
    
    db = DispatchDatabase(test_db_path)
    mock_wa = MockWhatsAppProvider()
    dispatcher = NotificationDispatcher(
        config=config,
        database=db,
        wa_provider=mock_wa,
        dry_run=True
    )
    
    student_no_email = StudentGradeRecord(
        student_id="999",
        name="No Email Student",
        phone="+201100000000",
        email=None,
        course="Comp 304"
    )
    
    results = dispatcher.dispatch_single_student(student_no_email, channel=DispatchChannel.EMAIL)
    assert len(results) == 1
    assert results[0].status == DispatchStatus.SKIPPED
