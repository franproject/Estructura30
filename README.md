# PITA / NexoCampus — Plataforma Integrada de Transacciones Académicas

**Universidad Popular del Cesar (UPC)**  
**Facultad de Ingenierías y Tecnologías** | **Ingeniería de Sistemas**  
**Asignatura:** Estructura de Datos | **Tema:** Listas Enlazadas  
**Proyecto Final de Asignatura**  

---

## 1. Presentación del Proyecto

**PITA** (*Programa Integrado de Transacciones Académicas*), cuya interfaz gráfica institucional se presenta bajo el nombre **NexoCampus**, es un sistema integral de gestión universitaria diseñado y desarrollado como solución de reemplazo académico al portal institucional (Vortal).

El objetivo pedagógico central del proyecto es la aplicación práctica, rigurosa y eficiente de **estructuras de datos dinámicas lineales (Listas Enlazadas Simples y Dobles)** para administrar entidades complejas en memoria volátil, complementado con persistencia transaccional en archivos JSON, cálculo avanzado de nómina conforme a la legislación laboral colombiana y una interfaz gráfica de escritorio moderna, responsiva y accesible desarrollada en **PySide6 (Qt6)**.

### Módulos Principales
1. **Gestión Académica y Curricular**: Facultades, Programas Académicos, Asignaturas/Cursos, Estudiantes, Inscripciones y Registro de Calificaciones.
2. **Talento Humano y Nómina Institucional**: Profesores (tiempo completo, medio tiempo, cátedra), Personal Administrativo, Ciclos de Liquidación de Nómina con devengados, deducciones de ley, auxilio de transporte, fondo de solidaridad pensional, retención en la fuente, provisiones de prestaciones sociales y aportes patronales a seguridad social y parafiscales (SENA, ICBF, Cajas de Compensación, ARL Clases I a V).
3. **Sistema de Alerta Temprana (EBRA)**: Algoritmo de detección proactiva para Estudiantes de Bajo Rendimiento Académico (promedios acumulados críticos o riesgo académico reiterado).
4. **Centro de Reportes Institucionales**: Informes estadísticos y ejecutivos sobre Carga Académica Docente, Consolidado Salarial por Categorías, Alertas EBRA e Indicadores Globales Universitarios, con exportación nativa a formato CSV.
5. **Generación de Desprendibles en PDF**: Generación vectorial individual y masiva de desprendibles de pago oficiales mediante **ReportLab**.

---

## 2. Guía de Instalación y Ejecución Rápida (PowerShell / Terminal)

> [!IMPORTANT]
> **Para el Docente / Evaluador:**  
> No es necesario contar con Visual Studio, Visual Studio Code ni ningún entorno de desarrollo integrado instalado.  
> El programa puede descargarse, configurarse y ejecutarse **directamente desde la terminal de Windows PowerShell** siguiendo los sencillos pasos a continuación.

### Requisitos Previos
- **Python 3.10 o superior** (verificar abriendo PowerShell y escribiendo `python --version`).
- Conexión a Internet para descargar las dependencias por primera vez.

---

### Paso a Paso en Windows PowerShell

#### 1. Abrir Windows PowerShell
Presione la tecla `Windows`, escriba `PowerShell` y presione `Enter`. Navegue hasta la carpeta raíz del proyecto donde se encuentra este archivo:

```powershell
cd c:\Ruta\De\Descarga\Estructura\Estructura\PITA-Taller1
```

*(Si ya se encuentra en la carpeta del proyecto, asegúrese de estar en el directorio `PITA-Taller1`)*.

#### 2. Habilitar la ejecución de scripts (si PowerShell lo requiere)
Por defecto, algunas versiones de Windows restringen la ejecución de scripts locales. Para habilitarlo temporalmente en la sesión activa de su terminal, ejecute:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

#### 3. Crear y activar el entorno virtual
El entorno virtual aísla las librerías del proyecto sin alterar la configuración global de su equipo:

```powershell
# Crear el entorno virtual
python -m venv .venv

# Activar el entorno virtual
.\.venv\Scripts\Activate.ps1
```

*(Una vez activado, observará el prefijo `(.venv)` al inicio de la línea de comandos).*

#### 4. Instalar las dependencias oficiales
Instale las dos únicas dependencias requeridas ejecutando:

```powershell
python -m pip install --upgrade pip
pip install -r python\requirements.txt
```

**¿Qué librerías se instalan?**
- `PySide6 (>=6.7)`: Framework gráfico oficial de Qt6 para Python (ventanas, tablas, controles, gráficos y estilos QSS).
- `reportlab (>=4.2)`: Motor de generación vectorial de documentos PDF utilizado para emitir los desprendibles de nómina oficiales.

#### 5. Ejecutar el Sistema Gráfico (NexoCampus)
Ingrese a la carpeta `python/` y lance la aplicación:

```powershell
cd python
python main.py
```

¡Listo! La interfaz institucional de NexoCampus se abrirá en su pantalla.

---

### Alternativa Rápida (Ejecución Directa sin Entorno Virtual)
Si prefiere instalar las librerías directamente en su intérprete de Python global sin crear un entorno virtual, puede ejecutar desde `PITA-Taller1`:

```powershell
pip install -r python\requirements.txt
cd python
python main.py
```

---

### Ejecución en Linux o macOS
Para evaluar el sistema en sistemas Unix:

```bash
cd PITA-Taller1
python3 -m venv .venv
source .venv/bin/activate
pip install -r python/requirements.txt
cd python
python main.py
```

---

## 3. Ejecución de Pruebas Automatizadas

El proyecto cuenta con una exhaustiva batería de **302 pruebas automatizadas** que validan la integridad de las listas enlazadas, los cálculos matemáticos de nómina, la persistencia atómica en JSON, la responsividad y la accesibilidad.

Con el entorno virtual activado, desde la carpeta `PITA-Taller1/python`:

```powershell
# Ejecutar la suite completa de 302 pruebas
python -m unittest discover -s tests -v
```

**Resultado esperado:**
```text
Ran 302 tests in XX.XXXs
OK
```

### Ejecutar suites de prueba específicas:
Si desea evaluar un módulo en particular:

```powershell
# 1. Pruebas de la estructura de datos Lista Enlazada
python -m unittest tests/test_linked_list.py

# 2. Pruebas de cálculo de Nómina, ARL y Seguridad Social Colombiana
python -m unittest tests/test_payroll_engine.py
python -m unittest tests/test_payroll_cycle.py

# 3. Pruebas del algoritmo EBRA (Alerta Temprana de Riesgo Académico)
python -m unittest tests/test_academic_ebra.py

# 4. Pruebas de dimensionamiento compacto de tablas (cero espacios vacíos)
python -m unittest tests/test_compact_tables.py

# 5. Pruebas de diseño responsivo (cero scroll horizontal en 960x600)
python -m unittest tests/test_responsive_layout.py

# 6. Pruebas de navegación (Breadcrumbs) y persistencia segura en disco
python -m unittest tests/test_breadcrumbs_and_persistence_ui.py
```

---

## 4. Ejecutar la Versión de Consola en C++ (Opcional)

Además de la interfaz gráfica completa en Python, el proyecto incluye una implementación complementaria en **C++17** desarrollada exclusivamente sobre estructuras de datos dinámicas manuales (`Node` y `LinkedList` con punteros en C++).

### Compilación y ejecución con CMake:
Desde la carpeta raíz `PITA-Taller1`:

```powershell
# 1. Configurar y compilar con CMake
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release

# 2. Ejecutar
.\cpp\build\Release\PITA.exe   # Con generador Visual Studio
# O bien:
.\cpp\build\PITA.exe           # Con generador Ninja o MinGW
```

### Compilación directa con MinGW / GCC (sin CMake ni Visual Studio):
Si tiene `g++` en su consola:

```powershell
g++ -std=c++17 cpp\PITA.cpp -o cpp\PITA.exe
.\cpp\PITA.exe
```

El programa de consola permite registrar datos y persistir su propio archivo `pita_datos.txt`.

---

## 5. Estructura y Organización del Código

El proyecto adopta una **Arquitectura en Capas (Layered Architecture)** con estricta separación de responsabilidades:

