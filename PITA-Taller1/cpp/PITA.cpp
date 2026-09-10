/* ============================================================================
   UNIVERSIDAD POPULAR DEL CESAR - FACULTAD DE INGENIERIAS Y TECNOLOGICAS
   INGENIERIA DE SISTEMAS - ESTRUCTURA DE DATOS - LISTAS - TALLER 1
   ----------------------------------------------------------------------------
   PITA: Programa Integrado de Transacciones Academicas
   Version en C++ (implementacion con LISTAS ENLAZADAS puras, sin STL para las
   estructuras principales, tal como corresponde a la unidad tematica del curso).

   ESTRUCTURA GENERAL (todo con listas enlazadas simples):

        Universidad
          |
          +-- Lista de FACULTADES
                 |
                 +-- Lista de PROGRAMAS ACADEMICOS (ej: Ing. de Sistemas, Medicina)
                        |
                        +-- Lista de CURSOS
                        +-- Lista de ESTUDIANTES --- Lista de NOTAS (matriculas)
                        +-- Lista de PROFESORES  --- Datos de NOMINA

          +-- Lista de ADMINISTRATIVOS (personal administrativo, nivel universidad)

   NOTA IMPORTANTE SOBRE LA NOMINA (Decreto 1279 de 2002 / Acuerdo 027 de 2024):
   El calculo real de nomina docente en universidades publicas colombianas se basa
   en un sistema de PUNTOS SALARIALES (por titulo, experiencia calificada,
   productividad academica, categoria, etc.) multiplicados por un "valor punto"
   que la universidad actualiza anualmente mediante acuerdo del Consejo Superior.
   Aqui se implementa el MODELO/MOTOR de calculo completo y parametrizable; las
   constantes (VALOR_PUNTO_SALARIAL, tarifas de hora catedra, etc.) son
   ILUSTRATIVAS PARA FINES ACADEMICOS y deben reemplazarse por los valores
   vigentes del acto administrativo real (ver mintrabajo.gov.co/mi-calculadora).
   ============================================================================ */

#include <iostream>
#include <fstream>
#include <sstream>
#include <string>
#include <iomanip>
#include <limits>
#include <cstdlib>
#include <utility>
#include <filesystem>
#include <algorithm>
#include <cctype>

#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#ifndef WIN32_LEAN_AND_MEAN
#define WIN32_LEAN_AND_MEAN
#endif
#include <windows.h>
#endif

#include "payroll_engine.hpp"
#include "payroll_cycle.hpp"

using namespace std;

// ======================================================================
// 1. CONSTANTES GLOBALES DEL MODELO DE NOMINA Y NEGOCIO
// ======================================================================
const double VALOR_PUNTO_SALARIAL   = 17690.0;  // valor ilustrativo (decreto 1279)

// Tarifas de hora catedra segun categoria docente
constexpr double TARIFA_CATEDRA_AUXILIAR    = 39000.0;
constexpr double TARIFA_CATEDRA_ASISTENTE   = 45000.0;
constexpr double TARIFA_CATEDRA_ASOCIADO    = 52000.0;
constexpr double TARIFA_CATEDRA_TITULAR     = 60000.0;

// Dias y meses estandar de nomina
constexpr int    DIAS_MES_NOMINA            = 30;
constexpr double MESES_ANIO                 = 12.0;

// Limites academicos
constexpr int    CREDITOS_MIN               = 1;
constexpr int    CREDITOS_MAX               = 10;
constexpr float  NOTA_MIN                   = 0.0f;
constexpr float  NOTA_MAX                   = 5.0f;
constexpr float  UMBRAL_EBRA                = 3.0f;   // Promedio minimo (escala 0-5)

// Tamano de buffer de campos
constexpr int    MAX_CAMPOS_CSV             = 25;
constexpr int    CAMPOS_PROFESOR            = 23;

// const string ARCHIVO_DATOS          = "pita_datos.txt";
string ARCHIVO_DATOS = "";

string resolverRutaArchivoDatos(const char* argv0 = nullptr) {
#ifdef _WIN32
    (void)argv0;
    char buffer[MAX_PATH];
    DWORD len = GetModuleFileNameA(NULL, buffer, MAX_PATH);
    if (len > 0) {
        return (std::filesystem::path(buffer).parent_path() / "pita_datos.txt").string();
    }
    return (std::filesystem::absolute("pita_datos.txt")).string();
#else
    std::error_code ec;
    std::filesystem::path exePath = std::filesystem::read_symlink("/proc/self/exe", ec);
    if (!ec && !exePath.empty()) {
        return (exePath.parent_path() / "pita_datos.txt").string();
    }
    if (argv0 && argv0[0] != '\0') {
        return (std::filesystem::absolute(std::filesystem::path(argv0).parent_path() / "pita_datos.txt")).string();
    }
    return (std::filesystem::absolute("pita_datos.txt")).string();
#endif
}

// ======================================================================
// 2. ENUMERACIONES
// ======================================================================
enum CategoriaDocente   { AUXILIAR = 0, ASISTENTE = 1, ASOCIADO = 2, TITULAR = 3 };
enum TipoContratoDocente{ PLANTA = 0, OCASIONAL = 1, CATEDRATICO = 2 };
enum TipoPrograma       { INGENIERIA = 0, MEDICINA = 1, ODONTOLOGIA = 2, ENFERMERIA = 3,
                          PSICOLOGIA = 4, DERECHO = 5, ADMINISTRACION = 6, EDUCACION = 7, OTRA = 8 };

string nombreCategoria(CategoriaDocente c);
string nombreTipoContrato(TipoContratoDocente t);
string nombreTipoPrograma(TipoPrograma t);
CategoriaDocente categoriaDesdeInt(int v, bool& esValido);
CategoriaDocente categoriaDesdeInt(int v);
TipoContratoDocente contratoDesdeInt(int v, bool& esValido);
TipoContratoDocente contratoDesdeInt(int v);
TipoPrograma tipoProgramaDesdeInt(int v, bool& esValido);
TipoPrograma tipoProgramaDesdeInt(int v);
double tarifaHoraCatedra(CategoriaDocente c);

// ======================================================================
// 3. ESTRUCTURAS (TAD - listas enlazadas)
// ======================================================================

// ---- Nota / matricula de un estudiante en un curso -------------------
struct Nota {
    string codigoCurso;
    string nombreCurso;
    float  valor;       // -1 si aun no se ha calificado
    bool   cancelado;
    Nota*  sig;
};

// ---- Estudiante --------------------------------------------------------
struct Estudiante {
    string codigo;
    string nombre;
    string documento;
    string email;
    string categoria;   // Regular, Transferencia, Intercambio, Reingreso...
    bool   activo;
    Nota*  cursosMatriculados; // lista enlazada de notas
    Estudiante* sig;
};

// ---- Curso ---------------------------------------------------------------
struct Curso {
    string codigo;
    string nombre;
    int    creditos;
    bool   activo;
    Curso* sig;
};

// ---- Datos de nomina de un profesor --------------------------------------
struct DatosNomina {
    TipoContratoDocente tipoContrato;
    CategoriaDocente    categoria;
    int    puntosTitulo;
    int    puntosExperiencia;
    int    puntosProductividad;
    int    horasCatedraMes;   // solo aplica si tipoContrato == CATEDRATICO
};

// ---- Profesor --------------------------------------------------------------
struct Profesor {
    string codigo;
    string nombre;
    string documento;
    string email;
    bool   activo;
    string fechaIngreso;
    string fechaRetiro;
    string tipoVinculacion;
    string estadoLaboral = "UNKNOWN";
    string tipoSalario = "FIXED_MONTHLY";
    string claseRiesgoARL = "I";
    string configuracionSeguridadSocial = "DEFAULT";
    int    diasLaborados = 0;
    double salarioBase = 0.0;
    double tarifaHora = 0.0;
    int    diasServicioContinuo = 0;
    vector<pita::payroll::PayrollNovelty> novelties;
    vector<pita::payroll::PayrollNovelty> bonuses;
    vector<pita::payroll::PayrollNovelty> salaryConcepts;
    vector<pita::payroll::PayrollNovelty> nonSalaryConcepts;
    DatosNomina nomina;
    Profesor* sig;
};

// ---- Administrativo (nivel universidad) -------------------------------------
struct Administrativo {
    string codigo;
    string nombre;
    string documento;
    string cargo;
    string tipoContrato; // Planta, Contratista, Provisional...
    double salarioBase;
    bool   activo;
    string fechaIngreso;
    string fechaRetiro;
    string tipoVinculacion;
    string estadoLaboral = "UNKNOWN";
    string tipoSalario = "FIXED_MONTHLY";
    string claseRiesgoARL = "I";
    string configuracionSeguridadSocial = "DEFAULT";
    int    diasLaborados = 0;
    int    diasServicioContinuo = 0;
    vector<pita::payroll::PayrollNovelty> novelties;
    vector<pita::payroll::PayrollNovelty> bonuses;
    vector<pita::payroll::PayrollNovelty> salaryConcepts;
    vector<pita::payroll::PayrollNovelty> nonSalaryConcepts;
    Administrativo* sig;
};

// ---- Programa academico -----------------------------------------------------
struct Programa {
    string codigo;
    string nombre;
    TipoPrograma tipo;
    bool   activo;
    Curso*       listaCursos;
    Estudiante*  listaEstudiantes;
    Profesor*    listaProfesores;
    Programa* sig;
};

// ---- Facultad --------------------------------------------------------------
struct Facultad {
    string codigo;
    string nombre;
    bool   activo;
    Programa* listaProgramas;
    Facultad* sig;
};

// ======================================================================
// 4. CABEZAS DE LISTAS GLOBALES
// ======================================================================
Facultad*        cabezaFacultades      = nullptr;
Administrativo*   cabezaAdministrativos = nullptr;

// contadores para generar codigos automaticos
int contF = 0, contP = 0, contC = 0, contE = 0, contD = 0, contA = 0;
pita::payroll::PayrollCycle cicloNominaFormal;

// ======================================================================
// 5. PROTOTIPOS
// ======================================================================
// -- utilidades de entrada / presentacion --
int    leerEntero(const string &prompt);
double leerDouble(const string &prompt);
string leerLinea(const string &prompt, bool requerido = false);
bool   leerSiNo(const string &prompt);
void   pausar();
void   titulo(const string &t);
void   linea();
void   verificarFinDeEntrada();

// -- funciones auxiliares de mensajeria --
void msgError(const string& msg);
void msgAdvert(const string& msg);
void msgOk(const string& msg);
void msgVacio(const string& entidad);

// -- generadores de codigo --
string generarCodigoFacultad();
string generarCodigoPrograma();
string generarCodigoCurso();
string generarCodigoEstudiante();
string generarCodigoProfesor();
string generarCodigoAdministrativo();

// -- busquedas --
Facultad*   buscarFacultad(const string &codigo);
Programa*   buscarProgramaEnFacultad(Facultad* fac, const string &codigo);
Programa*   buscarProgramaGlobal(const string &codigo, Facultad** facOut);
Curso*      buscarCursoEnPrograma(Programa* prog, const string &codigo);
Estudiante* buscarEstudianteEnPrograma(Programa* prog, const string &codigo);
Estudiante* buscarEstudianteGlobal(const string &codigo, Programa** progOut, Facultad** facOut);
Profesor*   buscarProfesorEnPrograma(Programa* prog, const string &codigo);
Profesor*   buscarProfesorGlobal(const string &codigo, Programa** progOut, Facultad** facOut);
Administrativo* buscarAdministrativo(const string &codigo);
Programa*   seleccionarProgramaPorCodigo(); // pide codigo y lo busca globalmente, imprime error si no existe
bool        documentoExiste(const string& doc, string& entidadEncontrada);

// -- CRUD Facultad --
void crearFacultad();
void listarFacultades();
void modificarFacultad();
void desactivarFacultad();
void eliminarFacultad();

// -- CRUD Programa --
void crearPrograma();
void listarProgramas();
void modificarPrograma();
void desactivarPrograma();
void eliminarPrograma();

// -- CRUD Curso --
void crearCurso();
void listarCursos();
void modificarCurso();
void eliminarCurso();

// -- CRUD Estudiante --
void crearEstudiante();
void listarEstudiantes();
void modificarEstudiante();
void desactivarEstudiante();
void eliminarEstudiante();
void matricularCurso();
void cancelarMatricula();
void calificarCurso();
double calcularPromedio(Estudiante* e);
void consultarPromedioEstudiante();

// -- CRUD Profesor --
void crearProfesor();
void listarProfesores();
void modificarProfesor();
void desactivarProfesor();
void eliminarProfesor();

// -- CRUD Administrativo --
void crearAdministrativo();
void listarAdministrativos();
void modificarAdministrativo();
void desactivarAdministrativo();
void eliminarAdministrativo();

// -- Nomina docente (motor de calculo) --
pita::payroll::PayrollEmployee crearEntradaNomina(Profesor* p);
pita::payroll::PayrollEmployee crearEntradaNomina(Administrativo* a);
pita::payroll::PayrollResult liquidarProfesor(Profesor* p, int diasLaborados);
pita::payroll::PayrollResult liquidarAdministrativo(Administrativo* a, int diasLaborados);
double calcularSalarioMensualBruto(Profesor* p);
double calcularSaludMensual(Profesor* p);
double calcularPensionMensual(Profesor* p);
double calcularNetoMensual(Profesor* p);
double calcularPrestacionesSocialesMensual(Profesor* p);
double calcularSalarioAnualBruto(Profesor* p);
double calcularSalarioAnualNeto(Profesor* p);
double calcularCostoAnualUniversidad(Profesor* p);
void   mostrarDesgloseNomina(Profesor* p);

// -- Reportes (recorridos completos de listas anidadas) --
void reporteNominaProfesorIndividual();
void generarDesprendibleProfesor();
void reporteNominaPorPrograma();
void reporteNominaPorFacultad();
void reporteNominaUniversidadCompleta();
void reporteEstudiantesEnEBRA();
void reporteArbolCompletoUniversidad();
void reporteProfesoresPorCategoria();

// -- Nomina de administrativos --
double calcularNetoMensualAdministrativo(Administrativo* a);
double calcularSalarioAnualBrutoAdministrativo(Administrativo* a);
double calcularSalarioAnualNetoAdministrativo(Administrativo* a);
void   reporteNominaAdministrativoIndividual();
void   reporteNominaTotalAdministrativos();

// -- Extremos (maximo/minimo) recorriendo listas --
void reporteProfesorMayorMenorSalario();
void reporteEstudianteMejorPeorPromedio();

// -- Ordenamiento de listas enlazadas (intercambio de datos, no de punteros) --
void ordenarProfesoresPorSalario();

// -- Busqueda por documento (cedula) en toda la universidad --
Estudiante* buscarEstudiantePorDocumento(const string &doc, Programa** progOut);
Profesor*   buscarProfesorPorDocumento(const string &doc, Programa** progOut);
void buscarPorDocumento();

// -- Censo general (conteo total recorriendo toda la estructura) --
void reporteCensoGeneral();

// -- Persistencia --
void guardarDatos();
void cargarDatos();
void cargarDatosDeEjemplo();
void liberarTodaLaMemoria();

// -- Menus --
void menuFacultades();
void menuProgramas();
void menuCursos();
void menuEstudiantes();
void menuProfesores();
void menuAdministrativos();
void menuReportesNomina();
void menuNominaFormal();
void dashboardFinancieroFormal();
void generarDesprendibleFormal();
void registrarNovedadFormal();
void menuPrincipal();

// ======================================================================
// 6. MAIN
// ======================================================================
int main(int argc, char* argv[]) {
    ARCHIVO_DATOS = resolverRutaArchivoDatos(argc > 0 ? argv[0] : nullptr);
    titulo("NexoCampus - PROGRAMA INTEGRADO DE TRANSACCIONES ACADEMICAS");
    cout << "  Universidad Popular del Cesar - Modulo C++ (Listas Enlazadas)\n";
    msgOk("Ruta de datos: " + ARCHIVO_DATOS);
    linea();

    if (leerSiNo("?Desea cargar los datos guardados en '" + ARCHIVO_DATOS + "'? (s/n): ")) {
        cargarDatos();
    } else {
        cout << "\nSe iniciara el sistema SIN datos previos.\n";
        if (leerSiNo("?Desea precargar datos de ejemplo (facultades, Medicina, Ing. Sistemas, etc.)? (s/n): ")) {
            cargarDatosDeEjemplo();
        }
    }

    menuPrincipal();

    if (leerSiNo("\n?Desea guardar los datos antes de salir? (s/n): ")) {
        guardarDatos();
    }
    liberarTodaLaMemoria();
    cout << "\nGracias por usar NexoCampus. Hasta pronto.\n";
    return 0;
}

// ======================================================================
// 7. UTILIDADES DE ENTRADA / PRESENTACION
// ======================================================================
void linea() {
    cout << "----------------------------------------------------------------------\n";
}

void limpiarPantalla() {
#ifdef _WIN32
    system("cls");
#else
    system("clear");
#endif
}

void titulo(const string &t) {
    limpiarPantalla();
    cout << "\n========================================================================\n";
    cout << "  " << t << "\n";
    cout << "========================================================================\n";
}

void pausar() {
    cout << "\n  >> Presione ENTER para continuar...";
    cin.get();
}

// Si el flujo de entrada se queda sin datos (EOF), el programa termina de forma
// controlada en vez de quedar en un bucle infinito pidiendo datos que ya no llegaran.
void verificarFinDeEntrada() {
    if (cin.eof()) {
        cout << "\n  >> Fin de la entrada de datos. Cerrando el programa.\n";
        exit(0);
    }
}

int leerEntero(const string &prompt) {
    int valor;
    while (true) {
        cout << prompt;
        cin >> valor;
        if (cin.fail()) {
            verificarFinDeEntrada();
            cin.clear();
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            msgError("Entrada invalida, ingrese un numero entero.");
        } else {
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            return valor;
        }
    }
}

