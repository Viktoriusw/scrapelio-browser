# 🚀 Scrapelio Browser

Navegador web profesional con funcionalidades avanzadas y sistema de plugins premium.

## 📋 Requisitos

- Python 3.9 o superior
- Sistema operativo: Linux, macOS o Windows
- 2GB de RAM mínimo
- Conexión a Internet

## 🔧 Instalación Rápida

### Linux / macOS

```bash
# 1. Dar permisos de ejecución al script
chmod +x install_dependencies.sh run_scrapelio.sh

# 2. Instalar dependencias
./install_dependencies.sh

# 3. Ejecutar Scrapelio
./run_scrapelio.sh
```

### Windows

```bash
# 1. Instalar dependencias
pip install -r requirements.txt

# 2. Ejecutar Scrapelio
python main.py
```

## 🎯 Primeros Pasos

### 1. Registro de Cuenta

Al abrir Scrapelio por primera vez:

1. Haz clic en el icono de cuenta (👤)
2. Selecciona "Registrarse"
3. Completa el formulario con tu email y contraseña
4. Verifica tu email (revisa tu bandeja de entrada)
5. Inicia sesión con tus credenciales

### 2. Explorar Plugins Premium

1. Haz clic en el icono de la tienda (🛒)
2. Explora los plugins disponibles
3. Los plugins premium requieren suscripción mensual
4. Prueba gratuita de 7 días disponible

### 3. Comprar Plugin Premium

**Desde el Sitio Web:**

1. Ve a https://scrapelio.com/precios.html
2. Selecciona el plugin que deseas
3. Completa el proceso de pago con Stripe
4. ¡Regresa al navegador y descarga tu plugin!

**Desde el Navegador:**

1. Abre la tienda de plugins
2. Haz clic en "Comprar" en el plugin deseado
3. Se abrirá el sitio web para completar el pago
4. Regresa y descarga el plugin

### 4. Instalar Plugin Premium

1. En la tienda de plugins, verás tus plugins comprados
2. Haz clic en "Descargar"
3. El plugin se instalará automáticamente
4. ¡Listo para usar!

## 🔌 Plugins Incluidos

### Plugins Gratuitos:

- **Split View** - Navegación en pantalla dividida

### Plugins Premium (Requieren Suscripción):

- **Advanced Scraping Panel** - Herramientas profesionales de web scraping (€9.99/mes)
- **Proxy Manager** - Gestión avanzada de proxies (€7.99/mes)
- **Theme System** - Editor de temas personalizado (€4.99/mes)
- **Bundle Completo** - Todos los plugins premium (€39.99/mes)

Todos incluyen **7 días de prueba gratuita**.

## ⚙️ Configuración

### Archivo de Configuración

Edita `config.yaml` para personalizar:

- URLs del backend y frontend
- Configuración de red y proxies
- Timeouts y reintentos
- Validación de licencias
- Rutas de plugins

### Backend API

Por defecto, el navegador se conecta a:
- **API:** http://192.168.1.130:8000
- **Web:** http://192.168.1.130:4321

Puedes cambiar estas URLs en `config.yaml`.

## 🎨 Características

### Navegación
- Pestañas múltiples
- Historial de navegación
- Marcadores y favoritos
- Modo incógnito

### Seguridad
- Gestor de contraseñas integrado
- Generador de contraseñas seguras
- Bloqueo de anuncios y rastreadores
- Privacidad mejorada

### Personalización
- Temas claro y oscuro
- Temas personalizados (plugin premium)
- Barra de herramientas configurable

### AI Assistant
- Chat integrado con AI
- Ayuda contextual
- Respuestas inteligentes

## 🆘 Solución de Problemas

### Error: "No se puede conectar al backend"

**Solución:**
1. Verifica que el backend esté ejecutándose
2. Comprueba la URL en `config.yaml`
3. Verifica tu conexión a internet

### Error: "Credenciales inválidas"

**Solución:**
1. Verifica tu email y contraseña
2. Asegúrate de haber verificado tu email
3. Intenta resetear tu contraseña

### Error: "Plugin no disponible"

**Solución:**
1. Verifica que tengas una suscripción activa
2. Cierra y vuelve a abrir el navegador
3. Revisa tu conexión al backend

### Error: "Dependencias faltantes"

**Solución:**
```bash
pip install -r requirements.txt
```

## 📚 Documentación

Para más información, visita:
- **Sitio Web:** https://scrapelio.com
- **Documentación:** https://scrapelio.com/docs
- **Soporte:** soporte@scrapelio.com

## 🔄 Actualizaciones

El navegador se actualiza automáticamente. Si prefieres actualizar manualmente:

```bash
# Descargar última versión del sitio web
# Extraer archivos
# Ejecutar install_dependencies.sh
```

## 📝 Licencia

Copyright © 2025 Scrapelio. Todos los derechos reservados.

Ver archivo `LICENSE` para más detalles.

## 💡 Consejos

1. **Mantén tu sesión iniciada** - No necesitas volver a iniciar sesión cada vez
2. **Sincroniza tus marcadores** - Se guardan en tu cuenta
3. **Prueba los plugins premium** - 7 días gratis, sin compromiso
4. **Usa el AI Assistant** - Te ayuda con dudas y tareas
5. **Personaliza tu experiencia** - Temas y configuraciones a tu gusto

## 🎉 ¡Disfruta de Scrapelio!

Gracias por elegir Scrapelio Browser. Esperamos que disfrutes de la experiencia de navegación mejorada y las herramientas profesionales que ofrecemos.

¿Preguntas? Contáctanos en soporte@scrapelio.com

---

**Versión:** 3.4
**Última actualización:** Noviembre 2025
