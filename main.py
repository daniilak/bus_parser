from setproctitle import setproctitle
setproctitle("TRANSPORT")
from lib import Parse
from models import Transport, UniqueTransport, AvailableTimestamps
from time import sleep, time
import logging
import sys
from datetime import datetime
import pytz

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('transport_parser.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Создание таблицы если не существует
Transport.create_table(safe=True)
AvailableTimestamps.create_table(safe=True)
UniqueTransport.create_table(safe=True)

parser = Parse()
NORMAL_SLEEP = 60  # время ожидания при нормальной работе
ERROR_SLEEP = 10   # время ожидания при ошибке
NIGHT_SLEEP = 1200  # время ожидания ночью (20 минут)

def is_night_time():
    """Проверка, ночное ли время (0:00 - 4:00 по МСК)"""
    moscow_tz = pytz.timezone('Europe/Moscow')
    moscow_time = datetime.now(moscow_tz)
    return 0 <= moscow_time.hour < 4


while True:
    try:
        data = parser.get_vehicles_markers()
        
        if not data:
            logger.warning("Получены пустые данные")
            parser._init_session()
            if is_night_time():
                logger.info("Ночное время (0:00 - 4:00 МСК), ожидание 20 минут")
                sleep(NIGHT_SLEEP)
            else:
                sleep(ERROR_SLEEP)
            continue
        
        # Обработка и сохранение данных
        processed_data = parser.process_vehicle_data(data)
        if processed_data:
            start_time = time()
            Transport.batch_insert(processed_data)
            # Обновляем вспомогательные таблицы
            UniqueTransport.update_unique_transports()
            AvailableTimestamps.update_available_timestamps()
            db_operation_time = time() - start_time
            
            # Корректируем время ожидания с учетом времени операций с БД
            adjusted_sleep = max(1, NORMAL_SLEEP - int(db_operation_time))
            logger.info(f"Операции с БД заняли {int(db_operation_time)} секунд")
            logger.info(f"Ожидание {adjusted_sleep} секунд перед следующим запросом")
            sleep(adjusted_sleep)
        else:
            logger.warning("Нет данных для сохранения")
            if is_night_time():
                logger.info("Ночное время (0:00 - 4:00 МСК), ожидание 20 минут")
                sleep(NIGHT_SLEEP)
            else:
                sleep(ERROR_SLEEP)
        
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        if is_night_time():
            logger.info("Ночное время (0:00 - 4:00 МСК), ожидание 20 минут")
            sleep(NIGHT_SLEEP)
        else:
            sleep(ERROR_SLEEP)
