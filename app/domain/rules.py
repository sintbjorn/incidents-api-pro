#правила переходов статусов 
from .models import Status

ALLOWED = {
    Status.NEW: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.RESOLVED},
    # разрешаем возврат на доработку
    Status.RESOLVED: {Status.IN_PROGRESS, Status.CLOSED},
    Status.CLOSED: set(),
}

def ensure_transition(old: Status, new: Status) -> None:
    #кидаем valueerror если переход недопустим - сервис слой мапит это в 409
    if new == old:
        return
    if new not in ALLOWED.get(old, set()):
        raise ValueError(f"Transition {old} -> {new} is not allowed")