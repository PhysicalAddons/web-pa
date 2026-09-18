### 3.0.9-beta <small>- released 18.09.2026</small>

Panoramic cameras work under Cycles, and the night sky is physical at its defaults: the stars were far too bright, brightest of all around the celestial poles, and are now counted right. Scenes made with 3.0.8-beta open as before, with one visible change at night (see the note). Requires **Blender 5.2 or newer**.

!!! note "Your night scenes will look darker"
    Stars Brightness now ships at 1.0, the physical level, like the Milky Way's Brightness always has, and the over-counting that made every star field 12 to 23 times too bright is fixed. At the same settings the stars are about 3 magnitudes dimmer than in 3.0.8-beta. If you liked the old look, raise **Stars Brightness**: it is a plain multiplier, and the Milky Way has its own. Scenes where you never touched the slider get the new default; scenes where you set a value keep it.

`new:`{: .label-new }

- **Panoramic cameras.** Set a camera to *Panoramic* under Cycles and the whole frame gets the full-quality sky: Fisheye Equidistant, Fisheye Equisolid, Fisheye Lens Polynomial, Equirectangular, Mirror Ball and Central Cylindrical, at every field of view. Until now only a small patch in the middle of the frame got the real sky, with a visible seam around it.
- **Full quality everywhere.** The sky is computed pixel for pixel through the lens itself, so a 180° fisheye or a 360° equirectangular render is as sharp at the edge as in the centre. Sun, moon, planets, stars, clouds and the ground all land where the lens puts them, in the Rendered viewport (zoom and pan the camera view as you like) and in the render alike.
- **Composite 3D Objects works through the lens.** Objects far to the side, or behind the camera in a 360° render, get the right haze and are no longer washed out.

`improvements:`{: .label-improvements }

- **The night sky is physical at its defaults.** With Stars Brightness and Milky Way Brightness at 1.0, the stars, the planets and the Milky Way are on the same scale as the sun and the sky. We checked the rendered star field against the star catalog itself: it delivers the real light of each star to within a few percent, and the planets match their textbook magnitudes. The Milky Way is set from its image, so it is right to within about a factor of two.
- **Points stars and small planets carry their real light.** The *Points* type from 3.0.8 was 4× too bright for stars and 6× for planets. Both now match the *PSF* type.
- **The black corners of a fisheye stay black** and no longer confuse Auto exposure.

`fixed:`{: .label-fixed }

- **Stars were 12 to 23 times too bright**, and more so the higher the Star Quality: every star in the catalog was being counted several times over. Only the *Draft* quality was ever right. Every star is now counted exactly once, in every quality.
- **Stars near the celestial poles were brighter still**, up to hundreds of times in *Precise* and *Points*. The sky is now as bright at the poles as anywhere else — Polaris is bright, but not that bright.
- **The Milky Way seam.** A thin line along one meridian, ending in a radial "pinch", could show through the galaxy. It was an artefact of how the panorama was sampled at its edge.

`research:`{: .label-research }

- EEVEE has no panoramic cameras (it draws a panoramic camera as a normal one), so this is a Cycles feature. With clouds on, a panoramic view updates a little more slowly than a rectangular one.
- **Star Image 0** (a star as one pixel whatever the zoom) keeps a star's *peak* brightness rather than its total light, by design: right at a normal field of view, brighter as the view gets wider. Use the default Star Image, or *Points*, for a physically exact star field.
- The Milky Way in a very wide view is slightly softer than before. That is the correct filtering, not a loss of detail.
- Verified on Windows (Vulkan) and macOS (Metal).

!!! quote "An official statement"
    The statement issued with 3.0.8-beta still stands.


### 3.0.8-beta <small>- released 17.09.2026</small>

The addon now leaves your scene alone when you add it, Earth textures are included (a colour map, city lights, real terrain and a Milky Way ship with the addon), and the Ground section is rebuilt around two materials: Ground and Water. Scenes made with 3.0.7-beta open and look the same. Requires **Blender 5.2 or newer**. The download is larger, about 90 MB, because the maps now come with it.

!!! note "Older scenes that used a water mask"
    The Water Mask slot is gone: water is now worked out from the terrain. If an older scene used a water mask *without* a height map, its seas will be missing. Switch Height to *Image* and the included terrain brings them back.

`new:`{: .label-new }

