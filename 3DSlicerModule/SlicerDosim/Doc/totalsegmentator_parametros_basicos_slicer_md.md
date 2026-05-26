# Parámetros básicos de TotalSegmentator en 3D Slicer

## Ejemplo mínimo

```python
parameters = {
    "inputVolume": inputVolumeNode,
    "outputSegmentation": outputSegmentationNode,
    "task": "total",
    "fast": True
}

cliNode = slicer.cli.run(
    slicer.modules.totalsegmentator,
    None,
    parameters,
    wait_for_completion=True
)
```

## Parámetros principales

| Parámetro | Descripción |
|---|---|
| `inputVolume` | Volumen de entrada |
| `outputSegmentation` | Segmentación de salida |
| `task` | Tipo de segmentación |
| `fast` | Usa modelo rápido |

## Tasks comunes

```python
"total"
"body"
"liver_vessels"
"lung_vessels"
"bones"
```

