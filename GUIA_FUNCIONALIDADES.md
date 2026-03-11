# GUÍA DE FUNCIONALIDADES IMPLEMENTADAS

## Cómo acceder a las nuevas funcionalidades en la interfaz

### 1. MOTOR DE BÚSQUEDA

**Ubicación:** Barra de navegación superior, junto a la barra de URL

**Cómo usar:**
1. Al iniciar el navegador, verás un botón con el nombre del motor actual (ej: "DuckDuckGo")
2. Haz clic en el botón para ver el menú con todos los motores disponibles:
   - Google
   - DuckDuckGo
   - Bing
   - Yahoo
   - Wikipedia
   - YouTube
   - GitHub
   - Stack Overflow
3. Selecciona un motor para usarlo temporalmente en tu próxima búsqueda
4. Escribe en la barra de URL y presiona Enter para buscar

**Cambiar motor predeterminado:**
- Menú ☰ → Ajustes → Tab "Búsqueda"
- O: Click en botón del motor → "Gestionar motores de búsqueda..."
- **IMPORTANTE:** Después de cambiar el motor predeterminado:
  - Las nuevas pestañas (Ctrl+T) abrirán la página de inicio del motor seleccionado
  - Las búsquedas desde la barra de URL usarán el motor seleccionado

**Búsqueda inteligente:**
- Si escribes texto con espacios → Búsqueda
- Si escribes una URL (con punto y dominio) → Navegación directa
- Ejemplo: "python tutorial" → Busca en el motor seleccionado
- Ejemplo: "github.com" → Navega directamente

---

### 2. ADMINISTRADOR DE TAREAS Y RENDIMIENTO

**Ubicación:** Menú ☰ → Más herramientas

**Opciones:**
1. **Administrador de tareas**
   - Ver uso de CPU y memoria del navegador
   - Lista de todas las pestañas activas
   - Cerrar pestañas individuales desde el administrador
   
2. **Diagnóstico de rendimiento**
   - Informe completo del estado del navegador
   - Recomendaciones de optimización
   - Estadísticas del sistema

---

### 3. CAPTURAS DE PANTALLA AVANZADAS

**Ubicación:** Menú ☰ → Captura de pantalla

**Opciones:**
1. **Captura básica**
   - Captura área visible o página completa
   - Guardar en archivo o copiar al portapapeles

2. **Captura de región**
   - Selecciona visualmente la región a capturar
   - Arrastra para definir el área
   - Se guarda automáticamente

3. **Captura con anotaciones**
   - Captura la página
   - Agrega flechas, rectángulos, texto o resaltados
   - Herramientas de edición incluidas
   - Guardar imagen anotada

---

### 4. GESTIÓN DE SESIONES

**Ubicación:** Menú ☰ → Sesiones

**Funcionalidades:**
1. **Guardar sesión actual**
   - Guarda todas las pestañas abiertas con nombre
   - Incluye posición de scroll
   - Pestañas fijadas se mantienen

2. **Restaurar sesión**
   - Ver lista de sesiones guardadas
   - Restaurar sesión específica
   - Eliminar sesiones antiguas

3. **Recuperación automática tras crash**
   - Si el navegador se cierra inesperadamente
   - Al reiniciar, pregunta si quieres restaurar la sesión

---

### 5. USER-AGENT (COMPLETAMENTE FUNCIONAL)

**Ubicación:** Menú ☰ → Más herramientas → Configuración de red

**Cómo cambiar el User-Agent:**
1. Abre "Configuración de red"
2. Ve al tab "User-Agent"
3. Verás DOS secciones:
   - **🌐 User-Agent ACTIVO**: El que está usando el navegador AHORA (fondo verde)
   - **📝 Preview**: El User-Agent que selecciones (fondo naranja)
4. Selecciona un User-Agent predefinido del menú desplegable:
   - Chrome (Windows)
   - Firefox (Windows)
   - Brave (Windows)
   - Safari (macOS)
   - Edge (Windows)
   - Android (Mobile)
   - iOS (iPhone)
   - Custom (Personalizado)
5. El **Preview** se actualizará automáticamente para mostrar el User-Agent completo
6. Si seleccionas "Custom", escribe tu propio User-Agent en el campo de texto
7. Haz clic en **"Aplicar"** o **"Guardar"**
8. Verás un mensaje confirmando que los cambios se aplicaron
9. El **User-Agent ACTIVO** se actualizará para mostrar el nuevo valor

**IMPORTANTE:** 
- El cambio se aplica INMEDIATAMENTE al interceptor
- Las pestañas NUEVAS que abras usarán el nuevo User-Agent
- Las pestañas YA ABIERTAS mantienen el User-Agent anterior