- **Earth textures included.** Switch the ground's Base Color or Height to *Image*, or tick Emission, and the slot fills itself: NASA's Blue Marble (April), NASA's city lights, and real terrain. No download, no setup.
- **A download button on every image slot**, next to Blender's usual picker and *Open* button. Choose the month (the snow and the greenery follow the seasons) and the resolution, up to 2 km per pixel. Nothing downloads twice: if the map is already on your disk the button says **Apply** and works offline, and downloaded maps are shared by all your projects.
- **Real terrain heights.** The height map is now high-precision data from NOAA. Mountains shade smoothly instead of in steps, and coastlines are right: with the old data, low-lying land such as Florida, the Netherlands and the Ganges delta was drawn as sea. NASA's older 8-bit terrain is still behind the download button, now up to 2 km. Finer versions of the new terrain (4 km and 2 km) will appear there when they are online.
- **The Milky Way is included.** Tick *Milky Way* and NASA's galaxy map (without stars — the addon draws its own) appears. Sharper 4k and 8k versions are behind the download button.
- **Stars Type.** *Points* (the default) draws every star as one clean pixel at any zoom. *PSF* keeps the soft star image, with Quality and Star Image size controls. Planets too small to show a disc follow the same choice.
- **Water finds its own place.** With a height map, the sea appears wherever the land is below the water **Level** — no mask to paint. Raise the Level to flood the coasts, lower it to drain the seas. Without a height map, any Level above zero covers the whole planet in water.
- **Surface Grid has a Draw choice:** *On Ground* (the lines dive under the water and fade with depth), *Over Everything* (the lines stay on top of land and sea alike), or *Chart Only* (a clean map with no shading).

`improvements:`{: .label-improvements }

- **The addon no longer touches your scene when you add it.** Blender's *Color Management → Exposure* stays exactly where you left it, and the addon's own Exposure slider picks up the same number: the two now show the same value in daylight and move together. The viewport keeps its focal length (no more switch to 35 mm), and white balance starts neutral.
- **Exposure Mode starts on *Exposure***, a plain manual slider. *Auto* is still there when you want the camera to meter the scene for you. The Simple layout offers *Exposure* and *Auto*; *Physical Camera* (aperture, shutter, ISO) lives in the Scientific layout.
- **A simpler Ground section**, built around what you are actually making. **Ground**: Base Color as a colour or an image, Emission for city lights, Height flat or from an image, and Roughness. In the Simple layout that is the whole section — everything else just works. The Scientific layout adds Height Mapping, **Water** (Level, Base Color, Roughness, Extinction, Shore Softness), Reflections and the Surface Grid.
- **City glow reacts instantly.** Changing Light Pollution, its gain or its colour used to do nothing until the sun moved. It now updates at once, switches off together with the ground's Emission, and large city-light maps no longer freeze Blender while they load.
- **Switching the Atmosphere off is fast** (it was, oddly, slower than leaving it on), and the addon keeps out of scenes where it is switched off: their renders are no longer touched or slowed.
- **Atmosphere Reflection is on by default.** Sky reflections on water and shiny ground are more accurate, at a small cost in speed. The switch is in the Scientific layout under *Ground / Earth → Reflections*.
- **Controls that did nothing useful are gone:** the ground Bounce slider (the bounce is simply physical now; the Base Color controls it), the Water Mask slot and the Water Depth slider, the Cloud Mask slider, the Milky Way's shader dropdown with the procedural galaxy (the Milky Way is an image now, and much cheaper to render), and the Cycles reference tools, which were only there for our own testing.

`fixed:`{: .label-fixed }

- **Command-line renders now animate.** Rendering from the command line, or through tools that do (render managers), used to produce the sky saved in the file, frozen. The sky now follows the animation there too. *(Reported by a customer — thank you.)*
- **The Milky Way was far too dim.** In some setups it stayed almost black however high you pushed its Brightness. It is now visible at night straight away.
- **Shore Softness now works** — it had no effect before. Set it to 0 for a hard, exact coastline.
- **The night side of the planet, seen from orbit, no longer glows.** The dark ground was wrongly mirroring the daytime sky from under the camera.
- **No more white line under a rising or setting moon.** Where the moon or the sun touched the sea horizon, the bottom row of the disc could turn pure white, most visibly through a long lens.
- Changing star settings now updates the sky right away.
- **macOS:** two shader errors that could appear in the console at startup.

!!! quote "An official statement"
    There is no hidden feature in this release.

    There is certainly no reason to fold and unfold "Sky & Observer" ten times in a row.

    The Earth is round. Please disperse.

<small>Earth imagery: NASA Earth Observatory (Blue Marble Next Generation, Black Marble). Terrain: NOAA ETOPO 2022. Milky Way: NASA/Goddard Space Flight Center Scientific Visualization Studio; Gaia DR2: ESA/Gaia/DPAC.</small>


### 3.0.7-beta <small>- released 10.09.2026</small>

A new sky rendering engine, vastly improved stability and performance, auto exposure, atmospheric refraction, improved planets, and objects and lamps that take part in the atmosphere and clouds. Requires **Blender 5.2 or newer**. Validated on Windows (Vulkan) and macOS (Metal); Linux/OpenGL has not had a full pass yet.

!!! note "The clouds are an interim system"
    The clouds in this release are temporary. Development of the real cloud system is ongoing and they will be replaced in a later release — treat the cloud controls as provisional.

`new:`{: .label-new }

