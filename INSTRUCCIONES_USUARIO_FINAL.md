# 🎯 SCRAPELIO - Guía del Usuario

**Navegador Web con Plugins Premium**

---

## 🚀 INICIO RÁPIDO (3 Pasos)

### 1️⃣ Iniciar los Servicios

```bash
cd "/media/vic/PROYECTOS FOLIO/Tron Browser/scrapelio"
./start_all_services.sh
```

✅ Esto inicia:
- Backend API (puerto 8000)
- Sitio Web (puerto 4321)
- Servidor de Email (puerto 8025)

### 2️⃣ Iniciar el Navegador

```bash
cd "/media/vic/PROYECTOS FOLIO/Tron Browser/scrapelio 3.4"
python3 main.py
```

### 3️⃣ Hacer Login

En el navegador:
1. Click en el botón de cuenta (👤) arriba a la derecha
2. Introduce credenciales:
   - **Email**: `test@scrapelio.com`
   - **Password**: `test123456`
3. Click en "Iniciar Sesión"

¡Listo! Ya puedes usar el navegador y descargar plugins.

---

## 🔌 USAR PLUGINS

### Ver Plugins Disponibles

1. Click en el botón de Plugins (🔌) en la barra superior
2. Verás una lista de plugins disponibles

### Descargar e Instalar un Plugin

Si el plugin aparece en **verde** con "🔓 DISPONIBLE":

1. Click en "📥 Descargar e Instalar"
2. Espera unos segundos (aparecerá barra de progreso)
3. Mensaje: "✅ Plugin instalado exitosamente"
4. El plugin está listo para usar

### Contratar un Plugin

Si el plugin aparece en **rojo** con "🔒 PREMIUM":

1. Click en "🛒 Ver en Dashboard"
2. Se abre el sitio web en tu navegador
3. En el dashboard, click en "Contratar" para el plugin
4. Completa el pago
5. Vuelve al navegador Scrapelio
6. Click en "🔄 Actualizar" en el panel de plugins
7. Ahora podrás descargar el plugin

---

## 📝 REGISTRO DE NUEVO USUARIO

Si quieres crear tu propia cuenta:

1. Abre: http://192.168.1.130:4321/auth/registro.html
2. Completa el formulario:
   - Email
   - Contraseña (mínimo 6 caracteres)
   - Nombre completo
3. Click en "Registrarse"
4. Abre MailHog: http://localhost:8025
5. Busca el email de verificación
6. Click en el link de verificación
7. Tu cuenta está verificada
8. Ahora puedes hacer login en el navegador

---

## 🛑 DETENER EL SISTEMA

Cuando termines de usar el navegador:

```bash
cd "/media/vic/PROYECTOS FOLIO/Tron Browser/scrapelio"
./stop_all_services.sh
```

---

## 🐛 PROBLEMAS COMUNES

### El panel de plugins está vacío

**Solución**:
1. Asegúrate de haber hecho login primero
2. Verifica que los servicios estén corriendo: `./start_all_services.sh`
3. Click en "🔄 Actualizar" en el panel de plugins

### No puedo descargar un plugin

**Solución**:
1. Verifica que el plugin tenga badge "🔓 DISPONIBLE" (verde)
2. Si dice "🔒 PREMIUM" (rojo), necesitas contratarlo primero
3. Para pruebas, usa el usuario: test@scrapelio.com / test123456 (tiene todos los plugins)

### El login no funciona

**Solución**:
1. Verifica que los servicios estén corriendo: `./start_all_services.sh`
2. Verifica el email y contraseña
3. Si registraste una cuenta nueva, verifica tu email en MailHog (http://localhost:8025)

---

## ✨ CARACTERÍSTICAS DEL NAVEGADOR

- 🌐 **Navegación Privada**: Sin rastreo
- 🔐 **Autenticación Segura**: JWT tokens
- 🔌 **Plugins Premium**: Scraping, Proxy, Themes
- 📥 **Descarga Automática**: Un click y listo
- 🎨 **Temas Personalizables**: Claro/Oscuro
- 🤖 **Chat IA Integrado**: Asistente virtual
- 🔒 **Gestor de Contraseñas**: Seguro y cifrado
- 📊 **Historial Privado**: Control total

---

## 📚 PLUGINS DISPONIBLES

| Plugin | Descripción | Precio |
|--------|-------------|--------|
| **Scraping Premium** | Extracción avanzada de datos de sitios web | $9.99/mes |
| **Proxy Manager** | Gestión y rotación de proxies | $7.99/mes |
| **Theme Editor** | Editor de temas personalizados | $4.99/mes |

---

## 💡 TIPS

- 💾 **Guarda tus pestañas**: Las pestañas se guardan automáticamente
- 🔖 **Usa favoritos**: Guarda tus sitios favoritos
- 🔐 **Gestor de contraseñas**: Guarda contraseñas de forma segura
- 🎨 **Cambia de tema**: Menú → Temas → Selecciona tu favorito
- 🤖 **Usa el chat IA**: Abre el panel lateral para consultas

---

## 📞 SOPORTE

Si necesitas ayuda:

1. **Revisa esta guía** primero
2. **Verifica los logs**: 
   - Terminal del navegador (donde ejecutaste `python3 main.py`)
   - Logs del backend: `/media/vic/PROYECTOS FOLIO/Tron Browser/scrapelio/logs/`
3. **Reinicia los servicios**: 
   ```bash
   ./stop_all_services.sh
   ./start_all_services.sh
   ```

---

**¡Disfruta de Scrapelio!** 🎉

