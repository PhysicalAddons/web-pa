### 2.7.4 <small>- released 31.07.2026</small>

A hotfix continuing the macOS work from 2.7.3, plus two important time-zone corrections.

`fixed:`{: .label-fixed }

- **The UTC field took your offset backwards.** It wanted the sign flipped, so entering the number every other tool uses (New York `-5`, Berlin `+1`, Tokyo `+9`) put the sky hours out. The field is now **UTC Offset**, stated the normal way. Existing scenes keep the times they were saved with, and `Set Current Time` was never affected.
- **Daylight Savings now moves the displayed time too.** The sun shifted by an hour but the panel readout did not, so one of the two always looked wrong. Both now agree, and the label reads `UTC-4.0 · DST` instead of the ambiguous `+1h DST adj.`.
- **macOS: the viewport no longer freezes after rendering**, and the sky pipeline no longer stops after sitting idle or after switching to Cycles. All the remaining GPU resource leaks behind those symptoms are gone, verified across eight stress scenarios (EEVEE orbit, clouds with object shadows and a moving sun, render-then-idle, idle both ways, and Cycles on CPU and GPU) with zero leaks.
- **macOS: Cycles no longer pays for work it has no stake in**, which had quietly re-armed the same class of leak.
- Quitting Blender while the sky was updating could crash; it no longer touches the interface once shutdown has begun.
- A GPU stability hazard in the object-shadow and scene-depth passes is closed: they now prepare their geometry up front and only draw.
- The safety limit is stricter. If resources do start leaking, the add-on stops its sky pipeline earlier and leaves Blender more headroom, so the sky freezes sooner rather than risking unsaved work.


### 2.7.3 <small>- released 31.07.2026</small>

A hotfix for three crash and stability issues reported on macOS after 2.7.2.

`fixed:`{: .label-fixed }

- **Quitting Blender while the sky was updating could crash.** The add-on wrote to the status bar as Blender was already tearing its windows down. It no longer touches the interface once shutdown has begun.
- **A GPU stability hazard is closed.** The object-shadow and scene-depth passes prepared their geometry at the wrong moment, which on Apple GPUs could leak resources and eventually wedge the session. They now prepare everything up front and only draw.
- **The safety limit is stricter.** If GPU resources do start leaking, the add-on now stops its sky pipeline earlier and leaves Blender more headroom to keep working. On a machine that is already in trouble the sky freezes sooner, which is far better than losing unsaved work.


### 2.7.2 <small>- released 31.07.2026</small>

The macOS release: Apple GPUs finally get the same fast, full-featured sky as Windows and Linux. Plus much better object shadows for everyone.

`new:`{: .label-new }

- **macOS is no longer the slow path.** The sky now publishes straight on the GPU instead of copying every frame back through the CPU: about 0.3 ms per update instead of ~67 ms, and the GPU works in the background instead of blocking Blender.
- **The smooth-motion machinery runs on Mac for the first time** — reprojection, rolling updates and temporal AA were Windows-only until now.
- **3D Object Shadows work on macOS.** Previously every Mac session reported them as unavailable; they now work on every platform, with no special cases left.
- **The long-standing Mac session-killer is gone** — the framebuffer leak that could take down Blender after seconds of orbiting no longer exists on the new path (verified across 1500 orbit ticks and 1800 sky updates with zero leaks).

`improvements:`{: .label-improvements }

- **Object shadows have proper soft edges.** Penumbras now spread both inward and outward from the shadow edge, the way real ones do, and the banded "nested outlines" in long low-sun shadows are gone.
- **Shadow softness follows your sun's size** — scaling the sun with the Body Scale sliders now correctly blurs its shadows instead of keeping a razor edge.
- Object shadows are no longer one frame behind the camera.
- The sky no longer trails the geometry while panning.
- Faster, lighter sky updates on high-DPI (Retina) displays.

`fixed:`{: .label-fixed }

- **The sky now shows in the Cycles viewport again**, and it anti-aliases there properly instead of showing an aliased sun disc and horizon.
- Blender starts with no shader warnings in the console.


### 2.7.1 <small>- released 30.07.2026</small>

