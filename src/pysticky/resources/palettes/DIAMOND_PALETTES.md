# Diamond-Painting-Paletten

PySticky erkennt Diamond-Painting-Paletten am Wort **"Diamond"** im Dateinamen
(z.B. `Diamond_Art_Club_Diamond_Painting_Farben.json`). Farben aus solchen
Paletten werden im Pattern automatisch als `StitchType.DIAMOND` platziert und
in der **Diamond-Painting-Ansicht** (`Ansicht → Diamond-Painting-Ansicht`,
`Ctrl+D`) als facettierte Drills gerendert.

## Status der mitgelieferten Paletten

| Palette | Status | Farben |
|---|---|---|
| `DMC_Diamond_Painting_Farben.json` | **Vollständig** — offizielle DMC-DP-Codes | 450 |
| `Diamond_Art_Club_Diamond_Painting_Farben.json` | **Skelett** — repräsentatives Sample | ~43 |
| `Diamond_Dotz_Diamond_Painting_Farben.json` | **Skelett** — repräsentatives Sample | ~36 |

## Warum nur Skelette?

Diamond Art Club (DAC) und Diamond Dotz veröffentlichen ihre RGB-Werte nicht
offiziell. Die mitgelieferten Sample-Paletten enthalten ein gleichmäßig über
den Farbraum verteiltes Set, das für Tests und Demos ausreicht, **aber nicht
die echten Codes deckt**. Wer mit einer echten DAC- oder Diamond-Dotz-Vorlage
arbeitet, sollte die JSON erweitern.

## Eigene Codes ergänzen

Format:
```json
[
    { "DacNumber": "DAC-123", "Color": { "R": 200, "G": 100, "B": 50 }, "Name": "Burnt Sienna" },
    ...
]
```

Wichtig:
- Das Number-Feld muss mit `Number` enden oder `Code` heißen (z.B. `DacNumber`,
  `DdNumber`, `DpDmcNumber`, `Code`). Der Loader sucht das erste solche Feld.
- RGB-Werte sind 0..255.
- Reihenfolge spielt keine Rolle — die Palette wird wie angegeben angezeigt.

## Paint With Diamonds / Dreamer Designs

Diese Hersteller verwenden **DMC-Codes**. Es gibt also keine separate
`Dreamer_Designs_...`-Palette — wer eine PWD- oder Dreamer-Designs-Vorlage
hat, nutzt einfach `DMC_Diamond_Painting_Farben.json`. Die Codes sind 1:1
kompatibel.
