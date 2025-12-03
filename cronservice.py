from crontab import CronTab
from croniter import croniter
from datetime import datetime, timedelta
import getpass
import subprocess
import os
import sys
import psutil
from pathlib import Path
import logging
import shlex
from cron_descriptor import get_description

from utils import add_log_file, Command, Name, Schedule, delete_log_file

logger = logging.getLogger(__name__)

_user = getpass.getuser()

_cron = CronTab(user=_user)


def add_cron_job(comm: Command, name: Name, sched: Schedule, job_id: int) -> None:
    if croniter.is_valid(sched):
        job = _cron.new(command=add_log_file(comm, name, job_id), comment=name)
        job.setall(sched)
        _cron.write()
    else:
        raise ValueError("Invalid Cron Expression")


def update_cron_job(comm: Command, name: Name, sched: Schedule, old_name: Name, job_id: int) -> None:
    match = _cron.find_comment(old_name)
    job = list(match)[0]
    job.setall(sched)
    job.set_command(add_log_file(comm, name, job_id))
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
    
    logger.info(f"Checking lock file: {lock_file}, exists: {lock_file.exists()}")
    
    if not lock_file.exists():
        logger.info(f"No lock file for job {job_id}")
        return False, None
    
    try:
        with open(lock_file, 'r') as f:
            pid = int(f.read().strip())
        
        logger.info(f"Lock file contains PID: {pid}")
        
        # Vérifier si le process existe toujours
        if psutil.pid_exists(pid):
            logger.info(f"PID {pid} exists in system")
            try:
                process = psutil.Process(pid)
                status = process.status()
                logger.info(f"Process {pid} status: {status}")
                # Vérifier que le process n'est pas un zombie
                if status != psutil.STATUS_ZOMBIE:
                    logger.info(f"Job {job_id} is running with PID {pid}")
                    return True, pid
                else:
                    logger.info(f"Process {pid} is zombie, cleaning lock")
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                logger.info(f"Process check failed: {e}")
                pass
        else:
            logger.info(f"PID {pid} does not exist")
        
        # Le process n'existe plus, nettoyer le lock
        lock_file.unlink()
        logger.info(f"Cleaned stale lock file for job {job_id}")
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


def run_manually(name: Name, job_id: int, db_command: str) -> dict:
    """
    Lance un job manuellement en arrière-plan de manière non-bloquante.
    
    Args:
        name: Nom du job
        job_id: ID du job
        db_command: Commande originale depuis la DB (sans wrapper cron)
    
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
        # Utiliser la commande originale (DB) avec logging, pas celle du crontab (qui a le wrapper)
        from utils import add_log_file
        command = add_log_file(db_command, name, job_id=None)  # Sans wrapper cron
        
        logger.info(f"Launching job {job_id} ({name}) in background")
        logger.debug(f"Command to execute: {command}")
        
        # Créer un script Python wrapper qui gère l'exécution
        wrapper_script = f"""#!/usr/bin/env python3
import subprocess
import sys
import os
import signal
import logging

# Configuration du logging
logging.basicConfig(
    filename='/tmp/crontab_wrapper_{job_id}.log',
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Wrapper started for job {job_id}")

# Ignorer SIGHUP pour survivre à la fermeture de la session parent
signal.signal(signal.SIGHUP, signal.SIG_IGN)

lock_file = "/tmp/crontab_job_{job_id}.lock"

try:
    command = {repr(command)}
    logger.info(f"Executing command: {{command}}")
    
    # Exécuter la commande via shell
    result = subprocess.run(
        command,
        shell=True,
        capture_output=False
    )
    
    logger.info(f"Command finished with return code: {{result.returncode}}")
    sys.exit(result.returncode)
finally:
    # Nettoyer le lock
    logger.info("Cleaning up lock file")
    try:
        os.remove(lock_file)
        logger.info("Lock file removed")
    except Exception as e:
        logger.error(f"Failed to remove lock: {{e}}")
"""
        
        # Créer un fichier temporaire pour le script wrapper
        wrapper_path = f"/tmp/crontab_wrapper_{job_id}.py"
        with open(wrapper_path, 'w') as f:
            f.write(wrapper_script)
        os.chmod(wrapper_path, 0o755)
        
        logger.debug(f"Wrapper script created at {wrapper_path}")
        
        # Lancer le processus en arrière-plan détaché
        process = subprocess.Popen(
            [sys.executable, wrapper_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            stdin=subprocess.DEVNULL,
            start_new_session=True,
            close_fds=True,
        )
        
        pid = process.pid
        
        # Créer immédiatement le lock avec le PID du wrapper
        create_lock(job_id, pid)
        logger.info(f"Lock created for job {job_id} with PID {pid}")
        
        # Attendre 0.5s et vérifier que le process existe toujours
        import time
        time.sleep(0.5)
        
        if not psutil.pid_exists(pid):
            release_lock(job_id)
            logger.error(f"Wrapper process {pid} died immediately - check wrapper script")
            return {
                "success": False,
                "message": "Le wrapper a échoué au démarrage. Vérifiez les logs.",
                "pid": None
            }
        
        # Ne pas attendre la fin du processus
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


def get_cron_description(schedule: str, locale: str = "en") -> str:
    """
    Génère une description lisible d'une expression cron.
    
    Args:
        schedule: Expression cron (ex: "0 2 * * *")
        locale: Code locale à 2 lettres (ex: "fr", "en")
    
    Returns:
        str: Description localisée ou expression brute en cas d'erreur
    """
    try:
        # cron-descriptor utilise des codes locales différents
        # Mapper les codes standards vers ceux de cron-descriptor
        locale_map = {
            'fr': 'fr_FR',
            'en': 'en_US',
            'es': 'es_ES',
            'de': 'de_DE',
            'it': 'it_IT',
            'pt': 'pt_BR',
            'ru': 'ru_RU',
            'nl': 'nl_NL',
            'pl': 'pl_PL',
            'ja': 'ja_JP',
            'zh': 'zh_CN',
            'ko': 'ko_KR'
        }
        
        cron_locale = locale_map.get(locale, 'en_US')
        return get_description(schedule, locale_code=cron_locale)
    except Exception as e:
        logger.warning(f"Failed to get cron description for '{schedule}': {e}")
        return schedule  # Fallback sur l'expression brute


def sync_job_to_cron(comm: Command, name: Name, sched: Schedule, job_id: int) -> None:
    """Synchronise un job de la DB vers le crontab système"""
    # Vérifier si le job existe déjà dans le crontab
    existing_jobs = list(_cron.find_comment(name))
    
    if existing_jobs:
        # Mettre à jour le job existant
        job = existing_jobs[0]
        job.setall(sched)
        job.set_command(add_log_file(comm, name, job_id))
    else:
        # Créer un nouveau job
        if croniter.is_valid(sched):
            job = _cron.new(command=add_log_file(comm, name, job_id), comment=name)
            job.setall(sched)
    
    _cron.write()
