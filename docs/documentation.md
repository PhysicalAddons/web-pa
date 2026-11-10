

!!! tip ""
    Hey👋, first time here? You can find the installation guide and first run in the [getting started](/physical-atmosphere/getting-started/) section.

This page follows the panel from top to bottom, as of **3.0.8-beta**. The add-on has two interface layouts, picked at the top of the panel: **Simple** shows the everyday controls, **Scientific** shows everything. Each section starts with what you see in Simple; controls marked *Scientific* only appear in that layout.

* [Sky & Observer](#sky-observer)
* [Camera Settings](#camera-settings)
* [Atmosphere](#atmosphere)
* [Clouds](#clouds)
* [Cloud Maps](#cloud-maps)
* [Sun, Moon & Planets](#sun-moon-planets)
* [Ground / Earth](#ground-earth)
* [Stars](#stars)
* [Rendering Settings](#rendering-settings)
* [Flight Path](#flight-path)
* [Overlay](#overlay)

!!! note "Adding the atmosphere leaves your scene alone"
    Since 3.0.8 the add-on does not change your exposure, your white balance or your viewport when you press `Add Atmosphere`. Its Exposure slider simply picks up the value your scene already had, and `Remove Atmosphere` restores whatever the add-on did change, such as your previous world and colour settings.



## Sky & Observer

This is where you decide where the sun is. There are two ways to work:

**Artistic** — you place the sun by hand. Perfect when you care about the picture, not the calendar.

**Earth** — you give a real place, date and time, and the add-on computes where the sun, moon and planets actually are in the sky.

### Artistic mode

- **Sun rotation** — `Horizontal` and `Vertical` angles. You can also grab the sun handle in the viewport and drag it, or rotate the sun lamp itself: the sun follows. The moon has its own rotation in the [Moon](#moon) section.
- **Observer** — `Lat`, `Lon` and `Altitude` still matter for the look of the sky (they affect the atmosphere and the stars), even when the sun is placed by hand. Altitude can be typed in kilometres or in metres; the two fields are the same value.
- **North Offset** — turns the whole modelled world (sun, moon, planets, stars, cloud map, ground and compass) about the vertical, so true north can sit at any angle from the scene's +Y axis. Useful when imported geometry, such as a building or a GIS model, has its own orientation.
- **Body scale** *(Scientific)* — one `Distance` / `Radius` pair scales all celestial bodies at once. Great for dramatic oversized moons. `Scale Earth` extends the scaling to the planet itself, and `Sun Energy Conservation` keeps the scene brightness sensible while you scale.

### Earth mode

- **Location** — press the search button to pick a city from the built-in list, or use the auto-detect button to find where you are (requires internet).
- **Coordinates** — latitude and longitude, if you'd rather enter them directly. *Scientific* adds a text field that takes coordinates pasted from an online map.
- **North Offset / Altitude** — as in Artistic mode. Go up far enough and you'll see the sky darken and the horizon curve.
- **Time / Date** — the moment you're rendering. The clock button sets the current date and time. An info box below shows the resolved date, local time and UTC time.
- **UTC Offset / Daylight Savings** *(Scientific)* — time-zone corrections, for when the automatic zone isn't the one you want.



## Camera Settings

Controls how bright the sky is on screen and how the picture is developed. In the Simple layout this section is called **Post Processing**, and its header carries the exposure mode.

### Exposure

Pick an **Exposure Mode**:

- **Exposure** (the default) — one `Exposure (EV)` slider. Up is brighter, down is darker. In daylight it shows the same number as Blender's own *Color Management → Exposure*, and the two move together: change either one, the other follows.
- **Auto** — the add-on meters the scene the way a camera does, and the slider shows the metered value. Dark scenes are allowed to stay dark, and the viewport eases into changes like an eye would, while renders use the settled value.
    - `Meter` chooses what is measured. *Sky* meters the atmosphere the camera sees. *Viewport* meters what the Rendered viewport actually shows, your objects, lamps and glowing materials included, so an interior is not exposed for the sky behind it (it needs a 3D viewport in Rendered shading). *Incident* works like a handheld light meter: it exposes for the light falling on the scene and ignores what is in frame.
    - `Compensation (EV)` brightens or darkens the metered result.
    - *Scientific* adds the adaptation curve: `Adaptation` (how much of a dark scene Auto brightens), `Adaptation Speed (s)` and `Full Adaptation Above (EV100)`.
- **Physical Camera** *(Scientific)* — set it like a real camera: `Aperture`, `Shutter Speed`, `ISO` and an `Exposure Bias (EV)` for fine-tuning.

### White Balance (K)

Pick the preset that matches the light in your scene and that light is neutralised: the low presets, from `2000 K (Candlelight)`, cool down warm light such as candles, tungsten or a sunset; the high ones, up to `12000 K (Blue Shade)`, warm up the bluish light of shade and overcast skies. The default, `6500 K (Neutral / Off)`, applies no shift at all and leaves your scene's own white balance alone. `Auto` takes the white point from the actual light falling on the scene (sun, sky and moon), follows the sun live, and shows the temperature and tint it arrived at.

### Range *(Scientific)*

`Range (Night 0 – Day 1)` places the add-on's internal brightness window: bright daylight at one end, a dark night at the other. It never changes how bright the picture looks. `Auto` is on by default and places the window from the brightest thing the render has to hold. Leave it on unless you have a reason not to: with the window parked at the day end, a night sky (Milky Way, stars, airglow) is too faint to be stored, however high you push its brightness. `Sun-safe placement` keeps room for the sun's reflections on your objects whenever the sun is up.

The info box underneath reads the exposure out as a photographic `EV100` value with a plain description ("Bright direct sunlight, clear sky"), plus the current world offset.

### Blend Objects into Atmosphere

An experimental compositing mode where your 3D objects are blended into the atmosphere by the add-on: distant objects pick up the same haze and light as the sky around them, with a clean silhouette. Tonemapping is then handled by the add-on (a `Tonemap` dropdown replaces the two rows below), and Blender's Color Management has no effect while it is enabled. In the Scientific layout the toggle is called `Composite 3D Scene (Experimental)` and adds an `Object Coverage` choice.

### Color Management

`View Transform` and `Look` are Blender's own settings, surfaced here for convenience.



## Atmosphere

The air itself. The checkbox in the header turns the whole atmosphere layer on or off.

- **Pollution** — a slider through real types of air, from the cleanest (Antarctic) to the dirtiest (Urban). The name of the current profile is shown on the slider.
- **Haze** — how much of that dust, smoke and salt is in the air. Low values give crystal-clear air; high values give thick haze.
- **Artistic Sky Color** — replaces the physical blue of the sky with a colour of your choice. `Color` sets the balance between red, green and blue, `Strength` how thick the air scatters. Redder gives a Mars-like sky, white a colourless grey haze. Off means real air.
- **Atmospheric Refraction** — the air bends light near the horizon. This is what makes the sun flatten and lift as it sets, lets you see it slightly after it has geometrically set, and produces mirages. Off by default; one checkbox turns it on.

### Atmosphere in the Scientific layout

- **Multiple Scattering** — light bouncing around in the air more than once. Keeps the sky from looking too dark, especially around sunset. Normally you leave this on.
- **Atmospheric Refraction**, in full: `Strength` exaggerates or reduces the bending. `Ray March` bends rays step by step, which is what mirages, the view from orbit and lifted ground need. `Mirage Layers` adds the thermal structure near the ground: `Ground ΔT (K)` for sun-heated ground (the low "reflection" of an inferior mirage) or a cold surface (looming), and an `Inversion` layer higher up with presets after real simulated sunsets (*Mock Mirage*, *Duct*, *Sub-duct / Santa Ana*) or a *Custom* one, optionally with slow `Waves` running through it. `Shimmer` is heat haze: the rippling edge of a low sun and twinkling stars, driven by turbulence strength, `Wind` and `Updraft`, with `Heat Blur` for the soft part. `Dispersion (green flash)` splits colours at the sun's rim, and `Sub-frame Dither` smooths banding where a mirage folds the sun.
- **Rayleigh** — the scattering that makes the sky blue during the day and red at sunset. Below it sit the state of the air: `Rayleigh Model` (Earth air or a generic gas mix), `Sea-Level Air Temp`, `Pressure`, `Gravity`, `Relative Humidity` and `CO2 Mole Fraction`, with an info box of the derived values.
- **Aerosols** — `Aerosol Mode` (the OPAC presets, or fully manual), `Turbidity` and the `OPAC Profile` dropdown (the Simple layout's Pollution slider drags through the same profiles), plus an optional low haze layer (`Bump Peak`, `FWHM`, `Bump Amount`).
- **Ozone** — the ozone layer's subtle influence on sky color: it deepens the blue of twilight. The monthly ozone value for your location and date is shown below the toggle.
- **Light Pollution** — the glow of cities in the night air, lighting the sky and the undersides of clouds. `Constant` is a uniform city glow everywhere; `Night Lights Map` and `Night Map (Hemisphere)` make the glow follow the ground's [Emission](#ground) map, so real cities glow where they are (the Hemisphere version is the sharpest from ground level). `Gain` scales it. The glow shares the Emission tint, updates the moment you change it, and switches off together with Emission.
- **Airglow** — the faint natural glow of the night sky itself, visible on clear moonless nights. `Scale` controls its strength; the three emission lines underneath are there for research.



## Clouds

Volumetric clouds, enabled with the checkbox in the section header.

!!! note "The clouds are an interim system"
    The clouds in the 3.0 betas are temporary. Development of the real cloud system is ongoing and they will be replaced in a later release, so treat the cloud controls as provisional.

- **Coverage** — the master slider: how much of the sky is covered in clouds, from clear skies to overcast.
- **Layers** — clouds live in three layers: `Layer 1 — Low (cumulus)`, `Layer 2 — Mid` and `Layer 3 — Cirrus`. Each has an enable checkbox, `Altitude (m)` and `Height (m)` (where the layer floats and how thick it is), and `Density Scale` (how dense, dark and opaque its clouds are).

### Clouds in the Scientific layout

The layers become tabs (`L0`, `L1`, `L2`, plus a `Rain` layer), and the selected layer shows everything:

- **Placement** — `Altitude (m)` and `Height (m)`. `Show Cloud Profile` draws the layers' vertical profile over the 3D view.
- **Layer Shape** — four sliders that sculpt the cloud silhouette: `Flat Base` (flat cumulus bottoms), `Crown Start` (where the puffy top begins), `Waist Erosion` (eats away the middle, leaving separate towers), `Crown Lean` (how few cells reach the top).
- **Coverage** — `Global` is where on the planet this layer has clouds: none, the built-in map, or your own image. `Local` is the repeating weather pattern that shapes cloud fields around you, built-in or your own. `Local Coverage Exp` and `Coverage Filter` sharpen or soften it.
- **Density & Material** — `Density Scale`, and `Droplet (µm)`: the size of the water droplets, which subtly changes how the clouds catch light.
- **Shape Noise** — `Shape 1/m` is the size of the large cloud shapes (smaller values make bigger formations); `Shape Amount` is how strongly they erode the clouds.
- **Wind & Skew** — `Skew Amount` / `Skew Curve` lean the clouds with altitude, like wind shear does; `Wind Phase` turns this layer's wind so decks can cross.

Around the tabs:

- **Map Strength** — blends between uniform coverage and the global cloud map.
- **Shape Volume** — the resolution of the 3D noise the clouds are carved from, with a button to regenerate it.
- **Local Coverage UV Repeat / UV Offset** and **Anti-Tiling** — the size and position of the repeating weather pattern, and hiding its repetition across large cloud fields.
- **Animated Clouds / Time Scale** — whether the clouds move with the timeline, and how fast. `0` freezes the sky completely, negative values run it backwards.
- **Cloud Optics (Mie)** — how strongly cloud droplets scatter and absorb light.

Wind, detail noise and turbulence controls join the section when `Density Model` (in [Rendering Settings](#rendering-settings)) is set to *Procedural (PA2)*.



## Cloud Maps

*(Scientific; a box at the bottom of the Clouds section.)* Real weather for your clouds. Using your scene's date and time, the add-on downloads the matching global cloud forecast (GFS weather data) and turns it into coverage maps.

- **Output location** — save the maps next to your .blend file (`Project`) or into a folder of your choice (`Custom Folder`). The folder in use is shown at the bottom of the box.
- **Generate Cloud Map** — downloads the forecast nearest to your scene's date/time and builds the maps (requires internet). The download runs in the background with a `Cancel Download` button.
- **Use as Cloud Coverage Maps** — plugs the generated maps into the cloud layers, so the sky above your chosen location matches the real weather for that moment.

!!! tip
    Scene set to today, location set to your city, `Generate` + `Use`, and you're rendering under today's actual sky.



## Sun, Moon & Planets

Each body has its own section with a visibility checkbox in the header. The Moon is in both layouts; the Sun and Planets sections are *Scientific*.

### Sun

- **Distance / Radius (km)** — in Artistic mode, place and size the sun disc freely.
- **Lamp / Physical Sun Energy** — the sun lamp the add-on keeps aligned with its sun. With `Physical Sun Energy` on, the lamp's strength and colour come from the atmosphere itself, sunset reddening included.
- **Spectrum** — the sun's light spectrum: the measured solar spectrum (AM0), or a Blackbody model where you pick the temperature (useful for alien suns or stylized skies).
- **Spectral Samples** — how finely the spectrum is sampled; higher is more accurate.

An info box shows the sun's radiance and the illuminance it delivers.

### Planets

In Earth mode, Mercury through Neptune appear in their true positions for your location, date and time. In Artistic mode you can set each planet's distance and radius yourself. `PSF Brightness` scales the planets while they are points of light, `Sun Light` the brightness of a resolved disc, and `Haze Scattering` / `Haze SSS` the blue limb of the gas giants. Saturn's rings have their own group (their sunlit and unlit sides, and the light the planet and the rings throw on each other), a `Textured Disc` switch, and a `Saturn Ephemeris` choice: the *Accurate (Cassini era)* table puts Saturn exactly where the bundled Cassini flight paths expect it.

### Moon

The moon renders with its correct phase and its familiar face. In Earth mode its position follows the real sky; in Artistic mode you place it by hand with `Rotation` (or drag its handle in the viewport) and, in Scientific, can change its `Distance` and `Radius`. `Sun Light` and `Earth Light` scale the brightness of its sunlit side and of the earthshine on its dark side (1.0 is physical).



## Ground / Earth

The planet under your feet, rendered by the add-on itself. The section is built around what you are making: a **Ground** and, if you want it, **Water**, each in its own box with an on/off checkbox. The checkbox in the section header switches the whole planet off, which leaves the world bottomless.

Earth textures are included. Pick *Image* for the Base Color or the Height, or tick Emission, and the slot fills itself with a map that ships with the add-on: NASA's Blue Marble (April), NASA's city lights, and real terrain from NOAA. Your own maps of Earth, Mars or something invented work just as well. A slot that already holds an image is never replaced.

!!! note "Physical brightness"
    The ground is normalized physically, so it reads darker than a plain texture would. That is the correct value; compensate with `Exposure` or a higher `Brightness` rather than by scaling the light.

### Ground

- **Base Color** — *Color* is one colour for the whole ground. *Image* is a colour map of the planet, seen from altitude; `Brightness` scales it to a believable surface brightness (satellite imagery is brighter than real ground, about 0.5 is physically plausible).
- **Bounce Tint** *(Scientific, with an image)* — the colour of the light the ground bounces back into the sky and onto cloud bases. With *Color*, the ground colour does this job itself.
- **Emission** — tick it for city lights and other night-side glow, faded in around dusk, with a tint and a `Strength`. The same map drives [Light Pollution](#atmosphere-in-the-scientific-layout).
- **Height** — *Flat* is a smooth planet. *Image* is terrain elevation: mountains catch the light, and water finds its place by itself (see Water below).
- **Roughness** — `0` is mirror-sharp, higher values give a broad, soft sheen. **Specular** *(Scientific)* adds the sheen of wet ground, ice sheets or salt flats; `0` is off.

**Image slots** look like Blender's own: the usual picker and an *Open* button for your own files. Next to them is a **download button** for more maps straight from NASA: other months of the Blue Marble (the snow and the greenery follow the seasons), higher resolutions up to 2 km per pixel, and NASA's older 8-bit terrain. Downloads need Blender's online access and run in the background with a Cancel button. Nothing downloads twice: if a map is already on your disk the button says **Apply** and works offline. Downloaded maps are kept in the same maps folder as the [Cloud Maps](#cloud-maps).

**Height Mapping** *(Scientific)* — how the height image is read: `Terrain Range (m)` is how tall the terrain is, `Zero Level (m)` where sea level sits in the data. For the included and downloaded maps both are filled in for you. `Height Normals` lets the relief show in the lighting, `Bicubic Sampling` smooths coarse maps, and the `Color Space` of a height map should stay on `Non-Color`.

### Surface Grid *(Scientific)*

An optional reference grid inside the Ground box, doubling as a scale reference and a mapping check. Choose the `Type` (*Local (metric)*, *Cube-Sphere* for orbital views, or a true *Latitude / Longitude* graticule), the `Cell` size (metres, or degrees for the graticule), `Ink` for line strength and up to three levels of `Major` lines. `Draw` decides how the grid meets the surface: *On Ground* (the lines dive under the water and fade with depth), *Over Everything* (on land and sea alike) or *Chart Only* (a clean map with no shading). `Geo-Anchored` locks the grid to the planet rather than to the scene.

### Water *(Scientific)*

In the Simple layout water is simply on, with sensible defaults. Scientific shows its box:

- **Level (m)** — where the water stands. With a height map, the sea appears wherever the land lies below this level, so there is no mask to paint: raise it to flood the coasts, lower it to drain the seas. Without a height map, any Level above zero covers the whole planet in water.
- **Base Color** — the colour deep water tends to.
- **Roughness** — of the water surface, which spreads or tightens the sun and moon glints.
- **Extinction (1/m)** — how quickly light fades with depth, per colour. The defaults are real: red dies within metres, blue only after a hundred, which is why shallow water is turquoise and deep water blue. Raise all three for murky water.
- **Shore Softness** — the width of the coastline in pixels. `0` is a hard, exact coastline.

### Reflections *(Scientific)*

- **Atmosphere Reflection** — more accurate sky reflections on water and shiny ground, most noticeable near the horizon. It costs an extra rendering step, and is on by default.



## Stars

The real night sky: stars appear in their correct positions for your location, date and time.

- **Stars Type** — *Points* (the default) draws every star as one clean pixel at any zoom. *PSF* draws a soft star image, so bright stars grow a small disc and a halo; it adds `Quality` (from *Draft* to *Precise*) and `Star Image (arcmin)`, the size of a star's image. Planets too small to show a disc follow the same choice.
- **Brightness** — how prominent the stars are. `1.0` is physically exact, which reads faint on screen at ordinary night exposures; the default is 10.
- **Starlight in Atmosphere** — the faint light the stars themselves add to the night air and the ground.
- **Milky Way** — tick it and NASA's galaxy map (without stars, the add-on draws its own) fills the slot. It follows the Stars checkbox. The slot works like the [ground's image slots](#ground): your own panorama through the picker, or sharper 4k and 8k versions from the download button. `Coordinates` says how your panorama is laid out (*Galactic* is the usual Milky Way panorama, *Celestial* matches star maps), and `Milky Way Brightness` scales it, with `1.0` being physical.

!!! tip "A night sky that stays black"
    If the Milky Way and stars stay dark however high you push their brightness, check `Range` in [Camera Settings](#range-scientific): its `Auto` should be on.



## Rendering Settings

Everything here trades quality against speed. The easiest way is the **Quality** preset dropdown, always visible in the section header: `Potato` to `NASA` sets everything below in one go. Expanding the section reveals the per-category presets (`Resolution`, `Reflections`, `Atmosphere`, `Clouds`); in the Simple layout, called **Quality**, that is the whole section. Change any individual value in Scientific and the preset shows `Custom`.

The sky is rendered at exactly the size it appears on screen, and final renders get full-resolution pixels. A lighter, all-around version of the sky feeds the lighting and reflections on your objects.

### Resolution *(Scientific)*

- **Atmosphere Resolution** — the resolution of the soft air haze only (`1x` to `0.25x`). Stars, planets, sun, moon and the ground always render at full resolution, so lower values are nearly free visually.

### Reflections *(Scientific)*

- **Reflection Probe / Probe Resolution** — the all-around sky that lights your objects and appears in their reflections, and how sharp it is.
- **Reflect Clouds** — whether clouds are part of it. Off is much cheaper; reflections and world lighting then ignore the clouds.
- **Simplified / Fast / LUT Lighting Sky** — three shortcuts that make that lighting sky cheaper without changing how bright it is. Final renders always use full lighting quality.
- **Probe Update** — refresh the lighting on every change, or once after changes settle.
- **Live Reflections** — automatically refresh reflections as the clouds move, at the chosen `Interval (s)`. The refresh button next to it updates reflections once, on demand.

### Visible Sky *(Scientific)*

- **Viewport TAA Samples** — on a still view the sky refines over this many rounds, then rests. Higher is smoother but takes longer to settle.
- **Render Samples (F12)** — the same for final renders and animation frames.
- **Cloud Jitter / Atmosphere Jitter** — a little per-pixel noise that the samples above average away; off gives noise-free single frames at the cost of visible banding.
- **Atmosphere Cloud Shadows** — clouds shadow the air: sun shafts through gaps. Off lights the air as if the sky were clear.
- **LUT Atmosphere** — the fast, precomputed sky (on by default). Off switches to the slower reference method, for comparison.
- **Interleaved Clouds** — spreads the cloud work over several frames while you move; still views sharpen to full detail. Viewport only.
- **Base Step / Step Growth / Max Step / Light Distance / Light Samples / Brightness** — the cloud ray-march budget. The Clouds quality preset sets these.
- **Cloud Shadow Volume**, **Ground Shadows**, **Shadows Only** — how cloud shadows are computed (a fast shared volume, or a slower full-density reference for the ground), and an option to keep the shadows while skipping the clouds themselves.

### Atmosphere *(Scientific)*

- **Steps / MS Steps** — how finely the air is sampled along each ray, and the same for multiple scattering. More steps, smoother sky, slower updates.
- **3D Object Shadows** — your scene's objects cast shadows into the atmosphere, onto the add-on's ground and, with `Object Shadows on Clouds`, onto the clouds. Choose all meshes or a specific collection.
- **Scene Lights** — Blender Point and Spot lights light the add-on's ground and the air (lamp glow in the haze, spot cones in fog), and the clouds with `Light Clouds`. All lights or a specific collection; `Light Samples` smooths the glow.

### Clouds *(Scientific)*

- **Density Model** — *KSA (Baked Weather)* is the fast default; *Procedural (PA2)* evaluates the full weather stack, with wind, detail noise and turbulence.
- **Sharp Ground Shadows** — crisper cloud shadows on the ground.
- **Cloud Shadows on Objects** — clouds darken your 3D scene as they pass in front of the sun, within the range next to the toggle.
- **Step Sprint** — a speed-up that skips ahead through thick, opaque clouds.
- **2D Far Clouds** — fades very distant clouds into a flat layer, for views from orbit.
- **Spherical Chart / Coverage SDF Skip** — how the weather pattern is wrapped around the planet, and skipping empty sky faster.
- **Step Counts** — `March Step Cap`, `SDF Skip Margin`, `Min Density`, `Min Transmit`: the limits and early-outs of the cloud march. Raising the minimums speeds things up and can slightly thin the wispiest cloud edges.
- **Atmosphere Occlusion** — `Godrays`, `Ground Ambient AO`, `MS Sun Occlusion`, `Cloud Bounce` and `Underside Light on Ground`: the individual light interactions between clouds, air and ground. Sun shafts through gaps, clouds darkening the sky light on the ground, clouds dimming the sky glow, and sunlit clouds brightening the land below them.



## Flight Path

*(Scientific.)* Draws a spacecraft trajectory in the scene and moves an empty along it, driven by the add-on's date and time. `Bundled` loads one of the included paths (Artemis II, the full Cassini mission, Cassini's Earth flyby), or point `OEM File` at your own trajectory file in the standard CCSDS OEM format.



## Overlay

Viewport helpers, drawn on top of the 3D view (never in renders):

- **Handle size** — the size of the draggable sun/moon handles in Artistic mode.
- **Motion paths** — the sun's and moon's paths across the sky for the current day.
- **Sun analemma** — the figure-eight the sun traces at the same clock time over a year.
- **Outlines** — the rings around the sun and moon handles. Turn off for clean screenshots; the handles stay draggable.
- **Sky labels** — name labels on sky objects.
- **Compass** — cardinal directions on the horizon.
- **Constellations** — constellation lines, with an `Opacity` slider.
