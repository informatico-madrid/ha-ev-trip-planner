# CI esencial y validación avanzada local

## GitHub: confianza funcional con un coste acotado

El workflow `Python Tests` instala únicamente `requirements_ci.txt` y ejecuta:

1. Ruff: errores básicos y formato, con reglas y versión explícitas.
2. Pyright: tipos del código de la integración.
3. Toda la suite Python de `tests/unit` y `tests/integration`.
4. Las pruebas ejecutables del panel nativo con Node.js.
5. Publicación del informe JUnit, también cuando falla una prueba.

Las versiones de Home Assistant y su plugin pytest corresponden al entorno
validado. Los cambios de reglas o de API de herramientas no se incorporan
automáticamente a cada push. El job tiene un límite de 15 minutos.

Para reproducir los controles Python:

```bash
.venv/bin/python -m pip install -r requirements_ci.txt
make quality-gate-ci PYTEST_WORKERS=2
node --experimental-vm-modules --test --test-reporter=spec tests/panel-planning.test.mjs
```

La suite funcional se conserva completa: no se elimina un caso de energía,
reserva o disponibilidad porque haya descubierto un error real. Las pruebas
obsoletas se adaptan al comportamiento acordado, con aserciones funcionales.

## Local: análisis avanzados disponibles a demanda

`requirements_dev.txt` incluye las dependencias esenciales y las herramientas
adicionales. Se conservan sus scripts y los siguientes comandos:

| Comando | Validación local |
|---|---|
| `make layer3a` | Pylint, SOLID, principios y antipatrones, además de lint/tipos |
| `make layer2` | Mutación, calidad y diversidad de pruebas |
| `make layer3b` | Contexto de revisión avanzada/BMAD |
| `make layer4` | Escaneo extensivo de seguridad y dependencias |
| `make e2e` / `make e2e-soc` | E2E contra el entorno de pruebas dedicado |
| `make quality-gate` | Flujo avanzado local completo |

Estos análisis no forman parte del target `quality-gate-ci` ni de las
dependencias instaladas por GitHub. Que un análisis sea útil en local no implica
que deba ejecutarse o bloquear cada publicación. E2E mantiene su separación del
entorno de producción y se ejecuta mediante los comandos dedicados del proyecto.
