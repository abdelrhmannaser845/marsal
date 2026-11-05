#!/usr/bin/env python3
"""
Multi-Channel Academic Notification & Dispatch System CLI
"""

import sys
from pathlib import Path
from typing import Optional

# Ensure standard output and error handles UTF-8 properly on Windows consoles
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint
import openpyxl

from src.core.config import get_config
from src.core.models import DispatchChannel, DispatchStatus
from src.core.database import DispatchDatabase
from src.utils.parser import ingest_records
from src.services.templating import TemplateEngine
from src.services.email_service import EmailService
from src.services.whatsapp_service import get_whatsapp_provider
from src.services.dispatcher import NotificationDispatcher

app = typer.Typer(
    name="notify",
    help="Multi-Channel Notification & Automation System for Student Academic Dispatch",
    add_completion=False
)
console = Console(legacy_windows=False)


@app.command()
def preview(
    file: Path = typer.Option(Path("data/students_sample.csv"), "--file", "-f", help="Path to CSV or Excel file"),
    student_id: Optional[str] = typer.Option(None, "--id", help="Optional student ID to preview (default: first record)"),
    channel: str = typer.Option("both", "--channel", "-c", help="wa, email, or both"),
    wa_template: str = typer.Option("wa_grade_report.txt.j2", "--template-wa", help="WhatsApp template file"),
    email_template: str = typer.Option("email_grade_report.html.j2", "--template-email", help="Email template file")
):
    """
    Preview rendered WhatsApp and/or Email notifications without sending.
    """
    if not file.exists():
        console.print(f"[bold red]Error:[/bold red] File not found: {file}")
        raise typer.Exit(1)

    records, errors = ingest_records(file)
    if not records:
        console.print(f"[bold red]Error:[/bold red] No valid student records found in {file}.")
        if errors:
            console.print(f"[yellow]Ingestion errors:[/yellow] {errors}")
        raise typer.Exit(1)

    selected = None
    if student_id:
        for r in records:
            if r.student_id == student_id:
                selected = r
                break
        if not selected:
            console.print(f"[bold red]Error:[/bold red] Student ID '{student_id}' not found in records.")
            raise typer.Exit(1)
    else:
        selected = records[0]

    engine = TemplateEngine()

    console.print(Panel(
        f"[bold cyan]Student Record Preview[/bold cyan]\n"
        f"ID: {selected.student_id} | Name: {selected.name}\n"
        f"Phone: {selected.phone} | Email: {selected.email or 'N/A'}\n"
        f"Course: {selected.course}",
        border_style="cyan"
    ))

    if channel.lower() in ("wa", "whatsapp", "both"):
        wa_text = engine.render_whatsapp(selected, template_name=wa_template)
        console.print(Panel(wa_text, title=f"[green]WhatsApp Message ({wa_template})[/green]", border_style="green"))

    if channel.lower() in ("email", "both"):
        html_code = engine.render_email_html(selected, template_name=email_template)
        syntax = Syntax(html_code[:1200] + "\n... [content truncated for preview] ...", "html", theme="monokai", line_numbers=True)
        console.print(Panel(syntax, title=f"[blue]Email HTML Preview ({email_template})[/blue]", border_style="blue"))


