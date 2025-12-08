#!/usr/bin/env python3
"""Update ROADMAP.md with User Experience Simplification section."""

def main():
    """Main function to update ROADMAP.md."""
    try:
        with open('ROADMAP.md', 'r') as f:
            content = f.read()

        # Verificar si la sección ya existe
        if 'User Experience Simplification' in content:
            print('⚠️ Sección User Experience Simplification ya existe en ROADMAP.md')
            return

        # Nueva sección a añadir
        new_section = '''---

## 🎯 User Experience Simplification (Post v1.0 - Critical Improvements)

**Goal**: Eliminate user friction and data inconsistencies

### Phase 1: Input Normalization & Validation
- [ ] **Day name normalization**: Sanitize any variant (Miércoles, Miercoles, miercoles, MIÉRCOLES) → canonical lowercase without accents
- [ ] **Vehicle ID normalization**: Auto-convert to slug format (spaces → underscores, lowercase)
- [ ] **Input validation**: Real-time feedback in config flow and services

### Phase 2: Smart Trip Creation
- [ ] **Eliminate kWh manual entry**: Remove redundant kWh field that risks contradictory data (e.g., 1000km with 1kWh)
- [ ] **Origin-destination geocoding**: Accept addresses/coordinates instead of manual km entry
- [ ] **Automatic consumption calculation**: kWh = distance × vehicle_efficiency
- [ ] **Travel time estimation**: Calculate duration based on route and traffic

### Phase 3: Conversational AI Interface
- [ ] **Natural language processing**: "Voy de Madrid a Barcelona mañana a las 9"
- [ ] **Intent recognition**: Extract origin, destination, datetime automatically
- [ ] **Voice integration**: HA Assist compatibility for hands-free trip planning

**Success Criteria**:
- ✅ Zero data entry errors from format inconsistencies
- ✅ No manual kWh calculations required
- ✅ Sub-30-second trip creation via voice/text
- ✅ 100% backward compatibility maintained

**Files to Modify**:
- `custom_components/ev_trip_planner/trip_manager.py` (normalization helpers)
- `custom_components/ev_trip_planner/services.yaml` (new parameters)
- `custom_components/ev_trip_planner/config_flow.py` (geocoding API config)
- `custom_components/ev_trip_planner/manifest.json` (add unidecode dependency)

**Dependencies**:
- `unidecode` library (for accent removal)
- Geocoding API (Google Maps / OpenStreetMap Nominatim)
- Vehicle efficiency database (kWh/km per model)
'''

        # Buscar dónde insertar (después de Milestone 5)
        if '### ⚪ Milestone 5: Advanced Features' in content:
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if '### ⚪ Milestone 5: Advanced Features' in line:
                    # Encontrar el final de Milestone 5 (buscar el siguiente '---' o final)
                    for j in range(i+1, len(lines)):
                        if lines[j].startswith('---') and j > i+10:
                            lines.insert(j, new_section.strip())
                            break
                        # Si no hay '---', insertar al final
                        if j == len(lines) - 1:
                            lines.append(new_section.strip())
                            break
                    break
            
            with open('ROADMAP.md', 'w') as f:
                f.write('\n'.join(lines))
            
            print('✅ ROADMAP.md actualizado con sección User Experience Simplification')
        else:
            print('❌ No se encontró Milestone 5 para insertar después')

    except Exception as e:
        print(f'❌ Error: {e}')

if __name__ == '__main__':
    main()