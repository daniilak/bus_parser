from peewee import (
    Model,
    SqliteDatabase,
    IntegerField,
    TextField,
    CharField,
    PrimaryKeyField,
    DateField
)
import logging
from typing import List, Dict
from datetime import datetime
import json

logger = logging.getLogger(__name__)

database = SqliteDatabase("database.db")


class BaseModel(Model):
    class Meta:
        database = database


class UniqueTransport(BaseModel):
    id = PrimaryKeyField()
    id_api = CharField(null=True)
    gos_num = CharField(null=True)
    rnum = CharField(null=True)
    rtype = CharField(null=True)
    class Meta:
        table_name = "unique_transports"

    @classmethod
    def update_unique_transports(cls) -> None:
        """Обновляет таблицу уникальных транспортов, добавляя только новые записи"""
        try:
            # Получаем все существующие записи
            existing = set((t.id_api, t.gos_num, t.rnum, t.rtype) 
                         for t in cls.select())
            
            # Получаем все записи из основной таблицы
            new_transports = Transport.select(
                Transport.id_api, 
                Transport.gos_num, 
                Transport.rnum, 
                Transport.rtype
            ).distinct()
            
            # Добавляем только новые записи
            for transport in new_transports:
                if (transport.id_api, transport.gos_num, transport.rnum, transport.rtype) not in existing:
                    cls.create(
                        id_api=transport.id_api,
                        gos_num=transport.gos_num,
                        rnum=transport.rnum,
                        rtype=transport.rtype
                    )
            
            logger.info("Таблица уникальных транспортов успешно обновлена")
        except Exception as e:
            logger.error(f"Ошибка при обновлении таблицы уникальных транспортов: {e}")


class AvailableTimestamps(BaseModel):
    id = PrimaryKeyField()
    created_at = IntegerField()
    class Meta:
        table_name = "available_timestamps"

    @classmethod
    def update_available_timestamps(cls) -> None:
        """Обновляет таблицу доступных временных меток, добавляя только новые записи"""
        try:
            # Получаем все существующие временные метки
            existing = set(t.created_at for t in cls.select())
            
            # Получаем все временные метки из основной таблицы
            new_timestamps = Transport.select(Transport.created_at).distinct()
            
            # Добавляем только новые временные метки
            for timestamp in new_timestamps:
                if timestamp.created_at not in existing:
                    cls.create(created_at=timestamp.created_at)
            
            logger.info("Таблица доступных временных меток успешно обновлена")
        except Exception as e:
            logger.error(f"Ошибка при обновлении таблицы доступных временных меток: {e}")


class Transport(BaseModel):
    id = PrimaryKeyField()

    created_at = IntegerField()

    id_api = CharField(null=True)
    lon = CharField(null=True)
    lat = CharField(null=True)
    dir_api = CharField(null=True)
    speed = CharField(null=True)
    lasttime = CharField(null=True)
    gos_num = CharField(null=True)
    rid = CharField(null=True)
    rnum = CharField(null=True)
    rtype = CharField(null=True)
    low_floor = CharField(null=True)
    wifi = CharField(null=True)
    anim_key = CharField(null=True)
    big_jump = CharField(null=True)
    anim_points = TextField(null=True)
    class Meta:
        table_name = "transport"

    @classmethod
    def batch_insert(cls, data: List[Dict], batch_size: int = 100) -> None:
        """Пакетная вставка данных в базу"""
        try:
            with database.atomic():
                for i in range(0, len(data), batch_size):
                    batch = data[i:i + batch_size]
                    cls.insert_many(batch).execute()
            logger.info(f"Успешно сохранено {len(data)} записей")
        except Exception as e:
            logger.error(f"Ошибка при сохранении данных: {e}")


