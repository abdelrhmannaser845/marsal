import time
import random
from typing import List, Optional, Callable, Dict, Any
from datetime import datetime

from src.core.config import AppConfig
from src.core.models import (
    StudentGradeRecord,
    DispatchChannel,
    DispatchStatus,
    DispatchResult
)
from src.core.database import DispatchDatabase
from src.services.templating import TemplateEngine
from src.services.email_service import EmailService
from src.services.whatsapp_service import BaseWhatsAppProvider, get_whatsapp_provider


class NotificationDispatcher:
    """
    Coordinates batch delivery across WhatsApp and Email channels with
    anti-ban throttling and SQLite audit logging.
    """

    def __init__(
        self,
        config: AppConfig,
        database: Optional[DispatchDatabase] = None,
        email_service: Optional[EmailService] = None,
        wa_provider: Optional[BaseWhatsAppProvider] = None,
        template_engine: Optional[TemplateEngine] = None,
        dry_run: bool = False
    ):
        self.config = config
        self.dry_run = dry_run
        self.database = database or DispatchDatabase(config.db_path)
        self.email_service = email_service or EmailService(config.smtp)
        self.wa_provider = wa_provider or get_whatsapp_provider(config.whatsapp, dry_run=dry_run)
        self.templates = template_engine or TemplateEngine()

    def _apply_throttle(self, on_sleep: Optional[Callable[[float], None]] = None):
        """Sleep for a randomized duration between successive messages to prevent ban flags."""
        min_sec = self.config.throttle.min_delay_seconds
        max_sec = self.config.throttle.max_delay_seconds
        if self.dry_run:
            # Brief pause during dry runs
            delay = 0.2
        else:
            delay = round(random.uniform(min_sec, max_sec), 2)
            
        if on_sleep:
            on_sleep(delay)
        time.sleep(delay)

    def dispatch_single_student(
        self,
        student: StudentGradeRecord,
        channel: DispatchChannel,
        wa_template: str = "wa_grade_report.txt.j2",
        email_template: str = "email_grade_report.html.j2",
        email_subject: Optional[str] = None
    ) -> List[DispatchResult]:
        """Dispatch notifications for a single student to selected channel(s)."""
        results: List[DispatchResult] = []
        now_iso = datetime.now().isoformat()
        subject = email_subject or f"Grade Report: {student.course} - {student.name}"

        # 1. WhatsApp Channel
        if channel in (DispatchChannel.WHATSAPP, DispatchChannel.BOTH):
            wa_text = self.templates.render_whatsapp(student, template_name=wa_template)
            success, err = self.wa_provider.send_message(student.phone, wa_text)
            
            status = DispatchStatus.SUCCESS if success else DispatchStatus.FAILED
            res = DispatchResult(
                student_id=student.student_id,
                recipient=student.phone,
                channel=DispatchChannel.WHATSAPP,
                status=status,
                message_snippet=wa_text[:120],
                error_message=err,
                timestamp=now_iso
            )
            self.database.log(res, student_name=student.name, message_preview=wa_text)
            results.append(res)

        # 2. Email Channel
        if channel in (DispatchChannel.EMAIL, DispatchChannel.BOTH):
            if not student.email:
                res = DispatchResult(
                    student_id=student.student_id,
                    recipient="NO_EMAIL",
                    channel=DispatchChannel.EMAIL,
                    status=DispatchStatus.SKIPPED,
                    message_snippet="",
                    error_message="Student record does not include an email address",
                    timestamp=now_iso
                )
                self.database.log(res, student_name=student.name)
                results.append(res)
            else:
                html_body = self.templates.render_email_html(student, template_name=email_template)
                plain_body = self.templates.render_email_plain(student, template_name=wa_template)
                
                if self.dry_run:
                    success, err = True, None
                else:
                    success, err = self.email_service.send_email(
                        recipient=student.email,
                        subject=subject,
                        html_content=html_body,
                        plain_content=plain_body
                    )

                status = DispatchStatus.SUCCESS if success else DispatchStatus.FAILED
                res = DispatchResult(
                    student_id=student.student_id,
                    recipient=student.email,
                    channel=DispatchChannel.EMAIL,
                    status=status,
                    message_snippet=subject,
                    error_message=err,
                    timestamp=now_iso
                )
                self.database.log(res, student_name=student.name, message_preview=subject)
                results.append(res)

        return results

    def dispatch_batch(
        self,
        records: List[StudentGradeRecord],
        channel: DispatchChannel,
        wa_template: str = "wa_grade_report.txt.j2",
        email_template: str = "email_grade_report.html.j2",
        email_subject: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int, StudentGradeRecord, List[DispatchResult]], None]] = None,
        throttle_callback: Optional[Callable[[float], None]] = None
    ) -> List[DispatchResult]:
        """Dispatch notifications across the entire batch with rate limiting."""
        all_results: List[DispatchResult] = []
        total = len(records)

        for idx, student in enumerate(records, start=1):
            results = self.dispatch_single_student(
                student=student,
                channel=channel,
                wa_template=wa_template,
                email_template=email_template,
                email_subject=email_subject
            )
            all_results.extend(results)

            if progress_callback:
                progress_callback(idx, total, student, results)

            # Throttle between successive students if not the last item
            if idx < total:
                self._apply_throttle(throttle_callback)

        return all_results
