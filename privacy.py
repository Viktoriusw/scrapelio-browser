from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 

                              QLabel, QComboBox, QCheckBox, QDialog, QSlider,

                              QGroupBox, QScrollArea, QFrame, QListWidget, QMessageBox,

                              QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,

                              QSizePolicy, QDialogButtonBox, QLineEdit, QTreeWidget,

                              QTreeWidgetItem, QMenu, QInputDialog, QApplication)

from PySide6.QtCore import Qt, Signal, QSettings, QUrl, QObject, QDateTime, QTimer

from PySide6.QtWebEngineCore import (QWebEngineProfile, QWebEngineSettings, 

                                    QWebEngineUrlRequestInterceptor, QWebEngineUrlRequestInfo,

                                    QWebEngineScript)

from PySide6.QtWebEngineWidgets import QWebEngineView

import json

import os

import urllib.request

import threading

import time

from datetime import datetime, timedelta

import sqlite3

import shutil

import requests

import re

from dataclasses import dataclass

from typing import Optional, Pattern, Set

from collections import OrderedDict



# Importar configuración

try:

    from config import PERFORMANCE_CONFIG

except ImportError:

    PERFORMANCE_CONFIG = {

        "async_filter_loading": True,

        "load_basic_filters_only": True,

        "skip_heavy_filters": True,

        "max_filter_rules": 1000,

    }



@dataclass

class ABPRule:

    """Simplified ABP (Adblock Plus) rule"""

    regex: Optional[Pattern] = None

    host_suffixes: Set[str] = None

    block: bool = True

    types: Optional[Set[str]] = None

    third_party: Optional[bool] = None

    include_domains: Set[str] = None

    exclude_domains: Set[str] = None

    

    def __post_init__(self):

        if self.host_suffixes is None:

            self.host_suffixes = set()

        if self.include_domains is None:

            self.include_domains = set()

        if self.exclude_domains is None:

            self.exclude_domains = set()