```text
Estructura/
├── README.md                           # Documentación principal para el docente
├── PITA-Taller1/
│   ├── data/                           # Almacén de persistencia física (Archivos JSON)
│   │   ├── administrative_staff.json   # Personal administrativo institucional
│   │   ├── courses.json                # Catálogo de cursos y asignaturas
│   │   ├── dashboard_snapshot.json     # Línea base para cálculo de métricas en tiempo real
│   │   ├── enrollments.json            # Matrículas e inscripciones académicas
│   │   ├── faculties.json              # Facultades universitarias
│   │   ├── payroll_audit.json          # Trazabilidad y auditoría de eventos de nómina
│   │   ├── payroll_novelties.json      # Novedades laborales (horas extras, bonificaciones)
│   │   ├── payroll_periods.json        # Períodos mensuales de liquidación
│   │   ├── payroll_runs.json           # Liquidaciones calculadas, aprobadas y cerradas
│   │   ├── professors.json             # Cuerpo docente universitario
│   │   ├── programs.json               # Programas académicos de pregrado y posgrado
│   │   └── students.json               # Población estudiantil
│   │
│   ├── cpp/                            # Versión complementaria de consola en C++17
│   │   ├── CMakeLists.txt              # Configuración de compilación CMake
│   │   ├── PITA.cpp                    # Menú interactivo y listas enlazadas en C++
│   │   ├── payroll_engine.hpp/.cpp     # Motor de nómina en C++
│   │   └── payroll_cycle.hpp/.cpp      # Ciclos de liquidación en C++
│   │
│   └── python/                         # Aplicación Gráfica Principal (PySide6)
│       ├── main.py                     # Punto de entrada de la aplicación
│       ├── requirements.txt            # Dependencias del sistema (PySide6, reportlab)
│       │
│       ├── models/                     # CAPA 1: Estructuras de Datos y Entidades
│       │   ├── linked_list.py          # Implementación de Lista Enlazada Genérica (LinkedList, Node)
│       │   ├── faculty.py              # Entidad Facultad
│       │   ├── program.py              # Entidad Programa Académico
│       │   ├── course.py               # Entidad Curso / Asignatura
│       │   ├── student.py              # Entidad Estudiante
│       │   ├── professor.py            # Entidad Profesor
│       │   ├── administrative_staff.py # Entidad Personal Administrativo
│       │   ├── enrollment.py           # Entidad Matrícula / Inscripción
│       │   ├── payroll_period.py       # Entidad Período de Nómina
│       │   ├── payroll_run.py          # Entidad Corrida de Nómina
│       │   └── payroll_novelty.py      # Entidad Novedad de Nómina
│       │
│       ├── services/                   # CAPA 2: Lógica de Negocio y Reglas de Dominio
│       │   ├── entity_manager.py       # Gestor central de colecciones en memoria (Listas)
│       │   ├── academic_metrics.py     # Evaluación del algoritmo de alerta temprana EBRA
│       │   ├── payroll_engine.py       # Motor legal de liquidación de nómina colombiana
│       │   └── payroll_cycle_service.py# Flujo de estados: CALCULATED -> APPROVED -> CLOSED
│       │
│       ├── persistence/                # CAPA 3: Almacenamiento Transaccional en Disco
│       │   └── file_manager.py         # Lectura/escritura atómica en JSON y copias de seguridad
│       │
│       ├── gui/                        # CAPA 4: Interfaz de Usuario (PySide6 + QSS)
│       │   ├── main_window.py          # Ventana principal, navegación y atajos globales
│       │   │
│       │   ├── components/             # Catálogo de componentes modulares reutilizables
│       │   │   ├── data_table.py       # Tabla paginada, ordenable, compacta y auto-dimensionada
│       │   │   ├── breadcrumb.py       # Barra de ruta jerárquica con indicador de cambios
│       │   │   ├── header.py           # Cabecera superior con buscador global y alertas
│       │   │   ├── sidebar.py          # Menú lateral y panel de persistencia física en disco
│       │   │   ├── page_header.py      # Encabezado estándar de sección
│       │   │   ├── search_bar.py       # Buscador con limpieza rápida y atajo Ctrl+F
│       │   │   ├── pagination_bar.py   # Control ergonómico de páginas
│       │   │   ├── stat_card.py        # Tarjetas estadísticas KPI con deltas dinámicos
│       │   │   ├── entity_dialog.py    # Formulario modal con scroll y validación en tiempo real
│       │   │   ├── confirm_dialog.py   # Modal de confirmación segura con foco en "Cancelar"
│       │   │   ├── empty_state.py      # Estado vacío ilustrado cuando no hay registros
│       │   │   ├── notification_panel.py# Centro de notificaciones del sistema
│       │   │   └── icons.py            # Catálogo de iconos vectoriales SVG institucionales
│       │   │
│       │   ├── pages/                  # Vistas de contenido de la aplicación
│       │   │   ├── dashboard_page.py   # Dashboard ejecutivo con métricas vivas y gráficos
│       │   │   ├── crud_page.py        # Vista genérica CRUD para las 7 entidades académicas
│       │   │   ├── payroll_page.py     # Centro de liquidación, gestión y aprobación de nómina
│       │   │   ├── payroll_dashboard.py# Dashboard analítico financiero de nómina
│       │   │   └── reports_page.py     # Centro de Reportes (EBRA, Carga, Salarios, Métricas)
│       │   │
│       │   ├── styles/
│       │   │   └── app.qss             # Hoja de estilos institucional con tokens de diseño
│       │   │
│       │   └── i18n/                   # Glosario y tooltips informativos de acrónimos
│       │       └── labels.py           # Tooltips para EBRA, IBC, ARL, CST, etc.
│       │
│       └── tests/                      # Batería Integral de Pruebas Automatizadas
│           ├── test_linked_list.py     # Validación matemática de las listas enlazadas
│           ├── test_compact_tables.py  # Verificación de altura exacta y cero espacios vacíos
│           ├── test_responsive_layout.py# Verificación de adaptabilidad a 960x600 sin scroll
│           ├── test_breadcrumbs_and_persistence_ui.py # Trazabilidad de rutas y guardado
│           ├── test_shortcuts_and_search_bar.py # Atajos de teclado y buscador
│           ├── test_interaction_and_a11y.py # Accesibilidad de teclado y foco
│           ├── test_vector_icons_and_no_emojis.py # Cero emojis y vectorización SVG
│           ├── test_design_system.py   # Tokens de color, tipografía y bordes QSS
│           ├── test_data_table_enhancements.py # Ordenamiento y alineación contable
│           ├── test_dashboard_page_enhancements.py # Métricas reales de Dashboard
│           ├── test_payroll_engine.py  # Reglas legales de liquidación de nómina
│           ├── test_academic_ebra.py   # Algoritmo de evaluación académica EBRA
│           └── ... (15 suites adicionales cubriendo dominio, persistencia y vistas)
```