A crash fix for renders, and a faster first cloud bake.

`fixed:`{: .label-fixed }

- **Renders no longer crash Blender.** Blender's own `Lock Interface` setting is what keeps a render from being disturbed while it runs, and the add-on was requesting it too late to take effect. It is now switched on and kept on whenever the atmosphere is enabled, including in older files. If a render somehow still starts unlocked, the add-on stands down for its duration and renders with the last baked sky rather than risking a crash, and says so in the console.
- Two harmless but noisy TIFF warnings on every add-on load are gone.

`improvements:`{: .label-improvements }

- **The first cloud bake of a session is about 300 ms faster** — the cloud sampler's inputs are now either pre-baked into the add-on or cached on your machine after the first build. Worth knowing: the bigger wait on a first-ever cloud enable is Blender compiling the shaders (~12 s), which this does not change.

`prototypes / research:`{: .label-research }

- **Faster shader compilation was investigated and rejected.** Two passes were built to hand the graphics driver far less shader code (down to a quarter of the original size in places). A careful A/B measured no improvement at all: drivers discard unused code cheaply and spend their time optimizing what actually runs. The machinery was removed rather than shipped for no gain.
- Known limitation surfaced by that work: the main cloud shader does not compile on Blender's OpenGL backend. This is long-standing rather than new, and only reachable if Blender falls back to OpenGL. Vulkan and Metal are unaffected.


### 2.7.0 <small>- released 30.07.2026</small>

The ground release: the planet surface is now rendered entirely by the add-on's own sky renderer, with physically correct brightness, and final renders match the viewport exactly. Plus proper Cycles viewport support and large performance gains.

!!! warning "Your scenes will look different"
    The ground now has physically correct brightness, which reads about **3x darker** than before. That is the true value; compensate with `Exposure` or brighter albedos rather than by scaling the light. Golden hour also changed: light bounced off clouds now reddens and dims with the sun instead of staying noon-white, so raise `Cloud Bounce` if you had tuned it against the old behavior.

`new:`{: .label-new }

- **Bring your own planet** — the ground now has plain `Day` / `Water` / `Night` / `Height` texture slots for any planet's maps, in all interface layouts. No textures ship with the add-on; with no Day map loaded, the flat `Albedo Color` is the ground. The old `Earth Texture` toggle is gone, since a loaded Day map is the switch.
- **Ground Roughness and Ground Specular** — rough terrain stays fuller toward grazing light, and a specular sheen turns land into wet ground, ice sheets or salt flats. Both default to off.
- **Hapke land shading** — a toggle switches the land to the research-grade model used for the Moon's regolith, with an opposition `Surge` control.
- **Sunlit clouds light the ground** — the new `Cloud Bounce` knob in Ground/Earth: a broken cumulus field visibly brightens the land below, sun-tinted and self-shadowed correctly.
- **Objects cast shadows on the ground** — scene geometry now shadows the planet surface with no setup, using the existing 3D Object Shadows machinery.
- **Reflections block** — `Atmosphere Reflection` and the cloud silhouette `Mask` are now independent controls instead of hiding behind one toggle.
- **Surface Grid** — an optional reference grid over the planet surface with a cell size in meters. A scale reference and a mapping check in one.

`improvements:`{: .label-improvements }

- **Renders match the viewport** — final renders now run the exact same GPU ground shading as the viewport: water glints, sky and cloud reflections, cloud bounce and Hapke all appear in F12.
- **Proper Cycles viewport support** — Cycles now gets the same sharp foveated sky as EEVEE, converges to a crisp preview instead of getting stuck blurry or blocky, and no longer restarts its path tracing every second.
- **Twilight cleaned up** — the smooth concentric arcs around a below-horizon sun are gone, and the twilight terminator in the sky's multiple scattering is softer and physically reddened.
- **Much faster playback** — timeline playback runs up to 3x faster, and rotating the camera during playback no longer drops the frame rate.
- **The sky pauses while you model** — with all viewports in Solid or Wireframe shading, the whole sky machinery stands down and stops burning GPU, resuming the moment a rendered viewport comes back.
- **Cloud light grid is ~3x cheaper** while flying and during sun drags.
- **The temporal controls work again** — `Temporal Upscaling` and `Interleaved Sweep` now actually drive the visible sky, and the UI lists them in the order the machinery works.
- **Smarter temporal filtering (part A of the TAA arc)** — the sky's history is now sampled with a higher-quality filter on the crisp channels (cloud edges, ground shadows), and during fast camera motion stale pixels fade toward the fresh frame instead of being stretched. Fast flicks show soft but current content instead of tearing or streak residue; slow, gentle motion is untouched.
- **The download is much smaller** — roughly 38 MB instead of 101 MB, thanks to a 20x smaller moon height map and no bundled earth textures.

