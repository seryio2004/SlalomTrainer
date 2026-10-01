import asyncio
import os
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from . import administration, auth, calendar_export, club, google_calendar, planning, recovery, training, prescriptions, execution, follow_up, account_access, personal_export
from .google_calendar_service import configuration
from .google_calendar_sync import poll_outbox

@asynccontextmanager
async def lifespan(_app: FastAPI):
    task = asyncio.create_task(poll_outbox()) if (
        configuration() and os.environ.get("GOOGLE_CALENDAR_SYNC_POLL", "1") == "1"
    ) else None
    mail_task = asyncio.create_task(account_access.poll_mail()) if account_access.mail_configuration() else None
    try:
        yield
    finally:
        if mail_task:
            mail_task.cancel()
            with suppress(asyncio.CancelledError):
                await mail_task
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task


app = FastAPI(title="TeiTraining API", version="0.1.0", lifespan=lifespan)
app.include_router(auth.router)
app.include_router(club.router)
app.include_router(training.router)

app.include_router(planning.router)
app.include_router(recovery.router)
app.include_router(administration.router)
app.include_router(calendar_export.router)
app.include_router(google_calendar.router)
app.include_router(google_calendar.callback_router)

app.include_router(prescriptions.router)
app.include_router(execution.router)
app.include_router(follow_up.router)
app.include_router(account_access.router)
app.include_router(personal_export.router)