- **A faster, more accurate sky.** The sky is now computed from precomputed lookup tables (based on Hillaire's atmosphere model) instead of being marched pixel by pixel. It costs about half as much and matches a fully converged reference to within half a percent on a clear day. The old method is still there as the reference option if you want to compare.
- **Improved night sky.** Moonlight actually lights the sky and the ground, and follows the real phase curve (a quarter moon is no longer four times too bright). Starlight and airglow are in. Light pollution comes from real night-lights data — from a city map or as a hemisphere glow — and reaches the undersides of clouds. There is a Milky Way (off by default; it follows the Stars toggle), bright stars have proper halos, and the exposure range now goes all the way down to a dark night.
- **Auto exposure, auto white balance, auto range.** Exposure meters the scene the way a camera does — the bright part of the frame lands on middle grey, dark scenes are allowed to stay dark, and the viewport eases into changes like an eye would while renders use the settled value. White balance is taken from the actual light falling on the scene. The storage range that keeps highlights from clipping is placed automatically. Auto is the default exposure mode.
- **Choose what Auto exposure meters.** *Sky* meters the atmosphere alone (the previous behaviour). *Viewport* meters what you actually see in the Rendered viewport — your objects, lamps and glowing materials included — so an interior or a wall no longer gets exposed for the sky behind it. *Incident* works like a handheld light meter: it exposes for the light on the scene and ignores what is in frame. The info box tells you which meter delivered the reading.
- **Atmospheric refraction.** Light rays now bend through the air. The sun flattens and lifts at the horizon, you get mirages with an adjustable inversion layer and gentle waves, heat shimmer close to the ground, and colour fringing at the sun's edge. Every part has its own switch, and it ships with a tuned mirage layer.
- **Saturn, Uranus and Neptune have rings.** Saturn's position comes from a bundled ephemeris table, the rings are lit physically, the gas giants have haze with a blue limb and seasonal poles, and planets are properly flattened at the poles. The full Cassini mission trajectory is bundled as a flight-path preset.
- **Your lamps light the scene's atmosphere.** Blender Point and Spot lights now light the addon's ground, the air and the clouds, using the same light law EEVEE uses on your meshes.
- **Your objects shadow the clouds.**
- **Cycles reference atmosphere** (Scientific): one button builds a path-traced twin of the atmosphere, with a switch to A/B it against the real-time sky.
- **Artistic Sky Color:** pick the sky's scattering colour and strength directly in the Simple layout.
- Altitude can be typed in kilometres or metres; in Artistic mode you can rotate the sun lamp itself and the sun follows; the sun, moon and planets have gizmos in the viewport.

`improvements:`{: .label-improvements }

- **Clouds are faster and sharper.** The cloud pipeline was rebuilt (ported from KSA): cloud passes are about five times faster, clouds are composited at full resolution regardless of the Atmosphere Resolution setting, and cloud shadows no longer flicker when the camera moves. See the note above — this is the interim system.
- **The sky is pixel-exact.** The sky is rendered at exactly the size it appears on screen (the camera frame in camera view), and renders get full-resolution pixels. Atmosphere Resolution now only affects the air haze texture.
- **A better ground.** Land and water share one physically based shading model with proper roughness, and reflections of the sun and moon on water are exact. With the ground turned off the world is bottomless by default.
- **The Range slider no longer changes your lamps.** Moving the range placement (or Auto Range doing it for you) used to make the scene's own lamps brighter or darker. It doesn't any more.
- **Objects blend into the atmosphere properly.** Geometry is cut into the sky with a clean silhouette and depth-correct haze, and the compositor setup is lighter.
- **Cycles updates faster.** The sky arrives as a quick draft first and a full-resolution image once you stop moving; Cycles no longer waits half a minute for it.
- **Two interface tiers instead of three.** *Simple* has the everyday controls, *Scientific* has everything. If you had *Advanced* selected, you'll land on Simple — pick Scientific once. Moon, Ground and the refraction toggle are now in Simple; the three cloud layers have their own groups; the exposure readout speaks in photographic EV; Post Processing shows its mode in the header.
- **Removing the atmosphere restores everything it changed** — your previous world, exposure, white balance, view transform and render lock — and several scenes in one file can share the atmosphere without stepping on each other.

`fixed:`{: .label-fixed }

- **Remove Atmosphere no longer crashes Blender**, and the crash that could happen when adding the atmosphere is fixed at the root.
- **macOS:** the cloud noise and the Milky Way compile again, and animation renders no longer leak GPU memory frame by frame.
- **The sun gizmo moves the sun** like it used to in Physical Starlight and Atmosphere, and adding, removing and re-adding the atmosphere leaves the sun where it was.
- A scrambled sky in renders on early 5.2 alpha builds; a bright seam at the planet's horizon; a white line under a setting sun; a dark line under the horizon at reduced Atmosphere Resolution; the far cloud deck ending in a straight edge from high orbit; banding in twilight cloud decks; the mirage sun sliced into bands; holes in the ground along a shimmering horizon in renders.
- No more "Save modified images" prompt for the addon's own images; a docked File or Asset Browser no longer pauses the sky; the sun disc's brightness and limb darkening now match measurements.

`research:`{: .label-research }

- Lock Interface is required while the atmosphere is enabled (Blender needs it to render safely). Removing the atmosphere restores your setting.
- In background and animation renders, Blender gives add-ons no GPU access after the first frame, so the baked sky (atmosphere and clouds) cannot update per frame in that job. The sun, moon and planets still move.
- The Viewport meter needs a 3D viewport in Rendered shading; renders reuse its last reading, and the Sky meter takes over when there is none.


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