`fixed:`{: .label-fixed }

- A Cycles crash on Blender 5.2 during its background sky bake.
- Cloud shadows no longer smear into long streaks when descending or orbiting.
- The ground compose no longer corrupts pixels belonging to your 3D scene when compositing is involved.


### 2.6.4 <small>- released 28.07.2026</small>

macOS hotfix — the definitive fix for the "framebuffer stack depth 16" session-killer.

`fixed:`{: .label-fixed }

- **macOS**: sky updates no longer share GPU state with EEVEE's live sampling path. On Apple GPUs the sky now publishes through the same CPU path final renders have always used, so Blender's Metal image-texture machinery can no longer leak framebuffer slots and take down the session. Windows and Linux are unchanged.

`improvements:`{: .label-improvements }

- Practical trade-off on Apple GPUs only: sky updates cost tens of milliseconds instead of ~3 ms, and motion reprojection is disabled (the view re-marches instead) — a slightly less snappy sky in exchange for sessions that no longer die.


### 2.6.3 <small>- released 28.07.2026</small>

The responsiveness release: quality switches drop from seconds to a blip, the status bar narrates the heavy stages, and macOS sessions that used to die at "framebuffer stack depth 16" now diagnose themselves and keep Blender alive.

`improvements:`{: .label-improvements }

- **Quality switches are ~5x faster** (measured heavy-tick wall time ~2.9 s → 0.6 s, after the earlier shape-volume fix): the cloud light grid rebuilds in the background while the old grid keeps lighting the scene, and texture uploads skip a slow Python-list conversion on Windows.
- **The status bar narrates heavy work** ("Compiling sky shader…", "Baking cloud light grid 12/32…") — and predictably heavy updates announce themselves one frame early, so the message is actually visible during the freeze instead of after it.
- MS Multiplier defaults to 2.0 — the Hillaire multiple-scattering LUT reads better at 2x.

`fixed:`{: .label-fixed }

- **macOS**: sessions could still hit **"Maximum framebuffer stack depth 16"** through silent leaks the earlier counter never saw. Every framebuffer bind now verifies the GPU state it restores; a detected leak is logged with its exact source, and the sky stops safely at 8 lost slots — Blender survives. Please report those console lines if you see them.


### 2.6.2 <small>- released 28.07.2026</small>

Hotfix for a Windows crash in 2.6.1, plus the first responsiveness work and two cloud-shading refinements.

`fixed:`{: .label-fixed }

- **Windows: crash when switching Quality** (also possible on other platforms): the sky renderer could touch a live image texture while EEVEE was still rebuilding its world probe. The guard now waits for two completed viewport redraws instead of a time window.

`improvements:`{: .label-improvements }

- **Live status feedback**: heavy pipeline stages (shader compile, shape-volume bake, light grid, LUTs, full bakes) now announce themselves in the status bar and as a small text label riding the mouse cursor in the viewport.
- **Cloud shape volume is disk-cached**: baked once per machine, then quality switches load it back in a fraction of a second (measured 12.3 s → 0.05 s). The cache invalidates itself when the noise shader changes.
- **Quality presets only write what changed** — no more redundant shader/texture/probe rebuilds when a preset re-applies values that were already set.
- **Ground bounce reworked** (was splotchy and missed the lit undersides): cloud bases receive fuller physical ground visibility — undersides get twice the previous bounce; tops are unchanged.


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
