# PITA / NexoCampus

PITA significa **Programa Integrado de Transacciones Académicas**. NexoCampus
es el nombre visible de la aplicación. El proyecto fue desarrollado para la
materia **Estructura de Datos**, tema **Listas**, de la **Universidad Popular
del Cesar**.

El sistema propone un reemplazo académico del Vortal para gestionar en un
mismo lugar facultades, programas, cursos, estudiantes, profesores,
administrativos, matrículas, notas, alertas EBRA, reportes y nómina docente.
Incluye una versión de consola en C++ basada en listas enlazadas y una interfaz
gráfica en Python con PySide6.

## Estructura del proyecto

```text
PITA-Taller1/
├── README.md
├── cpp/
│   ├── CMakeLists.txt        # Configuración portable de CMake
│   └── PITA.cpp              # Consola C++ y listas enlazadas
├── data/
│   ├── administrative_staff.json
│   ├── courses.json
│   ├── enrollments.json
│   ├── faculties.json
│   ├── professors.json
│   ├── programs.json
│   └── students.json         # Datos persistentes de la GUI Python
└── python/
    ├── main.py               # Punto de entrada de la GUI
    ├── requirements.txt      # Dependencias Python
    ├── models/               # Entidades y listas enlazadas
    ├── services/             # Reglas y operaciones del dominio
    ├── persistence/          # Lectura y escritura de JSON
    ├── gui/                  # Ventanas, páginas, componentes y estilos
    └── tests/                # 19 pruebas automatizadas
```

Los directorios `cpp/build/`, `cpp/build-*` y los entornos virtuales son
artefactos locales generados durante la compilación o ejecución. No son
necesarios para clonar ni configurar el proyecto.

## Requisitos previos

Instala antes de comenzar:

- Un compilador compatible con C++17: [Visual Studio](https://visualstudio.microsoft.com/downloads/) en Windows, o `g++`/`clang++` en macOS y Linux.
- [CMake 3.16 o superior](https://cmake.org/download/).
- [Python 3.10 o superior](https://www.python.org/downloads/), con `pip`.

En Windows, el instalador de Visual Studio debe incluir la carga de trabajo
**Desarrollo para el escritorio con C++**. En macOS se puede instalar el
compilador con Xcode Command Line Tools; en Linux, con el gestor de paquetes de
la distribución.

No se requiere una configuración específica de VS Code para compilar el
proyecto.

## Ejecutar la versión C++

Desde la carpeta raíz `PITA-Taller1/`, configura y compila con CMake:

```text
cmake -S cpp -B cpp/build
cmake --build cpp/build --config Release
```

La primera orden genera los archivos de construcción y la segunda compila el
ejecutable. La ubicación exacta depende del generador de CMake:

- Linux y macOS, normalmente: `cpp/build/PITA`.
- Windows con un generador de Visual Studio: `cpp/build/Release/PITA.exe`.
- Windows con Ninja u otro generador de una sola configuración: normalmente
  `cpp/build/PITA.exe`.

Ejemplos de ejecución desde la carpeta raíz:

```powershell
# Windows con Visual Studio
.\cpp\build\Release\PITA.exe

# Windows con Ninja
.\cpp\build\PITA.exe
```

```bash
# Linux o macOS
./cpp/build/PITA
```

El programa es interactivo. Desde el menú principal permite registrar datos y
guardar o cargar la información en `pita_datos.txt`, creado en el directorio
desde el que se ejecute el programa.

## Ejecutar la versión Python

Desde la carpeta raíz crea un entorno virtual e instala las dependencias.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r python\requirements.txt
cd python
python main.py
```

Linux o macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r python/requirements.txt
cd python
python main.py
```

La aplicación gráfica utiliza PySide6 y carga sus datos desde la carpeta
`data/` del proyecto.

## Ejecutar las pruebas

Con el entorno virtual activado, entra en `python/` y ejecuta:

```text
python -m unittest discover tests -v
```

El resultado esperado es `Ran 19 tests` seguido de `OK`.

## Persistencia de datos

- La versión Python utiliza los archivos `data/*.json` para cargar y guardar
  facultades, programas, cursos, estudiantes, profesores, administrativos y
  matrículas.
- La versión C++ utiliza su propio archivo de texto `pita_datos.txt`. Este
  archivo se crea cuando se elige guardar datos y no es necesario para compilar
  el proyecto.

## Extensiones recomendadas para VS Code

Para trabajar cómodamente en VS Code se recomiendan las extensiones oficiales
de Microsoft:

- [C/C++](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cpptools)
- [CMake Tools](https://marketplace.visualstudio.com/items?itemName=ms-vscode.cmake-tools)
- [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python)

Son recomendaciones de edición y ejecución. No hace falta agregar archivos de
configuración de VS Code ni instalar otra extensión para que el proyecto
funcione: CMake configura la versión C++ y Python usa `requirements.txt`.
