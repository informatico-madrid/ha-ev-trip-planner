#!/usr/bin/env node

// extract_report.js - Extrae y muestra un resumen estructurado de los resultados de los tests

const fs = require('fs');
const path = require('path');

const reportFile = path.join(__dirname, '..', 'playwright-results.json');

try {
  const report = JSON.parse(fs.readFileSync(reportFile, 'utf8'));

  console.log('\n' + '='.repeat(60));
  console.log('📊 RESUMEN DE TESTS E2E - HOME ASSISTANT');
  console.log('='.repeat(60));

  const suites = report.suites || [];
  const tests = report.tests || [];

  // Contar tests por estado
  const passed = tests.filter(t => t.status === 'passed').length;
  const failed = tests.filter(t => t.status === 'failed').length;
  const skipped = tests.filter(t => t.status === 'skipped').length;

  console.log(`\n📈 Total Tests: ${tests.length}`);
  console.log(`   ✅ Pasados: ${passed}`);
  console.log(`   ❌ Fallados: ${failed}`);
  console.log(`   ⏭️  Saltados: ${skipped}`);

  // Mostrar tests fallados con detalles
  if (failed > 0) {
    console.log('\n' + '-'.repeat(60));
    console.log('❌ TESTS FALLADOS:');
    console.log('-'.repeat(60));

    tests.filter(t => t.status === 'failed').forEach(test => {
      console.log(`\n🚨 ${test.title}`);
      console.log(`   Proyecto: ${test.location.file}`);
      console.log(`   Línea: ${test.location.line}:${test.location.column}`);
      console.log(`   Errores: ${test.errors?.length || 0}`);

      if (test.errors && test.errors.length > 0) {
        test.errors.forEach((error, idx) => {
          console.log(`   Error ${idx + 1}: ${error.message?.substring(0, 200) || 'Unknown'}`);
        });
      }
    });
  }

  // Mostrar tests pasados
  if (passed > 0) {
    console.log('\n' + '-'.repeat(60));
    console.log('✅ TESTS PASADOS:');
    console.log('-'.repeat(60));

    tests.filter(t => t.status === 'passed').forEach(test => {
      console.log(`   ✅ ${test.title}`);
    });
  }

  console.log('\n' + '='.repeat(60));
  console.log('📁 Reporte completo: playwright-results.json');
  console.log('📁 Trace files: playwright/trace.zip (si hay fallos)');
  console.log('='.repeat(60) + '\n');

} catch (error) {
  console.error('❌ Error leyendo reporte:', error.message);
  process.exit(1);
}