double leerDouble(const string &prompt) {
    double valor;
    while (true) {
        cout << prompt;
        cin >> valor;
        if (cin.fail()) {
            verificarFinDeEntrada();
            cin.clear();
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            msgError("Entrada invalida, ingrese un numero.");
        } else {
            cin.ignore(numeric_limits<streamsize>::max(), '\n');
            return valor;
        }
    }
}

string leerLinea(const string &prompt, bool requerido) {
    string resultado;
    cout << prompt;
    getline(cin, resultado);
    verificarFinDeEntrada();
    if (requerido) {
        while (resultado.empty() || resultado.find_first_not_of(" \t") == string::npos) {
            cout << ">> Este campo es obligatorio. Ingrese un valor: ";
            getline(cin, resultado);
            verificarFinDeEntrada();
        }
    }
    while (resultado.find('|') != string::npos) {
        cout << "  >> El caracter '|' no está permitido en este campo. Ingrese nuevamente: ";
        getline(cin, resultado);
        verificarFinDeEntrada();
        if (requerido) {
            while (resultado.empty() || resultado.find_first_not_of(" \t") == string::npos) {
                cout << ">> Este campo es obligatorio. Ingrese un valor: ";
                getline(cin, resultado);
                verificarFinDeEntrada();
            }
        }
    }
    return resultado;
}

bool leerSiNo(const string &prompt) {
    string s;
    while (true) {
        cout << prompt;
        getline(cin, s);
        verificarFinDeEntrada();
        if (!s.empty() && (s[0] == 's' || s[0] == 'S')) return true;
        if (!s.empty() && (s[0] == 'n' || s[0] == 'N')) return false;
        msgError("Responda 's' o 'n'.");
    }
}

// ======================================================================
// 8. ENUM <-> TEXTO
// ======================================================================
string nombreCategoria(CategoriaDocente c) {
    switch (c) {
        case AUXILIAR:   return "Auxiliar";
        case ASISTENTE:  return "Asistente";
        case ASOCIADO:   return "Asociado";
        case TITULAR:    return "Titular";
    }
    return "Desconocida";
}

string nombreTipoContrato(TipoContratoDocente t) {
    switch (t) {
        case PLANTA:      return "Planta";
        case OCASIONAL:   return "Ocasional";
        case CATEDRATICO: return "Catedratico";
    }
    return "Desconocido";
}

string nombreTipoPrograma(TipoPrograma t) {
    switch (t) {
        case INGENIERIA: return "Ingenieria";
        case MEDICINA: return "Medicina";
        case ODONTOLOGIA: return "Odontologia";
        case ENFERMERIA: return "Enfermeria";
        case PSICOLOGIA: return "Psicologia";
        case DERECHO: return "Derecho";
        case ADMINISTRACION: return "Administracion";
        case EDUCACION: return "Educacion";
        default: return "Otro";
    }
}

CategoriaDocente categoriaDesdeInt(int v, bool& esValido) {
    if (v < 0 || v > 3) {
        esValido = false;
        v = 0;
    } else {
        esValido = true;
    }
    return static_cast<CategoriaDocente>(v);
}
CategoriaDocente categoriaDesdeInt(int v) {
    bool dummy;
    return categoriaDesdeInt(v, dummy);
}

TipoContratoDocente contratoDesdeInt(int v, bool& esValido) {
    if (v < 0 || v > 2) {
        esValido = false;
        v = 2;
    } else {
        esValido = true;
    }
    return static_cast<TipoContratoDocente>(v);
}
TipoContratoDocente contratoDesdeInt(int v) {
    bool dummy;
    return contratoDesdeInt(v, dummy);
}

TipoPrograma tipoProgramaDesdeInt(int v, bool& esValido) {
    if (v < 0 || v > 8) {
        esValido = false;
        v = 8;
    } else {
        esValido = true;
    }
    return static_cast<TipoPrograma>(v);
}
TipoPrograma tipoProgramaDesdeInt(int v) {
    bool dummy;
    return tipoProgramaDesdeInt(v, dummy);
}

// ======================================================================
// 9. GENERADORES DE CODIGO
// ======================================================================
string generarCodigoFacultad() {
    contF++;
    ostringstream os; os << "F" << setw(3) << setfill('0') << contF;
    return os.str();
}
string generarCodigoPrograma() {
    contP++;
    ostringstream os; os << "P" << setw(3) << setfill('0') << contP;
    return os.str();
}
string generarCodigoCurso() {
    contC++;
    ostringstream os; os << "C" << setw(3) << setfill('0') << contC;
    return os.str();
}
string generarCodigoEstudiante() {
    contE++;
    ostringstream os; os << "E" << setw(3) << setfill('0') << contE;
    return os.str();
}
string generarCodigoProfesor() {
    contD++;
    ostringstream os; os << "D" << setw(3) << setfill('0') << contD;
    return os.str();
}
string generarCodigoAdministrativo() {
    contA++;
    ostringstream os; os << "A" << setw(3) << setfill('0') << contA;
    return os.str();
}