**CÓMO VERIFICAR QUE FUNCIONA:**

**Opción 1: Página de prueba local (RECOMENDADO)**
1. Abre una nueva pestaña (Ctrl+T)
2. En la barra de URL, escribe: `file:///` y navega a la carpeta del navegador
3. Abre el archivo `test_ua_page.html`
4. Verás una página que muestra tu User-Agent actual con colores

**Opción 2: Página web externa**
1. Cierra TODAS las pestañas actuales (Ctrl+W en cada una)
2. Abre una nueva pestaña (Ctrl+T)
3. Visita: https://www.whatismybrowser.com/detect/what-is-my-user-agent
4. Verifica que muestre el navegador que configuraste

**Opción 3: Verificar en los logs**
- En la terminal donde ejecutaste el navegador, busca líneas como:
  ```
  [UA] Applying User-Agent (Chrome): Mozilla/5.0...
  ```
- Esto confirma que el User-Agent se está aplicando correctamente

---

### 6. CONFIGURACIÓN GENERAL

**Ubicación:** Menú ☰ → Ajustes

**Tabs disponibles:**
1. **General** - Configuración básica
2. **Búsqueda** - Motor de búsqueda predeterminado
3. **Privacidad** - Acceso rápido al panel de privacidad

---

## VERIFICACIÓN VISUAL

### ¿Cómo saber si está funcionando?

**Motor de búsqueda:**
- ✅ Debes ver un botón con texto (ej: "DuckDuckGo") en la barra de navegación
- ✅ Al hacer clic, aparece un menú desplegable con 8 motores
- ✅ La barra de URL dice "Buscar o escribir URL..."

**Administrador de tareas:**
- ✅ Menú ☰ → Más herramientas → "Administrador de tareas"
- ✅ Se abre ventana con gráficas de CPU y memoria
- ✅ Lista de pestañas con botón "Cerrar"

**Capturas avanzadas:**
- ✅ Menú ☰ → "Captura de pantalla" (sección propia)
- ✅ 3 opciones: básica, región, anotaciones

**Sesiones:**
- ✅ Menú ☰ → "Sesiones" (sección propia)
- ✅ 2 opciones: Guardar / Restaurar

**User-Agent:**
- ✅ Menú ☰ → Más herramientas → "Configuración de red..."
- ✅ Tab "User-Agent" con combo box de opciones
- ✅ Preview del User-Agent actual

---

## SOLUCIÓN DE PROBLEMAS

### El botón del motor de búsqueda no aparece

**Causa:** El SearchEngineManager no se inicializó correctamente

**Solución:**
1. Verifica que `search_engine_manager.py` existe
2. Ejecuta: `python3 -c "from search_engine_manager import SearchEngineManager; print('OK')"`
3. Revisa los logs al iniciar el navegador: `python3 main.py 2>&1 | grep "Search Engine"`

### El User-Agent no cambia

**Causa:** El cambio solo aplica a nuevas pestañas que se creen DESPUÉS de cambiar la configuración

**Solución:**
1. Abre Menú ☰ → Más herramientas → Configuración de red
2. Ve al tab "User-Agent"
3. Selecciona el User-Agent deseado (Chrome, Firefox, Brave, Safari, Edge, Android, iOS, o Custom)
4. Haz clic en "Aplicar" o "Guardar"
5. **IMPORTANTE:** Cierra TODAS las pestañas actuales (Ctrl+W)
6. Abre una nueva pestaña (Ctrl+T)
7. Navega a: https://www.whatismybrowser.com/detect/what-is-my-user-agent
8. Verifica que el User-Agent haya cambiado

**Nota:** El cambio NO afecta a pestañas ya abiertas, solo a las nuevas que se creen después del cambio.

### Las capturas no se guardan

**Causa:** Permisos de carpeta o ruta inválida

**Solución:**
1. Verifica que tienes permisos de escritura en ~/Pictures
2. El diálogo te permite elegir otra ubicación
3. Revisa los logs para ver errores específicos

---

## ATAJOS DE TECLADO

- `Ctrl+F` - Buscar en página
- `Ctrl+T` - Nueva pestaña
- `Ctrl+W` - Cerrar pestaña
- `Ctrl+Shift+T` - Reabrir pestaña cerrada
- `Ctrl+P` - Imprimir
- `Ctrl+S` - Guardar página
- `F11` - Pantalla completa
- `F12` - DevTools
- `Ctrl+U` - Ver código fuente
- `Ctrl++` - Aumentar zoom
- `Ctrl+-` - Reducir zoom
- `Ctrl+0` - Restablecer zoom

---

**Última actualización:** 09/01/2026
**Versión:** 3.4.14
