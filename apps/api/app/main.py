from fastapi import FastAPI

from . import auth, club, training

app = FastAPI(title="TeiTraining API", version="0.1.0")
app.include_router(auth.router)
app.include_router(club.router)
app.include_router(training.router)