class AdBlockerInterceptor(QWebEngineUrlRequestInterceptor):

    def __init__(self, parent=None):

        super().__init__(parent)

        # Nuevas estructuras para ABP

        self.block_rules = []

        self.exception_rules = []

        self._host_index = {}  # dict suffix->list[rule] para optimización

        self._lock = threading.Lock()

        self._lru = OrderedDict()  # Cache LRU para decisiones

        self._lru_max_size = 512

        

        # Mantener compatibilidad temporal para ABP únicamente

        self.last_update = 0

        self.update_interval = 24 * 60 * 60  # 24 horas en segundos

        

        # Cargar filtros según configuración de rendimiento

        if PERFORMANCE_CONFIG.get("async_filter_loading", True):

            # Cargar solo filtros básicos al inicio

            if PERFORMANCE_CONFIG.get("load_basic_filters_only", True):

                threading.Thread(target=self.load_basic_filters, daemon=True).start()

            else:

                threading.Thread(target=self.load_filter_lists, daemon=True).start()

        else:

            # Carga síncrona (no recomendado)

            self.load_filter_lists()



    def parse_rule(self, line: str) -> Optional[ABPRule]:

        """Parse an ABP filter line and return ABPRule or None"""

        line = line.strip()

        

        # Ignorar comentarios y filtros cosméticos

        if not line or line.startswith('!') or '##' in line or '#?#' in line:

            return None

            

        # Verificar si es excepción (@@)

        is_exception = line.startswith('@@')

        if is_exception:

            line = line[2:]

            

        # Separar opciones si existen ($)

        if '$' in line:

            filter_part, options_part = line.rsplit('$', 1)

        else:

            filter_part, options_part = line, ""

            

        # Parsear opciones

        types = None

        third_party = None

        include_domains = set()

        exclude_domains = set()

        

        if options_part:

            for option in options_part.split(','):

                option = option.strip()

                if option in ['script', 'image', 'stylesheet', 'media', 'font', 'xmlhttprequest', 'subdocument', 'ping']:

                    if types is None:

                        types = set()

                    types.add(option)

                elif option == 'third-party':

                    third_party = True

                elif option == '~third-party':

                    third_party = False

                elif option.startswith('domain='):

                    domains = option[7:].split('|')

                    for domain in domains:

                        if domain.startswith('~'):

                            exclude_domains.add(domain[1:])

                        else:

                            include_domains.add(domain)

        

        # Parsear filtro principal

        host_suffixes = set()

        regex = None

        

        # Ancla de dominio ||domain^

        if filter_part.startswith('||') and '^' in filter_part:

            end_idx = filter_part.index('^')

            domain = filter_part[2:end_idx].lower()

            if '/' not in domain and '*' not in domain:

                host_suffixes.add(domain)

            else:

                # Convertir a regex si es complejo

                pattern = re.escape(filter_part).replace('\\*', '.*').replace('\\^', '[/?&=]')

                pattern = pattern.replace('\\|\\|', '^https?://([^/]+\\.)?')

                try:

                    regex = re.compile(pattern, re.IGNORECASE)

                except Exception as e:

                    print(f"Warning: Invalid regex pattern: {pattern[:50]}... Error: {e}")
                    return None

        elif '||' in filter_part or '*' in filter_part or '^' in filter_part:

            # Convertir a regex para patrones complejos

            pattern = re.escape(filter_part).replace('\\*', '.*').replace('\\^', '[/?&=]')

            if pattern.startswith('\\|\\|'):

                pattern = pattern.replace('\\|\\|', '^https?://([^/]+\\.)?', 1)

            pattern = pattern.replace('\\|', '')

            try:

                regex = re.compile(pattern, re.IGNORECASE)

            except:

                return None

        else:

            # Filtro de substring simple

            if len(filter_part) > 3:  # Evitar patrones muy cortos

                try:

                    regex = re.compile(re.escape(filter_part), re.IGNORECASE)

                except:

                    return None

            else:

                return None

                

        return ABPRule(

            regex=regex,

            host_suffixes=host_suffixes,

            block=not is_exception,

            types=types,

            third_party=third_party,

            include_domains=include_domains,

            exclude_domains=exclude_domains

        )



    def resource_matches(self, info, types: Set[str]) -> bool:

        """Check if resource type matches filter types"""

        if not types:

            return True  # Sin restricción de tipo

            

        try:

            resource_type = info.resourceType()

            

            # Mapeo seguro ABP -> Qt ResourceType

            type_mapping = {}

            

            # Solo agregar si existe en esta versión de Qt

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeScript'):

                type_mapping['script'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeScript

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'Script'):

                type_mapping['script'] = QWebEngineUrlRequestInfo.ResourceType.Script

                

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeImage'):

                type_mapping['image'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeImage

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'Image'):

                type_mapping['image'] = QWebEngineUrlRequestInfo.ResourceType.Image

                

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeStyleSheet'):

                type_mapping['stylesheet'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeStyleSheet

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'StyleSheet'):

                type_mapping['stylesheet'] = QWebEngineUrlRequestInfo.ResourceType.StyleSheet

                

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeMedia'):

                type_mapping['media'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeMedia

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'Media'):

                type_mapping['media'] = QWebEngineUrlRequestInfo.ResourceType.Media

                

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeFont'):

                type_mapping['font'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeFont

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'Font'):

                type_mapping['font'] = QWebEngineUrlRequestInfo.ResourceType.Font

                

            if hasattr(QWebEngineUrlRequestInfo.ResourceType, 'ResourceTypeXmlHttpRequest'):

                type_mapping['xmlhttprequest'] = QWebEngineUrlRequestInfo.ResourceType.ResourceTypeXmlHttpRequest

            elif hasattr(QWebEngineUrlRequestInfo.ResourceType, 'XmlHttpRequest'):

                type_mapping['xmlhttprequest'] = QWebEngineUrlRequestInfo.ResourceType.XmlHttpRequest

                

            # Verificar si algún tipo coincide

            for filter_type in types:

                if filter_type in type_mapping:

                    if resource_type == type_mapping[filter_type]:

                        return True

                        

            # Si ningún tipo mapeado coincide, es no match

            return False

            

        except (AttributeError, Exception):

            # Si no podemos determinar el tipo, ignorar restricción

            return True



    def is_third_party(self, info) -> Optional[bool]:

        """Determine if the request is from third parties"""

        try:

            if hasattr(info, 'firstPartyUrl'):

                # Obtener dominios principales (eTLD+1 simplificado)

                request_host = info.requestUrl().host().lower()

                first_party_host = info.firstPartyUrl().host().lower()

                

                # Simplificación: comparar hosts directamente

                # En implementación real se usaría public suffix list

                def get_main_domain(host):

                    parts = host.split('.')

                    if len(parts) >= 2:

                        return '.'.join(parts[-2:])

                    return host

                

                request_main = get_main_domain(request_host)

                first_party_main = get_main_domain(first_party_host)

                

                return request_main != first_party_main

            else:

                # API no disponible, no se puede determinar

                return None

        except (AttributeError, Exception):

            return None



    def load_basic_filters(self):

        """Carga solo filtros básicos para mejorar rendimiento"""

        try:

            # Cargar solo filtros personalizados (más ligeros)

            self.custom_filters = self.load_or_create_custom_filters()

            

            # Compilar solo filtros básicos

            block_rules, exception_rules, host_index = self.compile_filters(self.custom_filters)

            

            # Swap atómico bajo lock

            with self._lock:

                self.block_rules = block_rules

                self.exception_rules = exception_rules

                self._host_index = host_index

                

            print(f"Filtros básicos cargados: {len(block_rules)} bloqueos, {len(exception_rules)} excepciones")

            

            # Cargar filtros pesados en segundo plano si no están deshabilitados

            if not PERFORMANCE_CONFIG.get("skip_heavy_filters", False) and not PERFORMANCE_CONFIG.get("disable_heavy_filters", False):

                threading.Thread(target=self.load_heavy_filters, daemon=True).start()

            else:

                print("Heavy filters disabled for performance")

                

        except Exception as e:

            print(f"Error al cargar filtros básicos: {str(e)}")

            self.custom_filters = []

    

    def load_heavy_filters(self):

        """Carga filtros pesados en segundo plano"""

        try:

            # Cargar EasyList

            if os.path.exists("easylist.txt"):

                with open("easylist.txt", "r", encoding="utf-8") as f:

                    easylist_lines = f.read().splitlines()

            else:

                print("easylist.txt file not found")

                easylist_lines = []



            # Cargar EasyPrivacy

            if os.path.exists("easyprivacy.txt"):

                with open("easyprivacy.txt", "r", encoding="utf-8") as f:

                    easyprivacy_lines = f.read().splitlines()

            else:

                print("easyprivacy.txt file not found")

                easyprivacy_lines = []



            # Limitar número de reglas según configuración

            max_rules = PERFORMANCE_CONFIG.get("max_filter_rules", 1000)

            if len(easylist_lines) > max_rules:

                easylist_lines = easylist_lines[:max_rules]

            if len(easyprivacy_lines) > max_rules:

                easyprivacy_lines = easyprivacy_lines[:max_rules]



            # Compilar filtros pesados

            all_lines = easylist_lines + easyprivacy_lines

            block_rules, exception_rules, host_index = self.compile_filters(all_lines)

            

            # Actualizar reglas existentes

            with self._lock:

                self.block_rules.extend(block_rules)

                self.exception_rules.extend(exception_rules)

                self._host_index.update(host_index)

                

            print(f"Filtros pesados cargados: {len(block_rules)} bloqueos adicionales")

            

        except Exception as e:

            print(f"Error al cargar filtros pesados: {str(e)}")



    def load_filter_lists(self):

        """Carga las listas de filtros desde archivos locales"""

        try:

            # Cargar EasyList

            if os.path.exists("easylist.txt"):

                with open("easylist.txt", "r", encoding="utf-8") as f:

                    self.easylist = f.read().splitlines()

            else:

                print("easylist.txt file not found")

                self.easylist = []



            # Cargar EasyPrivacy

            if os.path.exists("easyprivacy.txt"):

                with open("easyprivacy.txt", "r", encoding="utf-8") as f:

                    self.easyprivacy = f.read().splitlines()

            else:

                print("easyprivacy.txt file not found")

                self.easyprivacy = []



            # Cargar filtros personalizados o crearlos si no existen

            self.custom_filters = self.load_or_create_custom_filters()



            # Compilar filtros después de cargar

            all_lines = self.easylist + self.easyprivacy + self.custom_filters

            block_rules, exception_rules, host_index = self.compile_filters(all_lines)

            

            # Swap atómico bajo lock

            with self._lock:

                self.block_rules = block_rules

                self.exception_rules = exception_rules

                self._host_index = host_index

                

            print(f"Listas de filtros cargadas: {len(block_rules)} bloqueos, {len(exception_rules)} excepciones")

        except Exception as e:

            print(f"Error al cargar las listas de filtros: {str(e)}")

            self.easylist = []

            self.easyprivacy = []

            self.custom_filters = []



    def compile_filters(self, lines):

        """Compila reglas de filtros ABP en block_rules y exception_rules"""

        block_rules = []

        exception_rules = []

        host_index = {}

        

        for line in lines:

            rule = self.parse_rule(line)

            if rule is None:

                continue

                

            if rule.block:

                block_rules.append(rule)

            else:

                exception_rules.append(rule)

                

            # Indexar por sufijos de host para optimización

            for suffix in rule.host_suffixes:

                if suffix not in host_index:

                    host_index[suffix] = []

                host_index[suffix].append(rule)

        

        return block_rules, exception_rules, host_index



    def load_or_create_custom_filters(self):

        """Carga custom_filters.txt o lo crea con reglas específicas de YouTube"""

        custom_filters_file = "custom_filters.txt"

        

        # Reglas específicas para YouTube y anuncios adicionales

        default_custom_rules = [

            "! Custom AdBlock filters for YouTube and additional ads",

            "||googleads.g.doubleclick.net^",

            "||pagead2.googlesyndication.com^",

            "||pubads.g.doubleclick.net^",

            "||securepubads.g.doubleclick.net^",

            "||youtube.com/api/stats/ads$xmlhttprequest",

            "||youtube.com/pagead/$xmlhttprequest,subdocument",

            "||youtube.com/get_video_info?*adformat*",

            "||youtube.com/youtubei/v1/player/ad_break*",

            "||youtube.com/api/stats/watchtime*",

            "||youtube.com/ptracking*",

            "||googlevideo.com/videoplayback*adformat*",

            "! Block additional ad tracking",

            "||google-analytics.com^$third-party",

            "||googletagmanager.com^$third-party",

            "||facebook.com/tr/*$image,script",

            "||facebook.net/en_US/fbevents.js",

            "||connect.facebook.net^$third-party"

        ]

        

        try:

            if os.path.exists(custom_filters_file):

                # Cargar archivo existente

                with open(custom_filters_file, "r", encoding="utf-8") as f:

                    custom_filters = f.read().splitlines()

                print(f"Filtros personalizados cargados: {len(custom_filters)} reglas")

                return custom_filters

            else:

                # Crear archivo con reglas por defecto

                with open(custom_filters_file, "w", encoding="utf-8") as f:

                    f.write("\n".join(default_custom_rules))

                print(f"Archivo {custom_filters_file} creado con {len(default_custom_rules)} reglas por defecto")

                return default_custom_rules

                

        except Exception as e:

            print(f"Error al manejar {custom_filters_file}: {e}")

            # Devolver reglas por defecto en caso de error

            return default_custom_rules







    def update_filter_lists(self):

        """Actualiza las listas de filtros desde las fuentes en línea"""

        try:

            # URLs de las listas de filtros

            easylist_url = "https://easylist.to/easylist/easylist.txt"

            easyprivacy_url = "https://easylist.to/easylist/easyprivacy.txt"



            # Descargar EasyList

            try:

                response = requests.get(easylist_url)

                response.raise_for_status()

                with open("easylist.txt", "w", encoding="utf-8") as f:

                    f.write(response.text)

                self.easylist = response.text.splitlines()

            except Exception as e:

                print(f"Error al actualizar EasyList: {str(e)}")



            # Descargar EasyPrivacy

            try:

                response = requests.get(easyprivacy_url)

                response.raise_for_status()

                with open("easyprivacy.txt", "w", encoding="utf-8") as f:

                    f.write(response.text)

                self.easyprivacy = response.text.splitlines()

            except Exception as e:

                print(f"Error al actualizar EasyPrivacy: {str(e)}")



            # Cargar filtros personalizados actualizados

            self.custom_filters = self.load_or_create_custom_filters()

            

            # Compilar filtros después de actualizar

            all_lines = self.easylist + self.easyprivacy + self.custom_filters

            block_rules, exception_rules, host_index = self.compile_filters(all_lines)

            

            # Swap atómico bajo lock

            with self._lock:

                self.block_rules = block_rules

                self.exception_rules = exception_rules

                self._host_index = host_index

                

            print(f"Listas de filtros actualizadas: {len(block_rules)} bloqueos, {len(exception_rules)} excepciones")

        except Exception as e:

            print(f"Error al actualizar las listas de filtros: {str(e)}")



    def _manage_lru_cache(self, key, value):

        """Gestiona el cache LRU"""

        if key in self._lru:

            del self._lru[key]

        elif len(self._lru) >= self._lru_max_size:

            self._lru.popitem(last=False)

        self._lru[key] = value



    def _rule_matches(self, rule, url, host, is_tp, info):

        """Verifica si una regla coincide con la solicitud"""

        # Verificar dominios include/exclude

        if rule.include_domains:

            if not any(host.endswith(d) for d in rule.include_domains):

                return False

        if rule.exclude_domains:

            if any(host.endswith(d) for d in rule.exclude_domains):

                return False

                

        # Verificar third-party

        if rule.third_party is not None:

            if is_tp is None:

                return False  # No se puede determinar, skip regla

            if rule.third_party != is_tp:

                return False

                

        # Verificar tipos de recurso

        if not self.resource_matches(info, rule.types):

            return False

            

        # Verificar host suffixes

        if rule.host_suffixes:

            if not any(host.endswith(suffix) for suffix in rule.host_suffixes):

                return False

        

        # Verificar regex si existe

        if rule.regex:

            if not rule.regex.search(url):

                return False

                

        return True



    def interceptRequest(self, info):

        """Intercepta y bloquea solicitudes usando filtros ABP"""

        try:

            url = info.requestUrl().toString()

            host = info.requestUrl().host().lower()

            

            # Verificar cache LRU

            cache_key = f"{host}:{url[-50:]}"  # Key optimizado

            if cache_key in self._lru:

                decision = self._lru[cache_key]

                if decision:

                    info.block(True)

                return

            

            # Calcular propiedades una vez

            is_tp = self.is_third_party(info)

            

            # Obtener reglas bajo lock (lectura rápida)

            with self._lock:

                exception_rules = self.exception_rules[:]

                block_rules = self.block_rules[:]

                host_index = self._host_index.copy()

            

            # Verificar excepciones primero

            for rule in exception_rules:

                if self._rule_matches(rule, url, host, is_tp, info):

                    self._manage_lru_cache(cache_key, False)

                    return  # Permitir

            

            # Verificar reglas de bloqueo indexadas por host

            matched_rules = []

            for suffix in host_index:

                if host.endswith(suffix):

                    matched_rules.extend(host_index[suffix])

            

            # Verificar reglas específicas del host primero

            for rule in matched_rules:

                if rule.block and self._rule_matches(rule, url, host, is_tp, info):

                    info.block(True)

                    self._manage_lru_cache(cache_key, True)

                    print(f"Blocked by ABP rule: {host}")

                    return

            

            # Verificar reglas globales (regex) como fallback

            for rule in block_rules:

                if rule.regex and not rule.host_suffixes:  # Solo regex globales

                    if self._rule_matches(rule, url, host, is_tp, info):

                        info.block(True)

                        self._manage_lru_cache(cache_key, True)

                        print(f"Blocked by regex rule: {url}")

                        return

            

            # No bloqueado

            self._manage_lru_cache(cache_key, False)

            

        except Exception as e:

            print(f"Error en interceptRequest: {str(e)}")



