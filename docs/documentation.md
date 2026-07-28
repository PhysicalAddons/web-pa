

!!! tip ""
    Hey👋, first time here? You can find the installation guide and first run in the [getting started](/physical-atmosphere/getting-started/) section.

This page follows the panel from top to bottom, as seen in the **Advanced** interface layout. In the **Simple** layout you get a reduced version of the same sections. Controls that only appear in the **Scientific** layout are not covered here; they will get their own documentation.

* [Sky & Observer](#sky-observer)
* [Camera Settings](#camera-settings)
* [Atmosphere](#atmosphere)
* [Clouds](#clouds)
* [Cloud Maps](#cloud-maps)
* [Sun, Moon & Planets](#sun-moon-planets)
* [Ground / Earth](#ground-earth)
* [Stars](#stars)
* [Rendering Settings](#rendering-settings)
* [Overlay](#overlay)



## Sky & Observer

This is where you decide where the sun and moon are. There are two ways to work:

**Artistic** — you place the sun and moon by hand. Perfect when you care about the picture, not the calendar.

**Earth** — you give a real place, date and time, and the add-on computes where the sun, moon and planets actually are in the sky.

### Artistic mode

- **Sun rotation / Moon rotation** — `Horizontal` and `Vertical` angles for each body. You can also simply grab the sun or moon handle in the viewport and drag it.
- **Observer** — latitude, longitude and altitude still matter for the look of the sky (they affect the atmosphere and the stars), even when the sun is placed by hand.
- **Body scale** — one `Distance` / `Radius` pair scales all celestial bodies at once. Great for dramatic oversized moons. `Scale Earth` extends the scaling to the planet itself, and `Sun Energy Conservation` keeps the scene brightness sensible while you scale.

### Earth mode

- **Location** — type a place name and use the search button, or use the auto-detect button to find where you are (requires internet).
- **Coordinates** — latitude and longitude, if you'd rather enter them directly.
- **Altitude (km)** — how high above sea level the camera is. Go up far enough and you'll see the sky darken and the horizon curve.
- **Time / Date** — the moment you're rendering. The clock button sets the current date and time. An info box below shows the resolved local and UTC time.
- **UTC Zone / Daylight Savings** — time-zone corrections, with sunrise and sunset times shown for the current settings.



## Camera Settings

Controls how bright the sky is on screen and how the picture is developed.

### Exposure

- **Simple** — one `Exposure (EV)` slider. Up is brighter, down is darker.
- **Photographic** — set it like a real camera: `Aperture (f-stop)`, `Shutter Speed`, `ISO` and an `Exposure Bias` for fine-tuning.

### White Balance (K)

Color temperature of the picture. Lower values are warmer (orange), higher values are cooler (blue). Default is 5600 K, a common daylight film value.

### World Output (f-stops)

Adjusts how much light the sky contributes to the rest of your scene, in f-stops, without changing how the sky itself looks.

### Blend Objects into Atmosphere

An experimental compositing mode where your 3D objects are blended into the atmosphere by the add-on: distant objects pick up the same haze and light as the sky around them, and tonemapping is handled by the add-on (pick a look with `Tonemap`). While enabled, Blender's Color Management has no effect.

!!! note
    This toggle is temporarily disabled while the compositor catches up with the new sky pipeline introduced in 2.6.0. Scenes that already have it enabled can still switch it off. With it off, the usual Blender `View Transform` and `Look` controls apply.



## Atmosphere

The air itself. The checkbox in the header turns the whole atmosphere layer on or off.

### Multiple Scattering

Light bouncing around in the air more than once. Keeps the sky and clouds from looking too dark, especially around sunset. `Multiple Scattering Multiplier` scales the effect, and `LUT Multiple Scattering (Hillaire)` switches to an alternative, film-industry-standard way of computing it. Feel free to A/B them.

### Sky Ambient

How much soft sky light falls onto clouds and the ground. Raise it for a brighter, softer look.

### Atmospheric Refraction

The air bends light near the horizon. This is what makes the sun flatten and squash as it sets, lets you see it slightly after it has geometrically set, and makes distant terrain loom above the horizon. The whole effect is physically driven by your scene's air pressure and temperature. `Refraction Strength` scales it, and `Ground Temp Offset` mimics hot or cold ground (mirage-like conditions). Off by default; one checkbox turns the whole suite on.

### Rayleigh

The scattering that makes the sky blue during the day and red at sunset. Normally you leave this on.

### Aerosols

Dust, smoke, salt and pollution in the air:

- **Turbidity** — how much of it there is. Low values give crystal-clear air; high values give thick haze.
- **OPAC Profile** — what kind of air it is: from clean arctic or maritime air to urban and desert profiles. In the Simple layout this is the `Pollution` slider.

### Ozone

The ozone layer's subtle influence on sky color: it deepens the blue of twilight. The monthly ozone value for your location and date is shown below the toggle.

### Airglow

The faint natural glow of the night sky itself, visible on clear moonless nights. `Scale` controls its strength.



## Clouds

Volumetric clouds, enabled with the checkbox in the section header.

### Coverage

The master slider: how much of the sky is covered in clouds, from clear skies to overcast.

### Layers

Clouds live in three layers, `L0` (low), `L1` (mid) and `L2` (high), plus a `Rain` layer. Each layer has an enable checkbox and its own tab; select a tab to edit that layer:

- **Global Coverage** — where on the planet this layer has clouds. Use the built-in map, or supply your own image.
- **Local Coverage** — the repeating weather pattern that shapes cloud fields around you. Also accepts a custom image.
- **Altitude (m) / Height (m)** — where the layer floats and how thick it is.
- **Density Scale** — how dense (dark and opaque) the clouds are.
- **Shape 1/m** — the size of the large cloud shapes. Smaller values make bigger cloud formations.
- **Droplet (µm)** — the size of the water droplets, which subtly changes how the clouds catch light (halos, silver lining).
- **Skew Amount / Skew Curve** — leans the clouds sideways with altitude, like wind shear does.
- **Wind Phase** — shifts this layer along the wind, so layers don't move in lockstep.
- **Layer Shape** — four sliders that sculpt the cloud silhouette: `Flat Base` (flat cumulus bottoms), `Crown Start` (where the puffy top begins), `Waist Erosion` (eats away the middle), `Crown Lean` (tilts the top).
- **Shape Amount / Detail Amount** — how strongly the large shapes and the fine detail erode the clouds.

The **Rain** layer works like the others, with two extras: `Rain Probability` (how much of the layer actually drops rain shafts) and `Rain Droplet` size.

### Global cloud controls

- **Anti-Tiling** — hides visible repetition across large cloud fields.
- **Wind Flow** — a flow map that steers the clouds. An empty slot means the built-in map from real global wind data is in use. `Wind Speed` sets how fast the weather drifts, `Wind Align Randomness` breaks up the uniformity.
- **Detail 1/m** — the size of the fine cloud detail shared by all layers.
- **Shape Speed / Detail Speed** — how fast the cloud shapes churn and evolve over time.
- **Cloud Time Scale** — one multiplier for all cloud motion at once. `0` freezes the sky completely, negative values run it backwards.
- **Turbulence** — large and fine turbulence that wrinkles the clouds (`Repeat` = pattern size, `Disp` = strength in meters).

### Cloud Shading

How the clouds respond to light: the bright silver lining toward the sun, the soft glow inside, the dark cores of heavy cumulus. The defaults are physically grounded and validated against path tracing, so treat these as look-development controls for when you want to art-direct the light:

- **Model** — the overall shading recipe. **KSA** (the default) is a clean, production-proven look; **Hybrid (PSA2)** is the fully tweakable model that responds to every knob below; **Octave MS** is a third, energy-conserving take. Try all three on your scene.
- **Mie LUT** — the physically measured way droplets scatter light, responsible for effects like the silver lining and cloud halos. `Strength` blends it in, `Depth Blur` softens it deeper into the cloud.
- **Droplet Model** — how droplet size varies through the cloud, which subtly shifts those scattering effects.
- **Direct / Indirect / Backscatter g** — how strongly light keeps its direction inside the cloud, split per lighting component.
- **Shadow / Indirect / Out-Scatter Depth** — three independent depth controls: how deep sunlight, bounced light and the darkening reach into the cloud.
- **MS Gain / Inner Glow / Out-Scatter / Interior Fill** — the brightness of multiply-scattered light, the glow inside dense regions, the darkening that gives cumulus their bright-rim, dark-core character, and a fill light for deep interiors.
- **Ambient AO / Gradient / Ambient Prob** — how much the cloud's own mass, height and shape occlude the soft sky light falling on it.



## Cloud Maps

Real weather for your clouds. Using your scene's date and time, the add-on downloads the matching global cloud forecast (GFS weather data) and turns it into coverage maps.

- **Output location** — save the maps next to your .blend file (`Project`) or into a folder of your choice (`Custom Folder`).
- **Generate Cloud Map** — downloads the forecast nearest to your scene's date/time and builds the maps (requires internet).
- **Use as Cloud Coverage Maps** — plugs the generated maps into the cloud layers, so the sky above your chosen location matches the real weather for that moment.

!!! tip
    Scene set to today, location set to your city, `Generate` + `Use`, and you're rendering under today's actual sky.



## Sun, Moon & Planets

Each body has its own section with a visibility checkbox in the header.

### Sun

- **Distance / Radius (km)** — in Artistic mode, place and size the sun disc freely.
- **Spectrum** — the sun's light spectrum: the measured solar spectrum (AM0), or a Blackbody model where you pick the `Temperature (K)` (useful for alien suns or stylized skies).
- **Spectral Samples** — how finely the spectrum is sampled; higher is more accurate.

### Planets

In Earth mode, Mercury through Neptune appear in their true positions for your location, date and time. In Artistic mode you can set each planet's distance and radius yourself.

### Moon

The moon renders with its correct phase and its familiar face. In Earth mode its position follows the real sky; in Artistic mode you place it by hand (`Moon rotation` in Sky & Observer) and can change its distance and radius.



## Ground / Earth

The planet under your feet.

- **Ground Albedo** — how bright the ground is. Brighter ground bounces more light back into the sky and onto cloud bases.
- **Bounce** — how much of that ground light is bounced back up.
- **Earth Texture** — use the built-in satellite texture of Earth (visible from altitude), with a `Brightness` control. Turn it off to use a flat `Albedo Color` instead, handy for snow, desert, or stylized planets.



## Stars

The real night sky: stars appear in their correct positions for your location, date and time. `Brightness` controls how prominent they are.



## Rendering Settings

Everything here trades quality against speed. The easiest way is the **Quality** preset dropdown, always visible in the section header: `Potato` to `NASA` sets everything below in one go. Expanding the section reveals the per-category presets (`Resolution`, `Lighting`, `Atmosphere`, `Clouds`); change any individual value and the preset shows `Custom`.

Since 2.6.0 the sky renders through a foveated pipeline: full detail where the camera looks, a lighter version everywhere else for lighting and reflections. The controls below reflect that split.

### Resolution

- **Sky Resolution** — how sharp the sky is where the camera looks: `Full`, `Half` or `Quarter` of the viewport (or render) resolution.
- **Probe Resolution** — resolution of the sky texture that feeds lighting and reflections on your objects.
- **Probe Update** — when those reflections refresh.
- **Live Reflections** — automatically refresh reflections as the clouds move, at the chosen `Interval`. Off by default, since each refresh costs a probe re-render. The refresh button next to it updates reflections once, on demand.
- **Temporal AA** — refines the image over a number of frames (the dropdown next to it) whenever the camera rests. Motion stays at full resolution and refreshes continuously; stopping converges to a clean anti-aliased image.
- **Interleaved Sweep** — spreads cloud refinement across frames for smoother convergence.
- **Sample Jitter** — adds a little per-frame noise that Temporal AA averages away, for faster convergence with clouds. It manages itself: on with clouds, off for the bare atmosphere.

### Atmosphere

- **Steps** — how finely the air is sampled along each ray. More steps, smoother sky, slower updates.
- **MS Steps** — same, for multiple scattering.
- **3D Object Shadows** — your scene's objects cast shadows into the atmosphere and onto clouds (visible god-rays from a mountain, for example). Choose all objects or a specific collection.

### Clouds

- **Light Grid** — resolution of the precomputed cloud lighting. Higher gives more detailed light and shadow inside the clouds.
- **Sun March Steps** — how precisely sunlight is traced through the clouds when that lighting is computed.
- **Sharp Ground Shadows** — crisper cloud shadows on the ground.
- **Cloud Shadows on Objects** — clouds darken your 3D scene as they pass in front of the sun, with a range dropdown and a `Shadow Contrast` control.
- **Step Sprint** — a speed-up that skips ahead through thick, opaque clouds.
- **2D Far Clouds** — fades very distant clouds into a flat layer, for views from orbit.
- **March Step Cap / Min & Max Step / Step Growth** — the ray-march budget: how finely the clouds are sampled with distance. Tighter values sharpen distant clouds and reduce banding at the cost of speed.
- **Min Density / Min Transmit** — early-out thresholds; raising them speeds things up and can slightly thin the wispiest cloud edges.
- **Godrays / Ground Ambient AO / MS Sun Occlusion / Cloud Bounce** — individual light interactions between clouds and atmosphere: sun shafts through gaps, clouds darkening the sky light on the ground, clouds shading each other, and cloud light bouncing off the ground.



## Overlay

Viewport helpers, drawn on top of the 3D view (never in renders):

- **Handle size** — the size of the draggable sun/moon handles in Artistic mode.
- **Motion Paths** — the sun's and moon's paths across the sky for the current day (Earth mode).
- **Sun Analemma** — the figure-eight the sun traces at the same clock time over a year (Earth mode).
- **Outlines** — the rings around the sun and moon handles. Turn off for clean screenshots; the handles stay draggable.
- **Labels** — name labels on sky objects.
- **Compass** — cardinal directions on the horizon.
- **Constellations** — constellation lines, with an `Opacity` slider.
