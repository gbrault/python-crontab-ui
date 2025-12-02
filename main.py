from fastapi import FastAPI, Request, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
import logging

import models
import cronservice
from models import Job
from utils import watch_status, load_logs
from database import SessionLocal, engine, JobRequest

# Configuration du logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")
models.Base.metadata.create_all(bind=engine)
templates = Jinja2Templates(directory="templates")


def get_db():
    try:
        db = SessionLocal()
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Synchronise la base de données avec le crontab système au démarrage"""
    logger.info("🚀 Application démarrée - Synchronisation des jobs cron...")
    
    db = SessionLocal()
    try:
        # Récupérer tous les jobs de la base de données
        jobs = db.query(Job).all()
        
        if jobs:
            logger.info(f"📋 Synchronisation de {len(jobs)} job(s) avec le crontab système...")
            
            for job in jobs:
                try:
                    cronservice.sync_job_to_cron(job.command, job.name, job.schedule)
                    logger.info(f"  ✅ Job '{job.name}' synchronisé")
                except Exception as e:
                    logger.error(f"  ❌ Erreur lors de la synchronisation du job '{job.name}': {e}")
            
            logger.info("✅ Synchronisation terminée avec succès")
        else:
            logger.info("ℹ️  Aucun job à synchroniser")
            
    except Exception as e:
        logger.error(f"❌ Erreur lors de la synchronisation au démarrage: {e}")
    finally:
        db.close()


def update_displayed_schedule(db: Session = Depends(get_db)) -> None:
    jobs = db.query(Job).all()
    for job in jobs:
        job.next_run = cronservice.get_next_schedule(job.name)
        job.status = watch_status(job.name)


@app.get("/")
async def home(request: Request, db: Session = Depends(get_db)):
    update_displayed_schedule(db)
    jobs = db.query(Job).all()
    output = {"request": request, "jobs": jobs}
    return templates.TemplateResponse("home.html", output)


@app.get("/jobs/{job_id}")
async def get_jobs(job_id: int, request: Request, db: Session = Depends(get_db)):
    job_update = db.query(Job).filter(Job.id == job_id).first()
    output = {"request": request, "job_update": job_update}
    return templates.TemplateResponse("jobs.html", output)


@app.get("/logs/{job_id}")
async def get_logs(job_id: int, request: Request, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    log_content = load_logs(job.name)
    output = {"request": request, "job": job, "log_content": log_content}
    return templates.TemplateResponse("logs.html", output)


@app.post("/create_job/")
async def create_job(job_request: JobRequest, db: Session = Depends(get_db)):
    job = Job()
    job.command = job_request.command
    job.name = job_request.name
    job.schedule = job_request.schedule
    try:
        cronservice.add_cron_job(job.command, job.name, job.schedule)
        job.next_run = cronservice.get_next_schedule(job.name)
        db.add(job)
        db.commit()
    except ValueError:
        raise HTTPException(status_code=404, detail="Invalid Cron Expression")
    return job_request


@app.put("/update_job/{job_id}/")
async def update_job(
    job_id: int, job_request: JobRequest, db: Session = Depends(get_db)
):
    existing_job = db.query(Job).filter(Job.id == job_id)
    cronservice.update_cron_job(
        job_request.command,
        job_request.name,
        job_request.schedule,
        existing_job.first().name,
    )
    existing_job.update(job_request.__dict__)
    existing_job.update({"next_run": cronservice.get_next_schedule(job_request.name)})
    db.commit()
    return {"msg": "Successfully updated data."}


@app.get("/run_job/{job_id}/")
async def run_job(job_id: int, db: Session = Depends(get_db)):
    chosen_job = db.query(Job).filter(Job.id == job_id).first()
    chosen_name = chosen_job.name
    cronservice.run_manually(chosen_name)
    return {"msg": "Successfully run job."}


@app.delete("/job/{job_id}/")
async def delete_job(job_id: int, db: Session = Depends(get_db)):
    job_update = db.query(Job).filter(Job.id == job_id).first()
    cronservice.delete_cron_job(job_update.name)
    db.delete(job_update)
    db.commit()
    return {"INFO": f"Deleted {job_id} Successfully"}