---

## 6. Características Técnicas y Novedades Implementadas

### A. Listas Enlazadas como Estructura Central en Memoria
- Implementación de `LinkedList` y `Node` en `models/linked_list.py` con operaciones fundamentales: inserción al inicio, inserción al final, búsqueda por predicado, eliminación por valor o índice, recorrido iterador y conversión a colecciones.
- El gestor `EntityManager` mantiene en listas dinámicas las colecciones de entidades, permitiendo búsquedas de alta eficiencia en memoria antes de volcar a disco.

### B. Tablas Dinámicas y Compactas (`DataTable`)
- **Ajuste automático al volumen de datos**: La tabla mide la altura de sus filas visibles y se dimensiona con exactitud matemática, eliminando los molestos espacios blancos vacíos inferiores tanto en tablas de 10 filas como en tablas pequeñas (ej. 4 filas en salarios, o 1 fila al filtrar).
- **Alineación contable profesional**: Alineación a la derecha para montos monetarios (`$ 3,500,000.00`), porcentajes y cantidades numéricas; alineación al centro para códigos, IDs, fechas y badges; alineación a la izquierda para textos y nombres.
- **Ordenamiento interactivo integral**: Al hacer clic sobre cualquier encabezado de columna, la tabla ordena el **conjunto de datos completo** (no solo la página visible), sincronizando los objetos de dominio asociados.

### C. Diseño Totalmente Responsivo (Resolución Mínima 960×600)
- **Cero scroll horizontal forzado**: Gracias al componente `AdaptiveStackedWidget`, el área principal adapta su geometría al 100% del ancho visible de la ventana.
- Los botones de acción principal (como `+ Nueva Facultad`), las barras de búsqueda y los botones de edición/eliminación permanecen siempre visibles dentro de la pantalla, sin recortarse ni requerir desplazamiento horizontal.

