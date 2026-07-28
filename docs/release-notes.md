### 2.6.1 <small>- released 28.07.2026</small>

A stability release for two field crashes, plus the first wave of post-2.6.0 sky physics.

`fixed:`{: .label-fixed }

- **Linux**: a hard crash from the GPU safety check is fixed.
- **macOS**: repeated display hiccups could eventually take down all of Blender. The add-on now stops its own sky pipeline first and asks for a restart, and Blender itself stays alive.
- Switching Quality presets no longer risks a crash.
- The setting sun is no longer cut off early above the horizon, and aerial cameras no longer show a sharp sky seam (both with refraction enabled).

`improvements:`{: .label-improvements }

- Fresh scenes now start at **Normal** quality (was Low), with Exposure (EV) at 5.0.
- The cirrus and rain cloud layers start disabled in new scenes while they are being reworked.
- The Rendering Settings section, with its Quality presets, now also appears in the Scientific layout.
- Deep twilight looks better: the dark wedge fills with scattered light and the banding in the high sky is gone.
- The bundled weather snapshot was refreshed.

`prototypes / research:`{: .label-research }

- **Atmospheric Refraction** — physically modeled bending of light in the air: the horizon rises, distant terrain looms, and the sun flattens as it sets, all driven by your scene's air pressure and temperature. One checkbox on the Atmosphere tab turns the whole suite on. Off by default while it collects feedback.
- **Cloud Shading models** — a `Model` dropdown in Cloud Shading with three looks: the new default **KSA** (a clean, production-proven reference look), the fully tweakable **Hybrid (PSA2)**, and **Octave MS**. The hybrid and all its knobs remain one click away.
- **LUT Multiple Scattering (Hillaire)** — an alternative, film-industry-standard way of computing the sky's multiple scattering, available as a toggle on the Atmosphere tab.
- **Baked Ground Shading** (experimental, Scientific layout) — a fully shaded planet surface with water glints, coastlines and night lights, folded straight into the sky.


### 2.6.0 <small>- released 27.07.2026</small>

The biggest release since the cloud system landed: a foveated sky pipeline that puts render-resolution detail where the camera looks, a ground-up rework of cloud light transport validated against Cycles path tracing, and the toolkit that made that validation possible.

`new:`{: .label-new }

- **Foveated Sky** — the sky is now rendered at full resolution where the camera is looking, while a lighter version keeps feeding lighting and reflections everywhere else. Sharper skies in the viewport and in renders, without paying the full cost for the parts you don't see. A new `Sky Resolution` setting (Full / Half / Quarter) controls how sharp that view is.
- **Cloud lighting, validated** — every part of the cloud lighting was compared against Blender's Cycles path tracer, and the parts that disagreed were replaced with measured ones. Ambient light on clouds now comes from the actual rendered sky, so dawn golds and overcast blues finally match reality. Deep cloud interiors darken naturally while rims stay bright, giving real cumulus their bright-core, dark-outline character.
- **More control over cloud shadows** — `Shadow`, `Indirect` and `Out-Scatter` depth are now independent sliders instead of one compromise value. The "Cloud Phase" section is now **Cloud Shading**, with the related controls grouped together.
- **Ground-truth toolkit** — for the curious: render any lighting component alone (`Isolate Light`), view clouds without atmospheric haze (`Raw Clouds`), or bake the exact procedural clouds into an OpenVDB volume and render them side by side in Cycles.

`improvements:`{: .label-improvements }

- **Quality presets redefined** — all five rows (`Potato` to `NASA`) now set everything: resolution, steps, lighting quality, anti-aliasing and temporal features, in one click.
- **Physical defaults** — out of the box the lighting is now physically correct with no boost multipliers. The defaults match the release hero scene.
- **Rendering Settings reorganized** — a clearer Resolution section, sampling folded in, and the overall Quality preset always visible in the header.
- **White balance presets named by scene** — "5600 K (Daylight)", "4000 K (Sunset)", "2000 K (Candlelight)" and friends.
- Smooth motion everywhere: camera movement shows full-resolution content that refreshes continuously, and the image converges to clean anti-aliased quality the moment you stop.

`fixed:`{: .label-fixed }

- The final anti-aliased image now appears on its own in EEVEE, without needing a nudge in the UI.
- Striping artifacts on cloud decks are gone.
- Stutter while orbiting the camera is fixed.
- Reflective materials no longer show a seam from the high-detail sky region.
- The experimental "Blend Objects into Atmosphere" compositor toggle is temporarily disabled while it catches up with the new sky pipeline.


### 2.5.3 <small>- released 24.07.2026</small>

`new:`{: .label-new }

- **Live Reflections** — reflections can now follow the moving clouds automatically (off by default, as each refresh costs a little), plus an `Update Reflections` button for one-shot refreshes.
- **Cloud Time Scale** — one slider for the speed of all cloud motion. `0` freezes the sky completely, negative values run it backwards.

`improvements:`{: .label-improvements }

- Cloud rendering got roughly 20% faster in its heaviest stage.
- The five separate Rolling toggles are now one switch: `Rolling Updates (reprojected)`.

`fixed:`{: .label-fixed }

- Animation renders no longer crash at high anti-aliasing settings.
- Cloud shadows on your scene now animate during renders instead of freezing on the first frame.
- Clouds no longer drift out of place in camera view and renders at wide aspect ratios.
- Rolling updates no longer silently stop working until the file is reloaded.


### 2.5.2 <small>- released 22.07.2026</small>

The first public release of Physical Atmosphere². 🎉

`new:`{: .label-new }

- A complete, physically-based sky: atmosphere, sun, moon, planets and stars, live in the viewport.
- **Volumetric clouds** in three layers (low, mid, high) plus a rain layer, each with its own coverage, shape and lighting controls.
- **Real weather**: generate cloud coverage maps from live GFS forecast data for your scene's location, date and time.
- **Earth mode** — pick a real place, date and time and get the true sun, moon, planet and star positions. Or use **Artistic mode** and simply drag the sun and moon where you want them.
- Three interface layouts: **Simple** (one screen, no science), **Advanced** (the full working set) and **Scientific** (every knob).
- Camera-style exposure (EV or aperture/shutter/ISO), white balance, and optional compositing that blends your 3D objects into the atmosphere.
- Cloud shadows on your objects, object shadows in the atmosphere (god-rays), quality presets from fast preview to final render.
- Ships as a Blender extension for Blender 5.2+.
