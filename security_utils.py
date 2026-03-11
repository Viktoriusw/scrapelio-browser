#!/usr/bin/env python3
"""
Utilidades de seguridad para cifrado de tokens y datos sensibles
"""

import os
import base64
import hashlib
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from typing import Optional


class TokenEncryption:
    """Clase para cifrado seguro de tokens"""
    
    def __init__(self):
        """Inicializa el sistema de cifrado"""
        self._key = None
        self._fernet = None
        self._initialize_encryption()
    
    def _initialize_encryption(self):
        """Inicializa la clave de cifrado"""
        # Generar una clave única por máquina basada en identificadores del sistema
        machine_id = self._get_machine_id()
        salt = b'scrapelio_browser_salt_v1'  # Salt fijo para consistencia
        
        # Derivar clave usando PBKDF2HMAC
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(machine_id.encode()))
        
        self._key = key
        self._fernet = Fernet(key)
    
    def _get_machine_id(self) -> str:
        """Obtiene un identificador único de la máquina"""
        try:
            # En Linux, usa /etc/machine-id
            if os.path.exists('/etc/machine-id'):
                with open('/etc/machine-id', 'r') as f:
                    return f.read().strip()
            
            # En Windows, usa una combinación de variables de entorno
            import platform
            machine_data = f"{platform.node()}_{platform.machine()}_{os.getenv('USERNAME', 'default')}"
            return hashlib.sha256(machine_data.encode()).hexdigest()
        except Exception:
            # Fallback: usar un hash del directorio home
            home = os.path.expanduser('~')
            return hashlib.sha256(home.encode()).hexdigest()
    
    def encrypt(self, data: str) -> str:
        """
        Cifra datos sensibles
        
        Args:
            data: String a cifrar
            
        Returns:
            String cifrado en base64
        """
        if not data:
            return ""
        
        try:
            encrypted = self._fernet.encrypt(data.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception as e:
            print(f"[SECURITY] Error encrypting data: {e}")
            return ""
    
    def decrypt(self, encrypted_data: str) -> str:
        """
        Descifra datos
        
        Args:
            encrypted_data: String cifrado en base64
            
        Returns:
            String descifrado
        """
        if not encrypted_data:
            return ""
        
        try:
            encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
            decrypted = self._fernet.decrypt(encrypted)
            return decrypted.decode()
        except Exception as e:
            print(f"[SECURITY] Error decrypting data: {e}")
            return ""
    
    # Alias para compatibilidad
    def encrypt_token(self, token: str) -> str:
        """Alias para encrypt() - compatibilidad con código existente"""
        return self.encrypt(token)
    
    def decrypt_token(self, encrypted_token: str) -> str:
        """Alias para decrypt() - compatibilidad con código existente"""
        return self.decrypt(encrypted_token)


# Instancia global
_token_encryption = None


def get_token_encryption() -> TokenEncryption:
    """Obtiene la instancia global de cifrado"""
    global _token_encryption
    if _token_encryption is None:
        _token_encryption = TokenEncryption()
    return _token_encryption
