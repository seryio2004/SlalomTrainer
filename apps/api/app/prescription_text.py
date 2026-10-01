"""Readable effective prescription for calendar exports."""


def prescription_text(prescription):
    details = [prescription.get('objective') or '', prescription.get('instructions') or '']
    if prescription.get('details'):
        labels = {'water_subtype': 'Subtipo', 'runs': 'Mangas', 'meters': 'Distancia (m)', 'seconds': 'Tiempo (s)', 'target_rpe': 'RPE objetivo', 'model': 'Modelo', 'resistance': 'Resistencia', 'protocol': 'Protocolo', 'protocol_version': 'Versión'}
        details.append(' · '.join(f'{labels.get(key, key)}: {value}' for key, value in prescription['details'].items() if value is not None))
    steps = prescription.get('steps') or []
    if steps:
        details.append('Indicaciones paso a paso:\n' + '\n'.join(f'{number}. {step}' for number, step in enumerate(steps, 1)))
    measures = {'sets': 'series', 'reps': 'reps', 'kg': 'kg', 'seconds': 's', 'meters': 'm', 'rest_seconds': 's descanso', 'rir': 'RIR', 'target_rpe': 'RPE objetivo'}
    for block in prescription.get('blocks', []):
        lines = [block['title'], block.get('instructions') or '']
        for exercise in block.get('exercises', []):
            values = [exercise['name']]
            values.extend(f'{exercise[key]} {unit}' for key, unit in measures.items() if exercise.get(key) is not None)
            for key in ('side', 'load_convention', 'intensity', 'zone', 'instructions'):
                if exercise.get(key):
                    values.append(str(exercise[key]))
            lines.append(' · '.join(values))
        details.append('\n'.join(line for line in lines if line))
    return '\n\n'.join(part for part in details if part)
