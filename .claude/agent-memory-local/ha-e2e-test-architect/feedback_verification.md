---
name: feedback_verification
description: Regla de verificación obligatoria antes de afirmar que algo funciona
type: feedback
---

## REGLA DE VERIFICACIÓN OBLIGATORIA

**Antes de afirmar que algo funciona o existe:**

1. **VERIFICA** el estado real del repo con `git log` o comandos similares
2. **VERIFICA** que el archivo existe antes de hacer afirmaciones
3. **VERIFICA** que tus cambios no rompen workflows existentes
4. **NUNCA** asumas que algo funciona sin evidencia
5. **SI NO SABES**, pregunta al usuario - no adivines

**Por qué:** Asumir sin verificar lleva a afirmaciones incorrectas que pierden tiempo y confianza.

**Cómo aplicar:** Cuando el usuario pregunte si un test pasa o un archivo existe, verifica primero con comandos git o lectura de archivos antes de responder.