### D. Formulario Inteligente con Validación en Tiempo Real (`EntityDialog`)
- **Indicador de obligatoriedad**: Distinción clara entre campos requeridos (asterisco rojo `*`) y opcionales.
- **Validación instantánea mientras se digita**: Validación reactiva de correos electrónicos (`usuario@dominio.com`), teléfonos colombianos (10 dígitos), documentos de identidad y validación estricta de salarios no negativos.
- **Desplazamiento vertical asistido**: Envuelto en `QScrollArea` para garantizar que formularios extensos (como Profesores o Administrativos) sean cómodamente navegables en pantallas reducidas.

### E. Atajos de Teclado Globales (Productividad sin Ratón)
| Atajo | Acción Ejecutada |
| :--- | :--- |
| `Ctrl + S` | **Guardar Datos**: Guarda de forma atómica en disco todos los cambios pendientes en memoria. |
| `F5` | **Cargar / Recargar Datos**: Recarga el estado desde los archivos JSON en disco (advierte si hay cambios sin guardar). |
| `Ctrl + N` | **Nuevo Registro**: Abre el diálogo para crear una nueva entidad en la sección activa. |
| `Ctrl + F` | **Buscar**: Enfoca inmediatamente la barra de búsqueda de la vista activa y selecciona su texto. |
| `Ctrl + K` | **Búsqueda Global**: Enfoca el buscador institucional del encabezado superior. |
| `Delete` / `Supr` | **Eliminar**: Dispara la confirmación de eliminación del elemento seleccionado en la tabla activa. |
| `Enter` / `Espacio` | **Interacción**: Activa tarjetas del dashboard y botones enfocados mediante teclado. |

### F. Prevención de Pérdida Accidental de Datos
- **Indicador de Cambios sin Guardar**: Si el usuario inserta, edita o elimina información, aparece la insignia visual ámbar `● Cambios sin guardar (Ctrl+S)` en el breadcrumb y el botón del sidebar se ilumina en ámbar.
- **Alerta ante Recarga**: Si se intenta presionar "Cargar Datos" existiendo modificaciones en memoria, un diálogo previene sobre la pérdida irreversible y solicita confirmación.
- **Alerta ante Cierre de la Aplicación**: Si el usuario cierra la ventana principal con cambios pendientes, se despliega un diálogo con 3 opciones seguras: *Guardar y Salir*, *Salir sin Guardar* o *Cancelar*.

### G. Iconografía 100% Vectorial SVG (Sin Emojis)
- Se erradicó el uso de emojis del sistema operativo (`⚠️`, `📋`, `👁`, `💰`, etc.), reemplazándolos por un catálogo vectorial nativo en `gui/components/icons.py` que garantiza una renderización nítida, sobria y uniforme entre Windows, Linux y macOS.

---

## 7. Preguntas Frecuentes y Solución de Problemas (Troubleshooting)

### P1: PowerShell muestra un error rojo diciendo que "la ejecución de scripts está deshabilitada en este sistema".
**Solución:** Windows bloquea por defecto la ejecución de entornos virtuales creados con `Activate.ps1`. Ejecute en la misma ventana de PowerShell:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Luego vuelva a ejecutar `.\.venv\Scripts\Activate.ps1`.

---

### P2: Al escribir `python` o `pip` la consola dice que el comando no se reconoce.
**Solución:** Python no fue añadido a la variable de entorno `PATH` durante su instalación.
- Puede ejecutar usando el lanzador de Windows: `py -m pip install -r python\requirements.txt` y `py python\main.py`.
- O bien, reinstale Python asegurándose de marcar la casilla **"Add Python to PATH"** en la primera pantalla del instalador.

---

### P3: ¿Cómo verificar rápidamente que todo el proyecto funciona correctamente?
**Solución:** Ejecute la suite de pruebas automatizadas:
```powershell
cd python
python -m unittest discover -s tests
```
Si observa `Ran 302 tests ... OK`, todas las reglas de negocio, modelos y componentes gráficos se encuentran en perfecto estado operativo.

---

## 8. Integrantes y Créditos Académicos

- **Universidad:** Universidad Popular del Cesar (UPC) — Sede Valledupar.
- **Programa:** Ingeniería de Sistemas.
- **Asignatura:** Estructura de Datos.
- **Tema:** Estructuras de Datos Lineales Dinámicas (Listas Enlazadas Simples y Dobles).