class TransportAggregates(BaseModel):
    id = PrimaryKeyField()
    date = DateField(unique=True)
    unique_transports = TextField()  # JSON строка с уникальными транспортами
    unique_routes = TextField()      # JSON строка с уникальными маршрутами
    last_updated = IntegerField()    # timestamp последнего обновления

    class Meta:
        table_name = "transport_aggregates"

    @classmethod
    def update_aggregates(cls, transport_data: List[Dict]) -> None:
        """Обновляет агрегированные данные на основе новых записей"""
        try:
            with database.atomic():
                # Получаем уникальные даты из новых данных
                dates = set(datetime.fromtimestamp(ts).date() for ts in 
                          [t['created_at'] for t in transport_data])
                
                for date in dates:
                    # Получаем все записи за эту дату
                    day_transports = Transport.select().where(
                        Transport.created_at >= int(datetime.combine(date, datetime.min.time()).timestamp()),
                        Transport.created_at < int(datetime.combine(date, datetime.max.time()).timestamp())
                    )
                    
                    # Собираем уникальные данные
                    unique_transports = set()
                    unique_routes = set()
                    
                    for t in day_transports:
                        if t.id_api and t.gos_num and t.rnum and t.rtype:
                            unique_transports.add(f"{t.id_api}:{t.rtype}{t.rnum} - {t.gos_num}")
                        if t.rnum and t.rtype:
                            unique_routes.add(f"{t.rtype}{t.rnum}")
                    
                    # Обновляем или создаем запись
                    cls.insert(
                        date=date,
                        unique_transports=json.dumps(list(unique_transports)),
                        unique_routes=json.dumps(list(unique_routes)),
                        last_updated=int(datetime.now().timestamp())
                    ).on_conflict(
                        conflict_target=[cls.date],
                        update={
                            cls.unique_transports: json.dumps(list(unique_transports)),
                            cls.unique_routes: json.dumps(list(unique_routes)),
                            cls.last_updated: int(datetime.now().timestamp())
                        }
                    ).execute()
                    
            logger.info(f"Успешно обновлены агрегированные данные")
        except Exception as e:
            logger.error(f"Ошибка при обновлении агрегированных данных: {e}")

    @classmethod
    def get_unique_transports(cls, date: datetime.date = None) -> List[tuple]:
        """Получает список уникальных транспортов за указанную дату"""
        try:
            if date is None:
                date = datetime.now().date()
            
            aggregate = cls.get_or_none(cls.date == date)
            if aggregate:
                return [tuple(t.split(':')) for t in json.loads(aggregate.unique_transports)]
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении уникальных транспортов: {e}")
            return []

    @classmethod
    def get_unique_routes(cls, date: datetime.date = None) -> List[str]:
        """Получает список уникальных маршрутов за указанную дату"""
        try:
            if date is None:
                date = datetime.now().date()
            
            aggregate = cls.get_or_none(cls.date == date)
            if aggregate:
                return json.loads(aggregate.unique_routes)
            return []
        except Exception as e:
            logger.error(f"Ошибка при получении уникальных маршрутов: {e}")
            return []

    @classmethod
    def get_available_dates(cls) -> List[datetime.date]:
        """Получает список доступных дат"""
        try:
            return [a.date for a in cls.select(cls.date).order_by(cls.date.desc())]
        except Exception as e:
            logger.error(f"Ошибка при получении доступных дат: {e}")
            return []





# class TransportDicts(BaseModel):
#     id = PrimaryKeyField()

#     created_at = IntegerField()

#     id_api = CharField(null=True)
#     lon = CharField(null=True)
#     lat = CharField(null=True)
#     dir_api = CharField(null=True)
#     speed = CharField(null=True)
#     lasttime = CharField(null=True)
#     gos_num = CharField(null=True)
#     rid = CharField(null=True)
#     rnum = CharField(null=True)
#     rtype = CharField(null=True)
#     low_floor = CharField(null=True)
#     wifi = CharField(null=True)
#     anim_key = CharField(null=True)
#     big_jump = CharField(null=True)
#     anim_points = TextField(null=True)
#     class Meta:
#         table_name = "transport"