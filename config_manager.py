#!/usr/bin/env python3
"""
Sistema de Gestión de Configuración Centralizada para Scrapelio Browser
Maneja la carga y acceso a configuraciones desde config.yaml
"""

import yaml
import os
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

# Configurar logging
logger = logging.getLogger(__name__)


@dataclass
class BackendConfig:
    """Configuración del backend"""
    primary_url: str
    fallback_urls: List[str]
    timeouts: Dict[str, int]
    max_retries: int
    retry_backoff: int
    license_validation: Dict[str, int]


@dataclass
class FrontendConfig:
    """Configuración del frontend"""
    url: str
    registration_url: str
    login_url: str
    dashboard_url: str


@dataclass
class SMTPConfig:
    """Configuración de email"""
    host: str
    port: int
    web_port: int
    from_email: str


@dataclass
class PluginsConfig:
    """Configuración de plugins"""
    directory: str
    cache_duration: int
    validate_checksum: bool
    validate_signature: bool
    create_backup: bool
    backup_directory: str


@dataclass
class SecurityConfig:
    """Configuración de seguridad"""
    use_keyring: bool
    use_qsettings: bool
    secret_key: str
    algorithm: str
    access_token_expire_minutes: int
    refresh_token_expire_days: int


class ConfigManager:
    """
    Gestor centralizado de configuración para Scrapelio Browser
    
    Características:
    - Carga configuración desde config.yaml
    - Soporta variables de entorno como override
    - Sistema de fallbacks para URLs
    - Validación de configuración
    - Cache de configuración en memoria
    """
    
    _instance = None
    _config: Dict[str, Any] = None
    
    def __new__(cls):
        """Singleton pattern para asegurar una sola instancia"""
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        """Inicializar el gestor de configuración"""
        if self._config is None:
            self.config_file = self._find_config_file()
            self.load_config()
    
    def _find_config_file(self) -> Path:
        """
        Buscar archivo config.yaml en múltiples ubicaciones
        
        Returns:
            Path: Ruta al archivo de configuración
        """
        # Posibles ubicaciones del archivo de configuración
        possible_paths = [
            Path(__file__).parent / "config.yaml",  # Mismo directorio que este script
            Path.cwd() / "config.yaml",  # Directorio actual
            Path.home() / ".scrapelio" / "config.yaml",  # Home del usuario
            Path("/etc/scrapelio/config.yaml"),  # Sistema (Linux)
        ]
        
        for path in possible_paths:
            if path.exists():
                logger.info(f"Config file found: {path}")
                return path
        
        # Si no se encuentra, usar el del directorio del script
        default_path = Path(__file__).parent / "config.yaml"
        logger.warning(f"Config file not found, using default: {default_path}")
        return default_path
    
    def load_config(self):
        """Cargar configuración desde archivo YAML"""
        try:
            if not self.config_file.exists():
                logger.error(f"Config file not found: {self.config_file}")
                self._config = self._get_default_config()
                return
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f)
            
            # Override con variables de entorno
            self._apply_env_overrides()
            
            logger.info("Configuration loaded successfully")
            
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            self._config = self._get_default_config()
    
    def _apply_env_overrides(self):
        """Aplicar overrides desde variables de entorno"""
        # Backend URL
        if os.getenv("SCRAPELIO_BACKEND_URL"):
            self._config['backend']['primary_url'] = os.getenv("SCRAPELIO_BACKEND_URL")
        
        # Frontend URL
        if os.getenv("SCRAPELIO_FRONTEND_URL"):
            self._config['frontend']['url'] = os.getenv("SCRAPELIO_FRONTEND_URL")
        
        # Network mode
        if os.getenv("SCRAPELIO_NETWORK_MODE"):
            self._config['network']['mode'] = os.getenv("SCRAPELIO_NETWORK_MODE")
        
        # Log level
        if os.getenv("SCRAPELIO_LOG_LEVEL"):
            self._config['logging']['level'] = os.getenv("SCRAPELIO_LOG_LEVEL")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Obtener configuración por defecto si no se puede cargar el archivo
        
        Returns:
            Dict: Configuración por defecto
        """
        return {
            'backend': {
                'primary_url': 'http://192.168.1.175:8000',
                'fallback_urls': ['http://localhost:8000', 'http://127.0.0.1:8000'],
                'timeouts': {'auth': 15, 'api': 10, 'plugin_download': 60, 'quick_check': 5},
                'max_retries': 3,
                'retry_backoff': 2,
                'license_validation': {'interval': 300, 'cache_duration': 300}
            },
            'frontend': {
                'url': 'http://192.168.1.175:4321',
                'registration_url': 'http://192.168.1.175:4321/auth/registro.html',
                'login_url': 'http://192.168.1.175:4321/auth/login.html',
                'dashboard_url': 'http://192.168.1.175:4321/app/dashboard.html'
            },
            'smtp': {
                'host': 'localhost',
                'port': 1025,
                'web_port': 8025,
                'from_email': 'noreply@scrapelio.com'
            },
            'plugins': {
                'directory': '../products',
                'cache_duration': 300,
                'validate_checksum': True,
                'validate_signature': False,
                'create_backup': True,
                'backup_directory': './plugin_backups'
            },
            'security': {
                'use_keyring': False,
                'use_qsettings': True,
                'secret_key': 'scrapelio-secret-key-change-in-production',
                'algorithm': 'HS256',
                'access_token_expire_minutes': 30,
                'refresh_token_expire_days': 7
            },
            'network': {
                'mode': 'network',
                'health_check_interval': 30,
                'connection_timeout': 10
            },
            'logging': {
                'level': 'INFO',
                'file': 'scrapelio_browser.log',
                'max_size': 10485760,
                'backup_count': 3
            }
        }
    
    # ============================================
    # MÉTODOS DE ACCESO A CONFIGURACIÓN
    # ============================================
    
    def get_backend_url(self, use_fallback: bool = False) -> str:
        """
        Obtener URL del backend
        
        Args:
            use_fallback: Si True, intenta con URLs de fallback
            
        Returns:
            str: URL del backend
        """
        if use_fallback and self._config['backend'].get('fallback_urls'):
            return self._config['backend']['fallback_urls'][0]
        return self._config['backend']['primary_url']
    
    def get_backend_fallback_urls(self) -> List[str]:
        """Obtener lista de URLs de fallback"""
        return self._config['backend'].get('fallback_urls', [])
    
    def get_all_backend_urls(self) -> List[str]:
        """Obtener todas las URLs del backend (primaria + fallbacks)"""
        urls = [self._config['backend']['primary_url']]
        urls.extend(self._config['backend'].get('fallback_urls', []))
        return urls
    
    def get_frontend_url(self) -> str:
        """Obtener URL del frontend/sitio web"""
        return self._config['frontend']['url']
    
    def get_registration_url(self) -> str:
        """Obtener URL de registro"""
        return self._config['frontend'].get('registration_url', 
                                           f"{self.get_frontend_url()}/auth/registro.html")
    
    def get_login_url(self) -> str:
        """Obtener URL de login"""
        return self._config['frontend'].get('login_url',
                                           f"{self.get_frontend_url()}/auth/login.html")
    
    def get_timeout(self, operation: str = 'api') -> int:
        """
        Obtener timeout para tipo de operación específica
        
        Args:
            operation: Tipo de operación ('auth', 'api', 'plugin_download', 'quick_check')
            
        Returns:
            int: Timeout en segundos
        """
        return self._config['backend']['timeouts'].get(operation, 10)
    
    def get_max_retries(self) -> int:
        """Obtener número máximo de reintentos"""
        return self._config['backend'].get('max_retries', 5)
    
    def get_retry_backoff(self) -> float:
        """Obtener multiplicador de backoff exponencial"""
        return self._config['backend'].get('retry_backoff', 2.0)
    
    def get_initial_retry_delay(self) -> float:
        """Obtener delay inicial antes del primer reintento (segundos)"""
        return self._config['backend'].get('initial_retry_delay', 1.0)
    
    def get_max_retry_delay(self) -> float:
        """Obtener delay máximo entre reintentos (segundos)"""
        return self._config['backend'].get('max_retry_delay', 30.0)
    
    def get_license_validation_interval(self) -> int:
        """Obtener intervalo de validación de licencias (en segundos)"""
        return self._config['backend']['license_validation'].get('interval', 300)
    
    def get_license_cache_duration(self) -> int:
        """Obtener duración del caché de licencias (en segundos)"""
        return self._config['backend']['license_validation'].get('cache_duration', 300)
    
    def get_smtp_config(self) -> SMTPConfig:
        """Obtener configuración de SMTP"""
        smtp = self._config.get('smtp', {})
        return SMTPConfig(
            host=smtp.get('host', 'localhost'),
            port=smtp.get('port', 1025),
            web_port=smtp.get('web_port', 8025),
            from_email=smtp.get('from_email', 'noreply@scrapelio.com')
        )
    
    def get_plugins_directory(self) -> str:
        """Obtener directorio de plugins"""
        return self._config['plugins'].get('directory', '../products')
    
    def use_keyring_for_tokens(self) -> bool:
        """Verificar si se debe usar keyring para tokens"""
        return self._config['security'].get('use_keyring', False)
    
    def use_qsettings_for_tokens(self) -> bool:
        """Verificar si se debe usar QSettings para tokens"""
        return self._config['security'].get('use_qsettings', True)
    
    def get_log_level(self) -> str:
        """Obtener nivel de logging"""
        return self._config['logging'].get('level', 'INFO')
    
    def get_log_file(self) -> str:
        """Obtener archivo de log"""
        return self._config['logging'].get('file', 'scrapelio_browser.log')

    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtener valor de configuración usando dot notation
        
        Args:
            key: Clave en formato dot notation (ej: 'plugins.validate_checksum')
            default: Valor por defecto si la clave no existe
            
        Returns:
            Any: Valor de configuración o default
            
        Examples:
            >>> config.get('plugins.validate_checksum', True)
            True
            >>> config.get('plugins.backup_directory', './backups')
            './plugin_backups'
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    # ============================================
    # MÉTODOS ÚTILES
    # ============================================
    
    def reload_config(self):
        """Recargar configuración desde archivo"""
        logger.info("Reloading configuration...")
        self.load_config()
    
    def get_raw_config(self) -> Dict[str, Any]:
        """Obtener configuración raw completa"""
        return self._config
    
    def print_config(self):
        """Imprimir configuración actual (para debugging)"""
        print("=" * 60)
        print("SCRAPELIO BROWSER - CONFIGURACIÓN ACTUAL")
        print("=" * 60)
        print(f"Backend URL: {self.get_backend_url()}")
        print(f"Frontend URL: {self.get_frontend_url()}")
        print(f"Timeouts: {self._config['backend']['timeouts']}")
        print(f"Max Retries: {self.get_max_retries()}")
        print(f"Log Level: {self.get_log_level()}")
        print("=" * 60)


# Instancia global única (singleton)
config = ConfigManager()


# ============================================
# FUNCIONES DE CONVENIENCIA
# ============================================

def get_backend_url() -> str:
    """Función de conveniencia para obtener URL del backend"""
    return config.get_backend_url()


def get_frontend_url() -> str:
    """Función de conveniencia para obtener URL del frontend"""
    return config.get_frontend_url()


def get_registration_url() -> str:
    """Función de conveniencia para obtener URL de registro"""
    return config.get_registration_url()


def get_config() -> ConfigManager:
    """Obtener instancia del ConfigManager"""
    return config


if __name__ == "__main__":
    # Test del ConfigManager
    print("Testing ConfigManager...")
    config.print_config()
    
    print("\nTesting accessors...")
    print(f"Backend URL: {get_backend_url()}")
    print(f"Frontend URL: {get_frontend_url()}")
    print(f"Registration URL: {get_registration_url()}")
    print(f"Auth timeout: {config.get_timeout('auth')}s")
    print(f"Plugin download timeout: {config.get_timeout('plugin_download')}s")