// ======================================================================
// 10. BUSQUEDAS - RECORRIDO DE LISTAS ENLAZADAS
// ======================================================================
Facultad* buscarFacultad(const string &codigo) {
    Facultad* actual = cabezaFacultades;
    while (actual != nullptr) {           // recorrido secuencial de la lista
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

Programa* buscarProgramaEnFacultad(Facultad* fac, const string &codigo) {
    if (fac == nullptr) return nullptr;
    Programa* actual = fac->listaProgramas;
    while (actual != nullptr) {
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

// Recorre TODAS las facultades y, dentro de cada una, todos los programas.
Programa* buscarProgramaGlobal(const string &codigo, Facultad** facOut) {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = buscarProgramaEnFacultad(f, codigo);
        if (p != nullptr) {
            if (facOut != nullptr) *facOut = f;
            return p;
        }
        f = f->sig;
    }
    if (facOut != nullptr) *facOut = nullptr;
    return nullptr;
}

Curso* buscarCursoEnPrograma(Programa* prog, const string &codigo) {
    if (prog == nullptr) return nullptr;
    Curso* actual = prog->listaCursos;
    while (actual != nullptr) {
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

Estudiante* buscarEstudianteEnPrograma(Programa* prog, const string &codigo) {
    if (prog == nullptr) return nullptr;
    Estudiante* actual = prog->listaEstudiantes;
    while (actual != nullptr) {
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

// Recorre facultades -> programas -> estudiantes (busqueda global anidada)
Estudiante* buscarEstudianteGlobal(const string &codigo, Programa** progOut, Facultad** facOut) {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = buscarEstudianteEnPrograma(p, codigo);
            if (e != nullptr) {
                if (progOut != nullptr) *progOut = p;
                if (facOut  != nullptr) *facOut  = f;
                return e;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    if (progOut != nullptr) *progOut = nullptr;
    if (facOut  != nullptr) *facOut  = nullptr;
    return nullptr;
}

Profesor* buscarProfesorEnPrograma(Programa* prog, const string &codigo) {
    if (prog == nullptr) return nullptr;
    Profesor* actual = prog->listaProfesores;
    while (actual != nullptr) {
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

Profesor* buscarProfesorGlobal(const string &codigo, Programa** progOut, Facultad** facOut) {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = buscarProfesorEnPrograma(p, codigo);
            if (d != nullptr) {
                if (progOut != nullptr) *progOut = p;
                if (facOut  != nullptr) *facOut  = f;
                return d;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    if (progOut != nullptr) *progOut = nullptr;
    if (facOut  != nullptr) *facOut  = nullptr;
    return nullptr;
}

Administrativo* buscarAdministrativo(const string &codigo) {
    Administrativo* actual = cabezaAdministrativos;
    while (actual != nullptr) {
        if (actual->codigo == codigo) return actual;
        actual = actual->sig;
    }
    return nullptr;
}

Programa* seleccionarProgramaPorCodigo() {
    string cod = leerLinea("Codigo del programa academico: ");
    Programa* p = buscarProgramaGlobal(cod, nullptr);
    if (p == nullptr) msgError("No existe un programa con ese codigo.");
    return p;
}

bool documentoExiste(const string& doc, string& entidadEncontrada) {
    if (doc.empty()) return false;

    // 1. Buscar en Profesores (de todos los programas de todas las facultades)
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                if (d->documento == doc) {
                    entidadEncontrada = "Profesor, Codigo: " + d->codigo;
                    return true;
                }
                d = d->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }

    // 2. Buscar en Estudiantes (de todos los programas de todas las facultades)
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                if (e->documento == doc) {
                    entidadEncontrada = "Estudiante, Codigo: " + e->codigo;
                    return true;
                }
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }

    // 3. Buscar en Administrativos
    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) {
        if (a->documento == doc) {
            entidadEncontrada = "Administrativo, Codigo: " + a->codigo;
            return true;
        }
        a = a->sig;
    }

    return false;
}

// ======================================================================
// 11. CRUD FACULTAD
// ======================================================================
void crearFacultad() {
    titulo("CREAR FACULTAD");
    Facultad* nueva = new Facultad();
    nueva->codigo = generarCodigoFacultad();
    nueva->nombre = leerLinea("Nombre de la facultad: ", true);
    nueva->activo = true;
    nueva->listaProgramas = nullptr;
    nueva->sig = nullptr;

    // Insercion al final de la lista (para conservar orden de creacion)
    if (cabezaFacultades == nullptr) {
        cabezaFacultades = nueva;
    } else {
        Facultad* actual = cabezaFacultades;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nueva;
    }
    msgOk("Facultad creada con codigo: " + nueva->codigo);
}

void listarFacultades() {
    titulo("LISTADO DE FACULTADES");
    if (cabezaFacultades == nullptr) {
        msgVacio("facultades");
        return;
    }
    cout << left << setw(8) << "CODIGO" << setw(40) << "NOMBRE"
         << setw(10) << "ESTADO" << setw(10) << "PROGRAMAS" << "\n";
    linea();
    Facultad* actual = cabezaFacultades;
    while (actual != nullptr) {
        int numProgramas = 0;
        Programa* p = actual->listaProgramas;
        while (p != nullptr) { numProgramas++; p = p->sig; }
        cout << left << setw(8) << actual->codigo << setw(40) << actual->nombre
             << setw(10) << (actual->activo ? "Activa" : "Inactiva")
             << setw(10) << numProgramas << "\n";
        actual = actual->sig;
    }
}

void modificarFacultad() {
    titulo("MODIFICAR FACULTAD");
    string cod = leerLinea("Codigo de la facultad a modificar: ");
    Facultad* f = buscarFacultad(cod);
    if (f == nullptr) { msgError("No existe esa facultad."); return; }
    cout << "  Nombre actual: " << f->nombre << "\n";
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) f->nombre = nuevoNombre;
    msgOk("Facultad actualizada.");
}

void desactivarFacultad() {
    titulo("ACTIVAR / DESACTIVAR FACULTAD");
    string cod = leerLinea("Codigo de la facultad: ");
    Facultad* f = buscarFacultad(cod);
    if (f == nullptr) { msgError("No existe esa facultad."); return; }
    f->activo = !f->activo;
    msgOk(string("Facultad ahora esta ") + (f->activo ? "ACTIVA" : "INACTIVA"));
}

// Libera recursivamente toda la memoria de un programa (cursos, estudiantes+notas, profesores)
void liberarPrograma(Programa* p) {
    if (p == nullptr) return;
    // liberar cursos
    Curso* c = p->listaCursos;
    while (c != nullptr) { Curso* tmp = c; c = c->sig; delete tmp; }
    // liberar estudiantes y sus notas
    Estudiante* e = p->listaEstudiantes;
    while (e != nullptr) {
        Nota* n = e->cursosMatriculados;
        while (n != nullptr) { Nota* tmpN = n; n = n->sig; delete tmpN; }
        Estudiante* tmpE = e; e = e->sig; delete tmpE;
    }
    // liberar profesores
    Profesor* d = p->listaProfesores;
    while (d != nullptr) { Profesor* tmpD = d; d = d->sig; delete tmpD; }
    delete p;
}

void eliminarFacultad() {
    titulo("ELIMINAR FACULTAD");
    string cod = leerLinea("Codigo de la facultad a eliminar: ");
    Facultad* actual = cabezaFacultades;
    Facultad* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe esa facultad."); return; }

    int numProgramas = 0;
    Programa* p = actual->listaProgramas;
    while (p != nullptr) { numProgramas++; p = p->sig; }

    if (numProgramas > 0) {
        msgAdvert("La facultad " + cod + " tiene " + to_string(numProgramas)
             + " programa(s) asociado(s). No se puede eliminar una facultad con programas activos.");
        return;
    }

    if (anterior == nullptr) cabezaFacultades = actual->sig;
    else anterior->sig = actual->sig;

    delete actual;
    msgOk("Facultad eliminada.");
}

// ======================================================================
// 12. CRUD PROGRAMA ACADEMICO
// ======================================================================
void crearPrograma() {
    titulo("CREAR PROGRAMA ACADEMICO");
    string codFac = leerLinea("Codigo de la facultad a la que pertenece: ");
    Facultad* f = buscarFacultad(codFac);
    if (f == nullptr) { msgError("No existe esa facultad."); return; }

    cout << "\n  Tipo de programa:\n";
    cout << "    0. Ingenieria\n    1. Medicina\n    2. Odontologia\n    3. Enfermeria\n";
    cout << "    4. Psicologia\n    5. Derecho\n    6. Administracion\n    7. Educacion\n    8. Otro\n";
    int tipoSel = leerEntero("  Seleccione (0-8): ");

    Programa* nuevo = new Programa();
    nuevo->codigo = generarCodigoPrograma();
    nuevo->nombre = leerLinea("Nombre del programa (ej: Medicina, Ingenieria de Sistemas): ", true);
    bool esValidoTipo = true;
    nuevo->tipo = tipoProgramaDesdeInt(tipoSel, esValidoTipo);
    if (!esValidoTipo) {
        msgAdvert("Opcion invalida. Se asigno el valor por defecto. Por favor revise el registro.");
    }
    nuevo->activo = true;
    nuevo->listaCursos = nullptr;
    nuevo->listaEstudiantes = nullptr;
    nuevo->listaProfesores = nullptr;
    nuevo->sig = nullptr;

    if (f->listaProgramas == nullptr) {
        f->listaProgramas = nuevo;
    } else {
        Programa* actual = f->listaProgramas;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nuevo;
    }
    msgOk("Programa creado con codigo: " + nuevo->codigo
         + " | Tipo: " + nombreTipoPrograma(nuevo->tipo)
         + " | Facultad: " + f->nombre);
}

void listarProgramas() {
    titulo("LISTADO DE PROGRAMAS ACADEMICOS (por facultad)");
    if (cabezaFacultades == nullptr) { msgVacio("facultades"); return; }
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        cout << "\nFacultad: " << f->nombre << " [" << f->codigo << "]\n";
        if (f->listaProgramas == nullptr) {
            msgVacio("programas");
        } else {
            cout << "    " << left << setw(8) << "CODIGO" << setw(28) << "NOMBRE"
                 << setw(18) << "TIPO" << setw(10) << "ESTADO" << "\n";
            Programa* p = f->listaProgramas;
            while (p != nullptr) {
                cout << "    " << left << setw(8) << p->codigo << setw(28) << p->nombre
                     << setw(18) << nombreTipoPrograma(p->tipo)
                     << setw(10) << (p->activo ? "Activo" : "Inactivo") << "\n";
                p = p->sig;
            }
        }
        f = f->sig;
    }
}

void modificarPrograma() {
    titulo("MODIFICAR PROGRAMA ACADEMICO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    cout << "  Nombre actual: " << p->nombre << "\n";
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) p->nombre = nuevoNombre;
    msgOk("Programa actualizado.");
}

void desactivarPrograma() {
    titulo("ACTIVAR / DESACTIVAR PROGRAMA");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    p->activo = !p->activo;
    msgOk(string("Programa ahora esta ") + (p->activo ? "ACTIVO" : "INACTIVO"));
}

void eliminarPrograma() {
    titulo("ELIMINAR PROGRAMA ACADEMICO");
    string codFac = leerLinea("Codigo de la facultad: ");
    Facultad* f = buscarFacultad(codFac);
    if (f == nullptr) { msgError("No existe esa facultad."); return; }
    string cod = leerLinea("Codigo del programa a eliminar: ");
    Programa* actual = f->listaProgramas;
    Programa* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe ese programa en esa facultad."); return; }

    int numCursos = 0;
    Curso* c = actual->listaCursos;
    while (c != nullptr) { numCursos++; c = c->sig; }

    int numEstudiantes = 0;
    Estudiante* e = actual->listaEstudiantes;
    while (e != nullptr) { numEstudiantes++; e = e->sig; }

    int numProfesores = 0;
    Profesor* d = actual->listaProfesores;
    while (d != nullptr) { numProfesores++; d = d->sig; }

    if (numCursos > 0 || numEstudiantes > 0 || numProfesores > 0) {
        string adv = "El programa " + cod + " tiene ";
        if (numCursos > 0) adv += to_string(numCursos) + " curso(s)";
        if (numCursos > 0 && (numEstudiantes > 0 || numProfesores > 0)) adv += ", ";
        if (numEstudiantes > 0) adv += to_string(numEstudiantes) + " estudiante(s)";
        if (numEstudiantes > 0 && numProfesores > 0) adv += " y ";
        if (numProfesores > 0) adv += to_string(numProfesores) + " profesor(es)";
        adv += " asociado(s). No se puede eliminar un programa con registros activos.";
        msgAdvert(adv);
        return;
    }

    if (anterior == nullptr) f->listaProgramas = actual->sig;
    else anterior->sig = actual->sig;
    liberarPrograma(actual);
    msgOk("Programa eliminado.");
}

// ======================================================================
// 13. CRUD CURSO
// ======================================================================
void crearCurso() {
    titulo("CREAR CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;

    Curso* nuevo = new Curso();
    nuevo->codigo = generarCodigoCurso();
    nuevo->nombre = leerLinea("Nombre del curso: ", true);
    int cred;
    do {
        cred = leerEntero("Numero de creditos: ");
        if (cred < CREDITOS_MIN || cred > CREDITOS_MAX)
            msgError("Los creditos deben ser un valor entre 1 y 10.");
    } while (cred < CREDITOS_MIN || cred > CREDITOS_MAX);
    nuevo->creditos = cred;
    nuevo->activo = true;
    nuevo->sig = nullptr;

    if (p->listaCursos == nullptr) {
        p->listaCursos = nuevo;
    } else {
        Curso* actual = p->listaCursos;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nuevo;
    }
    msgOk("Curso creado con codigo: " + nuevo->codigo + " en " + p->nombre);
}

void listarCursos() {
    titulo("LISTADO DE CURSOS");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    if (p->listaCursos == nullptr) { msgVacio("cursos"); return; }
    cout << left << setw(8) << "CODIGO" << setw(35) << "NOMBRE"
         << setw(10) << "CREDITOS" << setw(10) << "ESTADO" << "\n";
    linea();
    Curso* actual = p->listaCursos;
    while (actual != nullptr) {
        cout << left << setw(8) << actual->codigo << setw(35) << actual->nombre
             << setw(10) << actual->creditos
             << setw(10) << (actual->activo ? "Activo" : "Inactivo") << "\n";
        actual = actual->sig;
    }
}

void modificarCurso() {
    titulo("MODIFICAR CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del curso: ");
    Curso* c = buscarCursoEnPrograma(p, cod);
    if (c == nullptr) { msgError("No existe ese curso."); return; }
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) c->nombre = nuevoNombre;
    string cambiarCred = leerLinea("  ?Cambiar creditos? (s/n): ");
    if (!cambiarCred.empty() && (cambiarCred[0]=='s'||cambiarCred[0]=='S')) {
        int cred;
        do {
            cred = leerEntero("  Nuevos creditos: ");
            if (cred < CREDITOS_MIN || cred > CREDITOS_MAX)
                msgError("Los creditos deben ser un valor entre 1 y 10.");
        } while (cred < CREDITOS_MIN || cred > CREDITOS_MAX);
        c->creditos = cred;
    }
    msgOk("Curso actualizado.");
}

void eliminarCurso() {
    titulo("ELIMINAR CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del curso a eliminar: ");
    Curso* actual = p->listaCursos;
    Curso* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe ese curso."); return; }

    int matriculados = 0;
    Estudiante* e = p->listaEstudiantes;
    while (e != nullptr) {
        Nota* n = e->cursosMatriculados;
        while (n != nullptr) {
            if (n->codigoCurso == cod && !n->cancelado) {
                matriculados++;
                break;
            }
            n = n->sig;
        }
        e = e->sig;
    }

    if (matriculados > 0) {
        msgAdvert("El curso " + cod + " tiene " + to_string(matriculados)
             + " estudiante(s) matriculado(s). No se puede eliminar un curso con matriculas activas.");
        return;
    }

    if (anterior == nullptr) p->listaCursos = actual->sig;
    else anterior->sig = actual->sig;
    delete actual;
    msgOk("Curso eliminado.");
}

// ======================================================================
// 14. CRUD ESTUDIANTE + MATRICULAS + PROMEDIO + ALERTA EBRA
// ======================================================================
void crearEstudiante() {
    titulo("CREAR ESTUDIANTE");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;

    string nom = leerLinea("Nombre del estudiante: ", true);
    string doc = leerLinea("Documento de identidad: ");
    string entidadEncontrada;
    if (documentoExiste(doc, entidadEncontrada)) {
        msgError("Ya existe una persona registrada con el documento " + doc + ".\n  Entidad: " + entidadEncontrada + ".");
        return;
    }

    Estudiante* nuevo = new Estudiante();
    nuevo->codigo = generarCodigoEstudiante();
    nuevo->nombre = nom;
    nuevo->documento = doc;
    nuevo->email = leerLinea("Correo electronico: ");
    nuevo->categoria = leerLinea("Categoria (Regular/Transferencia/Intercambio/Reingreso): ");
    nuevo->activo = true;
    nuevo->cursosMatriculados = nullptr;
    nuevo->sig = nullptr;

    if (p->listaEstudiantes == nullptr) {
        p->listaEstudiantes = nuevo;
    } else {
        Estudiante* actual = p->listaEstudiantes;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nuevo;
    }
    msgOk("Estudiante creado con codigo: " + nuevo->codigo + " en " + p->nombre);
}

void listarEstudiantes() {
    titulo("LISTADO DE ESTUDIANTES");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    if (p->listaEstudiantes == nullptr) { msgVacio("estudiantes"); return; }
    cout << left << setw(8) << "CODIGO" << setw(28) << "NOMBRE" << setw(14) << "DOCUMENTO"
         << setw(14) << "CATEGORIA" << setw(10) << "ESTADO" << setw(10) << "PROMEDIO" << "\n";
    linea();
    Estudiante* actual = p->listaEstudiantes;
    while (actual != nullptr) {
        double prom = calcularPromedio(actual);
        cout << left << setw(8) << actual->codigo << setw(28) << actual->nombre
             << setw(14) << actual->documento << setw(14) << actual->categoria
             << setw(10) << (actual->activo ? "Activo" : "Inactivo");
        if (prom < 0) cout << setw(10) << "N/A" << "\n";
        else cout << fixed << setprecision(2) << setw(10) << prom << "\n";
        actual = actual->sig;
    }
}

void modificarEstudiante() {
    titulo("MODIFICAR ESTUDIANTE");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, cod);
    if (e == nullptr) { msgError("No existe ese estudiante."); return; }
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) e->nombre = nuevoNombre;
    string nuevoEmail = leerLinea("  Nuevo email (ENTER para no cambiar): ");
    if (!nuevoEmail.empty()) e->email = nuevoEmail;
    string nuevaCategoria = leerLinea("  Nueva categoria (ENTER para no cambiar): ");
    if (!nuevaCategoria.empty()) e->categoria = nuevaCategoria;
    msgOk("Estudiante actualizado.");
}

void desactivarEstudiante() {
    titulo("ACTIVAR / DESACTIVAR ESTUDIANTE");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, cod);
    if (e == nullptr) { msgError("No existe ese estudiante."); return; }
    e->activo = !e->activo;
    msgOk(string("Estudiante ahora esta ") + (e->activo ? "ACTIVO" : "INACTIVO"));
}

void eliminarEstudiante() {
    titulo("ELIMINAR ESTUDIANTE");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del estudiante a eliminar: ");
    Estudiante* actual = p->listaEstudiantes;
    Estudiante* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe ese estudiante."); return; }
    if (anterior == nullptr) p->listaEstudiantes = actual->sig;
    else anterior->sig = actual->sig;
    Nota* n = actual->cursosMatriculados;
    while (n != nullptr) { Nota* tmp = n; n = n->sig; delete tmp; }
    delete actual;
    msgOk("Estudiante eliminado.");
}

void matricularCurso() {
    titulo("MATRICULAR CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string codEst = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, codEst);
    if (e == nullptr) { msgError("No existe ese estudiante en el programa."); return; }
    string codCurso = leerLinea("Codigo del curso a matricular: ");
    Curso* c = buscarCursoEnPrograma(p, codCurso);
    if (c == nullptr) { msgError("No existe ese curso en el programa."); return; }

    // verificar que no este ya matriculado (y no cancelado)
    Nota* n = e->cursosMatriculados;
    while (n != nullptr) {
        if (n->codigoCurso == c->codigo && !n->cancelado) {
            msgError("El estudiante ya esta matriculado en ese curso.");
            return;
        }
        n = n->sig;
    }

    Nota* nueva = new Nota();
    nueva->codigoCurso = c->codigo;
    nueva->nombreCurso = c->nombre;
    nueva->valor = -1;
    nueva->cancelado = false;
    nueva->sig = nullptr;

    if (e->cursosMatriculados == nullptr) {
        e->cursosMatriculados = nueva;
    } else {
        Nota* actual = e->cursosMatriculados;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nueva;
    }
    msgOk("Matricula registrada: " + e->nombre + " -> " + c->nombre);
}

void cancelarMatricula() {
    titulo("CANCELAR MATRICULA DE UN CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string codEst = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, codEst);
    if (e == nullptr) { msgError("No existe ese estudiante."); return; }
    string codCurso = leerLinea("Codigo del curso a cancelar: ");
    Nota* n = e->cursosMatriculados;
    while (n != nullptr) {
        if (n->codigoCurso == codCurso && !n->cancelado) {
            n->cancelado = true;
            msgOk("Matricula cancelada: " + n->nombreCurso);
            return;
        }
        n = n->sig;
    }
    msgError("El estudiante no tiene una matricula activa en ese curso.");
}

void calificarCurso() {
    titulo("REGISTRAR NOTA DE UN CURSO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string codEst = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, codEst);
    if (e == nullptr) { msgError("No existe ese estudiante."); return; }
    string codCurso = leerLinea("Codigo del curso: ");
    Nota* n = e->cursosMatriculados;
    while (n != nullptr) {
        if (n->codigoCurso == codCurso && !n->cancelado) {
            double val;
            do {
                val = leerDouble("Nota (escala 0.0 a 5.0): ");
                if (val < NOTA_MIN || val > NOTA_MAX)
                    msgError("La nota debe estar entre 0.0 y 5.0. Intente de nuevo.");
            } while (val < NOTA_MIN || val > NOTA_MAX);
            n->valor = (float) val;
            msgOk("Nota registrada.");
            return;
        }
        n = n->sig;
    }
    msgError("El estudiante no tiene una matricula activa en ese curso.");
}

// Recorre la lista de notas de un estudiante (ignorando canceladas y sin calificar)
double calcularPromedio(Estudiante* e) {
    if (e == nullptr) return -1;
    double suma = 0;
    int cuenta = 0;
    Nota* n = e->cursosMatriculados;
    while (n != nullptr) {
        if (!n->cancelado && n->valor >= 0) {
            suma += n->valor;
            cuenta++;
        }
        n = n->sig;
    }
    if (cuenta == 0) return -1;
    return suma / cuenta;
}

void consultarPromedioEstudiante() {
    titulo("CONSULTAR PROMEDIO Y ALERTA ACADEMICA");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string codEst = leerLinea("Codigo del estudiante: ");
    Estudiante* e = buscarEstudianteEnPrograma(p, codEst);
    if (e == nullptr) { msgError("No existe ese estudiante."); return; }

    cout << "\n  Historial academico de " << e->nombre << ":\n";
    cout << "  " << left << setw(30) << "CURSO" << setw(10) << "NOTA" << setw(12) << "ESTADO" << "\n";
    Nota* n = e->cursosMatriculados;
    while (n != nullptr) {
        cout << "  " << left << setw(30) << n->nombreCurso;
        if (n->valor < 0) cout << setw(10) << "N/A"; else cout << fixed << setprecision(2) << setw(10) << n->valor;
        cout << setw(12) << (n->cancelado ? "Cancelado" : "Activo") << "\n";
        n = n->sig;
    }

    double prom = calcularPromedio(e);
    if (prom < 0) {
        msgVacio("notas");
        return;
    }
    cout << fixed << setprecision(2);
    cout << "\n  PROMEDIO ACUMULADO: " << prom << "\n";
    if (prom < UMBRAL_EBRA) {
        cout << "  >>>> ALERTA: El estudiante se encuentra en EBRA "
             << "(Estudiante en Bajo Rendimiento Academico, promedio < "
             << UMBRAL_EBRA << ") <<<<\n";
    }
}

// ======================================================================
// 15. CRUD PROFESOR
// ======================================================================
void crearProfesor() {
    titulo("CREAR PROFESOR");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;

    string nom = leerLinea("Nombre del profesor: ", true);
    string doc = leerLinea("Documento de identidad: ");
    string entidadEncontrada;
    if (documentoExiste(doc, entidadEncontrada)) {
        msgError("Ya existe una persona registrada con el documento " + doc + ".\n  Entidad: " + entidadEncontrada + ".");
        return;
    }

    Profesor* nuevo = new Profesor();
    nuevo->codigo = generarCodigoProfesor();
    nuevo->nombre = nom;
    nuevo->documento = doc;
    nuevo->email = leerLinea("Correo electronico: ");
    nuevo->activo = true;

    cout << "\n  Tipo de contratacion:\n";
    cout << "    0. Planta\n    1. Ocasional\n    2. Catedratico\n";
    int tc = leerEntero("  Seleccione (0-2): ");
    bool esValidoContrato = true;
    nuevo->nomina.tipoContrato = contratoDesdeInt(tc, esValidoContrato);
    if (!esValidoContrato) {
        msgAdvert("Opcion invalida. Se asigno el valor por defecto. Por favor revise el registro.");
    }

    cout << "\n  Categoria docente:\n";
    cout << "    0. Auxiliar\n    1. Asistente\n    2. Asociado\n    3. Titular\n";
    int cat = leerEntero("  Seleccione (0-3): ");
    bool esValidaCat = true;
    nuevo->nomina.categoria = categoriaDesdeInt(cat, esValidaCat);
    if (!esValidaCat) {
        msgAdvert("Opcion invalida. Se asigno el valor por defecto. Por favor revise el registro.");
    }

    if (nuevo->nomina.tipoContrato == CATEDRATICO) {
        int h;
        do {
            h = leerEntero("  Horas catedra al mes: ");
            if (h < 0 || h > 300)
                msgError("Las horas de catedra deben ser entre 0 y 300.");
        } while (h < 0 || h > 300);
        nuevo->nomina.horasCatedraMes = h;
        nuevo->nomina.puntosTitulo = 0;
        nuevo->nomina.puntosExperiencia = 0;
        nuevo->nomina.puntosProductividad = 0;
    } else {
        int pt;
        do {
            pt = leerEntero("  Puntos salariales por titulo: ");
            if (pt < 0)
                msgError("Los puntos no pueden ser negativos.");
        } while (pt < 0);
        nuevo->nomina.puntosTitulo = pt;

        int pe;
        do {
            pe = leerEntero("  Puntos salariales por experiencia calificada: ");
            if (pe < 0)
                msgError("Los puntos no pueden ser negativos.");
        } while (pe < 0);
        nuevo->nomina.puntosExperiencia = pe;

        int pp;
        do {
            pp = leerEntero("  Puntos salariales por productividad academica: ");
            if (pp < 0)
                msgError("Los puntos no pueden ser negativos.");
        } while (pp < 0);
        nuevo->nomina.puntosProductividad = pp;

        nuevo->nomina.horasCatedraMes = 0;
    }
    nuevo->sig = nullptr;

    if (p->listaProfesores == nullptr) {
        p->listaProfesores = nuevo;
    } else {
        Profesor* actual = p->listaProfesores;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nuevo;
    }
    msgOk("Profesor creado con codigo: " + nuevo->codigo + " en " + p->nombre);
}

void listarProfesores() {
    titulo("LISTADO DE PROFESORES");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    if (p->listaProfesores == nullptr) { msgVacio("profesores"); return; }
    cout << left << setw(8) << "CODIGO" << setw(26) << "NOMBRE" << setw(13) << "CONTRATO"
         << setw(12) << "CATEGORIA" << setw(10) << "ESTADO" << setw(14) << "SALARIO MES" << "\n";
    linea();
    Profesor* actual = p->listaProfesores;
    while (actual != nullptr) {
        cout << left << setw(8) << actual->codigo << setw(26) << actual->nombre
             << setw(13) << nombreTipoContrato(actual->nomina.tipoContrato)
             << setw(12) << nombreCategoria(actual->nomina.categoria)
             << setw(10) << (actual->activo ? "Activo" : "Inactivo")
             << fixed << setprecision(0) << setw(14) << calcularSalarioMensualBruto(actual) << "\n";
        actual = actual->sig;
    }
}

void modificarProfesor() {
    titulo("MODIFICAR PROFESOR");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del profesor: ");
    Profesor* d = buscarProfesorEnPrograma(p, cod);
    if (d == nullptr) { msgError("No existe ese profesor."); return; }
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) d->nombre = nuevoNombre;
    if (leerSiNo("  ?Actualizar categoria docente? (s/n): ")) {
        cout << "    0. Auxiliar\n    1. Asistente\n    2. Asociado\n    3. Titular\n";
        int c = leerEntero("    Seleccione (0-3): ");
        bool esValidaCat = true;
        d->nomina.categoria = categoriaDesdeInt(c, esValidaCat);
        if (!esValidaCat) {
            msgAdvert("Opcion invalida. Se asigno el valor por defecto. Por favor revise el registro.");
        }
    }
    if (leerSiNo("  ?Actualizar tipo de contratacion? (s/n): ")) {
        cout << "    0. Planta\n    1. Ocasional\n    2. Catedratico\n";
        int t = leerEntero("    Seleccione (0-2): ");
        bool esValidoContrato = true;
        d->nomina.tipoContrato = contratoDesdeInt(t, esValidoContrato);
        if (!esValidoContrato) {
            msgAdvert("Opcion invalida. Se asigno el valor por defecto. Por favor revise el registro.");
        }
    }
    if (d->nomina.tipoContrato == CATEDRATICO) {
        if (leerSiNo("  ?Actualizar horas catedra/mes? (s/n): ")) {
            int h;
            do {
                h = leerEntero("    Horas catedra al mes: ");
                if (h < 0 || h > 300)
                    msgError("Las horas de catedra deben ser entre 0 y 300.");
            } while (h < 0 || h > 300);
            d->nomina.horasCatedraMes = h;
        }
    } else {
        if (leerSiNo("  ?Actualizar puntos salariales? (s/n): ")) {
            int pt;
            do {
                pt = leerEntero("    Puntos por titulo: ");
                if (pt < 0)
                    msgError("Los puntos no pueden ser negativos.");
            } while (pt < 0);
            d->nomina.puntosTitulo = pt;

            int pe;
            do {
                pe = leerEntero("    Puntos por experiencia: ");
                if (pe < 0)
                    msgError("Los puntos no pueden ser negativos.");
            } while (pe < 0);
            d->nomina.puntosExperiencia = pe;

            int pp;
            do {
                pp = leerEntero("    Puntos por productividad: ");
                if (pp < 0)
                    msgError("Los puntos no pueden ser negativos.");
            } while (pp < 0);
            d->nomina.puntosProductividad = pp;
        }
    }
    msgOk("Profesor actualizado.");
}

void desactivarProfesor() {
    titulo("ACTIVAR / DESACTIVAR PROFESOR");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del profesor: ");
    Profesor* d = buscarProfesorEnPrograma(p, cod);
    if (d == nullptr) { msgError("No existe ese profesor."); return; }
    d->activo = !d->activo;
    msgOk("Profesor ahora esta " + string(d->activo ? "ACTIVO" : "INACTIVO"));
}

void eliminarProfesor() {
    titulo("ELIMINAR PROFESOR");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    string cod = leerLinea("Codigo del profesor a eliminar: ");
    Profesor* actual = p->listaProfesores;
    Profesor* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe ese profesor."); return; }
    if (anterior == nullptr) p->listaProfesores = actual->sig;
    else anterior->sig = actual->sig;
    delete actual;
    msgOk("Profesor eliminado.");
}

// ======================================================================
// 16. CRUD ADMINISTRATIVO
// ======================================================================
void crearAdministrativo() {
    titulo("CREAR ADMINISTRATIVO");
    string nom = leerLinea("Nombre: ", true);
    string doc = leerLinea("Documento de identidad: ");
    string entidadEncontrada;
    if (documentoExiste(doc, entidadEncontrada)) {
        msgError("Ya existe una persona registrada con el documento " + doc + ".\n  Entidad: " + entidadEncontrada + ".");
        return;
    }

    Administrativo* nuevo = new Administrativo();
    nuevo->codigo = generarCodigoAdministrativo();
    nuevo->nombre = nom;
    nuevo->documento = doc;
    nuevo->cargo = leerLinea("Cargo: ", true);
    nuevo->tipoContrato = leerLinea("Tipo de contratacion (Planta/Contratista/Provisional): ");
    double sal;
    do {
        sal = leerDouble("Salario base mensual: ");
        if (sal < 1300000.0)
            msgError("El salario base no puede ser inferior al salario minimo legal.");
    } while (sal < 1300000.0);
    nuevo->salarioBase = sal;
    nuevo->activo = true;
    nuevo->sig = nullptr;

    if (cabezaAdministrativos == nullptr) {
        cabezaAdministrativos = nuevo;
    } else {
        Administrativo* actual = cabezaAdministrativos;
        while (actual->sig != nullptr) actual = actual->sig;
        actual->sig = nuevo;
    }
    msgOk("Administrativo creado con codigo: " + nuevo->codigo);
}

void listarAdministrativos() {
    titulo("LISTADO DE ADMINISTRATIVOS");
    if (cabezaAdministrativos == nullptr) { msgVacio("administrativos"); return; }
    cout << left << setw(8) << "CODIGO" << setw(24) << "NOMBRE" << setw(20) << "CARGO"
         << setw(14) << "CONTRATO" << setw(10) << "ESTADO" << setw(14) << "SALARIO" << "\n";
    linea();
    Administrativo* actual = cabezaAdministrativos;
    while (actual != nullptr) {
        cout << left << setw(8) << actual->codigo << setw(24) << actual->nombre
             << setw(20) << actual->cargo << setw(14) << actual->tipoContrato
             << setw(10) << (actual->activo ? "Activo" : "Inactivo")
             << fixed << setprecision(0) << setw(14) << actual->salarioBase << "\n";
        actual = actual->sig;
    }
}

void modificarAdministrativo() {
    titulo("MODIFICAR ADMINISTRATIVO");
    string cod = leerLinea("Codigo del administrativo: ");
    Administrativo* a = buscarAdministrativo(cod);
    if (a == nullptr) { msgError("No existe ese administrativo."); return; }
    string nuevoNombre = leerLinea("  Nuevo nombre (ENTER para no cambiar): ");
    if (!nuevoNombre.empty()) a->nombre = nuevoNombre;
    string nuevoCargo = leerLinea("  Nuevo cargo (ENTER para no cambiar): ");
    if (!nuevoCargo.empty()) a->cargo = nuevoCargo;
    if (leerSiNo("  ?Actualizar salario base? (s/n): ")) {
        double sal;
        do {
            sal = leerDouble("  Nuevo salario base: ");
            if (sal < 1300000.0)
                msgError("El salario base no puede ser inferior al salario minimo legal.");
        } while (sal < 1300000.0);
        a->salarioBase = sal;
    }
    msgOk("Administrativo actualizado.");
}

void desactivarAdministrativo() {
    titulo("ACTIVAR / DESACTIVAR ADMINISTRATIVO");
    string cod = leerLinea("Codigo del administrativo: ");
    Administrativo* a = buscarAdministrativo(cod);
    if (a == nullptr) { msgError("No existe ese administrativo."); return; }
    a->activo = !a->activo;
    msgOk("Administrativo ahora esta " + string(a->activo ? "ACTIVO" : "INACTIVO"));
}

void eliminarAdministrativo() {
    titulo("ELIMINAR ADMINISTRATIVO");
    string cod = leerLinea("Codigo del administrativo a eliminar: ");
    Administrativo* actual = cabezaAdministrativos;
    Administrativo* anterior = nullptr;
    while (actual != nullptr && actual->codigo != cod) {
        anterior = actual;
        actual = actual->sig;
    }
    if (actual == nullptr) { msgError("No existe ese administrativo."); return; }
    if (anterior == nullptr) cabezaAdministrativos = actual->sig;
    else anterior->sig = actual->sig;
    delete actual;
    msgOk("Administrativo eliminado.");
}

// ======================================================================
// 17. MOTOR DE NOMINA DOCENTE (Decreto 1279/2002 - Acuerdo 027/2024)
// ======================================================================

pita::payroll::PayrollEmployee crearEntradaNomina(Profesor* p) {
    pita::payroll::PayrollEmployee employee;
    if (p == nullptr) return employee;
    employee.employeeId = p->codigo;
    employee.employeeType = "Professor";
    employee.employmentType = p->nomina.tipoContrato == CATEDRATICO
        ? "catedratico" : (p->nomina.tipoContrato == PLANTA ? "planta" : "ocasional");
    employee.baseMonthlySalary = static_cast<pita::payroll::Money>(p->salarioBase);
    employee.pointValue = static_cast<pita::payroll::Money>(VALOR_PUNTO_SALARIAL);
    employee.categoryScore = 0.0;
    employee.titleScore = p->nomina.puntosTitulo;
    employee.experienceScore = p->nomina.puntosExperiencia;
    employee.productivityScore = p->nomina.puntosProductividad;
    employee.hourlyRate = static_cast<pita::payroll::Money>(p->tarifaHora > 0 ? p->tarifaHora : tarifaHoraCatedra(p->nomina.categoria));
    employee.hoursWorked = p->nomina.horasCatedraMes;
    employee.continuousServiceDays = p->diasServicioContinuo;
    employee.active = p->activo;
    employee.workedDays = p->diasLaborados;
    employee.hireDate = p->fechaIngreso;
    employee.terminationDate = p->fechaRetiro;
    return employee;
}

pita::payroll::PayrollEmployee crearEntradaNomina(Administrativo* a) {
    pita::payroll::PayrollEmployee employee;
    if (a == nullptr) return employee;
    employee.employeeId = a->codigo;
    employee.employeeType = "Administrative";
    employee.employmentType = a->tipoContrato;
    employee.baseMonthlySalary = static_cast<pita::payroll::Money>(a->salarioBase);
    employee.continuousServiceDays = a->diasServicioContinuo;
    employee.active = a->activo;
    employee.workedDays = a->diasLaborados;
    employee.hireDate = a->fechaIngreso;
    employee.terminationDate = a->fechaRetiro;
    return employee;
}

vector<pita::payroll::PayrollNovelty> conceptosNomina(Profesor* p) {
    vector<pita::payroll::PayrollNovelty> result;
    if (p == nullptr) return result;
    result.insert(result.end(), p->novelties.begin(), p->novelties.end());
    result.insert(result.end(), p->bonuses.begin(), p->bonuses.end());
    result.insert(result.end(), p->salaryConcepts.begin(), p->salaryConcepts.end());
    result.insert(result.end(), p->nonSalaryConcepts.begin(), p->nonSalaryConcepts.end());
    return result;
}

vector<pita::payroll::PayrollNovelty> conceptosNomina(Administrativo* a) {
    vector<pita::payroll::PayrollNovelty> result;
    if (a == nullptr) return result;
    result.insert(result.end(), a->novelties.begin(), a->novelties.end());
    result.insert(result.end(), a->bonuses.begin(), a->bonuses.end());
    result.insert(result.end(), a->salaryConcepts.begin(), a->salaryConcepts.end());
    result.insert(result.end(), a->nonSalaryConcepts.begin(), a->nonSalaryConcepts.end());
    return result;
}

pita::payroll::PayrollResult liquidarProfesor(Profesor* p, int diasLaborados) {
    pita::payroll::PayrollPeriod period{"LEGACY", diasLaborados, 0, 0, "", "", "OPEN"};
    pita::payroll::PayrollRules rules;
    return pita::payroll::calculatePayroll(crearEntradaNomina(p), period, rules, conceptosNomina(p));
}

pita::payroll::PayrollResult liquidarAdministrativo(Administrativo* a, int diasLaborados) {
    pita::payroll::PayrollPeriod period{"LEGACY", diasLaborados, 0, 0, "", "", "OPEN"};
    pita::payroll::PayrollRules rules;
    return pita::payroll::calculatePayroll(crearEntradaNomina(a), period, rules, conceptosNomina(a));
}

// Tarifa de hora catedra segun categoria (ilustrativa, ajustar a valores reales)
double tarifaHoraCatedra(CategoriaDocente c) {
    switch (c) {
        case AUXILIAR:  return TARIFA_CATEDRA_AUXILIAR;
        case ASISTENTE: return TARIFA_CATEDRA_ASISTENTE;
        case ASOCIADO:  return TARIFA_CATEDRA_ASOCIADO;
        case TITULAR:   return TARIFA_CATEDRA_TITULAR;
    }
    return TARIFA_CATEDRA_AUXILIAR;
}

// Salario mensual BRUTO. Planta/Ocasional: puntos salariales * valor punto.
// Catedratico: horas catedra al mes * tarifa hora catedra segun su categoria.
double calcularSalarioMensualBruto(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(pita::payroll::salaryBase(crearEntradaNomina(p)));
}

double calcularSaludMensual(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(liquidarProfesor(p, DIAS_MES_NOMINA).employeeHealth);
}

double calcularPensionMensual(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(liquidarProfesor(p, DIAS_MES_NOMINA).employeePension);
}

double calcularNetoMensual(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(liquidarProfesor(p, DIAS_MES_NOMINA).netSalary);
}

// Provision de prestaciones sociales (cesantias + intereses + prima + vacaciones).
// No aplica tipicamente a catedraticos por hora (se liquidan de forma distinta).
double calcularPrestacionesSocialesMensual(Profesor* p) {
    if (p == nullptr) return 0.0;
    const auto result = liquidarProfesor(p, DIAS_MES_NOMINA);
    return static_cast<double>(result.serviceBonusProvision + result.severanceProvision +
        result.severanceInterest + result.christmasBonusProvision + result.vacationProvision +
        result.vacationBonusProvision);
}

double calcularSalarioAnualBruto(Profesor* p) {
    return calcularSalarioMensualBruto(p) * MESES_ANIO;
}

double calcularSalarioAnualNeto(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(liquidarProfesor(p, DIAS_MES_NOMINA).netSalary) * MESES_ANIO;
}

// Costo anual total para la universidad: 12 meses de salario bruto + prestaciones anuales
double calcularCostoAnualUniversidad(Profesor* p) {
    if (p == nullptr) return 0.0;
    return static_cast<double>(liquidarProfesor(p, DIAS_MES_NOMINA).totalEmployerCost) * MESES_ANIO;
}

void mostrarDesgloseNomina(Profesor* p) {
    if (p == nullptr) return;
    cout << fixed << setprecision(2);
    cout << "\n  Profesor: " << p->nombre << " [" << p->codigo << "]\n";
    cout << "  Contrato: " << nombreTipoContrato(p->nomina.tipoContrato)
         << "   Categoria: " << nombreCategoria(p->nomina.categoria) << "\n";
    if (p->nomina.tipoContrato == CATEDRATICO) {
        cout << "  Horas catedra/mes: " << p->nomina.horasCatedraMes
             << "   Tarifa hora: $" << tarifaHoraCatedra(p->nomina.categoria) << "\n";
    } else {
        int totalPuntos = p->nomina.puntosTitulo + p->nomina.puntosExperiencia + p->nomina.puntosProductividad;
        cout << "  Puntos: titulo=" << p->nomina.puntosTitulo
             << " experiencia=" << p->nomina.puntosExperiencia
             << " productividad=" << p->nomina.puntosProductividad
             << " (total=" << totalPuntos << ")  valor punto=$" << VALOR_PUNTO_SALARIAL << "\n";
    }
    linea();
    cout << "  Salario mensual BRUTO      : $ " << calcularSalarioMensualBruto(p) << "\n";
    cout << "  (-) Aporte salud (4%)      : $ " << calcularSaludMensual(p) << "\n";
    cout << "  (-) Aporte pension (4%)    : $ " << calcularPensionMensual(p) << "\n";
    cout << "  Salario mensual NETO       : $ " << calcularNetoMensual(p) << "\n";
    cout << "  Prestaciones sociales/mes  : $ " << calcularPrestacionesSocialesMensual(p) << "\n";
    linea();
    cout << "  SALARIO ANUAL BRUTO (x12)      : $ " << calcularSalarioAnualBruto(p) << "\n";
    cout << "  SALARIO ANUAL NETO (x12)       : $ " << calcularSalarioAnualNeto(p) << "\n";
    cout << "  COSTO ANUAL PARA LA UNIVERSIDAD: $ " << calcularCostoAnualUniversidad(p) << "\n";
}

// ======================================================================
// 18. REPORTES: RECORRIDOS COMPLETOS DE LA ESTRUCTURA ANIDADA
// ======================================================================
void reporteNominaProfesorIndividual() {
    titulo("NOMINA DE UN PROFESOR (mensual y anual)");
    string cod = leerLinea("Codigo del profesor: ");
    Profesor* d = buscarProfesorGlobal(cod, nullptr, nullptr);
    if (d == nullptr) { msgError("No existe ese profesor."); return; }
    mostrarDesgloseNomina(d);
}

void generarDesprendibleProfesor() {
    generarDesprendibleFormal();
}

// Recorre facultades -> programas -> profesores, sumando salarios de un programa puntual
void reporteNominaPorPrograma() {
    titulo("NOMINA TOTAL DE UN PROGRAMA ACADEMICO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    double totalMensual = 0, totalAnual = 0;
    int cuenta = 0;
    cout << left << setw(8) << "CODIGO" << setw(26) << "NOMBRE" << setw(13) << "CONTRATO"
         << setw(16) << "MENSUAL BRUTO" << setw(16) << "ANUAL BRUTO" << "\n";
    linea();
    Profesor* d = p->listaProfesores;
    while (d != nullptr) {
        double m = calcularSalarioMensualBruto(d);
        double a = calcularSalarioAnualBruto(d);
        cout << left << setw(8) << d->codigo << setw(26) << d->nombre
             << setw(13) << nombreTipoContrato(d->nomina.tipoContrato)
             << fixed << setprecision(0) << setw(16) << m << setw(16) << a << "\n";
        totalMensual += m; totalAnual += a; cuenta++;
        d = d->sig;
    }
    linea();
    cout << "  Profesores: " << cuenta << "\n";
    cout << fixed << setprecision(0);
    cout << "  TOTAL NOMINA MENSUAL DEL PROGRAMA: $ " << totalMensual << "\n";
    cout << "  TOTAL NOMINA ANUAL  DEL PROGRAMA : $ " << totalAnual << "\n";
}

// Recorre TODOS los programas de UNA facultad (dos niveles de listas anidadas)
void reporteNominaPorFacultad() {
    titulo("NOMINA TOTAL DE UNA FACULTAD");
    string codFac = leerLinea("Codigo de la facultad: ");
    Facultad* f = buscarFacultad(codFac);
    if (f == nullptr) { msgError("No existe esa facultad."); return; }

    double totalMensual = 0, totalAnual = 0;
    int cuentaProf = 0;
    Programa* p = f->listaProgramas;
    while (p != nullptr) {
        cout << "\n  Programa: " << p->nombre << " [" << p->codigo << "]\n";
        Profesor* d = p->listaProfesores;
        if (d == nullptr) msgVacio("profesores");
        while (d != nullptr) {
            double m = calcularSalarioMensualBruto(d);
            cout << "    - " << d->nombre << " (" << nombreTipoContrato(d->nomina.tipoContrato)
                 << "): $ " << fixed << setprecision(0) << m << " / mes\n";
            totalMensual += m;
            totalAnual += calcularSalarioAnualBruto(d);
            cuentaProf++;
            d = d->sig;
        }
        p = p->sig;
    }
    linea();
    cout << "  Total profesores en la facultad: " << cuentaProf << "\n";
    cout << fixed << setprecision(0);
    cout << "  TOTAL NOMINA MENSUAL DE LA FACULTAD: $ " << totalMensual << "\n";
    cout << "  TOTAL NOMINA ANUAL  DE LA FACULTAD : $ " << totalAnual << "\n";
}

// Recorre TODA la universidad: facultades -> programas -> profesores (recorrido completo)
void reporteNominaUniversidadCompleta() {
    titulo("NOMINA TOTAL DE TODA LA UNIVERSIDAD (recorrido completo)");
    double totalMensual = 0, totalAnual = 0, totalCostoAnualUniv = 0;
    int cuentaProf = 0;

    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        double subtotalFac = 0;
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                double m = calcularSalarioMensualBruto(d);
                subtotalFac += m;
                totalMensual += m;
                totalAnual += calcularSalarioAnualBruto(d);
                totalCostoAnualUniv += calcularCostoAnualUniversidad(d);
                cuentaProf++;
                d = d->sig;
            }
            p = p->sig;
        }
        cout << "  Facultad " << left << setw(30) << f->nombre
             << " -> nomina mensual: $ " << fixed << setprecision(0) << subtotalFac << "\n";
        f = f->sig;
    }

    linea();
    cout << "  Total de profesores en la universidad: " << cuentaProf << "\n";
    cout << fixed << setprecision(0);
    cout << "  NOMINA MENSUAL TOTAL (bruta)           : $ " << totalMensual << "\n";
    cout << "  NOMINA ANUAL TOTAL (bruta, x12)         : $ " << totalAnual << "\n";
    cout << "  COSTO ANUAL TOTAL PARA LA UNIVERSIDAD   : $ " << totalCostoAnualUniv
         << "  (incluye prestaciones sociales)\n";
}

// Recorre TODA la estructura buscando estudiantes con promedio < UMBRAL_EBRA
void reporteEstudiantesEnEBRA() {
    titulo("ESTUDIANTES EN EBRA (Bajo Rendimiento Academico) - TODA LA UNIVERSIDAD");
    int encontrados = 0;
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                double prom = calcularPromedio(e);
                if (prom >= 0 && prom < UMBRAL_EBRA) {
                    cout << "  [ALERTA] " << left << setw(25) << e->nombre
                         << " (" << e->codigo << ")  Programa: " << setw(25) << p->nombre
                         << " Promedio: " << fixed << setprecision(2) << prom << "\n";
                    encontrados++;
                }
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    if (encontrados == 0) cout << "  No hay estudiantes en EBRA actualmente.\n";
    else cout << "\n  Total de estudiantes en EBRA: " << encontrados << "\n";
}

// Recorrido jerarquico completo: facultad -> programa -> cursos/estudiantes/profesores
void reporteArbolCompletoUniversidad() {
    titulo("ARBOL COMPLETO DE LA UNIVERSIDAD (recorrido de todas las listas)");
    if (cabezaFacultades == nullptr) { msgVacio("facultades"); return; }
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        cout << "\nFACULTAD: " << f->nombre << " [" << f->codigo << "] "
             << (f->activo ? "(Activa)" : "(Inactiva)") << "\n";
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            cout << "  PROGRAMA: " << p->nombre << " [" << p->codigo << "] "
             << (p->activo ? "(Activo)" : "(Inactivo)") << "\n";

            cout << "    Cursos:\n";
            Curso* c = p->listaCursos;
            if (c == nullptr) msgVacio("cursos");
            while (c != nullptr) {
                cout << "      - " << c->nombre << " [" << c->codigo << "] ("
                     << c->creditos << " creditos)\n";
                c = c->sig;
            }

            cout << "    Profesores:\n";
            Profesor* d = p->listaProfesores;
            if (d == nullptr) msgVacio("profesores");
            while (d != nullptr) {
                cout << "      - " << d->nombre << " [" << d->codigo << "] "
                     << nombreTipoContrato(d->nomina.tipoContrato) << "/"
                     << nombreCategoria(d->nomina.categoria) << "\n";
                d = d->sig;
            }

            cout << "    Estudiantes:\n";
            Estudiante* e = p->listaEstudiantes;
            if (e == nullptr) msgVacio("estudiantes");
            while (e != nullptr) {
                double prom = calcularPromedio(e);
                cout << "      - " << e->nombre << " [" << e->codigo << "] promedio: ";
                if (prom < 0) cout << "N/A"; else cout << fixed << setprecision(2) << prom;
                cout << "\n";
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
}

// Recorre todos los profesores de la universidad y los agrupa/cuenta por categoria
void reporteProfesoresPorCategoria() {
    titulo("PROFESORES POR CATEGORIA Y TIPO DE CONTRATO (recorrido y conteo)");
    int porCategoria[4] = {0,0,0,0};
    int porContrato[3] = {0,0,0};
    int totalProfesores = 0;

    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                porCategoria[d->nomina.categoria]++;
                porContrato[d->nomina.tipoContrato]++;
                totalProfesores++;
                d = d->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }

    cout << "  Total de profesores: " << totalProfesores << "\n\n";
    cout << "  Por categoria:\n";
    cout << "    Auxiliar : " << porCategoria[AUXILIAR]  << "\n";
    cout << "    Asistente: " << porCategoria[ASISTENTE] << "\n";
    cout << "    Asociado : " << porCategoria[ASOCIADO]  << "\n";
    cout << "    Titular  : " << porCategoria[TITULAR]   << "\n";
    cout << "\n  Por tipo de contrato:\n";
    cout << "    Planta     : " << porContrato[PLANTA]      << "\n";
    cout << "    Ocasional  : " << porContrato[OCASIONAL]   << "\n";
    cout << "    Catedratico: " << porContrato[CATEDRATICO] << "\n";
}

// ======================================================================
// 18-B. NOMINA DE ADMINISTRATIVOS (mensual y anual) - MISMO MODELO QUE DOCENTES
// ======================================================================
double calcularNetoMensualAdministrativo(Administrativo* a) {
    if (a == nullptr) return 0.0;
    return static_cast<double>(liquidarAdministrativo(a, DIAS_MES_NOMINA).netSalary);
}

double calcularSalarioAnualBrutoAdministrativo(Administrativo* a) {
    if (a == nullptr) return 0.0;
    return static_cast<double>(liquidarAdministrativo(a, DIAS_MES_NOMINA).baseSalary) * MESES_ANIO;
}

double calcularSalarioAnualNetoAdministrativo(Administrativo* a) {
    return calcularNetoMensualAdministrativo(a) * MESES_ANIO;
}

void reporteNominaAdministrativoIndividual() {
    titulo("NOMINA DE UN ADMINISTRATIVO (mensual y anual)");
    string cod = leerLinea("Codigo del administrativo: ");
    Administrativo* a = buscarAdministrativo(cod);
    if (a == nullptr) { msgError("No existe ese administrativo."); return; }
    cout << fixed << setprecision(2);
    cout << "\n  Administrativo: " << a->nombre << " [" << a->codigo << "]\n";
    cout << "  Cargo: " << a->cargo << "   Contrato: " << a->tipoContrato << "\n";
    linea();
    const auto result = liquidarAdministrativo(a, DIAS_MES_NOMINA);
    cout << "  Salario mensual BRUTO : $ " << result.baseSalary << "\n";
    cout << "  (-) Salud             : $ " << result.employeeHealth << "\n";
    cout << "  (-) Pension           : $ " << result.employeePension << "\n";
    cout << "  Salario mensual NETO  : $ " << result.netSalary << "\n";
    linea();
    cout << "  SALARIO ANUAL BRUTO (x12): $ " << calcularSalarioAnualBrutoAdministrativo(a) << "\n";
    cout << "  SALARIO ANUAL NETO (x12) : $ " << calcularSalarioAnualNetoAdministrativo(a) << "\n";
}

// Recorre TODA la lista de administrativos sumando su nomina mensual y anual
void reporteNominaTotalAdministrativos() {
    titulo("NOMINA TOTAL DEL PERSONAL ADMINISTRATIVO (recorrido de lista)");
    if (cabezaAdministrativos == nullptr) { msgVacio("administrativos"); return; }
    double totalMensual = 0, totalAnual = 0;
    int cuenta = 0;
    cout << left << setw(8) << "CODIGO" << setw(24) << "NOMBRE" << setw(16) << "MENSUAL BRUTO"
         << setw(16) << "ANUAL BRUTO" << "\n";
    linea();
    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) {
        double anual = calcularSalarioAnualBrutoAdministrativo(a);
        cout << left << setw(8) << a->codigo << setw(24) << a->nombre
             << fixed << setprecision(0) << setw(16) << a->salarioBase << setw(16) << anual << "\n";
        totalMensual += a->salarioBase;
        totalAnual += anual;
        cuenta++;
        a = a->sig;
    }
    linea();
    cout << "  Total administrativos: " << cuenta << "\n";
    cout << fixed << setprecision(0);
    cout << "  NOMINA MENSUAL TOTAL ADMINISTRATIVOS: $ " << totalMensual << "\n";
    cout << "  NOMINA ANUAL TOTAL ADMINISTRATIVOS  : $ " << totalAnual << "\n";
}

// ======================================================================
// 18-C. EXTREMOS: MAYOR/MENOR SALARIO Y MEJOR/PEOR PROMEDIO (recorrido completo)
// ======================================================================
// Recorre facultades -> programas -> profesores buscando el salario mas alto y mas bajo
void reporteProfesorMayorMenorSalario() {
    titulo("PROFESOR CON MAYOR Y MENOR SALARIO (recorrido de toda la universidad)");
    Profesor* mayor = nullptr; Profesor* menor = nullptr;
    double salarioMayor = -1, salarioMenor = -1;

    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                double s = calcularSalarioMensualBruto(d);
                if (mayor == nullptr || s > salarioMayor) { mayor = d; salarioMayor = s; }
                if (menor == nullptr || s < salarioMenor) { menor = d; salarioMenor = s; }
                d = d->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }

    if (mayor == nullptr) { msgVacio("profesores"); return; }
    cout << fixed << setprecision(0);
    cout << "  MAYOR SALARIO: " << mayor->nombre << " [" << mayor->codigo << "] -> $ "
         << salarioMayor << " /mes ($ " << salarioMayor * MESES_ANIO << " /anio)\n";
    cout << "  MENOR SALARIO: " << menor->nombre << " [" << menor->codigo << "] -> $ "
         << salarioMenor << " /mes ($ " << salarioMenor * MESES_ANIO << " /anio)\n";
}

// Recorre facultades -> programas -> estudiantes buscando el mejor y el peor promedio
void reporteEstudianteMejorPeorPromedio() {
    titulo("ESTUDIANTE CON MEJOR Y PEOR PROMEDIO (recorrido de toda la universidad)");
    Estudiante* mejor = nullptr; Estudiante* peor = nullptr;
    double promMejor = -1, promPeor = -1;

    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                double prom = calcularPromedio(e);
                if (prom >= 0) { // solo cuenta si tiene al menos una nota
                    if (mejor == nullptr || prom > promMejor) { mejor = e; promMejor = prom; }
                    if (peor  == nullptr || prom < promPeor)  { peor  = e; promPeor  = prom; }
                }
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }

    if (mejor == nullptr) { msgVacio("estudiantes con notas"); return; }
    cout << fixed << setprecision(2);
    cout << "  MEJOR PROMEDIO: " << mejor->nombre << " [" << mejor->codigo << "] -> " << promMejor << "\n";
    cout << "  PEOR PROMEDIO : " << peor->nombre  << " [" << peor->codigo  << "] -> " << promPeor  << "\n";
}

