# 🧪 Instrucciones para Ejecutar Pruebas

## 📁 Estructura de Carpetas

El proyecto utiliza un entorno virtual para las pruebas. La estructura de carpetas es:

```
ha-ev-trip-planner/
├── venv/              # Entorno virtual
├── tests/             # Tests unitarios
└── custom_components/ # Componentes principales
```

## 🛠️ Configuración del Entorno

### 1. Activar el entorno virtual

```bash
cd /home/malka/ha-ev-trip-planner
source venv/bin/activate
```

### 2. Verificar dependencias

```bash
pip list | grep -E "(pytest|homeassistant)"
```

## 🧪 Ejecución de Pruebas

### Ejecutar todas las pruebas

```bash
cd /home/malka/ha-ev-trip-planner
source venv/bin/activate
pytest tests/ -v
```

### Ejecutar pruebas específicas

```bash
# Ejecutar solo tests de EMHASS
pytest tests/test_emhass_adapter.py -v

# Ejecutar tests de configuración
pytest tests/test_config_flow_*.py -v

# Ejecutar tests de trip manager
pytest tests/test_trip_manager*.py -v
```

### Ejecutar con cobertura

```bash
# Instalar coverage si no está instalado
pip install pytest-cov

# Ejecutar con cobertura
pytest tests/ --cov=custom_components/ --cov-report=html
```

## 📋 Prerrequisitos

Antes de ejecutar las pruebas, asegúrate de tener instaladas las dependencias:

```bash
cd /home/malka/ha-ev-trip-planner
source venv/bin/activate
pip install -e .
```

## 📝 Notas Importantes

1. **Entorno Virtual**: Es crucial activar el entorno virtual antes de ejecutar los tests
2. **Ruta de Ejecución**: Los comandos deben ejecutarse desde el directorio raíz del proyecto
3. **Dependencias**: El entorno virtual contiene todas las dependencias necesarias
4. **Pruebas Parciales**: Puedes ejecutar tests individuales para depurar problemas específicos

## 🚨 Posibles Errores

### Error de importación de homeassistant

```bash
# Solución alternativa si hay errores de importación
export PYTHONPATH="/home/malka/ha-ev-trip-planner:$PYTHONPATH"
```

### Ejecutar con PYTHONPATH

```bash
cd /home/malka/ha-ev-trip-planner
source venv/bin/activate
PYTHONPATH=/home/malka/ha-ev-trip-planner pytest tests/ -v
```

## 📊 Información de Pruebas

- **Número total de tests**: 29 (como se menciona en el README)
- **Cobertura mínima requerida**: 80%
- **Tipos de tests**: Unitarios y de integración
- **Frameworks utilizados**: pytest, unittest

## 📚 Recursos Adicionales

- Documentación de pytest: https://docs.pytest.org/
- Documentación de Home Assistant: https://developers.home-assistant.io/