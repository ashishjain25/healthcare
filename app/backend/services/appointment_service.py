"""Simulated appointment suggestions — a naive next-business-day placeholder,
no real calendar/EHR system is ever contacted (per the project's chosen
integration-depth boundary). Also backs patient-initiated booking: a fixed
15-minute slot grid within 10:00-13:00 and 16:00-19:00, validated here (not
just in the UI) since this is the actual booking write path."""
import sqlite3
from datetime import datetime, timedelta

from backend.db.repositories import appointment_repo, user_repo


def _next_business_day_9am(from_dt: datetime | None = None) -> datetime:
    dt = (from_dt or datetime.now()) + timedelta(days=1)
    while dt.weekday() >= 5:  # Saturday=5, Sunday=6
        dt += timedelta(days=1)
    return dt.replace(hour=9, minute=0, second=0, microsecond=0)


def suggest_appointment(conn: sqlite3.Connection, *, patient_id: int, alert_id: int | None,
                         reason: str, doctor_user_id: int | None = None) -> int:
    proposed = _next_business_day_9am()
    return appointment_repo.create_appointment(
        conn, patient_id=patient_id, doctor_user_id=doctor_user_id, alert_id=alert_id,
        suggested_reason=reason, proposed_datetime=proposed.isoformat(),
    )


class ValidationError(Exception):
    pass


class NotFoundError(Exception):
    pass


class ConflictError(Exception):
    pass


class ForbiddenError(Exception):
    pass


VALID_HOURS = (10, 11, 12, 16, 17, 18)
VALID_MINUTES = (0, 15, 30, 45)


def _parse_slot(date_str: str, time_str: str) -> datetime:
    try:
        dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")
    except ValueError as exc:
        raise ValidationError("Invalid date or time.") from exc
    if dt.hour not in VALID_HOURS or dt.minute not in VALID_MINUTES:
        raise ValidationError(
            "Appointments are only available 10:00 AM-1:00 PM and 4:00 PM-7:00 PM, in 15-minute slots."
        )
    if dt <= datetime.now():
        raise ValidationError("Choose a future date and time.")
    return dt


def _get_doctor(conn: sqlite3.Connection, doctor_user_id: int) -> sqlite3.Row:
    doctor = user_repo.get_by_id(conn, doctor_user_id)
    if doctor is None or doctor["role"] != "doctor":
        raise NotFoundError(f"Doctor {doctor_user_id} not found")
    return doctor


def list_available_slots(conn: sqlite3.Connection, doctor_user_id: int, date_str: str) -> list[str]:
    _get_doctor(conn, doctor_user_id)
    booked = set(appointment_repo.list_booked_times(conn, doctor_user_id, date_str))
    slots = []
    for hour in VALID_HOURS:
        for minute in VALID_MINUTES:
            slot = f"{hour:02d}:{minute:02d}"
            if slot in booked:
                continue
            try:
                candidate = datetime.strptime(f"{date_str} {slot}", "%Y-%m-%d %H:%M")
            except ValueError as exc:
                raise ValidationError("Invalid date.") from exc
            if candidate <= datetime.now():
                continue
            slots.append(slot)
    return slots


def book_appointment(conn: sqlite3.Connection, *, patient_id: int, doctor_user_id: int,
                      date_str: str, time_str: str, reason: str | None) -> int:
    _get_doctor(conn, doctor_user_id)
    dt = _parse_slot(date_str, time_str)
    proposed_datetime = dt.strftime("%Y-%m-%d %H:%M:00")

    if appointment_repo.has_conflict(conn, doctor_user_id, proposed_datetime):
        raise ConflictError("This slot was just booked — please choose another time.")

    reason_text = (reason or "").strip() or "Patient-requested appointment"
    appointment_id = appointment_repo.create_appointment(
        conn, patient_id=patient_id, doctor_user_id=doctor_user_id, alert_id=None,
        suggested_reason=reason_text, proposed_datetime=proposed_datetime,
    )
    appointment_repo.update_status(conn, appointment_id, "confirmed")
    return appointment_id


def cancel_appointment(conn: sqlite3.Connection, *, appointment_id: int, patient_id: int) -> None:
    appointment = appointment_repo.get_by_id(conn, appointment_id)
    if appointment is None:
        raise NotFoundError(f"Appointment {appointment_id} not found")
    if appointment["patient_id"] != patient_id:
        raise ForbiddenError("This appointment does not belong to the current patient")
    if appointment["status"] == "cancelled":
        raise ValidationError("This appointment is already cancelled.")
    proposed_dt = datetime.strptime(appointment["proposed_datetime"].replace("T", " ")[:19], "%Y-%m-%d %H:%M:%S")
    if proposed_dt <= datetime.now():
        raise ValidationError("Past appointments can't be cancelled.")
    appointment_repo.update_status(conn, appointment_id, "cancelled")