// ======================================================================
// 18-D. ORDENAMIENTO DE UNA LISTA ENLAZADA (burbuja intercambiando DATOS)
// ======================================================================
// Ordena la lista de profesores de UN programa por su salario mensual.
// Se intercambian los CAMPOS de los nodos (no los punteros 'sig'), que es
// la forma mas sencilla y la que normalmente se pide en el examen.
void ordenarProfesoresPorSalario() {
    titulo("ORDENAR PROFESORES DE UN PROGRAMA POR SALARIO");
    Programa* p = seleccionarProgramaPorCodigo();
    if (p == nullptr) return;
    if (p->listaProfesores == nullptr || p->listaProfesores->sig == nullptr) {
        msgAdvert("El programa tiene 0 o 1 profesor, no hay nada que ordenar.");
        return;
    }
    bool descendente = leerSiNo("?Ordenar de mayor a menor salario? (s = descendente / n = ascendente): ");

    bool huboIntercambio;
    do {
        huboIntercambio = false;
        Profesor* actual = p->listaProfesores;
        while (actual->sig != nullptr) {
            double sActual = calcularSalarioMensualBruto(actual);
            double sSiguiente = calcularSalarioMensualBruto(actual->sig);
            bool debeIntercambiar = descendente ? (sActual < sSiguiente) : (sActual > sSiguiente);
            if (debeIntercambiar) {
                Profesor* siguiente = actual->sig;
                Profesor* sigSiguiente = siguiente->sig;

                // Intercambio completo del struct Profesor (preservando los enlaces estructurales)
                std::swap(*actual, *siguiente);

                // Restaura los punteros sig a sus posiciones estructurales correctas
                actual->sig = siguiente;
                siguiente->sig = sigSiguiente;

                huboIntercambio = true;
            }
            actual = actual->sig;
        }
    } while (huboIntercambio);

    msgOk("Lista ordenada. Resultado:");
    listarProfesores(); // reutiliza el listado ya existente (pedira de nuevo el codigo del programa)
}

