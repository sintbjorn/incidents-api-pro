# Храним все, что касается подключения к базе
# В проде Alembic прогоняется отдельно, но для dev у нас автосоздание таблиц в app.entrypoints.api

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.settings import settings

# pool_pre_ping=True — защита от разорванных соединений в пуле

engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

# вкл autocommit/flush — контроль транзакции вручную через зависимость 
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def session_dep():
    """
    даем сессию в обработчик
    если всё прошло ок - commit
    если ловим искл то - rollback (чтоб не оставлять грязную транзакцию)
    энивей - закрываем
    """
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
