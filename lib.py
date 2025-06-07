import requests, json
from time import time
from fake_useragent import UserAgent
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)

class Parse:
    def __init__(self):
        self.ua = UserAgent()
        self.base_url = "https://buscheb.ru"
        self.api_url = f"{self.base_url}/php/getVehiclesMarkers.php"
        self.session = requests.Session()
        self.params = {
            "rids": "1-0,311-0,3-0,362-0,310-0,309-0,313-0,53-0,341-0,340-0,358-0,360-0,378-0,379-0,15-0,16-0,17-0,350-0,373-0,20-0,60-0,59-0,415-0,416-0,371-0,23-0,343-0,26-0,45-0,46-0,375-0,29-0,344-0,32-0,35-0,36-0,67-0,68-0,37-0,316-0,345-0,281-0,77-0,76-0,79-0,78-0,104-0,331-0,320-0,319-0,98-0,99-0,83-0,82-0,123-0,122-0,94-0,101-0,100-0,115-0,114-0,124-0,125-0,80-0,81-0,102-0,103-0,335-0,333-0,87-0,86-0,96-0,413-0,414-0,406-0,407-0,148-0,150-0,334-0,332-0,121-0,120-0,377-0,376-0,391-0,390-0,411-0,412-0,367-0,368-0,397-0,398-0,410-0,409-0,381-0,380-0,384-0,385-0,386-0,387-0,392-0,393-0,388-0,389-0",
            "lat0": 0,
            "lng0": 0,
            "lat1": 90,
            "lng1": 180,
            "curk": 0,
            "city": "cheboksari",
            "info": "12345",
        }
        self.headers = {
            "accept": "application/json, text/javascript, */*; q=0.01",
            "accept-language": "ru-RU,ru;q=0.8",
            "cache-control": "no-cache",
            "dnt": "1",
            "pragma": "no-cache",
            "priority": "u=1, i",
            "referer": "https://buscheb.ru/",
            "x-requested-with": "XMLHttpRequest"
        }
        self._init_session()
    
    def _init_session(self):
        """Инициализация сессии и получение cookies"""
        try:
            self.headers["user-agent"] = self.ua.random
            response = self.session.get(
                self.base_url,
                headers=self.headers,
                allow_redirects=True
            )
            response.raise_for_status()
            
            # Получаем PHPSESSID из cookies
            phpsessid = self.session.cookies.get("PHPSESSID")
            if not phpsessid:
                logger.error("Не удалось получить PHPSESSID")
                return
                
            logger.info(f"Успешно получен PHPSESSID: {phpsessid}")
            
        except Exception as e:
            logger.error(f"Ошибка при инициализации сессии: {e}")
    
    def _refresh_session_if_needed(self):
        """Обновление сессии если нужно"""
        if not self.session.cookies.get("PHPSESSID"):
            logger.info("Обновление сессии...")
            self._init_session()
    
    def get_vehicles_markers(self):
        """Получение данных о транспорте"""
        self._refresh_session_if_needed()
        self.params['_'] = int(time() * 1000)
        self.headers["user-agent"] = self.ua.random
        
        try:
            response = self.session.get(
                self.api_url,
                params=self.params,
                headers=self.headers
            )
            response.raise_for_status()
            # print(response.text)
            response = response.json().get("anims", [])
        except Exception as e:
            logger.error(f"Ошибка при получении данных: {e}")
            return []

        return response

    def process_vehicle_data(self, data: List[Dict]) -> List[Dict]:
        """Обработка данных о транспорте"""
        processed_data = []
        created_at = int(time())
        
        for item in data:
            try:
                processed_data.append({
                    "created_at": created_at,
                    "id_api": str(item.get("id", "")),
                    "lon": str(item.get("lon", "")),
                    "lat": str(item.get("lat", "")),
                    "dir_api": str(item.get("dir", "")),
                    "speed": str(item.get("speed", "")),
                    "lasttime": str(item.get("lasttime", "")),
                    "gos_num": str(item.get("gos_num", "")),
                    "rid": str(item.get("rid", "")),
                    "rnum": str(item.get("rnum", "")),
                    "rtype": str(item.get("rtype", "")),
                    "low_floor": str(item.get("low_floor", "")),
                    "wifi": str(item.get("wifi", "")),
                    "anim_key": str(item.get("anim_key", "")),
                    "big_jump": str(item.get("big_jump", "")),
                    "anim_points": json.dumps(item.get("anim_points", []), ensure_ascii=False),
                })
            except Exception as e:
                logger.error(f"Ошибка при обработке записи: {e}")
                continue
                
        return processed_data