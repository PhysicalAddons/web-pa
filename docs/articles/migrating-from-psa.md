---
template: overrides/article.html
---

# Migrating from Physical Starlight and Atmosphere

You can move a scene from Physical Starlight and Atmosphere (PSA) to Physical Atmosphere² with one button. Your scene stays as it is. Only the sky changes.

## What changes

Physical Atmosphere² removes the PSA sky from the world, together with the PSA nodes, drivers and the *Starlight Sun* lamp. It adds its own sky and its own sun lamp. The sun points the same way as before. Your objects, materials, cameras and lights do not change.

## What you keep and what you lose

You keep:

- The sun direction.
- A Physical Open Waters ocean, if the scene has one. It follows the new sky.

You lose:

- The PSA settings and presets. Set the look again in Physical Atmosphere².
- The time, date and location. The sun keeps its direction in *Artistic* mode. To use time and location again, switch to *Realistic* mode and enter them.
- PSA fog on materials. Use *Composite 3D Objects* in Physical Atmosphere² instead.

## How to migrate

1. Save the file.
2. Open the Physical Atmosphere² panel. On a PSA scene it shows *Another atmosphere is active* and the button **Replace with Atmosphere²**.
3. Push the button and confirm.

PSA can stay installed, or you can uninstall it first. Both work.

## Going back

Open the saved file. Undo does not bring the PSA sky back in every case. That is why you save first.

You need Physical Atmosphere² 3.0.10-beta or newer. Physical Open Waters needs version 1.2.3 or newer.
