import pathlib
import os

Command = str
Name = str
Schedule = str


def add_log_file(command: Command, name: Name, job_id: int = None) -> str:
    log_file_name = name.replace(" ", "")
    # Retourner la commande avec logging, sans wrapper cron
    return f"{{ {command} || echo Failed; }} 2>&1 | /usr/bin/ts >> {os.getcwd()}/logs/{log_file_name}.log"


def delete_log_file(name: Name) -> None:
    try:
        log_file_name = name.replace(" ", "")
        file = pathlib.Path(f"{os.getcwd()}/logs/{log_file_name}.log")
        file.unlink()
    except FileNotFoundError:
        return None


def clear_logs(name: Name) -> None:
    """Vide le contenu du fichier de log sans le supprimer"""
    log_file_name = name.replace(" ", "")
    filename = f"{os.getcwd()}/logs/{log_file_name}.log"
    try:
        with open(filename, 'w') as f:
            f.write("")
    except FileNotFoundError:
        # Créer le fichier s'il n'existe pas
        pathlib.Path(f"{os.getcwd()}/logs").mkdir(parents=True, exist_ok=True)
        with open(filename, 'w') as f:
            f.write("")


def load_logs(name: Name) -> str:
    log_file_name = name.replace(" ", "")
    filename = f"{os.getcwd()}/logs/{log_file_name}.log"
    try:
        with open(filename) as f:
            return f.read()
    except FileNotFoundError:
        return "No log yet"


def watch_status(name: Name) -> str:
    log = load_logs(name)
    if log == "No log yet":
        return log
    try:
        resp = log.split()[-1]
        if resp == "Failed":
            return resp
        else:
            return "Success"
    except IndexError:
        return "No log yet"
