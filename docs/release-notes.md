### 3.0.7-beta <small>- released 10.09.2026</small>

A beta of the 3.0 series, and everything since 2.8.1: a new sky engine, a real night, auto exposure, atmospheric refraction, ringed planets, and objects and lamps that take part in the atmosphere. Requires **Blender 5.2 or newer**, installed as an extension (drag the ZIP into Blender, or *Preferences → Get Extensions → ⌄ → Install from Disk…*); it updates 2.8.1 in place. Validated on Windows (Vulkan) and macOS (Metal); Linux/OpenGL has not had a full pass yet.

!!! note "The clouds are an interim system"
    The clouds in this release are temporary. Development of the real cloud system is ongoing and they will be replaced in a later release — treat the cloud controls as provisional.

`new:`{: .label-new }

- **A new sky engine by default — LUT Atmosphere.** The visible sky now resolves from a lookup-table chain based on Hillaire's atmosphere model, at about half the cost of the old march and verified against a converged reference (clear sky 0.5 %, civil twilight 4.5 % P95). It runs in renders and at night, follows the refracted path, and lights the reflection probe. The analytic march stays available as the reference option.
- **A real night.** Physical night calibration; the moon lights the atmosphere with the measured lunar phase curve; starlight and airglow join the multiple scattering with a **Starlight MS** slider; **light pollution** from real night-lights data (city map or hemisphere modes, single-city blobs, a Night Lights colour) that reaches the cloud undersides; a **Milky Way** (off by default, follows the Stars toggle); bright stars with proper halos; and an exposure range that reaches deep night (EV cap 32, EV minimum −21).
- **Auto exposure, auto white balance, auto range placement.** A percentile-band meter with an adaptation curve (eased like an eye in the viewport, settled in renders), white balance from the physical illuminant, and the fp16 storage window placed automatically from the brightest source in the shot. Auto is the shipped exposure mode.
- **Meter choice for Auto exposure — Sky / Viewport / Incident.** Meter the atmosphere alone, the whole Rendered viewport (objects, lamps and emission included), or the incident light like a handheld meter. The info box names the meter that delivered the reading.
- **Atmospheric refraction, stage 1.** Bent view rays, mirages with an elevated inversion and internal gravity waves on the layers, near-field heat shimmer on turbulence physics, heat blur, spectral dispersion and a North Offset — every feature its own switch, shipping with a tuned mirage layer.
- **Saturn, Uranus and Neptune with rings.** Accurate Saturn ephemeris from a bundled Horizons table, physical ring light transport with an exact annulus integral, gas-giant haze with a blue limb rim and seasonal blue pole, oblate planet discs on the true poles, and the full Cassini mission trajectory bundled as a path preset.
- **Scene Lights.** Blender Point and Spot lamps light the addon ground, the air and the clouds, using EEVEE's own light law.
- **Objects and clouds.** Your objects shadow the clouds, and scene lamps light them.
- **Cycles Reference Atmosphere** (Scientific): one button builds an Earth-sized path-traced twin of the pure atmosphere, with a Reference Mode switch to A/B it against the real-time sky.
- **Artistic Sky Color**: a normalised scattering-colour picker with a Strength multiplier in the Simple layout.
- **Altitude in km and m**, a **two-way sun lamp** in Artistic mode (rotate the lamp, the sun follows), and celestial gizmos.

`improvements:`{: .label-improvements }

- **Clouds rebuilt** on a pipeline ported from KSA: a baked density model with a per-layer weather chart and a Worley mip atlas (about 5× faster cloud passes), 3×3 interleaved sampling with motion vectors, a quality ladder that drives the march, clouds composited at full resolution whatever the Atmosphere Resolution, and a shadow volume anchored to a fixed 1 km cell that no longer flickers under camera motion.
- **1:1 window sky.** The sky rectangle is sized to the exact on-screen pixels (the camera frame in camera view) and renders serve full-frame pixels; **Atmosphere Resolution** now only scales the air texture.
- **Principled ground.** One GGX lobe unifies specular, sky reflection and roughness on land and water; exact sun and moon disc speculars; reflections carry multiple scattering and ozone. Ground off is bottomless by default.
- **Range Placement is brightness-neutral** — the slider only places the fp16 storage window, the display exposure compensates — and the scene's own lamps now follow it through their Exposure field, so they no longer drift when it moves.
- **Objects cut into the sky** with a hybrid silhouette + haze composite that puts depth-correct aerial perspective on geometry; the compositor is AOV-only and lighter.
- **Cycles** gets a two-tier sky publish (a tiny draft, then a 1:1 settled image), follows dragging promptly and no longer waits half a minute for the sky.
- **Interface: Simple and Scientific.** The Advanced tier is gone — Simple carries the everyday controls, Scientific everything (a saved Advanced preference falls back to Simple; pick Scientific once). Moon and Ground sections and the refraction toggle join the Simple layout; the three cloud decks get their own groups; the EV100 readout speaks photography; Post Processing carries its mode in the header.
- **Removing PA2 restores everything it changed** — the previous world, exposure, white balance, view transform and render lock — and resources are shared correctly across several enabled scenes.

`fixed:`{: .label-fixed }

- **Remove Atmosphere no longer crashes Blender**, and the enable-path crash family (draw-callback writes racing the world sync) is root-caused and closed.
- **macOS:** the cloud noise and the galaxy compile again on Metal, and animation renders no longer leak a GPU stack slot per frame.
- **The sun gizmo moves the sun again** in Artistic mode, and Add → Remove → Add leaves the sun where it was.
- A rendered sky scrambled on 5.2.0-alpha builds (reversed readback strides); a bright seam on the planet horizon; the white horizon line under a setting sun; a dark line under the horizon at reduced Atmosphere Resolution; the far cloud deck ending in a rectangle from high orbit; twilight decks with stripy gradients; the mirage sun sliced into bands; holes in the ground along a shimmering horizon in renders.
- No more "Save N modified images" prompt for PA2's datablocks; a docked File or Asset Browser no longer pauses the sky; a quarter moon no longer runs 4× hot; the sun disc's limb darkening and brightness are the measured ones.

`research:`{: .label-research }

- Lock Interface is required while PA2 is enabled (Blender needs it to render safely); removal restores your setting.
- Background and animation renders: Blender provides no GPU context to add-ons after the first frame, so the baked sky cannot update per frame in that job. Sun, moon and planet motion still renders.
- The Viewport meter needs a Rendered-shading 3D view; renders reuse its last reading, and the Sky meter stands in when there is none.


### 2.8.1 <small>- released 12.08.2026</small>

The last release before the 3.0 series (2.8.0 on 07.08.2026 was a defaults test build). Most of this work was reworked again in 3.0; it is listed here for completeness.

`new:`{: .label-new }

- **The KSA cloud march ships as the cloud renderer**, with a shadow volume for cloud shadows and godrays, interleaved rendering with motion-vector reprojection, and cloud shadows on 3D objects.
- **Ground shadow modes** and an exact far-object depth in the composite.
- **Two-way exposure**: the Color Management slider and the camera EV mirror each other, and the EV100 readout is scene-referred.
- A tonemapper family for the compositor (with the AgX pink fix), sphere-light sun and moon speculars on the ground, and the compute sky path enabled on Vulkan.

`fixed:`{: .label-fixed }

- The envmap and reflections could freeze under Cycles; the ground shifted while the sky accumulated; a long-session freeze from the jitter sequence; several Metal hardening fixes in the draw callbacks.


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