// ======================================================================
// 18-E. BUSQUEDA POR DOCUMENTO / CEDULA (campo alterno al codigo)
// ======================================================================
Estudiante* buscarEstudiantePorDocumento(const string &doc, Programa** progOut) {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                if (e->documento == doc) {
                    if (progOut != nullptr) *progOut = p;
                    return e;
                }
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    if (progOut != nullptr) *progOut = nullptr;
    return nullptr;
}

Profesor* buscarProfesorPorDocumento(const string &doc, Programa** progOut) {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                if (d->documento == doc) {
                    if (progOut != nullptr) *progOut = p;
                    return d;
                }
                d = d->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    if (progOut != nullptr) *progOut = nullptr;
    return nullptr;
}

void buscarPorDocumento() {
    titulo("BUSCAR ESTUDIANTE O PROFESOR POR DOCUMENTO");
    string doc = leerLinea("Numero de documento a buscar: ");

    Programa* progE = nullptr;
    Estudiante* e = buscarEstudiantePorDocumento(doc, &progE);
    if (e != nullptr) {
        msgOk("ESTUDIANTE encontrado: " + e->nombre + " [" + e->codigo + "] - Programa: " + progE->nombre);
    }

    Programa* progD = nullptr;
    Profesor* d = buscarProfesorPorDocumento(doc, &progD);
    if (d != nullptr) {
        msgOk("PROFESOR encontrado: " + d->nombre + " [" + d->codigo + "] - Programa: " + progD->nombre);
    }

    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) {
        if (a->documento == doc) {
            msgOk("ADMINISTRATIVO encontrado: " + a->nombre + " [" + a->codigo + "]");
            break;
        }
        a = a->sig;
    }

    if (e == nullptr && d == nullptr && a == nullptr)
        msgError("No se encontro ninguna persona con ese documento.");
}

// ======================================================================
// 18-F. CENSO GENERAL (conteo total recorriendo TODA la estructura anidada)
// ======================================================================
void reporteCensoGeneral() {
    titulo("CENSO GENERAL DE LA UNIVERSIDAD (recorrido completo)");
    int numFacultades = 0, numProgramas = 0, numCursos = 0, numEstudiantes = 0, numProfesores = 0;

    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        numFacultades++;
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            numProgramas++;
            Curso* c = p->listaCursos;
            while (c != nullptr) { numCursos++; c = c->sig; }
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) { numEstudiantes++; e = e->sig; }
            Profesor* d = p->listaProfesores;
            while (d != nullptr) { numProfesores++; d = d->sig; }
            p = p->sig;
        }
        f = f->sig;
    }

    int numAdministrativos = 0;
    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) { numAdministrativos++; a = a->sig; }

    cout << "  Facultades      : " << numFacultades << "\n";
    cout << "  Programas       : " << numProgramas << "\n";
    cout << "  Cursos          : " << numCursos << "\n";
    cout << "  Estudiantes     : " << numEstudiantes << "\n";
    cout << "  Profesores      : " << numProfesores << "\n";
    cout << "  Administrativos : " << numAdministrativos << "\n";
}

// ======================================================================
// 19. PERSISTENCIA (guardar / cargar TODA la estructura en un archivo)
// ======================================================================
// Formato de texto con secciones delimitadas y campos separados por '|'.
// El orden de las secciones importa al cargar: Facultades -> Programas ->
// Cursos -> Estudiantes -> Matriculas -> Profesores.

