from crontab import CronTab
from croniter import croniter
from datetime import datetime
import getpass
import subprocess
import os
import sys
import psutil
from pathlib import Path
import logging

from utils import add_log_file, Command, Name, Schedule, delete_log_file

logger = logging.getLogger(__name__)

_user = getpass.getuser()

_cron = CronTab(user=_user)


def add_cron_job(comm: Command, name: Name, sched: Schedule) -> None:
    if croniter.is_valid(sched):
        job = _cron.new(command=add_log_file(comm, name), comment=name)
        job.setall(sched)
        _cron.write()
    else:
        raise ValueError("Invalid Cron Expression")


def update_cron_job(comm: Command, name: Name, sched: Schedule, old_name: Name) -> None:
    match = _cron.find_comment(old_name)
    job = list(match)[0]
    job.setall(sched)
    job.set_command(add_log_file(comm, name))
    job.set_comment(name)
    _cron.write()


def delete_cron_job(name: Name) -> None:
    _cron.remove_all(comment=name)
    _cron.write()
    delete_log_file(name)


def get_lock_file_path(job_id: int) -> Path:
    """Retourne le chemin du fichier lock pour un job"""
    return Path(f"/tmp/crontab_job_{job_id}.lock")


def is_job_running(job_id: int) -> tuple[bool, int | None]:
    """
    Vérifie si un job est déjà en cours d'exécution.
    
    Returns:
        tuple: (is_running, pid) - True si le job tourne, False sinon, avec le PID ou None
    """
    lock_file = get_lock_file_path(job_id)
    
    if not lock_file.exists():
        return False, None
    
    try:
        with open(lock_file, 'r') as f:
            pid = int(f.read().strip())
        
        # Vérifier si le process existe toujours
        if psutil.pid_exists(pid):
            try:
                process = psutil.Process(pid)
                # Vérifier que le process n'est pas un zombie
                if process.status() != psutil.STATUS_ZOMBIE:
                    return True, pid
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        # Le process n'existe plus, nettoyer le lock
        lock_file.unlink()
        return False, None
        
    except (ValueError, FileNotFoundError):
        # Fichier lock corrompu ou supprimé entre-temps
        if lock_file.exists():
            lock_file.unlink()
        return False, None


def create_lock(job_id: int, pid: int) -> None:
    """Crée un fichier lock avec le PID du process"""
    lock_file = get_lock_file_path(job_id)
    with open(lock_file, 'w') as f:
        f.write(str(pid))


def release_lock(job_id: int) -> None:
    """Supprime le fichier lock"""
    lock_file = get_lock_file_path(job_id)
    if lock_file.exists():
        lock_file.unlink()


def run_manually(name: Name, job_id: int) -> dict:
    """
    Lance un job manuellement en arrière-plan de manière non-bloquante.
    
    Returns:
        dict: Informations sur le lancement (success, message, pid)
    """
    # Vérifier si le job est déjà en cours d'exécution
    is_running, existing_pid = is_job_running(job_id)
    if is_running:
        logger.warning(f"Job {job_id} ({name}) already running with PID {existing_pid}")
        return {
            "success": False,
            "message": f"Job already running with PID {existing_pid}",
            "pid": existing_pid
        }
    
    try:
        # Récupérer la commande du job
        match = _cron.find_comment(name)
        job = list(match)[0]
        command = job.command
        
        logger.info(f"Launching job {job_id} ({name}) in background")
        
        # Lancer le job en arrière-plan avec un wrapper pour gérer le lock
        wrapper_script = f"""#!/bin/bash
LOCK_FILE="/tmp/crontab_job_{job_id}.lock"
echo $$ > "$LOCK_FILE"
trap 'rm -f "$LOCK_FILE"' EXIT

# Exécuter la commande
{command}
"""
        
        # Créer un fichier temporaire pour le script wrapper
        wrapper_path = f"/tmp/crontab_wrapper_{job_id}.sh"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_script)
        os.chmod(wrapper_path, 0o755)
        
        # Lancer le processus en arrière-plan détaché
        # start_new_session=True suffit pour détacher complètement le processus
        process = subprocess.Popen(
            ['/bin/bash', wrapper_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
        )
        
        pid = process.pid
        logger.info(f"Job {job_id} ({name}) launched successfully with PID {pid}")
        
        return {
            "success": True,
            "message": f"Job lancé en arrière-plan (PID: {pid}). Consultez les logs pour suivre l'exécution.",
            "pid": pid
        }
        
    except IndexError:
        logger.error(f"Job {job_id} ({name}) not found in crontab")
        return {
            "success": False,
            "message": "Job not found in crontab",
            "pid": None
        }
    except Exception as e:
        logger.error(f"Error launching job {job_id} ({name}): {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"Error launching job: {str(e)}",
            "pid": None
        }


def get_next_schedule(name: Name) -> str:
    try:
        match = _cron.find_comment(name)
        job = list(match)[0]
        schedule = job.schedule(date_from=datetime.now())
        return schedule.get_next().strftime("%d/%m/%Y %H:%M:%S").replace("/", "-")
    except IndexError:
        return None


def sync_job_to_cron(comm: Command, name: Name, sched: Schedule) -> None:
    """Synchronise un job de la DB vers le crontab système"""
    # Vérifier si le job existe déjà dans le crontab
    existing_jobs = list(_cron.find_comment(name))
    
    if existing_jobs:
        # Mettre à jour le job existant
        job = existing_jobs[0]
        job.setall(sched)
        job.set_command(add_log_file(comm, name))
    else:
        # Créer un nouveau job
        if croniter.is_valid(sched):
            job = _cron.new(command=add_log_file(comm, name), comment=name)
            job.setall(sched)
    
    _cron.write()
