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
python SLF.py
```

¡Listo! La interfaz institucional de NexoCampus se abrirá en su pantalla.

---

### Alternativa Rápida (Ejecución Directa sin Entorno Virtual)
Si prefiere instalar las librerías directamente en su intérprete de Python global sin crear un entorno virtual, puede ejecutar desde `PITA-Taller1`:

```powershell
pip install -r python\requirements.txt
cd python
python SLF.py
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
.\cpp\build\Release\SLF.exe   # Con generador Visual Studio
# O bien:
.\cpp\build\SLF.exe           # Con generador Ninja o MinGW
```

### Compilación directa con MinGW / GCC (sin CMake ni Visual Studio):
Si tiene `g++` en su consola:

```powershell
g++ -std=c++17 cpp\SLF.cpp -o cpp\SLF.exe
.\cpp\SLF.exe
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
│   │   ├── SLF.cpp                     # Menú interactivo y listas enlazadas en C++
│   │   ├── payroll_engine.hpp/.cpp     # Motor de nómina en C++
│   │   └── payroll_cycle.hpp/.cpp      # Ciclos de liquidación en C++
│   │
│   └── python/                         # Aplicación Gráfica Principal (PySide6)
│       ├── SLF.py                      # Punto de entrada de la aplicación
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
```
---

## 6. Integrantes y Créditos Académicos

- **Universidad:** Universidad Popular del Cesar (UPC) — Sede Valledupar.
- **Programa:** Ingeniería de Sistemas.
- **Asignatura:** Estructura de Datos.
- **Tema:** Estructuras de Datos Lineales Dinámicas (Listas Enlazadas Simples y Dobles).