void guardarDatos() {
    string ARCHIVO_TEMP = ARCHIVO_DATOS + ".tmp";
    ofstream archivo(ARCHIVO_TEMP);
    if (!archivo.is_open()) {
        msgError("No se pudo abrir el archivo para escritura.");
        return;
    }
    archivo << fixed << setprecision(2); // evita notacion cientifica en los numeros guardados

    archivo << "#FACULTADES\n";
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        archivo << f->codigo << "|" << f->nombre << "|" << f->activo << "\n";
        f = f->sig;
    }
    archivo << "#FIN_FACULTADES\n";

    archivo << "#PROGRAMAS\n";
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            archivo << p->codigo << "|" << f->codigo << "|" << p->nombre << "|" << (int)p->tipo << "|" << p->activo << "\n";
            p = p->sig;
        }
        f = f->sig;
    }
    archivo << "#FIN_PROGRAMAS\n";

    archivo << "#CURSOS\n";
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Curso* c = p->listaCursos;
            while (c != nullptr) {
                archivo << c->codigo << "|" << p->codigo << "|" << c->nombre << "|"
                         << c->creditos << "|" << c->activo << "\n";
                c = c->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    archivo << "#FIN_CURSOS\n";

    archivo << "#ESTUDIANTES\n";
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                archivo << e->codigo << "|" << p->codigo << "|" << e->nombre << "|"
                         << e->documento << "|" << e->email << "|" << e->categoria << "|"
                         << e->activo << "\n";
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    archivo << "#FIN_ESTUDIANTES\n";

    archivo << "#MATRICULAS\n";
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Estudiante* e = p->listaEstudiantes;
            while (e != nullptr) {
                Nota* n = e->cursosMatriculados;
                while (n != nullptr) {
                    archivo << e->codigo << "|" << n->codigoCurso << "|" << n->nombreCurso << "|"
                             << n->valor << "|" << n->cancelado << "\n";
                    n = n->sig;
                }
                e = e->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    archivo << "#FIN_MATRICULAS\n";

    archivo << "#PROFESORES\n";
    f = cabezaFacultades;
    while (f != nullptr) {
        Programa* p = f->listaProgramas;
        while (p != nullptr) {
            Profesor* d = p->listaProfesores;
            while (d != nullptr) {
                archivo << d->codigo << "|" << p->codigo << "|" << d->nombre << "|"
                         << d->documento << "|" << d->email << "|"
                         << (int)d->nomina.tipoContrato << "|" << (int)d->nomina.categoria << "|"
                         << d->nomina.puntosTitulo << "|" << d->nomina.puntosExperiencia << "|"
                         << d->nomina.puntosProductividad << "|" << d->nomina.horasCatedraMes << "|"
                         << d->activo << "|" << d->fechaIngreso << "|" << d->fechaRetiro << "|"
                         << d->tipoVinculacion << "|" << d->estadoLaboral << "|" << d->tipoSalario << "|"
                         << d->claseRiesgoARL << "|" << d->configuracionSeguridadSocial << "|"
                         << d->diasLaborados << "|" << d->salarioBase << "|" << d->tarifaHora << "|"
                         << d->diasServicioContinuo << "\n";
                d = d->sig;
            }
            p = p->sig;
        }
        f = f->sig;
    }
    archivo << "#FIN_PROFESORES\n";

    archivo << "#ADMINISTRATIVOS\n";
    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) {
        archivo << a->codigo << "|" << a->nombre << "|" << a->documento << "|" << a->cargo << "|"
             << a->tipoContrato << "|" << a->salarioBase << "|" << a->activo << "|"
             << a->fechaIngreso << "|" << a->fechaRetiro << "|" << a->tipoVinculacion << "|"
             << a->estadoLaboral << "|" << a->tipoSalario << "|" << a->claseRiesgoARL << "|"
             << a->configuracionSeguridadSocial << "|" << a->diasLaborados << "|"
             << a->diasServicioContinuo << "\n";
        a = a->sig;
    }
    archivo << "#FIN_ADMINISTRATIVOS\n";

    archivo << "#CONTADORES\n";
    archivo << contF << "|" << contP << "|" << contC << "|" << contE << "|" << contD << "|" << contA << "\n";
    archivo << "#FIN_CONTADORES\n";

    pita::payroll::savePayrollCycleSections(archivo, cicloNominaFormal);

    archivo.close();
    try {
        std::filesystem::rename(ARCHIVO_TEMP, ARCHIVO_DATOS);
        msgOk("Datos guardados correctamente en '" + ARCHIVO_DATOS + "'.");
    } catch (const std::filesystem::filesystem_error &) {
        msgError("No se pudo reemplazar el archivo de datos. Tus datos estan en " + ARCHIVO_TEMP);
    }
}

// separa una linea por '|'
void separarCampos(const string &linea, string campos[], int maxCampos) {
    for (int i = 0; i < maxCampos; i++) campos[i] = "";
    stringstream ss(linea);
    string item;
    int i = 0;
    while (getline(ss, item, '|') && i < maxCampos) {
        campos[i] = item;
        i++;
    }
}

