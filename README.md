<p align="center">
  <img src="logoscrapelio.jpg" alt="Scrapelio Browser" width="220" />
</p>

<h1 align="center">Scrapelio Browser</h1>

<p align="center">
  <strong>Navegador web ligero con sistema de plugins, IA integrada y foco en privacidad.</strong>
</p>

<hr>

<h2> Instalación</h2>

<h3>🐧 Linux / macOS</h3>

<pre><code>cd /ruta/a/scrapelio-browser</code></pre>

<h4>1. Dependencias del sistema</h4>

<pre><code>sudo apt update
sudo apt install -y python3 python3-venv python3-pip \
  libxcb-cursor0 libxcb-xinerama0 libxcb-xtest0 \
  libgl1-mesa-glx libfontconfig1 libssl-dev</code></pre>

<h4>2. Entorno virtual</h4>

<pre><code>python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip</code></pre>

<h4>3. Dependencias Python</h4>

<pre><code>pip install -r requirements.txt</code></pre>

<h4>4. Verificar instalación</h4>

<pre><code>python3 check_dependencies.py
python3 -c "from PySide6.QtWebEngineWidgets import QWebEngineView; print('✅ OK')"</code></pre>

<h4>5. Ejecutar el navegador</h4>

<pre><code>python3 main.py</code></pre>

<hr>

<h2> Características principales</h2>

<ul>
  <li><strong> Plugins de la comunidad</strong>: sistema de plugins extensible, con plugins oficiales y desarrollados por la comunidad.</li>
  <li><strong> Chat IA integrado</strong>: panel de chat con IA y asistencia contextual dentro del navegador.</li>
  <li><strong> IA en la navegación</strong>: extracción de contexto de páginas, ayuda para búsquedas y tareas directamente sobre los sitios que visitas.</li>
  <li><strong> Privacidad y seguridad</strong>: gestor de contraseñas, controles avanzados de privacidad y utilidades de seguridad integradas.</li>
  <li><strong> Navegador muy ligero</strong>: interfaz en PySide6 optimizada, consumo reducido de recursos y tiempos de arranque rápidos.</li>
</ul>

<hr>

<h2>📄 Licencia</h2>

<p>Consulta el archivo <code>LICENSE</code> para los términos completos de uso.</p>

<hr>

<p align="center">
  <sub>Desarrollado con cariño para las personas libres</sub>
</p>