class PrivacySettings:

    def __init__(self):

        self.settings = QSettings("Scrapelio", "Privacy")

        self.load_settings()



    def load_settings(self):

        # Valores por defecto

        defaults = {

            "privacy_level": "balanced",  # strict, balanced, custom

            "block_trackers": True,

            "block_ads": True,

            "no_persistent_cookies": False,  # Política de cookies persistentes

            "block_javascript": False,

            "block_images": False,

            "block_webrtc": True,

            "block_fingerprinting": True,

            "block_third_party": True,  # Para cookies de terceros específicamente

            "clear_on_exit": True,

            "do_not_track": True

        }



        # Cargar configuración guardada o usar valores por defecto

        for key, default_value in defaults.items():

            if not self.settings.contains(key):

                self.settings.setValue(key, default_value)



    def save_settings(self):

        self.settings.sync()



    def get_setting(self, key):

        value = self.settings.value(key)

        if isinstance(value, str):

            # Convertir strings "true"/"false" a booleanos

            if value.lower() == "true":

                return True

            elif value.lower() == "false":

                return False

        return value



    def set_setting(self, key, value):

        self.settings.setValue(key, value)

        self.settings.sync()



class AutoClearSettings:

    def __init__(self):

        self.settings = QSettings("Scrapelio", "AutoClear")

        self.load_settings()

        self.timer = QTimer()

        self.timer.timeout.connect(self.auto_clear_data)

        self.start_timer()



    def load_settings(self):

        defaults = {

            "enabled": False,

            "frequency": "24 hours",

            "clear_history": True,

            "clear_cookies": True,

            "clear_cache": True,

            "clear_passwords": False,

            "clear_form_data": False,

            "clear_downloads": False

        }

        

        for key, default_value in defaults.items():

            if not self.settings.contains(key):

                self.settings.setValue(key, default_value)

        self.settings.sync()



    def save_settings(self):

        self.settings.sync()

        self.start_timer()



    def get_setting(self, key):

        value = self.settings.value(key)

        if isinstance(value, str):

            if value.lower() == "true":

                return True

            elif value.lower() == "false":

                return False

        return value



    def set_setting(self, key, value):

        self.settings.setValue(key, value)

        self.settings.sync()



    def start_timer(self):

        if not self.get_setting("enabled"):

            self.timer.stop()

            return



        frequency = self.get_setting("frequency")

        hours = int(frequency.split()[0])

        self.timer.start(hours * 60 * 60 * 1000)  # Convertir horas a milisegundos



    def auto_clear_data(self):

        profile = QWebEngineProfile.defaultProfile()

        

        if self.get_setting("clear_history"):

            self.clear_history_data()

        

        if self.get_setting("clear_cookies"):

            profile.cookieStore().deleteAllCookies()

        

        if self.get_setting("clear_cache"):

            profile.clearHttpCache()

        

        if self.get_setting("clear_passwords"):

            self.clear_saved_passwords()

        

        if self.get_setting("clear_form_data"):

            self.clear_form_data()

        

        if self.get_setting("clear_downloads"):

            self.clear_downloads()



    def clear_history_data(self):

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            history_db = os.path.join(profile_path, "History")

            

            if os.path.exists(history_db):

                conn = sqlite3.connect(history_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM urls")

                cursor.execute("DELETE FROM visits")

                conn.commit()

                conn.close()

        except Exception as e:

            print(f"Error clearing history: {str(e)}")



    def clear_saved_passwords(self):

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            login_db = os.path.join(profile_path, "Login Data")

            

            if os.path.exists(login_db):

                conn = sqlite3.connect(login_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM logins")

                conn.commit()

                conn.close()

        except Exception as e:

            print(f"Error clearing passwords: {str(e)}")



    def clear_form_data(self):

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            form_data_db = os.path.join(profile_path, "Web Data")

            

            if os.path.exists(form_data_db):

                conn = sqlite3.connect(form_data_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM autofill")

                conn.commit()

                conn.close()

        except Exception as e:

            print(f"Error clearing form data: {str(e)}")



    def clear_downloads(self):

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            downloads_db = os.path.join(profile_path, "History")

            

            if os.path.exists(downloads_db):

                conn = sqlite3.connect(downloads_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM downloads")

                cursor.execute("DELETE FROM downloads_url_chains")

                conn.commit()

                conn.close()

        except Exception as e:

            print(f"Error clearing downloads: {str(e)}")



class SavedDataDialog(QDialog):

    def __init__(self, title, data, parent=None):

        super().__init__(parent)

        self.setWindowTitle(title)

        self.setModal(True)

        

        layout = QVBoxLayout()

        

        # Crear tabla para mostrar datos

        self.table = QTableWidget()

        self.table.setColumnCount(2)

        self.table.setHorizontalHeaderLabels(["Site", "Data"])

        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        

        # Llenar tabla con datos

        self.table.setRowCount(len(data))

        for i, (site, info) in enumerate(data.items()):

            self.table.setItem(i, 0, QTableWidgetItem(site))

            self.table.setItem(i, 1, QTableWidgetItem(str(info)))

        

        layout.addWidget(self.table)

        

        # Botones

        buttons = QDialogButtonBox(

            QDialogButtonBox.Ok | QDialogButtonBox.Cancel

        )

        buttons.accepted.connect(self.accept)

        buttons.rejected.connect(self.reject)

        layout.addWidget(buttons)

        

        self.setLayout(layout)



class HistoryManager:

    def __init__(self):

        self.profile = QWebEngineProfile.defaultProfile()

        self.history_db = os.path.join(self.profile.persistentStoragePath(), "History")

        self.last_visit_time = None

        self.init_history_db()



    def init_history_db(self):

        """Inicializa la base de datos del historial si no existe"""

        try:

            if not os.path.exists(self.history_db):

                conn = sqlite3.connect(self.history_db)

                cursor = conn.cursor()

                cursor.execute('''

                    CREATE TABLE IF NOT EXISTS urls (

                        id INTEGER PRIMARY KEY,

                        url TEXT NOT NULL,

                        title TEXT,

                        visit_count INTEGER DEFAULT 1,

                        last_visit_time INTEGER,

                        created_time INTEGER

                    )

                ''')

                cursor.execute('''

                    CREATE TABLE IF NOT EXISTS visits (

                        id INTEGER PRIMARY KEY,

                        url_id INTEGER,

                        visit_time INTEGER,

                        FOREIGN KEY (url_id) REFERENCES urls(id)

                    )

                ''')

                conn.commit()

                conn.close()

        except Exception as e:

            print(f"Error initializing history database: {str(e)}")



    def add_url(self, url, title=""):

        """Añade una URL al historial"""

        try:

            conn = sqlite3.connect(self.history_db)

            cursor = conn.cursor()

            current_time = int(time.time() * 1000000)  # Microsegundos



            # Verificar si la URL ya existe

            cursor.execute("SELECT id, visit_count FROM urls WHERE url = ?", (url,))

            result = cursor.fetchone()



            if result:

                url_id, visit_count = result

                cursor.execute("""

                    UPDATE urls 

                    SET visit_count = ?, last_visit_time = ?, title = ?

                    WHERE id = ?

                """, (visit_count + 1, current_time, title, url_id))

            else:

                cursor.execute("""

                    INSERT INTO urls (url, title, visit_count, last_visit_time, created_time)

                    VALUES (?, ?, 1, ?, ?)

                """, (url, title, current_time, current_time))

                url_id = cursor.lastrowid



            # Añadir visita

            cursor.execute("""

                INSERT INTO visits (url_id, visit_time)

                VALUES (?, ?)

            """, (url_id, current_time))



            conn.commit()

            conn.close()

            self.last_visit_time = current_time

        except Exception as e:

            print(f"Error adding URL to history: {str(e)}")



    def get_history(self, time_range=None):

        """Obtiene el historial organizado por tiempo"""

        try:

            conn = sqlite3.connect(self.history_db)

            cursor = conn.cursor()

            

            if time_range:

                current_time = int(time.time() * 1000000)

                if time_range == "today":

                    start_time = current_time - (24 * 60 * 60 * 1000000)

                elif time_range == "yesterday":

                    start_time = current_time - (48 * 60 * 60 * 1000000)

                    end_time = current_time - (24 * 60 * 60 * 1000000)

                elif time_range == "last_week":

                    start_time = current_time - (7 * 24 * 60 * 60 * 1000000)

                elif time_range == "last_month":

                    start_time = current_time - (30 * 24 * 60 * 60 * 1000000)

                

                if time_range == "yesterday":

                    cursor.execute("""

                        SELECT u.url, u.title, v.visit_time

                        FROM urls u

                        JOIN visits v ON u.id = v.url_id

                        WHERE v.visit_time BETWEEN ? AND ?

                        ORDER BY v.visit_time DESC

                    """, (start_time, end_time))

                else:

                    cursor.execute("""

                        SELECT u.url, u.title, v.visit_time

                        FROM urls u

                        JOIN visits v ON u.id = v.url_id

                        WHERE v.visit_time > ?

                        ORDER BY v.visit_time DESC

                    """, (start_time,))

            else:

                cursor.execute("""

                    SELECT u.url, u.title, v.visit_time

                    FROM urls u

                    JOIN visits v ON u.id = v.url_id

                    ORDER BY v.visit_time DESC

                """)



            history = cursor.fetchall()

            conn.close()

            return history

        except Exception as e:

            print(f"Error getting history: {str(e)}")

            return []



    def clear_history(self, time_range=None):

        """Limpia el historial según el rango de tiempo especificado"""

        try:

            conn = sqlite3.connect(self.history_db)

            cursor = conn.cursor()

            

            if time_range:

                current_time = int(time.time() * 1000000)

                if time_range == "today":

                    start_time = current_time - (24 * 60 * 60 * 1000000)

                elif time_range == "yesterday":

                    start_time = current_time - (48 * 60 * 60 * 1000000)

                    end_time = current_time - (24 * 60 * 60 * 1000000)

                elif time_range == "last_week":

                    start_time = current_time - (7 * 24 * 60 * 60 * 1000000)

                elif time_range == "last_month":

                    start_time = current_time - (30 * 24 * 60 * 60 * 1000000)

                

                if time_range == "yesterday":

                    cursor.execute("""

                        DELETE FROM visits 

                        WHERE visit_time BETWEEN ? AND ?

                    """, (start_time, end_time))

                else:

                    cursor.execute("""

                        DELETE FROM visits 

                        WHERE visit_time > ?

                    """, (start_time,))

            else:

                cursor.execute("DELETE FROM visits")

                cursor.execute("DELETE FROM urls")

            

            conn.commit()

            conn.close()

        except Exception as e:

            print(f"Error clearing history: {str(e)}")



class HistoryDialog(QDialog):

    def __init__(self, history_manager, parent=None):

        super().__init__(parent)

        self.history_manager = history_manager

        self.init_ui()



    def init_ui(self):

        self.setWindowTitle("History")

        self.setMinimumSize(800, 600)

        

        layout = QVBoxLayout()

        

        # Barra de herramientas

        toolbar = QHBoxLayout()

        

        # Selector de rango de tiempo

        self.time_range_combo = QComboBox()

        self.time_range_combo.addItems([

            "All History",

            "Today",

            "Yesterday",

            "Last Week",

            "Last Month"

        ])

        self.time_range_combo.currentTextChanged.connect(self.update_history)

        toolbar.addWidget(QLabel("Show:"))

        toolbar.addWidget(self.time_range_combo)

        

        # Botón de búsqueda

        self.search_btn = QPushButton("Search")

        self.search_btn.clicked.connect(self.search_history)

        toolbar.addWidget(self.search_btn)

        

        # Botón de limpiar

        self.clear_btn = QPushButton("Clear History")

        self.clear_btn.clicked.connect(self.clear_history)

        toolbar.addWidget(self.clear_btn)

        

        toolbar.addStretch()

        layout.addLayout(toolbar)

        

        # Árbol de historial

        self.history_tree = QTreeWidget()

        self.history_tree.setHeaderLabels(["Title", "URL", "Visit Time"])

        self.history_tree.setColumnWidth(0, 300)

        self.history_tree.setColumnWidth(1, 300)

        self.history_tree.itemDoubleClicked.connect(self.open_url)

        self.history_tree.setContextMenuPolicy(Qt.CustomContextMenu)

        self.history_tree.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.history_tree)

        

        self.setLayout(layout)

        self.update_history()



    def update_history(self):

        """Actualiza el árbol de historial"""

        self.history_tree.clear()

        

        time_range = self.time_range_combo.currentText().lower().replace(" ", "_")

        history = self.history_manager.get_history(time_range)

        

        # Organizar por fecha

        current_date = None

        current_date_item = None

        

        for url, title, visit_time in history:

            visit_datetime = datetime.fromtimestamp(visit_time / 1000000)

            date_str = visit_datetime.strftime("%Y-%m-%d")

            

            if date_str != current_date:

                current_date = date_str

                current_date_item = QTreeWidgetItem(self.history_tree, [date_str])

                current_date_item.setExpanded(True)

            

            time_str = visit_datetime.strftime("%H:%M:%S")

            item = QTreeWidgetItem(current_date_item, [title or url, url, time_str])

            item.setData(0, Qt.UserRole, url)



    def open_url(self, item, column):

        """Abre la URL seleccionada"""

        if item.parent():  # Si no es un elemento de fecha

            url = item.data(0, Qt.UserRole)

            if url:

                self.parent().load_url(QUrl(url))

                self.accept()



    def search_history(self):

        """Busca en el historial"""

        text, ok = QInputDialog.getText(self, "Search History", "Enter search term:")

        if ok and text:

            self.history_tree.clear()

            history = self.history_manager.get_history()

            

            current_date = None

            current_date_item = None

            

            for url, title, visit_time in history:

                if text.lower() in url.lower() or (title and text.lower() in title.lower()):

                    visit_datetime = datetime.fromtimestamp(visit_time / 1000000)

                    date_str = visit_datetime.strftime("%Y-%m-%d")

                    

                    if date_str != current_date:

                        current_date = date_str

                        current_date_item = QTreeWidgetItem(self.history_tree, [date_str])

                        current_date_item.setExpanded(True)

                    

                    time_str = visit_datetime.strftime("%H:%M:%S")

                    item = QTreeWidgetItem(current_date_item, [title or url, url, time_str])

                    item.setData(0, Qt.UserRole, url)



    def clear_history(self):

        """Limpia el historial"""

        reply = QMessageBox.question(

            self,

            "Clear History",

            "Are you sure you want to clear the history?",

            QMessageBox.Yes | QMessageBox.No

        )

        

        if reply == QMessageBox.Yes:

            time_range = self.time_range_combo.currentText().lower().replace(" ", "_")

            self.history_manager.clear_history(time_range)

            self.update_history()



    def show_context_menu(self, position):

        """Muestra el menú contextual"""

        item = self.history_tree.itemAt(position)

        if item and item.parent():  # Si no es un elemento de fecha

            menu = QMenu()

            open_action = menu.addAction("Open")

            copy_action = menu.addAction("Copy URL")

            delete_action = menu.addAction("Delete")

            

            action = menu.exec(self.history_tree.mapToGlobal(position))

            

            if action == open_action:

                self.open_url(item, 0)

            elif action == copy_action:

                url = item.data(0, Qt.UserRole)

                QApplication.clipboard().setText(url)

            elif action == delete_action:

                # Implementar eliminación de URL específica

                pass



class PrivacyManager(QWidget):

    privacy_level_changed = Signal(str)

    tracker_blocked = Signal(str)

    data_shared = Signal(dict)

    data_cleared = Signal(str)

    settings_changed = Signal()  # Nueva señal para cambios en settings



    def __init__(self, parent=None):

        super().__init__(parent)

        self.parent = parent

        self.settings = PrivacySettings()

        self.history_manager = HistoryManager()

        self.auto_clear = AutoClearSettings()

        self.ad_blocker = AdBlockerInterceptor()

        self.init_ui()

        self.load_privacy_presets()

        self.load_auto_clear_settings()

        

        # Configurar actualización periódica de listas de filtros

        self.update_timer = QTimer()

        self.update_timer.timeout.connect(self.update_filter_lists)

        self.update_timer.start(24 * 60 * 60 * 1000)  # 24 horas en milisegundos



    def init_ui(self):

        layout = QVBoxLayout()

        layout.setSpacing(5)

        layout.setContentsMargins(5, 5, 5, 5)

        self.setLayout(layout)



        # Crear pestañas para organizar las funciones

        tab_widget = QTabWidget()

        tab_widget.setDocumentMode(True)  # Pestañas planas estilo moderno

        layout.addWidget(tab_widget)



        # Pestaña de Configuración General

        general_tab = QWidget()

        general_layout = QVBoxLayout()

        general_layout.setSpacing(5)

        general_tab.setLayout(general_layout)



        # Privacy Level Selector

        privacy_group = QGroupBox()

        privacy_group.setTitle("Privacy Level")

        privacy_layout = QHBoxLayout()

        privacy_layout.setContentsMargins(5, 5, 5, 5)

        

        self.privacy_combo = QComboBox()

        self.privacy_combo.addItems(["Strict", "Balanced", "Custom"])

        self.privacy_combo.setMaximumWidth(120)

        self.privacy_combo.currentTextChanged.connect(self.on_privacy_level_changed)

        privacy_layout.addWidget(self.privacy_combo)

        privacy_layout.addStretch()

        

        privacy_group.setLayout(privacy_layout)

        privacy_group.setMaximumHeight(50)  # Limitar la altura del grupo

        general_layout.addWidget(privacy_group)



        # Privacy Features

        features_group = QGroupBox("Privacy Features")

        features_layout = QVBoxLayout()

        features_layout.setSpacing(2)

        

        self.feature_checks = {

            "block_trackers": QCheckBox("Block Trackers"),

            "block_ads": QCheckBox("Block Ads"),

            "no_persistent_cookies": QCheckBox("No Persistent Cookies"),

            "block_javascript": QCheckBox("Block JavaScript"),

            "block_images": QCheckBox("Block Images"),

            "block_webrtc": QCheckBox("Block WebRTC"),

            "block_fingerprinting": QCheckBox("Block Fingerprinting"),

            "block_third_party": QCheckBox("Block Third-Party Cookies"),

            "clear_on_exit": QCheckBox("Clear Data on Exit"),

            "do_not_track": QCheckBox("Send Do Not Track Signal"),

            "block_phishing": QCheckBox("Block Phishing Sites"),

            "block_malware": QCheckBox("Block Malware Sites"),

            "block_location": QCheckBox("Block Location Access"),

            "block_notifications": QCheckBox("Block Notifications"),

            "block_camera": QCheckBox("Block Camera Access"),

            "block_microphone": QCheckBox("Block Microphone Access")

        }



        for check in self.feature_checks.values():

            features_layout.addWidget(check)

            check.stateChanged.connect(self.on_feature_changed)



        features_group.setLayout(features_layout)

        general_layout.addWidget(features_group)



        # Pestaña de Datos de Navegación

        data_tab = QWidget()

        data_layout = QVBoxLayout()

        data_layout.setSpacing(5)

        data_tab.setLayout(data_layout)



        # Selector de tiempo para borrado de datos

        time_selector_group = QGroupBox("Time Range for Data Clearing")

        time_selector_layout = QHBoxLayout()

        time_selector_layout.setContentsMargins(5, 5, 5, 5)

        time_selector_layout.setSpacing(5)

        

        time_selector_layout.addWidget(QLabel("Clear data from:"))

        self.time_range_combo = QComboBox()

        self.time_range_combo.addItems([

            "Last hour",

            "Last 24 hours", 

            "Last 7 days",

            "Last 15 days",

            "Last 30 days",

            "All time"

        ])

        self.time_range_combo.setCurrentText("Last 24 hours")  # Valor por defecto

        self.time_range_combo.setMinimumWidth(120)

        self.time_range_combo.currentTextChanged.connect(self.update_data_preview)

        time_selector_layout.addWidget(self.time_range_combo)

        

        # Etiqueta para mostrar preview de datos a borrar

        self.data_preview_label = QLabel("Calculating...")

        self.data_preview_label.setStyleSheet("color: #666; font-size: 11px;")

        time_selector_layout.addWidget(self.data_preview_label)

        time_selector_layout.addStretch()

        

        time_selector_group.setLayout(time_selector_layout)

        time_selector_group.setMaximumHeight(50)

        data_layout.addWidget(time_selector_group)



        # Botones para borrar datos

        clear_data_group = QGroupBox("Clear Browsing Data")

        clear_data_layout = QHBoxLayout()

        clear_data_layout.setContentsMargins(5, 5, 5, 5)

        clear_data_layout.setSpacing(3)

        clear_data_layout.setAlignment(Qt.AlignLeft)



        self.clear_history_btn = QPushButton("Clear History")

        self.clear_history_btn.setFixedWidth(100)

        self.clear_history_btn.clicked.connect(self.clear_history_with_time)

        clear_data_layout.addWidget(self.clear_history_btn)



        self.clear_cookies_btn = QPushButton("Clear Cookies")

        self.clear_cookies_btn.setFixedWidth(100)

        self.clear_cookies_btn.clicked.connect(self.clear_cookies_with_time)

        clear_data_layout.addWidget(self.clear_cookies_btn)



        self.clear_cache_btn = QPushButton("Clear Cache")

        self.clear_cache_btn.setFixedWidth(100)

        self.clear_cache_btn.clicked.connect(self.clear_cache_with_time)

        clear_data_layout.addWidget(self.clear_cache_btn)



        self.clear_all_btn = QPushButton("Clear All Data")

        self.clear_all_btn.setFixedWidth(100)

        self.clear_all_btn.clicked.connect(self.clear_all_data_with_time)

        clear_data_layout.addWidget(self.clear_all_btn)



        clear_data_group.setLayout(clear_data_layout)

        clear_data_group.setMaximumHeight(50)

        data_layout.addWidget(clear_data_group)



        # Grupo de opciones de borrado automático

        auto_clear_group = QGroupBox("Auto-Clear Settings")

        auto_clear_layout = QVBoxLayout()

        auto_clear_layout.setSpacing(5)



        # Opciones de borrado automático

        self.auto_clear_check = QCheckBox("Enable automatic data clearing")

        self.auto_clear_check.clicked.connect(self.toggle_auto_clear)

        auto_clear_layout.addWidget(self.auto_clear_check)



        # Selector de frecuencia

        frequency_layout = QHBoxLayout()

        frequency_layout.addWidget(QLabel("Clear data every:"))

        self.frequency_combo = QComboBox()

        self.frequency_combo.addItems(["1 hour", "4 hours", "8 hours", "12 hours", "24 hours", "7 days"])

        self.frequency_combo.setEnabled(False)

        self.frequency_combo.activated.connect(self.on_frequency_changed)

        frequency_layout.addWidget(self.frequency_combo)

        auto_clear_layout.addLayout(frequency_layout)



        # Opciones de qué borrar automáticamente

        self.auto_clear_options = {

            "history": QCheckBox("History"),

            "cookies": QCheckBox("Cookies"),

            "cache": QCheckBox("Cache"),

            "passwords": QCheckBox("Saved Passwords"),

            "form_data": QCheckBox("Form Data"),

            "downloads": QCheckBox("Download History")

        }



        for key, check in self.auto_clear_options.items():

            check.setEnabled(False)

            check.clicked.connect(lambda checked, k=key: self.on_option_changed(k, checked))

            auto_clear_layout.addWidget(check)



        auto_clear_group.setLayout(auto_clear_layout)

        data_layout.addWidget(auto_clear_group)



        # Grupo de gestión de datos guardados

        saved_data_group = QGroupBox("Saved Data Management")

        saved_data_layout = QVBoxLayout()

        saved_data_layout.setSpacing(5)



        # Botones para gestionar datos guardados

        saved_data_buttons = QHBoxLayout()

        

        self.view_passwords_btn = QPushButton("View Saved Passwords")

        self.view_passwords_btn.clicked.connect(self.show_saved_passwords)

        saved_data_buttons.addWidget(self.view_passwords_btn)



        self.view_form_data_btn = QPushButton("View Form Data")

        self.view_form_data_btn.clicked.connect(self.show_form_data)

        saved_data_buttons.addWidget(self.view_form_data_btn)



        self.view_downloads_btn = QPushButton("View Downloads")

        self.view_downloads_btn.clicked.connect(self.show_downloads)

        saved_data_buttons.addWidget(self.view_downloads_btn)



        saved_data_layout.addLayout(saved_data_buttons)

        saved_data_group.setLayout(saved_data_layout)

        data_layout.addWidget(saved_data_group)



        # Añadir un widget vacío que se expanda para empujar el grupo hacia arriba

        spacer = QWidget()

        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        data_layout.addWidget(spacer)



        # Pestaña de Permisos de Sitios

        permissions_tab = QWidget()

        permissions_layout = QVBoxLayout()

        permissions_layout.setSpacing(5)

        permissions_tab.setLayout(permissions_layout)



        self.permissions_table = QTableWidget()

        self.permissions_table.setColumnCount(3)

        self.permissions_table.setHorizontalHeaderLabels(["Site", "Permission", "Status"])

        self.permissions_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        permissions_layout.addWidget(self.permissions_table)



        # Añadir las pestañas al widget principal

        tab_widget.addTab(general_tab, "General")

        tab_widget.addTab(data_tab, "Browsing Data")

        tab_widget.addTab(permissions_tab, "Site Permissions")



        # Crear data_label para evitar AttributeError en update_data_sharing

        self.data_label = QLabel()

        # Nota: no añadido al layout, solo para evitar errores

        

        # Ajustar el tamaño mínimo del widget

        self.setMinimumWidth(300)

        self.setMinimumHeight(400)

        

        # Inicializar preview de datos

        QTimer.singleShot(100, self.update_data_preview)  # Delay para asegurar que la UI esté lista



    def load_privacy_presets(self):

        # Cargar configuración actual

        current_level = self.settings.get_setting("privacy_level")

        self.privacy_combo.setCurrentText(current_level.capitalize())

        

        # Actualizar checkboxes

        for key, check in self.feature_checks.items():

            check.setChecked(bool(self.settings.get_setting(key)))



    def on_privacy_level_changed(self, level):

        level = level.lower()

        self.settings.set_setting("privacy_level", level)

        

        # Aplicar configuración según el nivel

        if level == "strict":

            self.apply_strict_privacy()

        elif level == "balanced":

            self.apply_balanced_privacy()

        

        self.privacy_level_changed.emit(level)

        # Emitir señal para aplicar cambios al vuelo

        self.settings_changed.emit()



    def apply_strict_privacy(self):

        for key, check in self.feature_checks.items():

            check.setChecked(True)

            self.settings.set_setting(key, True)

        # Emitir señal para aplicar cambios al vuelo

        self.settings_changed.emit()



    def apply_balanced_privacy(self):

        balanced_settings = {

            "block_trackers": True,

            "block_ads": True,

            "no_persistent_cookies": False,

            "block_javascript": False,

            "block_images": False,

            "block_webrtc": True,

            "block_fingerprinting": True,

            "block_third_party": True,

            "clear_on_exit": True,

            "do_not_track": True

        }

        

        for key, value in balanced_settings.items():

            self.feature_checks[key].setChecked(bool(value))

            self.settings.set_setting(key, value)

        # Emitir señal para aplicar cambios al vuelo

        self.settings_changed.emit()



    def on_feature_changed(self):

        # Actualizar configuración cuando cambia cualquier feature

        for key, check in self.feature_checks.items():

            self.settings.set_setting(key, check.isChecked())

        # Emitir señal para aplicar cambios al vuelo

        self.settings_changed.emit()



    def on_font_size_changed(self, size):

        # Implementar cambio de tamaño de fuente en modo lectura

        pass



    def on_theme_changed(self, theme):

        # Implementar cambio de tema en modo lectura

        pass



    def update_data_sharing(self, data):

        """Actualiza el monitor de datos compartidos"""

        self.data_label.setText(f"Data being shared: {json.dumps(data, indent=2)}")

        self.data_shared.emit(data)



    def update_filter_lists(self):

        """Actualiza las listas de filtros delegando al AdBlocker"""

        try:

            # Delegar al ad_blocker para compilación y swap atómico

            self.ad_blocker.update_filter_lists()

        except Exception as e:

            print(f"Error al actualizar las listas de filtros: {str(e)}")

    

    def get_time_range_in_hours(self, time_range_text):

        """Convierte el texto del selector de tiempo a horas"""

        time_mapping = {

            "Last hour": 1,

            "Last 24 hours": 24,

            "Last 7 days": 24 * 7,

            "Last 15 days": 24 * 15,

            "Last 30 days": 24 * 30,

            "All time": None  # None significa todo el tiempo

        }

        return time_mapping.get(time_range_text, 24)  # Default: 24 horas

    

    def get_time_cutoff(self, hours):

        """Obtiene el timestamp de corte basado en las horas"""

        if hours is None:

            return None  # Todo el tiempo

        

        current_time = int(time.time() * 1000000)  # Microsegundos

        cutoff_time = current_time - (hours * 60 * 60 * 1000000)

        return cutoff_time

    

    def update_data_preview(self):

        """Actualiza el preview de datos que serán borrados"""

        try:

            time_range_text = self.time_range_combo.currentText()

            hours = self.get_time_range_in_hours(time_range_text)

            

            if hours is None:

                # Todo el tiempo

                history_count = self.count_all_history_entries()

                self.data_preview_label.setText(f"Will clear: ~{history_count} history entries, all cookies & cache")

            else:

                # Tiempo específico

                history_count = self.count_history_entries_by_time(hours)

                self.data_preview_label.setText(f"Will clear: ~{history_count} history entries from {time_range_text.lower()}")

                

        except Exception as e:

            self.data_preview_label.setText("Preview unavailable")

            print(f"Error updating data preview: {str(e)}")

    

    def count_all_history_entries(self):

        """Cuenta todas las entradas del historial"""

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            history_db = os.path.join(profile_path, "History")

            

            if os.path.exists(history_db):

                conn = sqlite3.connect(history_db)

                cursor = conn.cursor()

                cursor.execute("SELECT COUNT(*) FROM urls")

                count = cursor.fetchone()[0]

                conn.close()

                return count

            return 0

        except Exception as e:

            print(f"Error counting history entries: {str(e)}")

            return 0

    

    def count_history_entries_by_time(self, hours):

        """Cuenta las entradas del historial por rango de tiempo"""

        try:

            cutoff_time = self.get_time_cutoff(hours)

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            history_db = os.path.join(profile_path, "History")

            

            if os.path.exists(history_db):

                conn = sqlite3.connect(history_db)

                cursor = conn.cursor()

                cursor.execute("""

                    SELECT COUNT(DISTINCT url_id) FROM visits 

                    WHERE visit_time > ?

                """, (cutoff_time,))

                count = cursor.fetchone()[0]

                conn.close()

                return count

            return 0

        except Exception as e:

            print(f"Error counting history entries by time: {str(e)}")

            return 0



    def clear_history_with_time(self):

        """Borra el historial de navegación según el rango de tiempo seleccionado"""

        try:

            time_range_text = self.time_range_combo.currentText()

            hours = self.get_time_range_in_hours(time_range_text)

            

            reply = QMessageBox.question(

                self, 

                "Confirm Clear History",

                f"Are you sure you want to clear browsing history from {time_range_text.lower()}?",

                QMessageBox.Yes | QMessageBox.No

            )

            

            if reply == QMessageBox.Yes:

                if hours is None:

                    # Borrar todo el historial

                    self.history_manager.clear_history()

                else:

                    # Borrar historial con rango de tiempo específico

                    self.clear_history_by_time(hours)

                

                self.data_cleared.emit("history")

                QMessageBox.information(self, "Success", f"Browsing history from {time_range_text.lower()} cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing history: {str(e)}")

    

    def clear_history_by_time(self, hours):

        """Borra el historial por rango de tiempo específico"""

        try:

            cutoff_time = self.get_time_cutoff(hours)

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            history_db = os.path.join(profile_path, "History")

            

            if os.path.exists(history_db):

                conn = sqlite3.connect(history_db)

                cursor = conn.cursor()

                

                # Borrar visitas después del tiempo de corte

                cursor.execute("DELETE FROM visits WHERE visit_time > ?", (cutoff_time,))

                

                # Borrar URLs que no tienen visitas

                cursor.execute("""

                    DELETE FROM urls WHERE id NOT IN (

                        SELECT DISTINCT url_id FROM visits

                    )

                """)

                

                conn.commit()

                conn.close()

                print(f"History cleared for last {hours} hours")

        except Exception as e:

            print(f"Error clearing history by time: {str(e)}")

            raise



    def clear_cookies_with_time(self):

        """Borra las cookies según el rango de tiempo seleccionado"""

        try:

            time_range_text = self.time_range_combo.currentText()

            hours = self.get_time_range_in_hours(time_range_text)

            

            reply = QMessageBox.question(

                self, 

                "Confirm Clear Cookies",

                f"Are you sure you want to clear cookies from {time_range_text.lower()}?",

                QMessageBox.Yes | QMessageBox.No

            )

            

            if reply == QMessageBox.Yes:

                if hours is None:

                    # Borrar todas las cookies

                    profile = QWebEngineProfile.defaultProfile()

                    profile.cookieStore().deleteAllCookies()

                else:

                    # Para cookies, Qt WebEngine no permite borrado por tiempo específico

                    # Mostrar advertencia y borrar todas

                    reply2 = QMessageBox.question(

                        self,

                        "Cookie Clearing Limitation",

                        f"Qt WebEngine doesn't support time-based cookie clearing.\n"

                        f"Would you like to clear ALL cookies instead?",

                        QMessageBox.Yes | QMessageBox.No

                    )

                    

                    if reply2 == QMessageBox.Yes:

                        profile = QWebEngineProfile.defaultProfile()

                        profile.cookieStore().deleteAllCookies()

                    else:

                        return

                

                self.data_cleared.emit("cookies")

                QMessageBox.information(self, "Success", "Cookies cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing cookies: {str(e)}")



    def clear_cache_with_time(self):

        """Borra la caché del navegador según el rango de tiempo seleccionado"""

        try:

            time_range_text = self.time_range_combo.currentText()

            

            reply = QMessageBox.question(

                self, 

                "Confirm Clear Cache",

                f"Are you sure you want to clear cache from {time_range_text.lower()}?",

                QMessageBox.Yes | QMessageBox.No

            )

            

            if reply == QMessageBox.Yes:

                # Qt WebEngine no permite borrado de caché por tiempo específico

                # Siempre borra toda la caché

                profile = QWebEngineProfile.defaultProfile()

                profile.clearHttpCache()

                

                self.data_cleared.emit("cache")

                QMessageBox.information(self, "Success", "Cache cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing cache: {str(e)}")



    def clear_all_data_with_time(self):

        """Borra todos los datos de navegación según el rango de tiempo seleccionado"""

        try:

            time_range_text = self.time_range_combo.currentText()

            

            reply = QMessageBox.question(

                self, 

                "Confirm Clear All Data",

                f"Are you sure you want to clear ALL browsing data from {time_range_text.lower()}?\n"

                f"This includes history, cookies, cache, and other stored data.\n"

                f"This action cannot be undone.",

                QMessageBox.Yes | QMessageBox.No

            )

            

            if reply == QMessageBox.Yes:

                # Borrar historial con tiempo específico

                self.clear_history_with_time_internal()

                

                # Borrar cookies (siempre todas debido a limitaciones de Qt)

                profile = QWebEngineProfile.defaultProfile()

                profile.cookieStore().deleteAllCookies()

                

                # Borrar caché (siempre toda debido a limitaciones de Qt)

                profile.clearHttpCache()

                

                # Borrar datos adicionales si es "All time"

                hours = self.get_time_range_in_hours(time_range_text)

                if hours is None:

                    self.clear_additional_data()

                

                self.data_cleared.emit("all")

                QMessageBox.information(self, "Success", f"All browsing data from {time_range_text.lower()} cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing all data: {str(e)}")

    

    def clear_history_with_time_internal(self):

        """Método interno para borrar historial sin mostrar diálogos"""

        try:

            time_range_text = self.time_range_combo.currentText()

            hours = self.get_time_range_in_hours(time_range_text)

            

            if hours is None:

                self.history_manager.clear_history()

            else:

                self.clear_history_by_time(hours)

        except Exception as e:

            print(f"Error in clear_history_with_time_internal: {str(e)}")

    

    def clear_additional_data(self):

        """Borra datos adicionales cuando se selecciona 'All time'"""

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            

            # Borrar contraseñas guardadas

            login_db = os.path.join(profile_path, "Login Data")

            if os.path.exists(login_db):

                conn = sqlite3.connect(login_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM logins")

                conn.commit()

                conn.close()

            

            # Borrar datos de formularios

            form_data_db = os.path.join(profile_path, "Web Data")

            if os.path.exists(form_data_db):

                conn = sqlite3.connect(form_data_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM autofill")

                conn.commit()

                conn.close()

            

            # Borrar historial de descargas

            downloads_db = os.path.join(profile_path, "History")

            if os.path.exists(downloads_db):

                conn = sqlite3.connect(downloads_db)

                cursor = conn.cursor()

                cursor.execute("DELETE FROM downloads")

                cursor.execute("DELETE FROM downloads_url_chains")

                conn.commit()

                conn.close()

                

            print("Additional data cleared successfully")

        except Exception as e:

            print(f"Error clearing additional data: {str(e)}")



    def clear_history(self):

        """Borra el historial de navegación (método legacy)"""

        try:

            self.history_manager.clear_history()

            self.data_cleared.emit("history")

            QMessageBox.information(self, "Success", "Browsing history cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing history: {str(e)}")



    def clear_cookies(self):

        """Borra las cookies (método legacy)"""

        try:

            profile = QWebEngineProfile.defaultProfile()

            profile.cookieStore().deleteAllCookies()

            self.data_cleared.emit("cookies")

            QMessageBox.information(self, "Success", "Cookies cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing cookies: {str(e)}")



    def clear_cache(self):

        """Borra la caché del navegador (método legacy)"""

        try:

            profile = QWebEngineProfile.defaultProfile()

            profile.clearHttpCache()

            self.data_cleared.emit("cache")

            QMessageBox.information(self, "Success", "Cache cleared successfully")

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error clearing cache: {str(e)}")



    def clear_all_data(self):

        """Borra todos los datos de navegación (método legacy)"""

        reply = QMessageBox.question(self, "Confirm Clear All",

                                   "Are you sure you want to clear all browsing data? This cannot be undone.",

                                   QMessageBox.Yes | QMessageBox.No)

        

        if reply == QMessageBox.Yes:

            self.clear_history()

            self.clear_cookies()

            self.clear_cache()

            self.data_cleared.emit("all")

            QMessageBox.information(self, "Success", "All browsing data cleared successfully")



    def update_site_permissions(self):

        """Actualiza la tabla de permisos de sitios"""

        try:

            profile = QWebEngineProfile.defaultProfile()

            # Obtener permisos de sitios

            # Implementar lógica para obtener y mostrar permisos

            pass

        except Exception as e:

            print(f"Error updating site permissions: {str(e)}")



    def install_youtube_script(self, profile):

        """Instala script para bloquear anuncios específicamente en YouTube"""

        try:

            # Remover script existente si ya existe

            scripts = profile.scripts()

            existing_script = scripts.findScript("yt-adblock")

            if not existing_script.isNull():

                scripts.remove(existing_script)



            # Crear nuevo script

            script = QWebEngineScript()

            script.setName("yt-adblock")

            script.setInjectionPoint(QWebEngineScript.DocumentCreation)

            script.setWorldId(QWebEngineScript.ApplicationWorld)

            script.setRunsOnSubFrames(True)

            

            # JavaScript para bloquear anuncios de YouTube

            js_code = """

(function() {

    'use strict';

    

    console.log('YouTube AdBlock script loaded');

    

    // Interceptar ytInitialPlayerResponse

    let originalDefineProperty = Object.defineProperty;

    Object.defineProperty = function(obj, prop, descriptor) {

        if (prop === 'ytInitialPlayerResponse' && descriptor && descriptor.value) {

            try {

                if (descriptor.value.adPlacements) {

                    delete descriptor.value.adPlacements;

                }

                if (descriptor.value.playerAds) {

                    delete descriptor.value.playerAds;

                }

                if (descriptor.value.adSlots) {

                    delete descriptor.value.adSlots;

                }

            } catch (e) {}

        }

        return originalDefineProperty.call(this, obj, prop, descriptor);

    };

    

    // Parchear fetch para bloquear requests de anuncios

    const originalFetch = window.fetch;

    window.fetch = function(url, options) {

        if (typeof url === 'string' || url instanceof URL) {

            const urlStr = url.toString();

            const blockedPatterns = [

                'pagead2.googlesyndication.com',

                'googleads.g.doubleclick.net',

                'pubads.g.doubleclick.net',

                'securepubads.g.doubleclick.net',

                '/pagead/',

                '/api/stats/ads'

            ];

            

            for (const pattern of blockedPatterns) {

                if (urlStr.includes(pattern)) {

                    console.log('Blocked fetch to:', urlStr);

                    return Promise.reject(new Error('Blocked by AdBlock'));

                }

            }

        }

        return originalFetch.apply(this, arguments);

    };

    

    // Parchear XMLHttpRequest

    const originalOpen = XMLHttpRequest.prototype.open;

    XMLHttpRequest.prototype.open = function(method, url) {

        if (typeof url === 'string') {

            const blockedPatterns = [

                'pagead2.googlesyndication.com',

                'googleads.g.doubleclick.net',

                'pubads.g.doubleclick.net',

                'securepubads.g.doubleclick.net',

                '/pagead/',

                '/api/stats/ads'

            ];

            

            for (const pattern of blockedPatterns) {

                if (url.includes(pattern)) {

                    console.log('Blocked XHR to:', url);

                    // Redirigir a endpoint dummy

                    arguments[1] = 'data:text/plain,blocked';

                    break;

                }

            }

        }

        return originalOpen.apply(this, arguments);

    };

    

    // Limpiar config de player existente

    if (window.ytplayer && window.ytplayer.config) {

        try {

            if (window.ytplayer.config.args) {

                delete window.ytplayer.config.args.ad_device;

                delete window.ytplayer.config.args.ad_flags;

                delete window.ytplayer.config.args.ad_logging_flag;

                delete window.ytplayer.config.args.ad_preroll;

                delete window.ytplayer.config.args.ad_tag;

                delete window.ytplayer.config.args.adsystem;

            }

        } catch (e) {}

    }

    

})();

            """

            

            script.setSourceCode(js_code)

            

            # Aplicar solo a YouTube

            script.setWorldId(QWebEngineScript.ApplicationWorld)

            

            # Añadir script al perfil

            scripts.insert(script)

            print("Script de YouTube AdBlock instalado")

            

        except Exception as e:

            print(f"Error instalando script de YouTube: {e}")



    def apply_privacy_settings(self, browser):

        """Aplica la configuración de privacidad al navegador"""

        try:

            if browser and hasattr(browser, 'page'):

                profile = browser.page().profile()

                

                # Aplicar interceptor de anuncios solo si Block Ads está activado

                if self.settings.get_setting("block_ads"):

                    profile.setUrlRequestInterceptor(self.ad_blocker)

                    # Instalar script de YouTube para bloqueo adicional

                    self.install_youtube_script(profile)

                else:

                    profile.setUrlRequestInterceptor(None)

                    # Remover script de YouTube si existe

                    try:

                        scripts = profile.scripts()

                        existing_script = scripts.findScript("yt-adblock")

                        if not existing_script.isNull():

                            scripts.remove(existing_script)

                    except Exception as e:

                        print(f"Error removiendo script de YouTube: {e}")

                

                # Configurar permisos

                settings = profile.settings()

                

                # JavaScript

                settings.setAttribute(QWebEngineSettings.JavascriptEnabled, 

                                   not self.settings.get_setting("block_javascript"))

                

                # Fingerprinting/WebGL

                settings.setAttribute(QWebEngineSettings.WebGLEnabled, 

                                   not self.settings.get_setting("block_fingerprinting"))

                

                # Política de cookies persistentes (separada de third-party)

                if self.settings.get_setting("no_persistent_cookies"):

                    profile.setPersistentCookiesPolicy(QWebEngineProfile.NoPersistentCookies)

                else:

                    profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)

                

                # Configurar third-party cookies específicamente

                if hasattr(profile, 'setThirdPartyCookiePolicy'):

                    if self.settings.get_setting("block_third_party"):

                        # Bloquear cookies de terceros usando API nativa

                        if hasattr(QWebEngineProfile, 'NoThirdPartyCookies'):

                            profile.setThirdPartyCookiePolicy(QWebEngineProfile.NoThirdPartyCookies)

                        elif hasattr(QWebEngineProfile, 'ForcePersistentCookies'):

                            # Fallback para versiones más antiguas

                            profile.setPersistentCookiesPolicy(QWebEngineProfile.ForcePersistentCookies)

                    else:

                        # Permitir cookies de terceros

                        if hasattr(QWebEngineProfile, 'AllowThirdPartyCookies'):

                            profile.setThirdPartyCookiePolicy(QWebEngineProfile.AllowThirdPartyCookies)

                        elif hasattr(QWebEngineProfile, 'AllowAll'):

                            profile.setThirdPartyCookiePolicy(QWebEngineProfile.AllowAll)

                        else:

                            # Fallback: usar política persistente por defecto

                            profile.setPersistentCookiesPolicy(QWebEngineProfile.AllowPersistentCookies)

                else:

                    # Qt 6.x: confiar en reglas $third-party del adblock

                    pass

                

                # Configurar WebRTC

                if self.settings.get_setting("block_webrtc"):

                    if hasattr(QWebEngineSettings, "WebRTCPublicInterfacesOnly"):

                        settings.setAttribute(QWebEngineSettings.WebRTCPublicInterfacesOnly, True)

                    # WebRTC configuration applied

                

                print("Configuración de privacidad aplicada correctamente")

        except Exception as e:

            print(f"Error al aplicar configuración de privacidad: {str(e)}")



    def load_auto_clear_settings(self):

        """Carga la configuración de borrado automático"""

        try:

            # Cargar estado del checkbox principal

            enabled = self.settings.get_setting("auto_clear_enabled")

            self.auto_clear_check.setChecked(bool(enabled))

            

            # Cargar frecuencia

            frequency = self.settings.get_setting("auto_clear_frequency")

            if frequency:

                self.frequency_combo.setCurrentText(frequency)

            

            # Cargar opciones individuales

            for key, check in self.auto_clear_options.items():

                value = self.settings.get_setting(f"auto_clear_{key}")

                check.setChecked(bool(value))

                check.setEnabled(enabled)

            

            # Iniciar temporizador si está habilitado

            if enabled:

                self.start_auto_clear_timer()

                

            print("Auto-clear settings loaded")

        except Exception as e:

            print(f"Error loading auto-clear settings: {str(e)}")



    def toggle_auto_clear(self, checked):

        """Habilita/deshabilita las opciones de borrado automático"""

        try:

            self.frequency_combo.setEnabled(checked)

            for check in self.auto_clear_options.values():

                check.setEnabled(checked)

            

            # Guardar configuración

            self.settings.set_setting("auto_clear_enabled", checked)

            self.settings.save_settings()

            

            # Iniciar/detener temporizador

            if checked:

                self.start_auto_clear_timer()

            else:

                self.stop_auto_clear_timer()

                

            print(f"Auto-clear {'enabled' if checked else 'disabled'}")

        except Exception as e:

            print(f"Error toggling auto-clear: {str(e)}")



    def on_frequency_changed(self, index):

        """Maneja el cambio en la frecuencia de borrado"""

        try:

            frequency = self.frequency_combo.currentText()

            self.settings.set_setting("auto_clear_frequency", frequency)

            self.settings.save_settings()

            

            if self.auto_clear_check.isChecked():

                self.start_auto_clear_timer()

                

            print(f"Frequency changed to: {frequency}")

        except Exception as e:

            print(f"Error changing frequency: {str(e)}")



    def on_option_changed(self, key, checked):

        """Maneja el cambio en una opción específica"""

        try:

            self.settings.set_setting(f"auto_clear_{key}", checked)

            self.settings.save_settings()

            print(f"Option {key} {'enabled' if checked else 'disabled'}")

        except Exception as e:

            print(f"Error updating option {key}: {str(e)}")



    def start_auto_clear_timer(self):

        """Inicia el temporizador de borrado automático"""

        try:

            if hasattr(self, 'auto_clear_timer'):

                self.auto_clear_timer.stop()

            

            self.auto_clear_timer = QTimer(self)  # Asegurar ciclo de vida correcto

            self.auto_clear_timer.timeout.connect(self.auto_clear_data)

            

            frequency = self.settings.get_setting("auto_clear_frequency")

            hours = int(frequency.split()[0])

            self.auto_clear_timer.start(hours * 60 * 60 * 1000)

            print(f"Auto-clear timer started: {hours} hours")

        except Exception as e:

            print(f"Error starting auto-clear timer: {str(e)}")



    def stop_auto_clear_timer(self):

        """Detiene el temporizador de borrado automático"""

        try:

            if hasattr(self, 'auto_clear_timer'):

                self.auto_clear_timer.stop()

                print("Auto-clear timer stopped")

        except Exception as e:

            print(f"Error stopping auto-clear timer: {str(e)}")



    def auto_clear_data(self):

        """Ejecuta el borrado automático de datos"""

        try:

            profile = QWebEngineProfile.defaultProfile()

            

            if self.settings.get_setting("auto_clear_history"):

                self.clear_history()

            

            if self.settings.get_setting("auto_clear_cookies"):

                profile.cookieStore().deleteAllCookies()

            

            if self.settings.get_setting("auto_clear_cache"):

                profile.clearHttpCache()

            

            if self.settings.get_setting("auto_clear_passwords"):

                self.auto_clear.clear_saved_passwords()

            

            if self.settings.get_setting("auto_clear_form_data"):

                self.auto_clear.clear_form_data()

            

            if self.settings.get_setting("auto_clear_downloads"):

                self.auto_clear.clear_downloads()

                

            print("Auto-clear data completed")

        except Exception as e:

            print(f"Error in auto-clear data: {str(e)}")



    def show_saved_passwords(self):

        """Muestra las contraseñas guardadas"""

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            login_db = os.path.join(profile_path, "Login Data")

            

            if os.path.exists(login_db):

                conn = sqlite3.connect(login_db)

                cursor = conn.cursor()

                cursor.execute("SELECT origin_url, username_value FROM logins")

                passwords = {row[0]: row[1] for row in cursor.fetchall()}

                conn.close()

                

                dialog = SavedDataDialog("Saved Passwords", passwords, self)

                dialog.exec()

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error loading passwords: {str(e)}")



    def show_form_data(self):

        """Muestra los datos de formularios guardados"""

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            form_data_db = os.path.join(profile_path, "Web Data")

            

            if os.path.exists(form_data_db):

                conn = sqlite3.connect(form_data_db)

                cursor = conn.cursor()

                cursor.execute("SELECT name, value FROM autofill")

                form_data = {row[0]: row[1] for row in cursor.fetchall()}

                conn.close()

                

                dialog = SavedDataDialog("Saved Form Data", form_data, self)

                dialog.exec()

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error loading form data: {str(e)}")



    def show_downloads(self):

        """Muestra el historial de descargas"""

        try:

            profile_path = QWebEngineProfile.defaultProfile().persistentStoragePath()

            downloads_db = os.path.join(profile_path, "History")

            

            if os.path.exists(downloads_db):

                conn = sqlite3.connect(downloads_db)

                cursor = conn.cursor()

                cursor.execute("""

                    SELECT url, target_path, start_time 

                    FROM downloads 

                    JOIN downloads_url_chains ON downloads.id = downloads_url_chains.id

                """)

                downloads = {row[0]: f"Path: {row[1]}, Time: {row[2]}" for row in cursor.fetchall()}

                conn.close()

                

                dialog = SavedDataDialog("Download History", downloads, self)

                dialog.exec()

        except Exception as e:

            QMessageBox.critical(self, "Error", f"Error loading downloads: {str(e)}")



    def show_history(self):

        """Muestra el diálogo de historial"""

        dialog = HistoryDialog(self.history_manager, self.parent)

        dialog.exec() 