void cargarDatos() {
    ifstream archivo(ARCHIVO_DATOS);
    if (!archivo.is_open()) {
        msgAdvert("No se encontro el archivo '" + ARCHIVO_DATOS + "'. Se iniciara sin datos.");
        return;
    }

    try {
        liberarTodaLaMemoria(); // limpiar lo que hubiera en memoria antes de cargar

    int warningCount = 0;
    string linea;
    string seccion = "";
    while (getline(archivo, linea)) {
        if (linea.empty()) continue;
        if (linea[0] == '#') {
            seccion = linea;
            continue;
        }
        string campos[MAX_CAMPOS_CSV];

        if (seccion == "#FACULTADES") {
            separarCampos(linea, campos, 3);
            Facultad* nueva = new Facultad();
            nueva->codigo = campos[0];
            nueva->nombre = campos[1];
            nueva->activo = (campos[2] == "1");
            nueva->listaProgramas = nullptr;
            nueva->sig = nullptr;
            if (cabezaFacultades == nullptr) cabezaFacultades = nueva;
            else {
                Facultad* act = cabezaFacultades;
                while (act->sig != nullptr) act = act->sig;
                act->sig = nueva;
            }
        } else if (seccion == "#PROGRAMAS") {
            separarCampos(linea, campos, 5);
            Facultad* f = buscarFacultad(campos[1]);
            if (f != nullptr) {
                Programa* nuevo = new Programa();
                nuevo->codigo = campos[0];
                nuevo->nombre = campos[2];
                try {
                    nuevo->tipo = tipoProgramaDesdeInt(stoi(campos[3]));
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                nuevo->activo = (campos[4] == "1");
                nuevo->listaCursos = nullptr;
                nuevo->listaEstudiantes = nullptr;
                nuevo->listaProfesores = nullptr;
                nuevo->sig = nullptr;
                if (f->listaProgramas == nullptr) f->listaProgramas = nuevo;
                else {
                    Programa* act = f->listaProgramas;
                    while (act->sig != nullptr) act = act->sig;
                    act->sig = nuevo;
                }
            } else {
                warningCount++;
                msgAdvert("No se encontro el padre \"" + campos[1] + "\" para el registro \"" + linea + "\". Se omite.");
            }
        } else if (seccion == "#CURSOS") {
            separarCampos(linea, campos, 5);
            Programa* p = buscarProgramaGlobal(campos[1], nullptr);
            if (p != nullptr) {
                Curso* nuevo = new Curso();
                nuevo->codigo = campos[0];
                nuevo->nombre = campos[2];
                try {
                    nuevo->creditos = stoi(campos[3]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                nuevo->activo = (campos[4] == "1");
                nuevo->sig = nullptr;
                if (p->listaCursos == nullptr) p->listaCursos = nuevo;
                else {
                    Curso* act = p->listaCursos;
                    while (act->sig != nullptr) act = act->sig;
                    act->sig = nuevo;
                }
            } else {
                warningCount++;
                msgAdvert("No se encontro el padre \"" + campos[1] + "\" para el registro \"" + linea + "\". Se omite.");
            }
        } else if (seccion == "#ESTUDIANTES") {
            separarCampos(linea, campos, 7);
            Programa* p = buscarProgramaGlobal(campos[1], nullptr);
            if (p != nullptr) {
                Estudiante* nuevo = new Estudiante();
                nuevo->codigo = campos[0];
                nuevo->nombre = campos[2];
                nuevo->documento = campos[3];
                nuevo->email = campos[4];
                nuevo->categoria = campos[5];
                nuevo->activo = (campos[6] == "1");
                nuevo->cursosMatriculados = nullptr;
                nuevo->sig = nullptr;
                if (p->listaEstudiantes == nullptr) p->listaEstudiantes = nuevo;
                else {
                    Estudiante* act = p->listaEstudiantes;
                    while (act->sig != nullptr) act = act->sig;
                    act->sig = nuevo;
                }
            } else {
                warningCount++;
                msgAdvert("No se encontro el padre \"" + campos[1] + "\" para el registro \"" + linea + "\". Se omite.");
            }
        } else if (seccion == "#MATRICULAS") {
            separarCampos(linea, campos, 5);
            Estudiante* e = buscarEstudianteGlobal(campos[0], nullptr, nullptr);
            if (e != nullptr) {
                Nota* nueva = new Nota();
                nueva->codigoCurso = campos[1];
                nueva->nombreCurso = campos[2];
                try {
                    nueva->valor = stof(campos[3]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                nueva->cancelado = (campos[4] == "1");
                nueva->sig = nullptr;
                if (e->cursosMatriculados == nullptr) e->cursosMatriculados = nueva;
                else {
                    Nota* act = e->cursosMatriculados;
                    while (act->sig != nullptr) act = act->sig;
                    act->sig = nueva;
                }
            } else {
                warningCount++;
                msgAdvert("No se encontro el padre \"" + campos[0] + "\" para el registro \"" + linea + "\". Se omite.");
            }
        } else if (seccion == "#PROFESORES") {
            separarCampos(linea, campos, CAMPOS_PROFESOR);
            Programa* p = buscarProgramaGlobal(campos[1], nullptr);
            if (p != nullptr) {
                Profesor* nuevo = new Profesor();
                nuevo->codigo = campos[0];
                nuevo->nombre = campos[2];
                nuevo->documento = campos[3];
                nuevo->email = campos[4];
                try {
                    nuevo->nomina.tipoContrato = contratoDesdeInt(stoi(campos[5]));
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                try {
                    nuevo->nomina.categoria = categoriaDesdeInt(stoi(campos[6]));
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                try {
                    nuevo->nomina.puntosTitulo = stoi(campos[7]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                try {
                    nuevo->nomina.puntosExperiencia = stoi(campos[8]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                try {
                    nuevo->nomina.puntosProductividad = stoi(campos[9]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                try {
                    nuevo->nomina.horasCatedraMes = stoi(campos[10]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
                nuevo->activo = (campos[11] == "1");
                if (!campos[12].empty()) nuevo->fechaIngreso = campos[12];
                if (!campos[13].empty()) nuevo->fechaRetiro = campos[13];
                if (!campos[14].empty()) nuevo->tipoVinculacion = campos[14];
                if (!campos[15].empty()) nuevo->estadoLaboral = campos[15];
                if (!campos[16].empty()) nuevo->tipoSalario = campos[16];
                if (!campos[17].empty()) nuevo->claseRiesgoARL = campos[17];
                if (!campos[18].empty()) nuevo->configuracionSeguridadSocial = campos[18];
                if (!campos[19].empty()) {
                    try {
                        nuevo->diasLaborados = stoi(campos[19]);
                    } catch (const std::exception& e) {
                        msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                        continue;
                    }
                }
                if (!campos[20].empty()) {
                    try {
                        nuevo->salarioBase = stod(campos[20]);
                    } catch (const std::exception& e) {
                        msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                        continue;
                    }
                }
                if (!campos[21].empty()) {
                    try {
                        nuevo->tarifaHora = stod(campos[21]);
                    } catch (const std::exception& e) {
                        msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                        continue;
                    }
                }
                if (!campos[22].empty()) {
                    try {
                        nuevo->diasServicioContinuo = stoi(campos[22]);
                    } catch (const std::exception& e) {
                        msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                        continue;
                    }
                }
                nuevo->sig = nullptr;
                if (p->listaProfesores == nullptr) p->listaProfesores = nuevo;
                else {
                    Profesor* act = p->listaProfesores;
                    while (act->sig != nullptr) act = act->sig;
                    act->sig = nuevo;
                }
            } else {
                warningCount++;
                msgAdvert("No se encontro el padre \"" + campos[1] + "\" para el registro \"" + linea + "\". Se omite.");
            }
        } else if (seccion == "#ADMINISTRATIVOS") {
            separarCampos(linea, campos, 16);
            Administrativo* nuevo = new Administrativo();
            nuevo->codigo = campos[0];
            nuevo->nombre = campos[1];
            nuevo->documento = campos[2];
            nuevo->cargo = campos[3];
            nuevo->tipoContrato = campos[4];
            try {
                nuevo->salarioBase = stod(campos[5]);
            } catch (const std::exception& e) {
                msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                continue;
            }
            nuevo->activo = (campos[6] == "1");
            if (!campos[7].empty()) nuevo->fechaIngreso = campos[7];
            if (!campos[8].empty()) nuevo->fechaRetiro = campos[8];
            if (!campos[9].empty()) nuevo->tipoVinculacion = campos[9];
            if (!campos[10].empty()) nuevo->estadoLaboral = campos[10];
            if (!campos[11].empty()) nuevo->tipoSalario = campos[11];
            if (!campos[12].empty()) nuevo->claseRiesgoARL = campos[12];
            if (!campos[13].empty()) nuevo->configuracionSeguridadSocial = campos[13];
            if (!campos[14].empty()) {
                try {
                    nuevo->diasLaborados = stoi(campos[14]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[15].empty()) {
                try {
                    nuevo->diasServicioContinuo = stoi(campos[15]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            nuevo->sig = nullptr;
            if (cabezaAdministrativos == nullptr) cabezaAdministrativos = nuevo;
            else {
                Administrativo* act = cabezaAdministrativos;
                while (act->sig != nullptr) act = act->sig;
                act->sig = nuevo;
            }
        } else if (seccion == "#CONTADORES") {
            separarCampos(linea, campos, 6);
            if (!campos[0].empty()) {
                try {
                    contF = stoi(campos[0]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[1].empty()) {
                try {
                    contP = stoi(campos[1]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[2].empty()) {
                try {
                    contC = stoi(campos[2]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[3].empty()) {
                try {
                    contE = stoi(campos[3]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[4].empty()) {
                try {
                    contD = stoi(campos[4]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
            if (!campos[5].empty()) {
                try {
                    contA = stoi(campos[5]);
                } catch (const std::exception& e) {
                    msgAdvert("Error al parsear campo en linea \"" + linea + "\". Se omite el registro.");
                    continue;
                }
            }
        }
    }
    archivo.clear();
    archivo.seekg(0);
    pita::payroll::loadPayrollCycleSections(archivo, cicloNominaFormal);
    archivo.close();

    // Recalibracion de contadores recorriendo los nodos cargados en memoria
    auto extraerNumeroCodigo = [](const string& codigo) -> int {
        if (codigo.empty()) return 0;
        size_t start = 0;
        while (start < codigo.size() && !isdigit(static_cast<unsigned char>(codigo[start]))) {
            start++;
        }
        if (start < codigo.size()) {
            try {
                return stoi(codigo.substr(start));
            } catch (...) {
                return 0;
            }
        }
        return 0;
    };

    Facultad* rf = cabezaFacultades;
    while (rf != nullptr) {
        contF = max(contF, extraerNumeroCodigo(rf->codigo));
        Programa* rp = rf->listaProgramas;
        while (rp != nullptr) {
            contP = max(contP, extraerNumeroCodigo(rp->codigo));
            Curso* rc = rp->listaCursos;
            while (rc != nullptr) {
                contC = max(contC, extraerNumeroCodigo(rc->codigo));
                rc = rc->sig;
            }
            Estudiante* re = rp->listaEstudiantes;
            while (re != nullptr) {
                contE = max(contE, extraerNumeroCodigo(re->codigo));
                re = re->sig;
            }
            Profesor* rd = rp->listaProfesores;
            while (rd != nullptr) {
                contD = max(contD, extraerNumeroCodigo(rd->codigo));
                rd = rd->sig;
            }
            rp = rp->sig;
        }
        rf = rf->sig;
    }

    Administrativo* ra = cabezaAdministrativos;
    while (ra != nullptr) {
        contA = max(contA, extraerNumeroCodigo(ra->codigo));
        ra = ra->sig;
    }

    msgOk("Contadores recalibrados: F=" + to_string(contF)
         + " P=" + to_string(contP)
         + " C=" + to_string(contC)
         + " E=" + to_string(contE)
         + " D=" + to_string(contD)
         + " A=" + to_string(contA));
    if (warningCount > 0) {
        msgAdvert("Se omitieron " + to_string(warningCount) + " registros por referencias de padre no encontradas. Revisa pita_datos.txt.");
    }
    msgOk("Datos cargados correctamente desde '" + ARCHIVO_DATOS + "'.");
    } catch (...) {
        if (archivo.is_open()) {
            archivo.close();
        }
        msgError("CRITICO: La carga de datos fue interrumpida. Se liberara la memoria parcialmente cargada para evitar estado corrupto.");
        liberarTodaLaMemoria();
        cabezaFacultades = nullptr;
        cabezaAdministrativos = nullptr;
    }
}

// ======================================================================
// 20. DATOS DE EJEMPLO (demuestra que se puede a?adir cualquier programa,
//     por ejemplo Medicina, sin modificar la estructura de datos)
// ======================================================================
void cargarDatosDeEjemplo() {
    // ---- Facultad de Ingenierias y Tecnologicas ----
    Facultad* fIng = new Facultad();
    fIng->codigo = generarCodigoFacultad();
    fIng->nombre = "Facultad de Ingenierias y Tecnologicas";
    fIng->activo = true; fIng->listaProgramas = nullptr; fIng->sig = nullptr;
    cabezaFacultades = fIng;

    Programa* pSis = new Programa();
    pSis->codigo = generarCodigoPrograma();
    pSis->nombre = "Ingenieria de Sistemas";
    pSis->tipo = INGENIERIA;
    pSis->activo = true;
    pSis->listaCursos = nullptr; pSis->listaEstudiantes = nullptr; pSis->listaProfesores = nullptr;
    pSis->sig = nullptr;
    fIng->listaProgramas = pSis;

    Curso* c1 = new Curso(); c1->codigo = generarCodigoCurso(); c1->nombre = "Estructura de Datos";
    c1->creditos = 4; c1->activo = true; c1->sig = nullptr;
    Curso* c2 = new Curso(); c2->codigo = generarCodigoCurso(); c2->nombre = "Programacion Orientada a Objetos";
    c2->creditos = 3; c2->activo = true; c2->sig = c1==nullptr?nullptr:nullptr;
    c1->sig = c2; c2->sig = nullptr;
    pSis->listaCursos = c1;

    Profesor* d1 = new Profesor();
    d1->codigo = generarCodigoProfesor(); d1->nombre = "Adith Perez"; d1->documento = "1065800000";
    d1->email = "adithperez@unicesar.edu.co"; d1->activo = true;
    d1->nomina.tipoContrato = PLANTA; d1->nomina.categoria = ASOCIADO;
    d1->nomina.puntosTitulo = 900; d1->nomina.puntosExperiencia = 300; d1->nomina.puntosProductividad = 150;
    d1->nomina.horasCatedraMes = 0; d1->sig = nullptr;
    pSis->listaProfesores = d1;

    Estudiante* e1 = new Estudiante();
    e1->codigo = generarCodigoEstudiante(); e1->nombre = "Estudiante Ejemplo Uno";
    e1->documento = "1090000001"; e1->email = "est1@unicesar.edu.co"; e1->categoria = "Regular";
    e1->activo = true; e1->cursosMatriculados = nullptr; e1->sig = nullptr;
    pSis->listaEstudiantes = e1;

    // ---- Facultad de Ciencias de la Salud (con Medicina) ----
    Facultad* fSalud = new Facultad();
    fSalud->codigo = generarCodigoFacultad();
    fSalud->nombre = "Facultad de Ciencias de la Salud";
    fSalud->activo = true; fSalud->listaProgramas = nullptr; fSalud->sig = nullptr;
    fIng->sig = fSalud;

    Programa* pMed = new Programa();
    pMed->codigo = generarCodigoPrograma();
    pMed->nombre = "Medicina";
    pMed->tipo = MEDICINA;
    pMed->activo = true;
    pMed->listaCursos = nullptr; pMed->listaEstudiantes = nullptr; pMed->listaProfesores = nullptr;
    pMed->sig = nullptr;
    fSalud->listaProgramas = pMed;

    Programa* pEnf = new Programa();
    pEnf->codigo = generarCodigoPrograma();
    pEnf->nombre = "Enfermeria";
    pEnf->tipo = ENFERMERIA;
    pEnf->activo = true;
    pEnf->listaCursos = nullptr; pEnf->listaEstudiantes = nullptr; pEnf->listaProfesores = nullptr;
    pEnf->sig = nullptr;
    pMed->sig = pEnf;

    Curso* cm1 = new Curso(); cm1->codigo = generarCodigoCurso(); cm1->nombre = "Anatomia Humana I";
    cm1->creditos = 5; cm1->activo = true; cm1->sig = nullptr;
    pMed->listaCursos = cm1;

    Curso* ce1 = new Curso(); ce1->codigo = generarCodigoCurso(); ce1->nombre = "Fundamentos de Enfermeria";
    ce1->creditos = 4; ce1->activo = true; ce1->sig = nullptr;
    pEnf->listaCursos = ce1;

    Profesor* dm1 = new Profesor();
    dm1->codigo = generarCodigoProfesor(); dm1->nombre = "Doctora Ejemplo Medicina";
    dm1->documento = "1065900000"; dm1->email = "docmedicina@unicesar.edu.co"; dm1->activo = true;
    dm1->nomina.tipoContrato = CATEDRATICO; dm1->nomina.categoria = TITULAR;
    dm1->nomina.puntosTitulo = 0; dm1->nomina.puntosExperiencia = 0; dm1->nomina.puntosProductividad = 0;
    dm1->nomina.horasCatedraMes = 60; dm1->sig = nullptr;
    pMed->listaProfesores = dm1;

    Estudiante* em1 = new Estudiante();
    em1->codigo = generarCodigoEstudiante(); em1->nombre = "Estudiante Ejemplo Medicina";
    em1->documento = "1090000002"; em1->email = "estmed@unicesar.edu.co"; em1->categoria = "Regular";
    em1->activo = true; em1->cursosMatriculados = nullptr; em1->sig = nullptr;
    pMed->listaEstudiantes = em1;

    // ---- Administrativo de ejemplo ----
    Administrativo* a1 = new Administrativo();
    a1->codigo = generarCodigoAdministrativo(); a1->nombre = "Administrativo Ejemplo";
    a1->documento = "1065700000"; a1->cargo = "Secretario Academico";
    a1->tipoContrato = "Planta"; a1->salarioBase = 2500000; a1->activo = true; a1->sig = nullptr;
    cabezaAdministrativos = a1;

    msgOk("Datos de ejemplo cargados (incluye Medicina, Enfermeria y otras carreras del area de salud).");
}

// ======================================================================
// 21. LIBERACION TOTAL DE MEMORIA (evita fugas al salir o recargar)
// ======================================================================
void liberarTodaLaMemoria() {
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Facultad* tmpF = f;
        f = f->sig;
        Programa* p = tmpF->listaProgramas;
        while (p != nullptr) { Programa* tmpP = p; p = p->sig; liberarPrograma(tmpP); }
        delete tmpF;
    }
    cabezaFacultades = nullptr;

    Administrativo* a = cabezaAdministrativos;
    while (a != nullptr) { Administrativo* tmp = a; a = a->sig; delete tmp; }
    cabezaAdministrativos = nullptr;

    cicloNominaFormal.clear();
}

// ======================================================================
// 21-B. FUNCIONES AUXILIARES DE MENSAJERIA
// ======================================================================
void msgError(const string& msg)    { cout << ">> ERROR: " << msg << "\n"; }
void msgAdvert(const string& msg)   { cout << ">> ADVERTENCIA: " << msg << "\n"; }
void msgOk(const string& msg)       { cout << ">> " << msg << "\n"; }
void msgVacio(const string& entidad){ cout << "(No hay " << entidad << " registrados)\n"; }

// ======================================================================
// 22. MENUS
// ======================================================================
const pita::payroll::PayrollRunRecord* buscarRunFormal(const string& periodId) {
    for (const auto& run : cicloNominaFormal.runs()) {
        if (run.periodId == periodId) return &run;
    }
    return nullptr;
}

const pita::payroll::PayrollPeriodRecord* buscarPeriodoFormal(const string& periodId) {
    for (const auto& period : cicloNominaFormal.periods()) {
        if (period.periodId == periodId) return &period;
    }
    return nullptr;
}

const pita::payroll::PayrollResult* buscarDetalleFormal(
    const pita::payroll::PayrollRunRecord* run, const string& employeeId) {
    if (run == nullptr) return nullptr;
    for (const auto& detail : run->details) {
        if (detail.employeeId == employeeId) return &detail;
    }
    return nullptr;
}

void listarPeriodosFormales() {
    titulo("NOMINA - PERIODOS");
    if (cicloNominaFormal.periods().empty()) {
        msgVacio("periodos");
        return;
    }
    for (const auto& period : cicloNominaFormal.periods()) {
        cout << "  " << period.periodId << " | " << period.startDate << " a "
             << period.endDate << " | estado: " << static_cast<int>(period.status) << "\n";
    }
}

string nombreEstadoPeriodo(pita::payroll::PeriodStatus status) {
    switch (status) {
        case pita::payroll::PeriodStatus::OPEN: return "ABIERTO";
        case pita::payroll::PeriodStatus::CALCULATED: return "CALCULADO";
        case pita::payroll::PeriodStatus::APPROVED: return "APROBADO";
        case pita::payroll::PeriodStatus::CLOSED: return "CERRADO";
        case pita::payroll::PeriodStatus::CANCELLED: return "CANCELADO";
    }
    return "DESCONOCIDO";
}

string nombreEstadoRun(pita::payroll::RunStatus status) {
    switch (status) {
        case pita::payroll::RunStatus::CALCULATED: return "CALCULADO";
        case pita::payroll::RunStatus::APPROVED: return "APROBADO";
        case pita::payroll::RunStatus::CLOSED: return "CERRADO";
        case pita::payroll::RunStatus::CANCELLED: return "CANCELADO";
    }
    return "DESCONOCIDO";
}

vector<pita::payroll::PayrollEmployee> empleadosFormales() {
    vector<pita::payroll::PayrollEmployee> employees;
    Facultad* f = cabezaFacultades;
    while (f != nullptr) {
        Programa* program = f->listaProgramas;
        while (program != nullptr) {
            Profesor* professor = program->listaProfesores;
            while (professor != nullptr) {
                if (professor->activo) {
                    if (professor->configuracionSeguridadSocial.empty() || professor->claseRiesgoARL != "I")
                        throw invalid_argument("el profesor " + professor->codigo + " no tiene ARL/seguridad social configurada");
                    pita::payroll::PayrollEmployee employee = crearEntradaNomina(professor);
                    if (pita::payroll::salaryBase(employee) <= 0)
                        throw invalid_argument("el profesor " + professor->codigo + " no tiene salario valido");
                    employees.push_back(employee);
                }
                professor = professor->sig;
            }
            program = program->sig;
        }
        f = f->sig;
    }
    Administrativo* administrative = cabezaAdministrativos;
    while (administrative != nullptr) {
        if (administrative->activo) {
            if (administrative->configuracionSeguridadSocial.empty() || administrative->claseRiesgoARL != "I")
                throw invalid_argument("el administrativo " + administrative->codigo + " no tiene ARL/seguridad social configurada");
            pita::payroll::PayrollEmployee employee = crearEntradaNomina(administrative);
            if (pita::payroll::salaryBase(employee) <= 0)
                throw invalid_argument("el administrativo " + administrative->codigo + " no tiene salario valido");
            employees.push_back(employee);
        }
        administrative = administrative->sig;
    }
    return employees;
}

void crearPeriodoFormal() {
    titulo("NOMINA - CREAR PERIODO");
    const string periodId = leerLinea("Identificador del periodo (ej. 2026-09): ");
    const int year = leerEntero("Anio: ");
    const int month = leerEntero("Mes (1-12): ");
    const string startDate = leerLinea("Fecha inicial (YYYY-MM-DD): ");
    const string endDate = leerLinea("Fecha final (YYYY-MM-DD): ");
    try {
        cicloNominaFormal.createPeriod(periodId, year, month, startDate, endDate, "console");
        msgOk("Periodo creado correctamente.");
    } catch (const exception& error) {
        msgError("No se pudo crear el periodo: " + string(error.what()));
    }
}

void calcularNominaFormal() {
    titulo("NOMINA - CALCULAR");
    const string periodId = leerLinea("Identificador del periodo: ");
    if (buscarPeriodoFormal(periodId) == nullptr) {
        msgError("El periodo no existe.");
        return;
    }
    try {
        const auto employees = empleadosFormales();
        const auto run = cicloNominaFormal.calculateRun(periodId, employees, pita::payroll::PayrollRules{}, "console");
        msgOk("Liquidacion creada: " + run.runId + " (" + to_string(run.details.size()) + " empleados).");
    } catch (const exception& error) {
        msgError("No se pudo calcular la nomina: " + string(error.what()));
    }
}

void consultarNominaFormal() {
    titulo("NOMINA - CONSULTAR LIQUIDACION");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* period = buscarPeriodoFormal(periodId);
    const auto* run = buscarRunFormal(periodId);
    if (period == nullptr || run == nullptr) {
        msgError("No existe una liquidacion para ese periodo.");
        return;
    }
    cout << "  Periodo: " << periodId << " | Estado: " << nombreEstadoPeriodo(period->status)
         << " | Liquidacion: " << nombreEstadoRun(run->status) << "\n";
    cout << left << setw(14) << "EMPLEADO" << setw(14) << "TIPO" << setw(14) << "DEVENGADO"
         << setw(14) << "DEDUCCIONES" << setw(14) << "IBC" << setw(14) << "NETO" << "\n";
    linea();
    for (const auto& detail : run->details) {
        cout << left << setw(14) << detail.employeeId << setw(14) << detail.employeeType
             << setw(14) << detail.grossSalary << setw(14) << detail.totalEmployeeDeductions
             << setw(14) << detail.ibc << setw(14) << detail.netSalary << "\n";
    }
}

void consultarProfesorFormal() {
    titulo("NOMINA - CONSULTAR PROFESOR");
    const string employeeId = leerLinea("Codigo del profesor: ");
    Profesor* professor = buscarProfesorGlobal(employeeId, nullptr, nullptr);
    if (professor == nullptr) {
        msgError("No existe ese profesor.");
        return;
    }
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* detail = buscarDetalleFormal(buscarRunFormal(periodId), employeeId);
    if (detail == nullptr) {
        msgError("El profesor no tiene liquidacion en ese periodo.");
        return;
    }
    cout << "  Profesor: " << professor->nombre << " [" << professor->codigo << "]\n";
    cout << "  Periodo: " << detail->period << " | Salario base: $ " << detail->baseSalary << "\n";
    cout << "  Devengado: $ " << detail->grossSalary << " | Deducciones: $ " << detail->totalEmployeeDeductions << "\n";
    cout << "  IBC: $ " << detail->ibc << " | Neto: $ " << detail->netSalary << "\n";
    cout << "  Aportes patronales: $ " << detail->totalEmployerContributions
         << " | Costo empleador: $ " << detail->totalEmployerCost << "\n";
}

bool empleadoFormalPorId(const string& employeeId, pita::payroll::PayrollEmployee& employee, string& name) {
    Profesor* professor = buscarProfesorGlobal(employeeId, nullptr, nullptr);
    if (professor != nullptr) {
        employee = crearEntradaNomina(professor);
        name = professor->nombre;
        return true;
    }
    Administrativo* administrative = buscarAdministrativo(employeeId);
    if (administrative != nullptr) {
        employee = crearEntradaNomina(administrative);
        name = administrative->nombre;
        return true;
    }
    return false;
}

void imprimirDesprendibleFormal(const string& periodId, const string& employeeId) {
    const auto* run = buscarRunFormal(periodId);
    const auto* period = buscarPeriodoFormal(periodId);
    const auto* detail = buscarDetalleFormal(run, employeeId);
    if (run == nullptr || period == nullptr || detail == nullptr) {
        msgError("No existe una liquidacion oficial para ese empleado y periodo.");
        return;
    }
    pita::payroll::PayrollEmployee employee;
    string name;
    if (!empleadoFormalPorId(employeeId, employee, name)) {
        msgError("El empleado no existe en las listas actuales.");
        return;
    }
    const auto payslip = pita::payroll::generatePayslip(
        employee, pita::payroll::PayrollPeriod{periodId, detail->daysWorked, period->year, period->month, period->startDate, period->endDate, "OPEN"}, *detail,
        pita::payroll::PayrollConfiguration{}, run->runId);
    cout << "\n  DESPRENDIBLE " << payslip.payslipId << "\n";
    cout << "  Empleado: " << name << " [" << employeeId << "]\n";
    cout << "  Periodo: " << periodId << " | Liquidacion: " << run->runId << "\n";
    linea();
    cout << "  Salario base: $ " << detail->baseSalary << "\n";
    cout << "  Total devengado: $ " << detail->grossSalary << "\n";
    cout << "  Deducciones: $ " << detail->totalEmployeeDeductions << "\n";
    cout << "  IBC: $ " << detail->ibc << "\n";
    cout << "  Neto a pagar: $ " << detail->netSalary << "\n";
    cout << "  Aportes patronales: $ " << detail->totalEmployerContributions << "\n";
    cout << "  Costo total empleador: $ " << detail->totalEmployerCost << "\n";
}

void generarDesprendibleFormal() {
    titulo("NOMINA - GENERAR DESPRENDIBLE");
    const string employeeId = leerLinea("Codigo del empleado: ");
    const string periodId = leerLinea("Identificador del periodo: ");
    try {
        imprimirDesprendibleFormal(periodId, employeeId);
    } catch (const exception& error) {
        msgError("No se pudo generar el desprendible: " + string(error.what()));
    }
}

void listarDesprendiblesFormales() {
    titulo("NOMINA - LISTAR DESPRENDIBLES");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) {
        msgError("No hay liquidacion para ese periodo.");
        return;
    }
    for (const auto& detail : run->details)
        cout << "  PS-" << detail.employeeId << "-" << periodId << " | empleado: " << detail.employeeId << "\n";
}

void resumenFinancieroFormal() {
    titulo("NOMINA - RESUMEN FINANCIERO");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) { msgError("No hay liquidacion para ese periodo."); return; }
    cout << "  Total devengado: $ " << run->grossTotal << "\n";
    cout << "  Total deducciones: $ " << run->employeeDeductionTotal << "\n";
    cout << "  Total neto: $ " << run->netTotal << "\n";
    cout << "  Aportes patronales: $ " << run->employerContributionTotal << "\n";
    cout << "  Costo total empleador: $ " << run->employerCost << "\n";
}

void aportesPatronalesFormales() {
    titulo("NOMINA - APORTES PATRONALES");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) { msgError("No hay liquidacion para ese periodo."); return; }
    for (const auto& detail : run->details)
        cout << "  " << detail.employeeId << " | aportes patronales: $ " << detail.totalEmployerContributions << "\n";
}

void prestacionesFormales() {
    titulo("NOMINA - PRESTACIONES");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) { msgError("No hay liquidacion para ese periodo."); return; }
    for (const auto& detail : run->details) {
        const auto total = detail.serviceBonusProvision + detail.severanceProvision + detail.severanceInterest +
            detail.christmasBonusProvision + detail.vacationProvision + detail.vacationBonusProvision;
        cout << "  " << detail.employeeId << " | prestaciones: $ " << total << "\n";
    }
}

void novedadesFormales() {
    titulo("NOMINA - NOVEDADES");
    const string periodId = leerLinea("Identificador del periodo: ");
    bool found = false;
    for (const auto& novelty : cicloNominaFormal.novelties()) {
        if (novelty.periodId == periodId) {
            found = true;
            cout << "  " << novelty.noveltyId << " | empleado: " << novelty.employeeId
                 << " | valor: $ " << novelty.amount << " | estado: " << novelty.status << "\n";
        }
    }
    if (!found) msgVacio("novedades");
}

void registrarNovedadFormal() {
    titulo("NOMINA - REGISTRAR NOVEDAD");
    const string employeeId = leerLinea("  Codigo del empleado: ");
    pita::payroll::PayrollEmployee employee;
    string name;
    if (!empleadoFormalPorId(employeeId, employee, name)) {
        msgError("No se encontro un empleado con ese codigo.");
        return;
    }

    cout << "  Empleado seleccionado: " << name << " [" << employeeId << "]\n";
    cout << "  Tipos de novedad disponibles:\n"
         << "  1. Bonificacion (BONUS)\n"
         << "  2. Descuento (DISCOUNT)\n"
         << "  3. Incapacidad (INCAPACITY)\n"
         << "  4. Licencia (LICENSE)\n"
         << "  5. Vacaciones (VACATION)\n"
         << "  6. Ausencia (ABSENCE)\n"
         << "  7. Horas adicionales (ADDITIONAL_HOURS)\n"
         << "  8. Embargo (GARNISHMENT)\n"
         << "  9. Anticipo (ADVANCE)\n"
         << "  10. Ajuste salarial (SALARY_ADJUSTMENT)\n"
         << "  11. Ingreso (INCOME)\n"
         << "  12. Terminacion / Retiro (TERMINATION)\n";
    int tipoOp = leerEntero("  Opcion de tipo: ");
    pita::payroll::NoveltyType tipoNovedad;
    bool isSalary = true;
    bool affectsIbc = true;
    switch (tipoOp) {
        case 1:  tipoNovedad = pita::payroll::NoveltyType::BONUS; isSalary = true; affectsIbc = true; break;
        case 2:  tipoNovedad = pita::payroll::NoveltyType::DISCOUNT; isSalary = false; affectsIbc = false; break;
        case 3:  tipoNovedad = pita::payroll::NoveltyType::INCAPACITY; isSalary = true; affectsIbc = false; break;
        case 4:  tipoNovedad = pita::payroll::NoveltyType::LICENSE; isSalary = false; affectsIbc = false; break;
        case 5:  tipoNovedad = pita::payroll::NoveltyType::VACATION; isSalary = true; affectsIbc = true; break;
        case 6:  tipoNovedad = pita::payroll::NoveltyType::ABSENCE; isSalary = false; affectsIbc = false; break;
        case 7:  tipoNovedad = pita::payroll::NoveltyType::ADDITIONAL_HOURS; isSalary = true; affectsIbc = true; break;
        case 8:  tipoNovedad = pita::payroll::NoveltyType::GARNISHMENT; isSalary = false; affectsIbc = false; break;
        case 9:  tipoNovedad = pita::payroll::NoveltyType::ADVANCE; isSalary = false; affectsIbc = false; break;
        case 10: tipoNovedad = pita::payroll::NoveltyType::SALARY_ADJUSTMENT; isSalary = true; affectsIbc = true; break;
        case 11: tipoNovedad = pita::payroll::NoveltyType::INCOME; isSalary = true; affectsIbc = true; break;
        case 12: tipoNovedad = pita::payroll::NoveltyType::TERMINATION; isSalary = false; affectsIbc = false; break;
        default:
            msgError("Tipo de novedad invalido.");
            return;
    }

    double valorNum = leerDouble("  Valor numerico de la novedad: ");

    string periodId = "";
    for (auto it = cicloNominaFormal.periods().rbegin(); it != cicloNominaFormal.periods().rend(); ++it) {
        if (it->status == pita::payroll::PeriodStatus::OPEN) {
            periodId = it->periodId;
            break;
        }
    }
    if (periodId.empty() && !cicloNominaFormal.periods().empty()) {
        periodId = cicloNominaFormal.periods().back().periodId;
    }
    if (periodId.empty()) {
        auto per = cicloNominaFormal.createPeriod("PER-ACTUAL", 2026, 9, "2026-09-01", "2026-09-30", "admin");
        periodId = per.periodId;
    }

    pita::payroll::PayrollNoveltyRecord novedad;
    novedad.noveltyId = "NOV-" + to_string(cicloNominaFormal.novelties().size() + 1);
    novedad.periodId = periodId;
    novedad.employeeId = employeeId;
    novedad.type = tipoNovedad;
    novedad.quantity = 1;
    novedad.amount = static_cast<pita::payroll::Money>(valorNum);
    novedad.isSalary = isSalary;
    novedad.affectsIbc = affectsIbc;
    novedad.status = "APPROVED";
    novedad.createdBy = "admin";

    try {
        cicloNominaFormal.registerNovelty(novedad);
        msgOk("Novedad registrada exitosamente para " + name + ".");
    } catch (const exception& e) {
        msgError("Error al registrar novedad: " + string(e.what()));
    }
}

void aprobarNominaFormal() {
    titulo("NOMINA - APROBAR");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) { msgError("No existe liquidacion para ese periodo."); return; }
    try {
        cicloNominaFormal.approveRun(run->runId, "console");
        msgOk("Nomina aprobada.");
    } catch (const exception& error) { msgError("No se pudo aprobar: " + string(error.what())); }
}

void cerrarNominaFormal() {
    titulo("NOMINA - CERRAR");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) { msgError("No existe liquidacion para ese periodo."); return; }
    try {
        cicloNominaFormal.closeRun(run->runId, "console");
        msgOk("Nomina cerrada.");
    } catch (const exception& error) { msgError("No se pudo cerrar: " + string(error.what())); }
}

void historialNominaFormal() {
    titulo("NOMINA - HISTORIAL");
    for (const auto& audit : cicloNominaFormal.audits())
        cout << "  " << audit.timestamp << " | " << audit.action << " | "
             << audit.entityType << " | " << audit.entityId << "\n";
    if (cicloNominaFormal.audits().empty()) msgVacio("movimientos");
}

void dashboardFinancieroFormal() {
    titulo("NOMINA - DASHBOARD FINANCIERO");
    const string periodId = leerLinea("Identificador del periodo: ");
    const auto* run = buscarRunFormal(periodId);
    if (run == nullptr) {
        msgError("No existe un PayrollRun oficial para ese periodo.");
        return;
    }

    map<string, int> professorTypes;
    map<string, int> faculties;
    map<string, int> categories;
    map<string, int> linkages;
    pita::payroll::Money basic = 0, gross = 0, deductions = 0, ibc = 0;
    pita::payroll::Money employeeHealth = 0, employeePension = 0, benefits = 0;
    pita::payroll::Money employerPension = 0, employerHealth = 0, arl = 0;
    pita::payroll::Money compensationFund = 0, sena = 0, icbf = 0;
    int professors = 0, administratives = 0;

    for (const auto& detail : run->details) {
        basic += detail.baseSalary;
        gross += detail.grossSalary;
        deductions += detail.totalEmployeeDeductions;
        ibc += detail.ibc;
        employeeHealth += detail.employeeHealth;
        employeePension += detail.employeePension;
        benefits += detail.serviceBonusProvision + detail.severanceProvision + detail.severanceInterest +
            detail.christmasBonusProvision + detail.vacationProvision + detail.vacationBonusProvision;
        employerPension += detail.employerPension;
        employerHealth += detail.employerHealth;
        arl += detail.arl;
        compensationFund += detail.compensationFund;
        sena += detail.sena;
        icbf += detail.icbf;

        if (detail.employeeType == "Professor") {
            professors++;
            Programa* program = nullptr;
            Profesor* professor = buscarProfesorGlobal(detail.employeeId, &program, nullptr);
            if (professor != nullptr) {
                professorTypes[nombreTipoContrato(professor->nomina.tipoContrato)]++;
                categories[nombreCategoria(professor->nomina.categoria)]++;
                linkages[professor->tipoVinculacion.empty() ? nombreTipoContrato(professor->nomina.tipoContrato) : professor->tipoVinculacion]++;
                Facultad* faculty = cabezaFacultades;
                while (faculty != nullptr) {
                    Programa* candidate = faculty->listaProgramas;
                    while (candidate != nullptr && candidate != program) candidate = candidate->sig;
                    if (candidate == program) break;
                    faculty = faculty->sig;
                }
                faculties[faculty == nullptr ? "Sin facultad" : faculty->nombre]++;
            } else {
                professorTypes["Sin configurar"]++;
                categories["Sin configurar"]++;
                linkages["Sin configurar"]++;
                faculties["Sin facultad"]++;
            }
        } else {
            administratives++;
            Administrativo* administrative = buscarAdministrativo(detail.employeeId);
            linkages[administrative == nullptr || administrative->tipoVinculacion.empty()
                ? "Sin configurar" : administrative->tipoVinculacion]++;
        }
    }

    cout << "  Periodo: " << periodId << " | PayrollRun: " << run->runId
         << " | Estado: " << nombreEstadoRun(run->status) << "\n";
    linea();
    cout << "  Total empleados              : " << run->details.size() << "\n";
    cout << "  Total profesores             : " << professors << "\n";
    cout << "  Total administrativos        : " << administratives << "\n";
    cout << "  Salario basico total         : $ " << basic << "\n";
    cout << "  Total devengado              : $ " << gross << "\n";
    cout << "  Total deducciones            : $ " << deductions << "\n";
    cout << "  Total IBC                    : $ " << ibc << "\n";
    cout << "  Salud trabajador             : $ " << employeeHealth << "\n";
    cout << "  Pension trabajador           : $ " << employeePension << "\n";
    cout << "  Total prestaciones           : $ " << benefits << "\n";
    cout << "  Pension patronal             : $ " << employerPension << "\n";
    cout << "  Salud patronal               : $ " << employerHealth << "\n";
    cout << "  ARL                          : $ " << arl << "\n";
    cout << "  Caja                         : $ " << compensationFund << "\n";
    cout << "  SENA                         : $ " << sena << "\n";
    cout << "  ICBF                         : $ " << icbf << "\n";
    cout << "  Total aportes patronales    : $ " << run->employerContributionTotal << "\n";
    cout << "  Costo total empleador       : $ " << run->employerCost << "\n";
    cout << "  Total neto pagado           : $ " << run->netTotal << "\n";

    auto printDistribution = [](const string& titleText, const map<string, int>& values) {
        cout << "\n  " << titleText << "\n";
        for (const auto& value : values) cout << "    " << value.first << ": " << value.second << "\n";
    };
    printDistribution("Distribucion por tipo de profesor", professorTypes);
    printDistribution("Distribucion por facultad", faculties);
    printDistribution("Distribucion por categoria", categories);
    printDistribution("Distribucion por tipo de vinculacion", linkages);
    cout << "\n  Costo de prestaciones       : $ " << benefits << "\n";
    cout << "  Costo de seguridad social  : $ " << run->employerContributionTotal << "\n";
}

void menuNominaFormal() {
    int op;
    do {
        titulo("NOMINA");
        cout << "  1. Crear periodo\n  2. Consultar periodos\n  3. Calcular nomina\n"
             << "  4. Consultar nomina\n  5. Consultar profesor\n  6. Generar desprendible\n"
             << "  7. Listar desprendibles\n  8. Ver resumen financiero\n  9. Ver aportes patronales\n"
             << "  10. Ver prestaciones\n  11. Ver novedades\n  12. Registrar novedad a empleado\n"
             << "  13. Aprobar nomina\n  14. Cerrar nomina\n  15. Consultar historial\n"
             << "  16. Dashboard financiero\n  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearPeriodoFormal(); break;
            case 2: listarPeriodosFormales(); break;
            case 3: calcularNominaFormal(); break;
            case 4: consultarNominaFormal(); break;
            case 5: consultarProfesorFormal(); break;
            case 6: generarDesprendibleFormal(); break;
            case 7: listarDesprendiblesFormales(); break;
            case 8: resumenFinancieroFormal(); break;
            case 9: aportesPatronalesFormales(); break;
            case 10: prestacionesFormales(); break;
            case 11: novedadesFormales(); break;
            case 12: registrarNovedadFormal(); break;
            case 13: aprobarNominaFormal(); break;
            case 14: cerrarNominaFormal(); break;
            case 15: historialNominaFormal(); break;
            case 16: dashboardFinancieroFormal(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuFacultades() {
    int op;
    do {
        titulo("GESTION DE FACULTADES");
        cout << "  1. Crear facultad\n";
        cout << "  2. Listar facultades\n";
        cout << "  3. Modificar facultad\n";
        cout << "  4. Activar/Desactivar facultad\n";
        cout << "  5. Eliminar facultad\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearFacultad(); break;
            case 2: listarFacultades(); break;
            case 3: modificarFacultad(); break;
            case 4: desactivarFacultad(); break;
            case 5: eliminarFacultad(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuProgramas() {
    int op;
    do {
        titulo("GESTION DE PROGRAMAS ACADEMICOS");
        cout << "  1. Crear programa (ej: Medicina, Ing. de Sistemas, etc.)\n";
        cout << "  2. Listar programas por facultad\n";
        cout << "  3. Modificar programa\n";
        cout << "  4. Activar/Desactivar programa\n";
        cout << "  5. Eliminar programa\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearPrograma(); break;
            case 2: listarProgramas(); break;
            case 3: modificarPrograma(); break;
            case 4: desactivarPrograma(); break;
            case 5: eliminarPrograma(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuCursos() {
    int op;
    do {
        titulo("GESTION DE CURSOS");
        cout << "  1. Crear curso\n";
        cout << "  2. Listar cursos de un programa\n";
        cout << "  3. Modificar curso\n";
        cout << "  4. Eliminar curso\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearCurso(); break;
            case 2: listarCursos(); break;
            case 3: modificarCurso(); break;
            case 4: eliminarCurso(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuEstudiantes() {
    int op;
    do {
        titulo("GESTION DE ESTUDIANTES");
        cout << "  1. Crear estudiante\n";
        cout << "  2. Listar estudiantes de un programa\n";
        cout << "  3. Modificar estudiante\n";
        cout << "  4. Activar/Desactivar estudiante\n";
        cout << "  5. Eliminar estudiante\n";
        cout << "  6. Matricular curso\n";
        cout << "  7. Cancelar matricula de un curso\n";
        cout << "  8. Registrar nota de un curso\n";
        cout << "  9. Consultar promedio y alerta EBRA\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearEstudiante(); break;
            case 2: listarEstudiantes(); break;
            case 3: modificarEstudiante(); break;
            case 4: desactivarEstudiante(); break;
            case 5: eliminarEstudiante(); break;
            case 6: matricularCurso(); break;
            case 7: cancelarMatricula(); break;
            case 8: calificarCurso(); break;
            case 9: consultarPromedioEstudiante(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuProfesores() {
    int op;
    do {
        titulo("GESTION DE PROFESORES");
        cout << "  1. Crear profesor\n";
        cout << "  2. Listar profesores de un programa\n";
        cout << "  3. Modificar profesor\n";
        cout << "  4. Activar/Desactivar profesor\n";
        cout << "  5. Eliminar profesor\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearProfesor(); break;
            case 2: listarProfesores(); break;
            case 3: modificarProfesor(); break;
            case 4: desactivarProfesor(); break;
            case 5: eliminarProfesor(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuAdministrativos() {
    int op;
    do {
        titulo("GESTION DE ADMINISTRATIVOS");
        cout << "  1. Crear administrativo\n";
        cout << "  2. Listar administrativos\n";
        cout << "  3. Modificar administrativo\n";
        cout << "  4. Activar/Desactivar administrativo\n";
        cout << "  5. Eliminar administrativo\n";
        cout << "  0. Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: crearAdministrativo(); break;
            case 2: listarAdministrativos(); break;
            case 3: modificarAdministrativo(); break;
            case 4: desactivarAdministrativo(); break;
            case 5: eliminarAdministrativo(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuReportesNomina() {
    int op;
    do {
        titulo("REPORTES Y NOMINA (recorridos de listas)");
        cout << "  1.  Nomina de un profesor (mensual y anual)\n";
        cout << "  2.  Nomina total de un programa\n";
        cout << "  3.  Nomina total de una facultad\n";
        cout << "  4.  Nomina total de TODA la universidad (mensual y anual)\n";
        cout << "  5.  Estudiantes en EBRA (toda la universidad)\n";
        cout << "  6.  Arbol completo de la universidad\n";
        cout << "  7.  Profesores por categoria y tipo de contrato\n";
        cout << "  8.  Nomina de un administrativo (mensual y anual)\n";
        cout << "  9.  Nomina total de TODOS los administrativos\n";
        cout << "  10. Profesor con mayor y menor salario\n";
        cout << "  11. Estudiante con mejor y peor promedio\n";
        cout << "  12. Ordenar profesores de un programa por salario\n";
        cout << "  13. Buscar estudiante/profesor/administrativo por documento\n";
        cout << "  14. Censo general de la universidad (conteos totales)\n";
        cout << "  15. Generar desprendible individual de profesor\n";
        cout << "  0.  Volver\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1:  reporteNominaProfesorIndividual(); break;
            case 2:  reporteNominaPorPrograma(); break;
            case 3:  reporteNominaPorFacultad(); break;
            case 4:  reporteNominaUniversidadCompleta(); break;
            case 5:  reporteEstudiantesEnEBRA(); break;
            case 6:  reporteArbolCompletoUniversidad(); break;
            case 7:  reporteProfesoresPorCategoria(); break;
            case 8:  reporteNominaAdministrativoIndividual(); break;
            case 9:  reporteNominaTotalAdministrativos(); break;
            case 10: reporteProfesorMayorMenorSalario(); break;
            case 11: reporteEstudianteMejorPeorPromedio(); break;
            case 12: ordenarProfesoresPorSalario(); break;
            case 13: buscarPorDocumento(); break;
            case 14: reporteCensoGeneral(); break;
            case 15: generarDesprendibleProfesor(); break;
            case 0: break;
            default: msgError("Opcion invalida.");
        }
        if (op != 0) pausar();
    } while (op != 0);
}

void menuPrincipal() {
    int op;
    do {
        titulo("MENU PRINCIPAL - NexoCampus (UPC)");
        cout << "  1. Gestion de Facultades\n";
        cout << "  2. Gestion de Programas Academicos\n";
        cout << "  3. Gestion de Cursos\n";
        cout << "  4. Gestion de Estudiantes\n";
        cout << "  5. Gestion de Profesores\n";
        cout << "  6. Gestion de Administrativos\n";
        cout << "  7. NOMINA\n";
        cout << "  8. Reportes y Nomina (legacy)\n";
        cout << "  9. Guardar datos en archivo\n";
        cout << "  10. Cargar datos desde archivo\n";
        cout << "  11. Cargar datos de ejemplo\n";
        cout << "  0. Salir\n";
        op = leerEntero("  Opcion: ");
        switch (op) {
            case 1: menuFacultades(); break;
            case 2: menuProgramas(); break;
            case 3: menuCursos(); break;
            case 4: menuEstudiantes(); break;
            case 5: menuProfesores(); break;
            case 6: menuAdministrativos(); break;
            case 7: menuNominaFormal(); break;
            case 8: menuReportesNomina(); break;
            case 9: guardarDatos(); pausar(); break;
            case 10: cargarDatos(); pausar(); break;
            case 11: {
                if (leerSiNo("  >> ADVERTENCIA: Esto borrará todos los datos actuales en memoria. ¿Desea continuar? (s/n): ")) {
                    liberarTodaLaMemoria();
                    cargarDatosDeEjemplo();
                    msgOk("Datos de ejemplo cargados correctamente.");
                }
                pausar();
                break;
            }
            case 0: cout << "\n  Saliendo del menu principal...\n"; break;
            default: msgError("Opcion invalida."); pausar(); break;
        }
    } while (op != 0);
}
