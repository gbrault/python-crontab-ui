import pathlib
import os

Command = str
Name = str
Schedule = str


def get_locale_from_accept_language(accept_language: str) -> str:
    """
    Parse le header Accept-Language et retourne la locale principale.
    
    Args:
        accept_language: Header HTTP Accept-Language (ex: "fr-FR,fr;q=0.9,en;q=0.8")
    
    Returns:
        str: Code locale à 2 lettres (ex: "fr", "en")
    """
    if not accept_language:
        return "en"
    
    # Prendre la première langue de la liste
    # Format: "fr-FR,fr;q=0.9,en;q=0.8" -> "fr-FR" -> "fr"
    try:
        primary_lang = accept_language.split(",")[0].split("-")[0].lower()
        # Valider que c'est une locale supportée (liste non exhaustive)
        supported_locales = ['fr', 'en', 'es', 'de', 'it', 'pt', 'ru', 'nl', 'pl', 'ja', 'zh', 'ko']
        return primary_lang if primary_lang in supported_locales else "en"
    except (IndexError, AttributeError):
        return "en"


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
