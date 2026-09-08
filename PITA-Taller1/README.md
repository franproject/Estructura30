# NexoCampus - PITA

Sistema universitario para gestionar facultades, programas académicos,
cursos, estudiantes, profesores, personal administrativo, matrículas, notas,
alertas EBRA, nómina, reportes y persistencia de datos.

El nombre visible de la aplicación es **NexoCampus**. `PITA` se conserva como
identificador técnico y nombre original del proyecto.

---

## ⚡ COMANDOS DIRECTOS DE EJECUCIÓN

### 🐍 1. Para ejecutar la interfaz PYTHON (NexoCampus GUI)

Copia y pega este bloque en PowerShell:

```powershell
cd "C:\Users\Yepin\Downloads\universidad\Estructura de Datos\estructura c++\Estructura\PITA-Taller1\python"
pip install PySide6
python main.py
```

- **Archivo principal:** [main.py](file:///C:/Users/Yepin/Downloads/universidad/Estructura%20de%20Datos/estructura%20c++/Estructura/PITA-Taller1/python/main.py)
- **Ventana GUI:** [main_window.py](file:///C:/Users/Yepin/Downloads/universidad/Estructura%20de%20Datos/estructura%20c++/Estructura/PITA-Taller1/python/gui/main_window.py)

---

### 💻 2. Para ejecutar la consola C++ (PITA Console)

Copia y pega este bloque en PowerShell:

```powershell
cd "C:\Users\Yepin\Downloads\universidad\Estructura de Datos\estructura c++\Estructura\PITA-Taller1\cpp"
.\build-vs\Debug\PITA.exe
```

- **Código fuente C++:** [PITA.cpp](file:///C:/Users/Yepin/Downloads/universidad/Estructura%20de%20Datos/estructura%20c++/Estructura/PITA-Taller1/cpp/PITA.cpp)
- **Ejecutable compilado:** [PITA.exe](file:///C:/Users/Yepin/Downloads/universidad/Estructura%20de%20Datos/estructura%20c++/Estructura/PITA-Taller1/cpp/build-vs/Debug/PITA.exe)

> 💡 **Si modificas el código C++ y deseas recompilarlo:**
> ```powershell
> cd "C:\Users\Yepin\Downloads\universidad\Estructura de Datos\estructura c++\Estructura\PITA-Taller1\cpp"
> cmake --build build-vs --config Debug
> .\build-vs\Debug\PITA.exe
> ```

---

### 🧪 3. Para ejecutar las Pruebas Automatizadas (19 tests)

```powershell
cd "C:\Users\Yepin\Downloads\universidad\Estructura de Datos\estructura c++\Estructura\PITA-Taller1\python"
python -m unittest discover tests -v
```

---

## 🛠️ Herramientas utilizadas

### C++
- C++17 / Visual Studio MSVC / CMake 3.16+
- Listas enlazadas implementadas en [PITA.cpp](file:///C:/Users/Yepin/Downloads/universidad/Estructura%20de%20Datos/estructura%20c++/Estructura/PITA-Taller1/cpp/PITA.cpp)

### Python
- Python 3.10+ (Probado en Python 3.13)
- PySide6 para la interfaz Qt
- Qt Charts para la gráfica de distribución
- `unittest` para las 19 pruebas
- JSON para la persistencia

---

## 📂 Estructura del proyecto

```text
PITA-Taller1/
├── README.md
├── cpp/
│   ├── CMakeLists.txt
│   ├── PITA.cpp
│   └── build-vs/
│       └── Debug/
│           └── PITA.exe
├── data/
│   ├── administrative_staff.json
│   ├── courses.json
│   ├── enrollments.json
│   ├── faculties.json
│   ├── professors.json
│   ├── programs.json
│   └── students.json
└── python/
    ├── main.py
    ├── models/
    ├── services/
    ├── persistence/
    ├── gui/
    │   ├── main_window.py
    │   ├── styles/
    │   ├── components/
    │   └── pages/
    └── tests/
```

---

## 📊 Estado de validación

```text
Ran 19 tests in 0.044s
OK
```
