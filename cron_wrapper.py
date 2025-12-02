#!/usr/bin/env python3
"""
Wrapper pour les jobs cron qui gère le système de lock.
Empêche l'exécution simultanée d'un même job (manuel ou cron).
"""
import sys
import subprocess
import os
import psutil
from pathlib import Path
from datetime import datetime


def log_message(message: str):
    """Log un message avec timestamp"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}")


def get_lock_file_path(job_id: str) -> Path:
    """Retourne le chemin du fichier lock"""
    return Path(f"/tmp/crontab_job_{job_id}.lock")


def is_process_running(pid: int) -> bool:
    """Vérifie si un processus est vivant (pas zombie)"""
    try:
        if psutil.pid_exists(pid):
            process = psutil.Process(pid)
            if process.status() != psutil.STATUS_ZOMBIE:
                return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False


def main():
    if len(sys.argv) < 3:
        log_message("Usage: cron_wrapper.py <job_id> <command>")
        sys.exit(1)
    
    job_id = sys.argv[1]
    command = sys.argv[2]
    lock_file = get_lock_file_path(job_id)
    
    # Vérifier si le job est déjà en cours d'exécution
    if lock_file.exists():
        try:
            with open(lock_file, 'r') as f:
                existing_pid = int(f.read().strip())
            
            if is_process_running(existing_pid):
                log_message(f"Job {job_id} already running (PID: {existing_pid}), skipping execution")
                sys.exit(0)
            else:
                log_message(f"Found stale lock file (PID: {existing_pid} not running), removing")
                lock_file.unlink()
        except (ValueError, FileNotFoundError) as e:
            log_message(f"Error reading lock file: {e}, removing")
            if lock_file.exists():
                lock_file.unlink()
    
    # Créer le lock avec notre PID
    my_pid = os.getpid()
    try:
        with open(lock_file, 'w') as f:
            f.write(str(my_pid))
        log_message(f"Job {job_id} started (PID: {my_pid})")
    except Exception as e:
        log_message(f"Failed to create lock file: {e}")
        sys.exit(1)
    
    # Exécuter la commande
    exit_code = 0
    try:
        # os.system() préserve mieux les redirections shell complexes
        # Retourne le wait() status (exit_code << 8)
        status = os.system(command)
        exit_code = status >> 8 if status >= 0 else 1
        log_message(f"Job {job_id} completed with exit code {exit_code}")
    except Exception as e:
        log_message(f"Error executing job {job_id}: {e}")
        exit_code = 1
    finally:
        # Supprimer le lock
        try:
            if lock_file.exists():
                lock_file.unlink()
                log_message(f"Lock released for job {job_id}")
        except Exception as e:
            log_message(f"Failed to remove lock file: {e}")
    
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
