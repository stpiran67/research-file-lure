import os
import pwd
import time
import logging
import syslog
import subprocess
from inotify_simple import INotify, flags

# Configuration
MONITORED_FILE = "/home/mark/Documents/python scripts/secret_snn.txt"  # Change this to the file you want to monitor
LOG_FILE = "/var/log/file_access_monitor.log"
SYSLOG_SERVER = "10.99.4.10"

# Setup logging
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_user_info(uid):
    """Get the username of the process accessing the file."""
    try:
        return pwd.getpwuid(uid).pw_name
    except KeyError:
        return "Unknown User"

def get_recent_bash_history(user):
    """Retrieve the last 5 commands from the user's bash history file."""
    history_file = os.path.expanduser(f"~{user}/.bash_history")
    if os.path.exists(history_file):
        with open(history_file, "r") as f:
            lines = f.readlines()
            return lines[-5:]
    return []

def get_live_commands():
    """Retrieve the last 5 commands executed in real-time from the process list."""
    try:
        result = subprocess.run(["bash", "-c", "history | tail -n 5"], capture_output=True, text=True, check=True)
        return result.stdout.strip().split('\n')
    except subprocess.CalledProcessError:
        return []

def log_event(user, history, live_commands):
    """Log the file access event both locally and remotely."""
    message = f"File accessed: {MONITORED_FILE}\nUser: {user}\n"
    message += "Last 5 commands from bash history:\n" + "\n".join(history) + "\n"
    message += "Last 5 live commands:\n" + "\n".join(live_commands) + "\n"
    
    # Log locally
    logging.info(message)
    
    # Log to remote syslog server
    syslog.openlog(ident="FileMonitor", logoption=syslog.LOG_PID, facility=syslog.LOG_AUTH)
    syslog.syslog(syslog.LOG_INFO, message)
    syslog.closelog()

# Initialize inotify
inotify = INotify()
watch_flags = flags.ACCESS
watch_descriptor = inotify.add_watch(MONITORED_FILE, watch_flags)

print(f"Monitoring {MONITORED_FILE} for access...")

try:
    while True:
        for event in inotify.read():
            user = get_user_info(event.uid)
            history = get_recent_bash_history(user)
            live_commands = get_live_commands()
            log_event(user, history, live_commands)
        time.sleep(1)
except KeyboardInterrupt:
    print("Stopping file monitoring.")