@app.command()
def send(
    file: Path = typer.Option(..., "--file", "-f", help="Path to student records (.csv or .xlsx)"),
    channel: str = typer.Option("wa", "--channel", "-c", help="Delivery channel: wa, email, or both"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Simulate dispatches without actually sending messages"),
    wa_template: str = typer.Option("wa_grade_report.txt.j2", "--template-wa", help="WhatsApp Jinja2 template"),
    email_template: str = typer.Option("email_grade_report.html.j2", "--template-email", help="Email Jinja2 template"),
    min_delay: Optional[float] = typer.Option(None, "--min-delay", help="Minimum anti-ban delay (seconds)"),
    max_delay: Optional[float] = typer.Option(None, "--max-delay", help="Maximum anti-ban delay (seconds)")
):
    """
    Dispatch student grade notices via WhatsApp, Email, or Both.
    """
    config = get_config()
    if min_delay is not None:
        config.throttle.min_delay_seconds = min_delay
    if max_delay is not None:
        config.throttle.max_delay_seconds = max_delay

    # Validate channel
    ch_map = {
        "wa": DispatchChannel.WHATSAPP,
        "whatsapp": DispatchChannel.WHATSAPP,
        "email": DispatchChannel.EMAIL,
        "mail": DispatchChannel.EMAIL,
        "both": DispatchChannel.BOTH
    }
    selected_channel = ch_map.get(channel.lower())
    if not selected_channel:
        console.print(f"[bold red]Error:[/bold red] Unknown channel '{channel}'. Choose from 'wa', 'email', 'both'.")
        raise typer.Exit(1)

    console.print(Panel(
        f"[bold]Batch Notification Dispatch[/bold]\n"
        f"File: [yellow]{file}[/yellow]\n"
        f"Channel: [magenta]{selected_channel.value.upper()}[/magenta]\n"
        f"Dry-Run Mode: [{'green]ACTIVE' if dry_run else 'red]OFF (LIVE TRANSMISSION)'}[/]\n"
        f"Throttling Window: [cyan]{config.throttle.min_delay_seconds}s - {config.throttle.max_delay_seconds}s[/cyan]",
        border_style="magenta"
    ))

    # Ingest file
    with console.status("[bold green]Ingesting student records..."):
        records, errors = ingest_records(file)

    if errors:
        console.print(f"[yellow]Encountered {len(errors)} row validation warning(s):[/yellow]")
        for err in errors[:5]:
            console.print(f"  [red]• Row {err.get('row')}:[/red] {err.get('error')}")
        if len(errors) > 5:
            console.print(f"  ... and {len(errors) - 5} more.")

    if not records:
        console.print("[bold red]No valid student records found to dispatch. Exiting.[/bold red]")
        raise typer.Exit(1)

    console.print(f"[bold green]Ready to dispatch {len(records)} student record(s).[/bold green]\n")

    dispatcher = NotificationDispatcher(config=config, dry_run=dry_run)

    # Progress tracking
    results = []
    for idx, student in enumerate(records, start=1):
        console.print(f"[bold cyan][{idx}/{len(records)}][/bold cyan] Processing: [bold]{student.name}[/bold] (ID: {student.student_id})")
        student_results = dispatcher.dispatch_single_student(
            student=student,
            channel=selected_channel,
            wa_template=wa_template,
            email_template=email_template
        )
        results.extend(student_results)

        for res in student_results:
            icon = "[+]" if res.status == DispatchStatus.SUCCESS else ("[!]" if res.status == DispatchStatus.SKIPPED else "[-]")
            color = "green" if res.status == DispatchStatus.SUCCESS else ("yellow" if res.status == DispatchStatus.SKIPPED else "red")
            err_str = f" - Reason: {res.error_message}" if res.error_message else ""
            console.print(f"   {icon} [{color}]{res.channel.value.upper()}[/{color}] -> {res.recipient} [{res.status.value}]{err_str}")

        if idx < len(records):
            def sleep_cb(sec):
                console.print(f"   ... [dim]Throttling pause ({sec}s) for anti-ban rate limiting...[/dim]")
            dispatcher._apply_throttle(sleep_cb)

    # Summary table
    table = Table(title="Dispatch Summary Report", show_header=True, header_style="bold blue")
    table.add_column("Channel", style="dim")
    table.add_column("Total Attempted", justify="right")
    table.add_column("Successful", justify="right", style="green")
    table.add_column("Failed", justify="right", style="red")
    table.add_column("Skipped", justify="right", style="yellow")

    for ch in [DispatchChannel.WHATSAPP, DispatchChannel.EMAIL]:
        ch_results = [r for r in results if r.channel == ch]
        if ch_results:
            s_count = sum(1 for r in ch_results if r.status == DispatchStatus.SUCCESS)
            f_count = sum(1 for r in ch_results if r.status == DispatchStatus.FAILED)
            k_count = sum(1 for r in ch_results if r.status == DispatchStatus.SKIPPED)
            table.add_row(ch.value.upper(), str(len(ch_results)), str(s_count), str(f_count), str(k_count))

    console.print("\n")
    console.print(table)


@app.command()
def test_connection(
    channel: str = typer.Option("all", "--channel", "-c", help="email, wa, or all")
):
    """
    Test SMTP and WhatsApp provider credentials and setup.
    """
    config = get_config()
    console.print("[bold cyan]Testing Delivery Channels Connectivity...[/bold cyan]\n")

    # 1. Test Email
    if channel.lower() in ("email", "mail", "all"):
        email_svc = EmailService(config.smtp)
        ok, msg = email_svc.test_connection()
        if ok:
            console.print(f"  [green][OK] SMTP Email Service:[/green] {msg}")
        else:
            console.print(f"  [red][X] SMTP Email Service:[/red] {msg}")

    # 2. Test WhatsApp
    if channel.lower() in ("wa", "whatsapp", "all"):
        wa_prov = get_whatsapp_provider(config.whatsapp, dry_run=False)
        ok, msg = wa_prov.test_connection()
        if ok:
            console.print(f"  [green][OK] WhatsApp Provider ({config.whatsapp.provider}):[/green] {msg}")
        else:
            console.print(f"  [red][X] WhatsApp Provider ({config.whatsapp.provider}):[/red] {msg}")


@app.command()
def history(
    limit: int = typer.Option(20, "--limit", "-n", help="Number of recent dispatches to display"),
    channel: Optional[str] = typer.Option(None, "--channel", "-c", help="Filter by channel (wa, email)")
):
    """
    View dispatch audit log history stored in SQLite.
    """
    config = get_config()
    db = DispatchDatabase(config.db_path)
    records = db.get_history(limit=limit, channel=channel)
    summary = db.get_summary()

    if not records:
        console.print("[yellow]No dispatch history recorded yet.[/yellow]")
        return

    table = Table(title=f"Dispatch Audit History (Last {len(records)} Events)", show_header=True, header_style="bold magenta")
    table.add_column("ID", justify="right", style="dim")
    table.add_column("Timestamp", style="cyan")
    table.add_column("Student", style="bold")
    table.add_column("Channel", justify="center")
    table.add_column("Recipient")
    table.add_column("Status", justify="center")
    table.add_column("Error", style="red")

    for r in records:
        status_style = "green" if r["status"] == "SUCCESS" else ("yellow" if r["status"] == "SKIPPED" else "red")
        table.add_row(
            str(r["id"]),
            str(r["timestamp"])[:19].replace("T", " "),
            f"{r['student_name']} ({r['student_id']})",
            r["channel"].upper(),
            r["recipient"],
            f"[{status_style}]{r['status']}[/{status_style}]",
            r["error_message"] or ""
        )

    console.print(table)
    console.print(
        f"[dim]Total: {summary['total']} | Success: [green]{summary['success']}[/green] | "
        f"Failed: [red]{summary['failed']}[/red] | Skipped: [yellow]{summary['skipped']}[/yellow][/dim]"
    )


@app.command()
def generate_sample(
    output_dir: Path = typer.Option(Path("data"), "--dir", "-d", help="Directory to save sample files")
):
    """
    Generate sample CSV and Excel (.xlsx) files with student grade templates.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "students_sample.csv"
    xlsx_path = output_dir / "students_sample.xlsx"

    sample_rows = [
        ["student_id", "name", "phone", "email", "course", "midterm", "lab", "oral", "bonus", "total", "notes"],
        ["220769", "عبدالرحمن خالد سعد الدين", "01120844781", "abdelrhmannaser06@gmail.com", "Comp 304 Compiler Design - Spring", 12, 15, 5, 0, 32, "Score after adding extra bonus"],
        ["220770", "Sarah Ahmed Mahmoud", "+201012345678", "sarah.ahmed@example.com", "Comp 304 Compiler Design - Spring", 14, 35, 8, 2, 59, "Outstanding lab project"],
        ["220771", "Mohamed Omar Farouk", "01298765432", "mohamed.omar@example.com", "Comp 304 Compiler Design - Spring", 10, 28, 6, 0, 44, "Solid parser implementation"],
        ["220772", "Nour Ibrahim Youssef", "01555554321", "nour.ibrahim@example.com", "Comp 304 Compiler Design - Spring", 13, 32, 7, 1, 53, "Excellent presentation"]
    ]

    # 1. Write CSV
    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        import csv
        writer = csv.writer(f)
        writer.writerows(sample_rows)

    # 2. Write Excel (.xlsx)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Grades"
    for row in sample_rows:
        ws.append(row)
    wb.save(str(xlsx_path))

    console.print(f"[green][OK] Created sample CSV:[/green] {csv_path}")
    console.print(f"[green][OK] Created sample Excel:[/green] {xlsx_path}")


if __name__ == "__main__":
    app()
