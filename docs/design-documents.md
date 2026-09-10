---
title: Design documents
---

# Design documents

How _Physical Atmosphere²_ renders, and why it renders that way: the architecture reference for the rendering pipeline, the engineering design documents behind its major features, and the credits and references the work stands on. Everything is published as written. The design documents are working notes rather than user documentation: each records a direction, the physics and architecture chosen for it and the stage plan, and is amended as stages land with what actually shipped and where it departed from the plan. "User" in them is the add-on's author setting the direction, commit hashes and file paths refer to the add-on's source tree, and dates are when a decision was made. For what the features do, see the [documentation](/physical-atmosphere/documentation/) and the [release notes](/physical-atmosphere/release-notes/).

| Section | Status | Date |
| --- | --- | --- |
| [Rendering pipeline](#pipeline)<br><small>The architecture reference: one atmosphere core compiled many ways, the rect and equirect renderers, the TAA round, shader assembly, every pass and LUT, and how the sky reaches EEVEE and Cycles.</small> | `reference:`{: .label-improvements } Architecture reference | 03.09.2026 |
| [Auto Range placement, Auto Exposure, Auto White Balance — design (2026-09-07)](#auto-exposure)<br><small>Auto range placement, auto exposure and auto white balance on one measurement core: a percentile-band meter over the published planes, an adaptation curve, and the physical illuminant. Amended with the Meter choice (Sky / Viewport / Incident), the offscreen viewport meter and what it took to make it read the sky, and the law that keeps the scene's own lamps neutral under the Range placement.</small> | `shipped:`{: .label-fixed } Shipping · Auto modes 3.0.0-beta · Meter choice 3.0.7-beta | 07.09.2026 |
| [KSA/KSP-style LUT atmosphere for PA2](#lut-atmosphere)<br><small>The visible sky as a lookup-table chain — transmittance, sky-view and aerial LUTs resolved by the rectangle and the lighting equirect — with the cloud pipeline ported from KSA on top. The decision, the resources, every phase with its measured gate, the review amendments and the open decisions.</small> | `shipped:`{: .label-fixed } Shipping · the default sky since 3.0.0-beta | 05.09.2026 |
| [Atmospheric Refraction — ray-marched, one law for sky, ground and celestials](#refraction)<br><small>One ray-marched refraction law for sky, ground and celestials: bending from the air's pressure and temperature profile, the green flash, horizon shimmer and space views. Every stage has landed: bent view rays for sky, ground, clouds and celestials, dispersion, the shimmer split and Young's inversion presets. Amended with the sun's chromatic limb law, the LUT sky's horizon-band transmittance limit, and what landed after: the near shimmer on turbulence physics, heat blur, gravity-wave mirage layers, and the air masses retired in favour of them.</small> | `design:`{: .label-research } Shipping · every stage landed · amended 10.09.2026 | 03.09.2026 |
| [1:1 Window-mapped sky — design & stage plan](#window-sky)<br><small>The sky and composed ground are marched at exact view resolution through Window-coordinate mapping, with EEVEE's own temporal AA recipe and the hybrid cut against scene geometry. Amended with what actually shipped and where it departs from the plan; one fovea variant for both engines and 1:1 clouds since.</small> | `shipped:`{: .label-fixed } Shipped · amended 10.09.2026 | 04.08.2026 |
| [Optimized cloud rendering: interleaved low-res march + temporal upscale](#cloud-upscale)<br><small>The cloud march leaves the 1:1 sky pass for its own interleaved low-resolution pass with a KSA-style temporal resolve, the KSA march port and the dual-paraboloid shadow volume. Includes the fidelity audit against the KSA sources and the cost measurements. Since then the light grid and the house march are gone and the density model is the ported one; the clouds are an interim system pending the real cloud renderer.</small> | `shipped:`{: .label-fixed } Shipped · superseded in part · interim system | 05.08.2026 |
| [North Offset — Design (2026-07-31)](#north-offset)<br><small>A single angle that rotates the modelled world against true north, so GIS-derived geometry keeps its imported orientation. Scoped and costed on 31.07.2026, implemented on 04.09.2026 as recommended: sun, stars, cloud map, wind, city lights, flight paths and the compass all turn together.</small> | `shipped:`{: .label-fixed } Implemented 04.09.2026 | 31.07.2026 |
| [Ground Shader — Design (2026-07)](#ground-shader)<br><small>A dedicated GPU compose pass shades the planet surface offscreen and folds it into the scatter/transmittance pair: water reflections, cloud bounce, night lights, moonlight, the heightmap and object shadows on the ground. The Hapke-lite land BRDF it recommends was replaced by the Principled model in August 2026.</small> | `shipped:`{: .label-fixed } Shipped · 2.7 · BRDF superseded 08.2026 | 07.2026 |
| [Credits & references](#credits)<br><small>The published work the add-on is built on: shader code used directly, techniques and ideas adapted, papers and data, and the third-party licenses.</small> | `reference:`{: .label-improvements } Credits | — |


## Rendering pipeline {#pipeline}

`reference:`{: .label-improvements } Architecture reference · `celestials-rect` branch · updated 03.09.2026

**In this section:** [The big picture](#pipeline-big-picture) · [One atmosphere, two renderers](#pipeline-two-renderers) · [Anatomy of a rect TAA round](#pipeline-taa-round) · [How a shader gets built](#pipeline-shader-build) · [Pass reference](#pipeline-passes) · [LUTs and precomputed textures](#pipeline-luts) · [Reaching Blender](#pipeline-blender) · [Where objects meet the atmosphere](#pipeline-objects) · [The CPU science layer](#pipeline-cpu) · [Three invariants worth knowing](#pipeline-invariants)

One Shadertoy-derived atmosphere core, compiled many ways. A Python science layer packs a single UBO; a small set of LUTs re-bake only when their keys change; and **two renderers share the same march shader**: a per-frame foveated **rect** pipeline with three temporal domains, and an on-change **equirect** lighting probe. Results reach EEVEE and Cycles through a world node group and a rect-only compositor graph whose **hybrid cut** keys objects into the atmosphere by EEVEE's own alpha while the march supplies the haze up to their surface.

`1 march shader · 4 builds` `3 temporal domains` `5 rect planes + 1 probe image` `world v17 · compositor v25 · AOV group v8` `compute publish on Vulkan + Metal`

### The big picture {#pipeline-big-picture}

Everything on the GPU descends from `shaders/atmosphere_15/atmosphere.glsl`, a Shadertoy-compatible reference that hosted builds cut at `mainImage()` and re-drive with a per-pass driver. The Python side is split EEVEE-style into `sky_*` modules behind the `offscreen_sky` facade. A 20 Hz watcher timer plus a `PRE_VIEW` draw callback decide what runs each tick: LUT re-bakes when a key changes, a rect TAA round when the camera sky wants samples, a reprojection warp when only the pose moved, and an equirect re-march when the lighting probe is stale.

<figure class="pa2-fig">
<svg viewBox="0 0 1140 560" style="min-width:1020px" role="img" aria-label="System map: CPU science modules pack a UBO; LUT bakes feed samplers; the rect and equirect renderers march the same shader; outputs publish to the Blender world node group and compositor.">
  <defs>
    <marker id="m1mut" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-mut"/></marker>
    <marker id="m1sky" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-sky"/></marker>
    <marker id="m1sun" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-sun"/></marker>
    <marker id="m1lut" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-lut"/></marker>
    <marker id="m1vio" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-vio"/></marker>
  </defs>
  <text x="130" y="20" text-anchor="middle" class="th">CPU · PYTHON</text>
  <text x="390" y="20" text-anchor="middle" class="th">PRECOMPUTED · ON CHANGE</text>
  <text x="670" y="20" text-anchor="middle" class="th">MARCHED · PER FRAME</text>
  <text x="960" y="20" text-anchor="middle" class="th">PUBLISHED · BLENDER</text>
  <rect x="20" y="36" width="220" height="156" rx="8" class="bx"/>
  <text x="32" y="58" class="t1">celestial_math.move_sun</text>
  <text x="32" y="72" class="t2">VSOP87/ELP · sun moon planets axes</text>
  <text x="32" y="94" class="t1">atmosphere.py · solar.py</text>
  <text x="32" y="108" class="t2">OPAC aerosols · spectrum → RGB</text>
  <text x="32" y="130" class="t1">cloud_maps.py</text>
  <text x="32" y="144" class="t2">GRIB2 weather → coverage/wind</text>
  <text x="32" y="166" class="t1">refraction.py</text>
  <text x="32" y="180" class="t2">reference ODE · G(h) profile (stage 0)</text>
  <line x1="130" y1="192" x2="130" y2="344" class="arw" marker-end="url(#m1mut)"/>
  <text x="140" y="272" class="t2">PA2_DATA_* idprops</text>
  <rect x="20" y="348" width="480" height="46" rx="8" class="bx2 st-sky"/>
  <text x="260" y="368" text-anchor="middle" class="t1">PA2SkyUBO — sky_params._gather_params</text>
  <text x="260" y="384" text-anchor="middle" class="t2">~100 vec4 lanes · binding 0 in every pass</text>
  <rect x="280" y="36" width="220" height="252" rx="8" class="bx"/>
  <text x="292" y="56" class="t1">LUT &amp; texture bakes</text>
  <text x="292" y="70" class="t2">sky_luts · sky_textures · sky_depth</text>
  <rect x="292" y="84" width="8" height="8" class="sw mk-lut"/>
  <text x="306" y="92" class="t3">ambient atlas 64×256</text>
  <text x="306" y="104" class="t2">psi_ms + ambient_lut_ss · SS MS Ψ SH-1</text>
  <rect x="292" y="116" width="8" height="8" class="sw mk-lut"/>
  <text x="306" y="124" class="t3">coverage SDF 512²</text>
  <text x="306" y="136" class="t2">coverage_mask → CPU distance xform</text>
  <rect x="292" y="148" width="8" height="8" class="sw mk-lut"/>
  <text x="306" y="156" class="t3">shadow volume 192²×48</text>
  <text x="306" y="168" class="t2">compute · rolling 8 slices per round</text>
  <rect x="292" y="180" width="8" height="8" class="sw mk-lut"/>
  <text x="306" y="188" class="t3">shape noise 64³ + LOD</text>
  <text x="306" y="200" class="t2">cloud_shape_atlas · disk-cached</text>
  <rect x="292" y="212" width="8" height="8" class="sw mk-cloud"/>
  <text x="306" y="220" class="t3">caster 1024² · viewgeo surface 1:1</text>
  <text x="306" y="232" class="t2">sun-space + eye-space rasters · coverage decode</text>
  <rect x="292" y="244" width="8" height="8" class="sw mk-mut"/>
  <text x="306" y="252" class="t3">static set</text>
  <text x="306" y="264" class="t2">blue noise · Mie · stars · moon · LTC</text>
  <line x1="500" y1="150" x2="536" y2="150" class="arw-lut" marker-end="url(#m1lut)"/>
  <text x="503" y="142" class="t2">samplers</text>
  <polyline points="500,260 520,260 520,380 536,380" class="arw-lut" marker-end="url(#m1lut)"/>
  <polyline points="500,371 531,371 531,240 536,240" class="arw-sky" marker-end="url(#m1sky)"/>
  <polyline points="531,371 531,412 536,412" class="arw-sky" marker-end="url(#m1sky)"/>
  <rect x="540" y="44" width="260" height="252" rx="10" class="bx2 st-sky"/>
  <text x="552" y="64" class="t1">RECT — foveated camera sky</text>
  <text x="552" y="79" class="t2">sky_rect · every frame / draw · TAA</text>
  <rect x="552" y="90" width="236" height="22" rx="5" class="bx st-cloud"/>
  <text x="560" y="105" class="t3">1  cloud split march — CLOUD_PASS ÷4</text>
  <rect x="552" y="118" width="236" height="22" rx="5" class="bx st-cloud"/>
  <text x="560" y="133" class="t3">2  cloud resolve — ×16 @ display</text>
  <rect x="552" y="146" width="236" height="22" rx="5" class="bx st-sky"/>
  <text x="560" y="161" class="t3">3  air march S T IND SHD @ air dims</text>
  <rect x="552" y="174" width="236" height="22" rx="5" class="bx st-sky"/>
  <text x="560" y="189" class="t3">4  TAA resolve + aux — S/T film, SHADOW.a film</text>
  <rect x="552" y="202" width="236" height="22" rx="5" class="bx st-sun"/>
  <text x="560" y="217" class="t3">5  BG compose — celestials + ground</text>
  <rect x="552" y="230" width="236" height="22" rx="5" class="bx st-sun"/>
  <text x="560" y="245" class="t3">6  BG film tail — inside the compose @ 1:1</text>
  <text x="552" y="276" class="t2">no round? rect_reproject warps last pose</text>
  <rect x="540" y="320" width="260" height="150" rx="10" class="bx2 st-vio"/>
  <text x="552" y="340" class="t1">EQUIRECT — lighting probe</text>
  <text x="552" y="355" class="t2">sky_equirect · on change · no TAA/history</text>
  <rect x="552" y="366" width="236" height="22" rx="5" class="bx st-vio"/>
  <text x="560" y="381" class="t3">1  full-shell march — tiered lighting</text>
  <rect x="552" y="394" width="236" height="22" rx="5" class="bx st-sun"/>
  <text x="560" y="409" class="t3">2  ground fold — ground_compose</text>
  <rect x="552" y="422" width="236" height="22" rx="5" class="bx st-sun"/>
  <text x="560" y="437" class="t3">3  celestial compose — × T, + S</text>
  <text x="552" y="461" class="t2">quiescent under the fovea · 2×probe (512–4096)</text>
  <rect x="840" y="44" width="240" height="88" rx="8" class="bx2 st-sky"/>
  <text x="852" y="64" class="t1">5 rect image planes</text>
  <text x="852" y="80" class="t2">S · T · SHADOW · INDIRECT @ air dims</text>
  <text x="852" y="94" class="t2">B (celestials + ground) @ display 1:1</text>
  <text x="852" y="112" class="t2">surface = region · camera view ≤ render res</text>
  <polyline points="800,170 820,170 820,88 836,88" class="arw-sky" marker-end="url(#m1sky)"/>
  <rect x="840" y="162" width="240" height="88" rx="8" class="bx"/>
  <text x="852" y="182" class="t1">World — PA2_fovea_blend v17</text>
  <text x="852" y="198" class="t2">camera rays: B + S (rect planes)</text>
  <text x="852" y="212" class="t2">everything else: equirect probe</text>
  <text x="852" y="230" class="t2">EEVEE Window UV · Cycles dual basis</text>
  <line x1="960" y1="132" x2="960" y2="158" class="arw-sky" marker-end="url(#m1sky)"/>
  <text x="968" y="150" class="t2">camera arm</text>
  <rect x="840" y="280" width="240" height="60" rx="8" class="bx2 st-vio"/>
  <text x="852" y="300" class="t1">PA2_ATMOSPHERE_SKY</text>
  <text x="852" y="316" class="t2">one equirect image — IBL · reflections</text>
  <text x="852" y="330" class="t2">· probes · Cycles world</text>
  <line x1="960" y1="280" x2="960" y2="254" class="arw-vio" marker-end="url(#m1vio)"/>
  <text x="968" y="272" class="t2">probe arm</text>
  <polyline points="800,395 820,395 820,310 836,310" class="arw-vio" marker-end="url(#m1vio)"/>
  <rect x="840" y="370" width="240" height="76" rx="8" class="bx"/>
  <text x="852" y="390" class="t1">Compositor v25 — rect-only</text>
  <text x="852" y="406" class="t2">PA2_rect_AOV → S T B D G AOVs</text>
  <text x="852" y="420" class="t2">G = per-fragment terrain test (1/km lane)</text>
  <text x="852" y="434" class="t2">out = mix(B_T+S_sky, obj·T_obj+S_obj, α)</text>
  <polyline points="1080,100 1104,100 1104,408 1084,408" class="arw" marker-end="url(#m1mut)"/>
  <text x="1076" y="92" text-anchor="end" class="t2">AOVs (Window-sampled)</text>
  <rect x="20" y="488" width="1100" height="32" rx="8" class="bx dash nf"/>
  <text x="570" y="508" text-anchor="middle" class="t2">sky_bake orchestration — watcher timer 20 Hz · PRE_VIEW draw callback · render hooks — schedules every bake, warp, and round</text>
  <rect x="245" y="541" width="9" height="9" class="sw mk-sky"/><text x="260" y="550" class="t2">air / sky march</text>
  <rect x="395" y="541" width="9" height="9" class="sw mk-cloud"/><text x="410" y="550" class="t2">clouds · temporal</text>
  <rect x="545" y="541" width="9" height="9" class="sw mk-sun"/><text x="560" y="550" class="t2">celestials · ground</text>
  <rect x="705" y="541" width="9" height="9" class="sw mk-lut"/><text x="720" y="550" class="t2">LUT / precompute</text>
  <rect x="860" y="541" width="9" height="9" class="sw mk-vio"/><text x="875" y="550" class="t2">equirect probe</text>
</svg>
<figcaption>The system map: CPU science fills <code>PA2_DATA_*</code> idprops, packed into one UBO. LUT bakes fire only on key change. Both renderers march the same <code>sky_driver</code> builds; the rect path publishes five planes for the camera, the equirect one image for lighting. The compositor consumes the planes as view-layer AOVs and cuts objects in by their own alpha.</figcaption>
</figure>

### One atmosphere, two renderers {#pipeline-two-renderers}

#### Rect — the picture

`core/sky_rect.py` · camera frustum, Window-mapped 1:1

- Five planes with a resolution split: **S, T, SHADOW, INDIRECT** march at surface × `sky_air_resolution` % (quantized to 32); **B** is always exact surface pixels so celestials never blur. The surface is the **full window region, uncapped**; in camera view it is the camera frame's on-screen size, limited to the render resolution. Sky Resolution is the only reducer.
- A new surface size is adopted only after it has held for 0.3 s, so a window drag never re-scales the planes mid-drag (they stretch, correctly mapped); the churn gate after a real re-scale is 0.35 s off Metal.
- **Three temporal domains:** cloud resolve (16-frame Bayer interleave, display dims so motion never destroys cloud history), S/T film TAA (EEVEE-model jitter and filter from `core/taa.py`), and BG film (celestial TAA running mean, since the merge a film tail inside the compose pass, no separate shader).
- Between rounds, `rect_reproject.frag` warps the pristine history capture to the new pose: rotation base plus parallax from the T-plane front distance, with disocclusion discard.
- Jitter is a **uniform frustum nudge**; the march shader itself is never modified per sample.

#### Equirect — the light

`core/sky_equirect.py` · panorama probe, 2×probe res (512–4096)

- One full-shell march per change, with **no TAA, no reprojection, no history**. Every parameter change re-marches the whole panorama.
- Lighting-tier simplification halves step counts and drops refraction and sharp shadows: energy-preserving, never dimmer.
- The four MRT planes are internal scratch; `_eq_publish_sky` folds the ground into S, composes celestials × T, and publishes a single image: `PA2_ATMOSPHERE_SKY`.
- Goes **quiescent under the fovea**: while the rect covers the view, the probe refreshes at most once a second.

Both are the same `sky_driver.glsl`: the ray-gen block is a literal string swap (`_RAYGEN_EQUIRECT` → `_RAYGEN_RECT`), so the Shadertoy reference stays the single source of truth.

### Anatomy of a rect TAA round {#pipeline-taa-round}

The canonical per-frame order, run by `_rect_taa_round` from the timer or at draw rate inside the `PRE_VIEW` callback:

<figure class="pa2-fig">
<svg viewBox="0 0 1140 330" style="min-width:1020px" role="img" aria-label="One rect TAA round: jitter selection, cloud split march, temporal cloud resolve, air march, TAA resolve, background compose and film, with history feedback loops, and a reprojection fallback lane for draws with no round.">
  <defs>
    <marker id="m2mut" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-mut"/></marker>
    <marker id="m2sky" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-sky"/></marker>
    <marker id="m2sun" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-sun"/></marker>
    <marker id="m2cloud" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-cloud"/></marker>
  </defs>
  <path d="M 526 110 C 536 70, 406 70, 426 106" class="arw-cloud dash" marker-end="url(#m2cloud)"/>
  <text x="471" y="66" text-anchor="middle" class="t2">history triple</text>
  <path d="M 892 110 C 902 70, 772 70, 792 106" class="arw-sky dash" marker-end="url(#m2sky)"/>
  <text x="837" y="66" text-anchor="middle" class="t2">S/T ping-pong</text>
  <path d="M 1075 110 C 1085 70, 955 70, 975 106" class="arw-sun dash" marker-end="url(#m2sun)"/>
  <text x="1020" y="66" text-anchor="middle" class="t2">BG film hist</text>
  <rect x="20" y="110" width="170" height="78" rx="8" class="bx"/>
  <text x="30" y="130" class="t1">jitter + seed</text>
  <text x="30" y="147" class="t2">core/taa · Halton + B-H</text>
  <text x="30" y="161" class="t2">uniform frustum nudge</text>
  <rect x="203" y="110" width="170" height="78" rx="8" class="bx st-cloud"/>
  <text x="213" y="130" class="t1">cloud split march</text>
  <text x="213" y="147" class="t2">sky_driver CLOUD_PASS</text>
  <text x="213" y="161" class="t2">÷4 dims · Bayer cell n/16</text>
  <rect x="386" y="110" width="170" height="78" rx="8" class="bx st-cloud"/>
  <text x="396" y="130" class="t1">cloud resolve</text>
  <text x="396" y="147" class="t2">cloud_resolve_lib</text>
  <text x="396" y="161" class="t2">display dims · MV warp</text>
  <text x="396" y="175" class="t2">+ variance clamp</text>
  <rect x="569" y="110" width="170" height="78" rx="8" class="bx st-sky"/>
  <text x="579" y="130" class="t1">air march</text>
  <text x="579" y="147" class="t2">sky_driver FROM_TEX</text>
  <text x="579" y="161" class="t2">S T IND SHD @ air dims</text>
  <rect x="752" y="110" width="170" height="78" rx="8" class="bx st-sky"/>
  <text x="762" y="130" class="t1">TAA resolve + aux</text>
  <text x="762" y="147" class="t2">rect_taa_resolve.frag</text>
  <text x="762" y="161" class="t2">capped film accum</text>
  <text x="762" y="175" class="t2">YCoCg clamp · aux films SHADOW.a</text>
  <rect x="935" y="110" width="170" height="78" rx="8" class="bx st-sun"/>
  <text x="945" y="130" class="t1">BG compose + film</text>
  <text x="945" y="147" class="t2">ground_compose BG_DRAW</text>
  <text x="945" y="161" class="t2">film tail in-pass · 1:1</text>
  <text x="945" y="175" class="t2">celestials + ground</text>
  <line x1="190" y1="149" x2="199" y2="149" class="arw" marker-end="url(#m2mut)"/>
  <line x1="373" y1="149" x2="382" y2="149" class="arw" marker-end="url(#m2mut)"/>
  <line x1="556" y1="149" x2="565" y2="149" class="arw" marker-end="url(#m2mut)"/>
  <line x1="739" y1="149" x2="748" y2="149" class="arw" marker-end="url(#m2mut)"/>
  <line x1="922" y1="149" x2="931" y2="149" class="arw" marker-end="url(#m2mut)"/>
  <line x1="1020" y1="188" x2="1020" y2="216" class="arw-sun" marker-end="url(#m2sun)"/>
  <text x="1105" y="236" text-anchor="end" class="t2">S · T · SHADOW · INDIRECT · B images</text>
  <text x="1105" y="251" text-anchor="end" class="t2">_rect_set_live → world poke · redraw tag</text>
  <text x="20" y="280" class="t2">PRE_VIEW fallback:</text>
  <rect x="130" y="256" width="600" height="52" rx="8" class="bx dash nf"/>
  <text x="430" y="277" text-anchor="middle" class="t2">no round this draw → rect_reproject.frag warps the pristine history capture</text>
  <text x="430" y="293" text-anchor="middle" class="t2">rotation + parallax from T front-distance · whisper gates · then a fresh BG redraw</text>
  <line x1="730" y1="282" x2="920" y2="282" class="arw dash" marker-end="url(#m2mut)"/>
  <text x="928" y="286" class="t2">same images</text>
</svg>
<figcaption>One TAA round. Three history loops converge independently: the cloud triple, the S/T film, and the background film. Draws that fall between rounds take the dashed bridge instead.</figcaption>
</figure>

1. **Classify the change.** A *hard* key change (params, shader key, surface size, air fraction) discards all history; pose-only and time-only changes each get their own jitter policy, with a 0.35 s settle window holding phase 0.
2. **Refresh the caster map** if the sun or time moved, before the march, so shadows never lag a frame.
3. **Pick jitter and noise seed** (`core/taa.py` Halton, Blackman-Harris filter radius) and apply it as a frustum nudge on `fwd`.
4. **Cloud split march** at ÷4 dims into the interleave cell, then **cloud resolve** warps the ping-pong history triple at display dims: motion vectors, variance clamp, 255-sample counter.
5. **Air march** (the `CLOUD_FROM_TEX` build reads the resolved cloud pair) into four scratch MRTs at air dims.
6. **TAA resolve** writes S and T plus their history; a second aux pass writes INDIRECT and SHADOW (framebuffer attachment limit) and films `SHADOW.a`, the rect's inverse ground distance, into a smooth positive field for the compositor's occlusion test.
7. **Stamp the unjittered pose** into the rect idprops and bump the serial. This is what the warp bridge and the world UV basis anchor to.
8. **BG compose + film:** `ground_compose`'s BG variant draws celestials × T plus the ground at surface dims and, in the same pass, blends the jittered result into the running celestial-TAA mean → the B image. The ground is composed behind every partly covered pixel, so the composite always has sky to show through an antialiased edge.
9. **Go live:** `_rect_set_live` pokes the world, and a redraw tag keeps the convergence self-driving until the sample target is met.

### How a shader gets built {#pipeline-shader-build}

There is no per-pass GLSL duplication. Every march-family pass is assembled at load time from the same blocks, and every pass has a fragment and a compute twin (the compute prelude redirects `gl_FragCoord` and stubs the derivatives). Quality spinners never recompile: the step-count constants are regex-lifted into UBO-backed defines.

<figure class="pa2-fig">
<svg viewBox="0 0 1140 360" style="min-width:900px" role="img" aria-label="Shader assembly: toggle defines, shim, caster shadow lib, common.glsl and atmosphere.glsl are concatenated with a pass driver; atmosphere.glsl expands a linear chain of seven cloud libraries.">
  <defs>
    <marker id="m3mut" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-mut"/></marker>
    <marker id="m3sky" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-sky"/></marker>
  </defs>
  <text x="80" y="36" class="t2">every hosted build is a concatenation — <tspan class="t3">_assemble_fragment_source / _assemble_compute_source</tspan></text>
  <rect x="80" y="52" width="340" height="30" rx="6" class="bx"/><text x="94" y="71" class="t3">toggle #defines — USE_* closures · quality</text>
  <rect x="80" y="88" width="340" height="30" rx="6" class="bx"/><text x="94" y="107" class="t3">Shadertoy shim (+ compute prelude)</text>
  <rect x="80" y="124" width="340" height="30" rx="6" class="bx"/><text x="94" y="143" class="t3">caster_shadow_lib.glsl</text>
  <rect x="80" y="160" width="340" height="30" rx="6" class="bx"/><text x="94" y="179" class="t3">common.glsl — constants · Re · solvers</text>
  <rect x="80" y="196" width="340" height="30" rx="6" class="bx st-sky"/><text x="94" y="215" class="t3">atmosphere.glsl — cut at mainImage()</text>
  <rect x="80" y="232" width="340" height="44" rx="6" class="bx st-sky"/>
  <text x="94" y="250" class="t3">pass driver — sky_driver · psi_ms ·</text>
  <text x="94" y="265" class="t3">ambient_lut_ss · coverage · density · SV</text>
  <polyline points="420,211 540,211 540,67 646,67" class="arw-sky" marker-end="url(#m3sky)"/>
  <text x="548" y="150" class="t2">expands the lib chain</text>
  <text x="660" y="36" class="t2">linear include chain — each lib includes its predecessor</text>
  <rect x="660" y="52" width="330" height="26" rx="6" class="bx"/><text x="672" y="69" class="t3">params_lib · tunables, shared markers</text>
  <rect x="660" y="86" width="330" height="26" rx="6" class="bx"/><text x="672" y="103" class="t3">noise_lib · blue/white noise, jitter</text>
  <rect x="660" y="120" width="330" height="26" rx="6" class="bx"/><text x="672" y="137" class="t3">transport_lib · phase fns, 2-stream MS</text>
  <rect x="660" y="154" width="330" height="26" rx="6" class="bx"/><text x="672" y="171" class="t3">model_lib · weather, shape, density</text>
  <rect x="660" y="188" width="330" height="26" rx="6" class="bx"/><text x="672" y="205" class="t3">light_lib · sun-depth walks, bins</text>
  <rect x="660" y="222" width="330" height="26" rx="6" class="bx"/><text x="672" y="239" class="t3">ambient_lib · LUT taps, shadow volume</text>
  <rect x="660" y="256" width="330" height="26" rx="6" class="bx"/><text x="672" y="273" class="t3">march_lib · KSA segment march</text>
  <line x1="825" y1="78" x2="825" y2="84" class="arw" marker-end="url(#m3mut)"/>
  <line x1="825" y1="112" x2="825" y2="118" class="arw" marker-end="url(#m3mut)"/>
  <line x1="825" y1="146" x2="825" y2="152" class="arw" marker-end="url(#m3mut)"/>
  <line x1="825" y1="180" x2="825" y2="186" class="arw" marker-end="url(#m3mut)"/>
  <line x1="825" y1="214" x2="825" y2="220" class="arw" marker-end="url(#m3mut)"/>
  <line x1="825" y1="248" x2="825" y2="254" class="arw" marker-end="url(#m3mut)"/>
  <text x="80" y="316" class="t2">Resample passes — rect_reproject · rect_taa_resolve · cloud_resolve — skip the library entirely.</text>
  <text x="80" y="334" class="t2">ground_compose lifts only the shared constant blocks (INF · shell · layer altitudes), so it can never disagree with the march.</text>
</svg>
<figcaption>Source assembly. The Shadertoy reference stays runnable as-is; hosted builds cut it at <code>mainImage()</code> and append a pass driver instead.</figcaption>
</figure>

### Pass reference {#pipeline-passes}

| Pass | What it computes | Resolution | Runs |
| --- | --- | --- | --- |
| `sky_driver.glsl` | The one atmosphere march: view segment through the shell with refraction-bent radius, cloud arm, column composite, ambient, ground shadow. Compiles four ways: equirect, rect air (`CLOUD_FROM_TEX`), cloud-only (`CLOUD_PASS`), each with a compute twin. MRT: S, T, INDIRECT, SHADOW (+B). Rect builds decode the viewgeo map as a bilinear *coverage* and mix the full and the truncated column by it; `SHADOW.a` carries the inverse ground distance (equirect builds keep km). | 2×probe / display×air% | every bake & round |
| `psi_ms_driver.glsl` | Hillaire Ψ_ms: 256-point Fibonacci-sphere single-scatter per texel, closed under re-scatter (Ψ = lum / (1−f_ms)). | 64×64 atlas band | ambient key change |
| `ambient_lut_ss_driver.glsl` | Measured hemispheric irradiance vs (sun zenith, altitude): 128-point hemisphere; uniform, cosine, and SH-1 sun-tangent moment estimators. Built twice: SS mode and MS mode (reads Ψ scratch). | 4 bands of 64×256 | ambient key change |
| `coverage_mask_driver.glsl` | The marcher's own weather rejection at 8 altitude fractions → binary mask, then a CPU distance transform bakes the empty-space-skipping SDF. | 512² | coverage key change |
| shadow-volume compute | Dual-paraboloid cloud shadow + AO volumes anchored under the camera; 40-step sun march per voxel. | 192×192×48 ×2 | 8 slices per round |
| `rect_compute_prelude/main` | Compute wrapper for any driver: `imageStore` instead of framebuffers; dims arrive as a push constant. | 8×8 groups | Vulkan + Metal (default publish) |
| `rect_reproject.frag` | Pose warp bridge: rotation base + parallax from the T front-distance channel, disocclusion discard, whisper gates so a static view never resamples. | air dims | draws between rounds |
| `rect_taa_resolve.frag` | EEVEE-model film resolve: Blackman-Harris 3×3 gather at the CPU jitter, YCoCg neighborhood clamp, capped film accumulation. Aux pass carries INDIRECT + SHADOW and films SHADOW.a (RG16F mean/count history). | air dims | per round |
| `ground_compose.frag` | Ground + background compose: GGX, sphere-light and LTC area specular, day/night/water/height maps, and under `BG_DRAW` the whole background plane (celestials × T on sky rays, ground on ground rays) plus the celestial-TAA film tail (the former `rect_bg_film`, merged). Skips the ground only under fully covered geometry. Four build variants. | surface 1:1 | every draw |
| `cloud_resolve_lib.glsl` | Temporal cloud upscale: bicubic history fetch, motion vectors from the history basis, variance clamp; resolves the 1/16 interleave to full res. | display 1:1 | per round |
| `rect_celestials_lib.glsl` | Stars (catalog PSF: gauss core + Airy tail), sun, moon, planets, Saturn + rings; a library spliced into every B-carrying build. | — | library |
| `caster_shadow_lib.glsl` | Sun-space object shadows with a blue-noise-dithered penumbra disc, spliced into *every* assembled source. | — | library |
| `density_bake_driver.glsl` | Voxel density slices → OpenVDB fog volume, for Cycles ground-truth validation. | user grid | operator |

### LUTs and precomputed textures {#pipeline-luts}

| Texture | Size · format | Feeds | Rebuilds |
| --- | --- | --- | --- |
| ambient LUT atlas | 64×256 RGBA16F | MS in-scatter, cloud ambient, ground indirect: SS / MS / Ψ / SH-1 moment bands; sun angle and altitude are LUT axes, so sun motion costs nothing | composition key only |
| cloud shadow volume | 192×192×48 R16F ×2 | cloud light march far tap, self-shadow, godrays | rolling 8 slices/round |
| coverage SDF | 512² R16F | cloud march empty-space skipping (weather-tile units) | coverage key |
| shape noise 3D + LOD | 64³ (atlas-baked) | cloud density everywhere | once · disk-cached |
| blue noise | 1024² RGBA16F | march jitter (.x) · caster penumbra (.z) | once |
| Mie phase LUT | EXR, angle × droplet size | cloud phase function | selection change |
| transmittance LUT | 256×64 RGBA16F | the LUT atmosphere (3.0): optical depth to the top of the atmosphere per altitude and zenith angle | atmosphere key change (keyed generations, last-good kept) |
| sky-view LUT + atlas | 192×256 per generation, packed to one RGBA32F atlas | the LUT atmosphere: phase-free in-scatter for pure-sky rays, resolved by the rectangle and the lighting equirect (LUT Lighting Sky) | atmosphere or sun key change |
| aerial LUT | 96×96×96, six 3D planes + a range plane | the LUT atmosphere: aerial perspective in front of ground, objects and clouds | atmosphere or sun key change |
| star catalog ×2 | 2048×1024 | one star per texel: mag/CI + position | once |
| moon · Saturn · rings | octahedral / 2k | celestials lib (moon parallax + shadow cone) | once |
| light pollution pyramid | 2048×1984 atlas | night arm, level picked by sample altitude | map change |
| LTC GGX | 64×128 (EEVEE tables) | ground area-light specular | once |
| caster depth | 1024² R32F sun-space | object shadows in every pass | timer, settle-gated |
| viewgeo depth | surface 1:1 (×1.06 pad) R32F | the cut map: rect builds sample it as a bilinear coverage (depth = farthest covered tap) and mix full and cut columns; dims ride the UBO, non-square | pose · geometry · size change |
| refraction profile | 512 × G(h) floats in the UBO (design, stage 1) | every rect ray owner: the air, cloud and BG passes walk the same bent path | atmosphere knobs: T, P, RH, CO₂, ground layer, inversion |

The 2048×2 refraction LUT image of the 2.6.x releases was retired on 03.09.2026 (stage 0 of the [refraction design](#refraction)): nothing had read it since the node-side celestials went. Its replacement is the UBO profile table in the last row, which lands with stage 1; until then the view rays keep the effective-sphere approximation.

### Reaching Blender {#pipeline-blender}

**World.** `atmosphere_world.ensure_fovea` splices the `PA2_fovea_blend` group (v17) into the world tree. Camera rays take the rect arm, `B + S`, with B arriving premultiplied by T (stored ÷64 in the image, ×64 in-group for fp16 headroom); every other ray (IBL, reflections, probes) samples the equirect `PA2_ATMOSPHERE_SKY`. EEVEE maps the rect planes by Window coordinates for a pixel-perfect 1:1; Cycles rebuilds the UV from `Geometry.Incoming` through the `rectCam` dual basis, because its Window output quantizes far from origin.

**Compositor.** The auto-built graph (v25) is rect-only and AOV-only: the injected `PA2_rect_AOV` group (v8) samples the rect planes at Window coordinates and writes `PA2_rect_S/T/B/D/G` view-layer AOVs, GPU-resident, frame-synchronized, with no image nodes and no throttling. `G` is a per-fragment terrain test, the rect's inverse ground distance against the fragment's own view distance, so a mesh below the analytic ground loses its pixel to the terrain, and EEVEE's film turns that into a coverage fraction. The composite is the hybrid cut described below, followed by exposure and a tonemap node group; color management is bypassed in this mode.

### Where objects meet the atmosphere {#pipeline-objects}

Three mechanisms cooperate so that a mesh gets aerial perspective up to its surface while its silhouette stays exactly EEVEE's. Each fixed a measured defect on the way (03.09.2026).

1. **Coverage cut in the march.** The viewgeo map is decoded as a bilinear *coverage* at the sample's map position instead of a binary hit; the march computes the full and the truncated column anyway and mixes them by it. Under the film jitter this converges to the pixel's true geometry coverage. The earlier one-texel erosion sat 2.8 px inside the silhouette and aliased.
2. **Interpolation-safe occlusion lane.** `SHADOW.a` is the *inverse* ground distance (1/km, sky = 0). The AOV group samples it bilinearly; a distance interpolated across the limb sweeps through every small value and once read "nearer than the mesh" on the limb row. A blend of far ground and sky in the inverse domain never exceeds the far ground's inverse, so the compare `inv > 1000 / view distance` cannot fire there.
3. **Hybrid composite.** The silhouette comes from EEVEE's alpha; the haze and transmittance on the object come from the cut planes. Because the planes hold one column per pixel, the edge band recovers both sides from a 5×5 luminance min/max: along a ray `S_full ≥ S_cut` and `T_full ≤ T_cut`, so the neighbourhood minimum of S is the object side and the maximum the sky side. The recovery is gated to pixels within 2 px of fractional alpha; everywhere else the planes pass through (ungated, the maximum lifted the two ground rows under the horizon to the sky's in-scatter).

<figure class="pa2-fig">
<svg viewBox="0 0 1140 250" style="min-width:900px" role="img" aria-label="A row of pixels across a silhouette against the sky: the cut planes switch from the full column to the cut column about two pixels inside EEVEE's alpha edge; within the two-pixel band around the alpha edge the composite takes the 5x5 minimum of S for the object side and the maximum for the sky side, so the silhouette is alpha's and the haze is the cut's.">
  <defs>
    <marker id="m4mut" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" class="mk-mut"/></marker>
  </defs>
  <text x="20" y="28" class="t2">one pixel row across a silhouette against the sky — left: sky, right: object</text>
  <g>
    <rect x="20" y="48" width="66" height="28" class="bx st-sky"/><rect x="86" y="48" width="66" height="28" class="bx st-sky"/><rect x="152" y="48" width="66" height="28" class="bx st-sky"/>
    <rect x="218" y="48" width="66" height="28" class="bx st-sun"/><rect x="284" y="48" width="66" height="28" class="bx st-sun"/>
    <rect x="350" y="48" width="66" height="28" class="bx st-cloud"/><rect x="416" y="48" width="66" height="28" class="bx st-cloud"/><rect x="482" y="48" width="66" height="28" class="bx st-cloud"/>
    <text x="53" y="67" text-anchor="middle" class="t3">α 0</text><text x="119" y="67" text-anchor="middle" class="t3">α 0</text><text x="185" y="67" text-anchor="middle" class="t3">α 0</text>
    <text x="251" y="67" text-anchor="middle" class="t3">α .3</text><text x="317" y="67" text-anchor="middle" class="t3">α .8</text>
    <text x="383" y="67" text-anchor="middle" class="t3">α 1</text><text x="449" y="67" text-anchor="middle" class="t3">α 1</text><text x="515" y="67" text-anchor="middle" class="t3">α 1</text>
  </g>
  <text x="20" y="100" class="t2">EEVEE alpha edge</text>
  <line x1="284" y1="82" x2="284" y2="130" class="arw-sun dash"/>
  <text x="20" y="128" class="t2">cut planes (S)</text>
  <g>
    <rect x="20" y="136" width="66" height="24" class="bx"/><rect x="86" y="136" width="66" height="24" class="bx"/><rect x="152" y="136" width="66" height="24" class="bx"/><rect x="218" y="136" width="66" height="24" class="bx"/><rect x="284" y="136" width="66" height="24" class="bx"/>
    <rect x="350" y="136" width="66" height="24" class="bx st-lut"/><rect x="416" y="136" width="66" height="24" class="bx st-lut"/><rect x="482" y="136" width="66" height="24" class="bx st-lut"/>
    <text x="53" y="152" text-anchor="middle" class="t3">full</text><text x="119" y="152" text-anchor="middle" class="t3">full</text><text x="185" y="152" text-anchor="middle" class="t3">full</text><text x="251" y="152" text-anchor="middle" class="t3">full</text><text x="317" y="152" text-anchor="middle" class="t3">mix</text>
    <text x="383" y="152" text-anchor="middle" class="t3">cut</text><text x="449" y="152" text-anchor="middle" class="t3">cut</text><text x="515" y="152" text-anchor="middle" class="t3">cut</text>
  </g>
  <text x="350" y="178" text-anchor="middle" class="t2">the plane switches ~2 px inside the alpha edge</text>
  <rect x="152" y="196" width="264" height="26" rx="6" class="bx dash nf"/>
  <text x="284" y="213" text-anchor="middle" class="t2">band: fractional α, dilated 2 px</text>
  <rect x="600" y="48" width="520" height="174" rx="10" class="bx2"/>
  <text x="616" y="72" class="t1">inside the band, per pixel</text>
  <text x="616" y="96" class="t3">S_obj = min₅ₓ₅(S)   T_obj = max₅ₓ₅(T)   S_sky = max₅ₓ₅(S)</text>
  <text x="616" y="114" class="t2">along a ray S_full ≥ S_cut and T_full ≤ T_cut — the extremes ARE the two sides</text>
  <text x="616" y="142" class="t3">out = mix( B_T + S_sky ,  obj·T_obj + S_obj ,  f )</text>
  <text x="616" y="160" class="t2">f = α · (1 − G) — EEVEE's coverage, minus the pixels the terrain wins</text>
  <text x="616" y="188" class="t2">outside the band: S_obj = S_sky = S, T_obj = T — the planes pass through</text>
  <text x="616" y="206" class="t2">measured: composite edge within 0.7 px of the alpha edge, 1 px ramp, no rim</text>
</svg>
<figcaption>The hybrid cut. The cut planes carry one column per pixel and switch about two pixels inside the true silhouette; the composite takes the silhouette from alpha and rebuilds both sides of the haze from the neighbourhood extremes, but only within the band where an edge is being resolved.</figcaption>
</figure>

### The CPU science layer {#pipeline-cpu}

- **`celestial_math.py`**, the orchestrator: `move_sun` computes sun/moon/planet/star positions and axes, then writes the whole physics payload onto `PA2_DATA_*` objects as idprops.
- **`vsop_elp.py`**: truncated VSOP87 + ELP ephemeris: geocentric RA/Dec/distance, plus the equatorial → local-ENU frame.
- **`solar.py` · `solar_spectra.py` · `cie1931.py` · `color.py`**: Planck + AM0 spectrum integrated through the CIE observer → solar radiance RGB and luminous efficacy.
- **`atmosphere.py`**: the OPAC aerosol model at 680/550/440 nm: scattering/absorption β, effective g, scale heights; also defines the idprop → UBO contract tables.
- **`refraction.py`**: the CPU reference model of the refraction design (stage 0): an ISA-layer temperature profile anchored to the scene's surface temperature with the surface layer and an elevated inversion, hydrostatic refractivity from the Ciddor N₀, the planar RK2 ray walk and the closed forms. It is the numpy twin every later GPU integrator is checked against; the 2.6.x LUT bake is gone.
- **`cloud_maps.py`**: fetches GRIB2 weather into the coverage and wind maps the texture layer composites.
- **`trajectory.py`**: OEM flight paths (Artemis, Cassini) driving the camera along real geocentric ICRF trajectories.
- **`taa.py`**: bpy-free EEVEE film math: Halton jitter, filter weights, filter radius.

### Three invariants worth knowing {#pipeline-invariants}

!!! note "The backend fork"
    Every march-family pass exists three ways: compute + `imageStore` straight into the image textures (the default publish on **Vulkan and Metal**), fragment + framebuffer (OpenGL, which is not a target, and the override flag), and scratch + CPU readback (render jobs and Cycles viewports, which read only the CPU buffers). Metal additionally forbids framebuffers over image textures, so its few unconverted publishes take the readback twins. Measured on an RTX 4080 under Vulkan, compute and fragment are within 10% per accumulation round: the compute path buys stability, not speed.

!!! note "Surface and resize"
    The rect serves the full window region at 1:1 with no cap beyond the GPU texture ceiling; in camera view it serves the camera frame's on-screen size, limited to the render resolution, so F12 content is 1:1 or zoom-scaled. A new size is adopted only after it has held for 0.3 s (a drag stretches the old planes instead of re-scaling them per step), and the image-churn gate that follows a real re-scale is 0.35 s off Metal (the two-clean-draws counter remains the real guard).

!!! note "Declared-sampler discipline"
    Binding an undeclared sampler name corrupts the heap before it raises. Hence the frozen sampler sets per build and the `with_b` flag threaded through every builder: a build without the background plane must never be handed the star maps, and a 5-output image list must never reach a 4-output shader.

### Since 3.0 — what moved {#pipeline-since-3-0}

The reference above describes the analytic pipeline of the 2.x releases; 3.0 keeps its structure and replaces several stages. In brief, as of 3.0.7-beta:

- **The visible sky is a LUT chain** based on Hillaire's atmosphere model — transmittance, sky-view and aerial LUTs (table above) resolved by the rectangle's air pass — and the lighting equirect resolves the same chain (*LUT Lighting Sky*). The analytic march is the reference option (*LUT Atmosphere (Rect)* off) and the correctness gate: clear sky 0.5 %, twilight 4.5 % P95 against a converged reference. See the [LUT atmosphere design](#lut-atmosphere).
- **Clouds are an interim system** on a pipeline ported from KSA: a baked density model with a per-layer weather chart and a Worley mip atlas, a 3×3 interleaved march with motion-vector resolve, a shadow volume for cloud shadows and godrays, objects shadowing the clouds and scene lamps lighting them. The light grid and the house march are gone. The real cloud renderer is in development and will replace this stage. See the [cloud design](#cloud-upscale).
- **The ground compose is Principled**: one GGX lobe for land and water, LTC disc speculars for sun and moon, multiple scattering and ozone in the sky reflection; the Hapke-lite BRDF of the [ground design](#ground-shader) is retired.
- **Rays bend**: the [refraction walk](#refraction) runs inside the air pass and the compose — sky, ground, clouds and celestials share one law — with shimmer, mirages and dispersion.
- **Blender lamps enter the atmosphere**: Point and Spot lights shade the composed ground, the air and the clouds through the UBO's light lanes (`sky_lights.py`, EEVEE's own light law, no shadow maps), and every non-managed lamp carries the Range placement delta in its Exposure field (`lamp_exposure.py`).
- **Night has physical radiance**: moonlight and starlight in the multiple scattering, light pollution from a city map or hemisphere mode, a Milky Way, and a Range placement that reaches +16 stops.
- **Exposure is metered**: the rect meter (a compute reduction over the published planes), an incident-light meter from the illuminant, and a viewport meter from a small scene-linear offscreen draw feed the Auto exposure mode; Auto Range places the fp16 window from the brightest source. See the [auto exposure design](#auto-exposure).
- **The world fovea group is one variant** for EEVEE and Cycles (Window 1:1), the compositor is AOV-only, and the interface has two tiers, Simple and Scientific.


## Auto Range placement, Auto Exposure, Auto White Balance — design (2026-09-07) {#auto-exposure}

`shipped:`{: .label-fixed } Shipping · Auto modes 3.0.0-beta · Meter choice 3.0.7-beta · 07.09.2026 · `docs/design-auto-exposure-2026-09.md`

**In this document:** [What exists today](#auto-exposure-what-exists-today) · [1. Auto Range — `camera_range_auto`](#auto-exposure-1-auto-range-camerarangeauto) · [2b. The curve, the ramp and the band](#auto-exposure-2b-the-curve-the-ramp-and-the-band) · [2. Auto Exposure — button `world.pa2_auto_exposure`](#auto-exposure-2-auto-exposure-button-world-pa2autoexposure) · [2c. The Meter choice — Sky / Viewport / Incident](#auto-exposure-2c-the-meter-choice-sky-viewport-incident) · [3. Auto White Balance — button `world.pa2_auto_white_balance`](#auto-exposure-3-auto-white-balance-button-world-pa2autowhiteba) · [Shared core — `core/exposure_auto.py`](#auto-exposure-shared-core-core-exposureauto-py) · [Laws to keep](#auto-exposure-laws-to-keep) · [Open questions for the user](#auto-exposure-open-questions-for-the-user)

Status: SHIPPING — Auto exposure / white balance / range in 3.0.0-beta, the Meter choice and the lamp placement law in 3.0.7-beta (see CHANGELOG). Changes from the proposal: Auto Exposure is a live third EXPOSURE MODE (user), with a Compensation slider and an Artist-tier toggle; the meter is a GPU reduction pass (the EEVEE viewport publishes GPU-direct, so there were no free CPU arrays), double-buffered and read a round late; the ambient bands are ABSOLUTE (the band driver bakes sunrad·omegaSun in), so the sky term adds without a sun factor. Two more, measured in the scripted-GUI runs: the METER IS A COMPUTE DISPATCH (the fragment version lost a framebuffer-stack slot at every world change, 7 of 85 calls, all from the tick's TAA round — imageStore needs no bind, 0 of 78 after), and the key is the BRIGHT-HALF geometric mean (the plain log-average let the dark ground half drag a 5° sunset to EV100 8.1; the bright half meters 9.4, the photographer's table). Verified values, sun 5° / moon 35° crescent / moonless: placements −5 (sun, transmittance-dimmed) / +14 (moon) / +16 (frame); WB 5008 K tint −31 (red beam + blue sky = magenta, physical) / 4786 K / held by the illuminant floor; CM compensation exact at every placement; the slider keeps the metered EV on a switch back to Simple. PLANE UNITS LAW: the world composes B×64 + S — B is stored ÷64 for fp16 headroom (ground_compose.frag) and premultiplied by T; the meter composes the same (BG_PLANE_STORE_SCALE in sky_state) — the first build composed B·T + S and read the ground 64× too dark. Three features, one measurement core. UPDATE 2026-09-10: Auto Exposure gained a **Meter choice — Sky / Viewport / Incident** (§2c; the Viewport meter is a scene-linear off-screen draw, since no draw callback can read the scene colour), and the neutrality law was extended to the scene's own lamps (`lamp_exposure`, §2c companion fix).

### What exists today (facts, measured 2026-09-07 on the live scene) {#auto-exposure-what-exists-today}

| item | value | where |
|---|---|---|
| sun disc radiance, scene units (Y) | 2.89e6 | `solar.compute_scene_solar_parameters` |
| sun TOA irradiance (Y) | 196 W/m² | same |
| fp16 ceiling / clean floor | 65504 / ~6e-5 | EEVEE film + world probe |
| Range slider → stops | `16 − 22·range` (night +16 … day −6) | `config/properties.py:range_placement_update` |
| day default −6 st | 2.89e6 / 64 = 45 100 = ceiling / √2 | i.e. the sun disc sits **½ stop under the ceiling** |
| CM compensation | `cm_stops = log2(exposure_scale) − wstops` | `celestial_math._apply_exposure_policy` |
| lighting equirect | **no sun disc** (`PA2_CEL_NO_SUN`); moon + planets + stars + ground only | `sky_ground._eq_cel_sources` |
| moon disc, full, clear | ≈ 0.12/π · 196 · Hapke centre ≈ 10–15 units | `rect_celestials_lib.glsl` Hapke block |
| Venus disc (resolved) | 2.89e6 · Ω₁AU/π · 0.7 / 0.72² ≈ 84 units | Lambert disc law |
| Jupiter / Saturn discs | ≈ 1–2 units | same |
| CM white balance API | `white_balance_whitepoint` is a colour; writing it derives temperature + tint (verified both ways, restored) | Blender 5.2 `ColorManagedViewSettings` |
| illuminant twins on the CPU | Beer/Kasten-Young sun transmittance (`shadow_plane._lamp_physical`), Chapman twin (`sky_ground._sun_trans_np`), earth idprops carry betas + scale heights | |
| sky irradiance on the CPU | ambient atlas 64×256 RGBA, cosine bands SS rows [32,64) / MS rows [96,128), u = coschi·½+½, v = h/LAYER_PEAK_H, **per unit sun**; `tex.read()` is 64 KB | `atmosphere_cloud_ambient_lib.glsl` layout comment |
| rect planes on the CPU | every publish tick `raw = [tex.read() …]` hands B/S/T/SHADOW/INDIRECT to numpy | `sky_rect.py` "rect readback + publish" block |

Consequences that shape the design:

1. The **sun's ceiling only binds when the sun disc is inside the camera frame** (rect arm). The probe never sees it.
2. The **moon's and the planets' ceilings bind whenever they are above the horizon** — the probe sees the whole sphere. At the slider's +16 night end a full moon (≈12 units · 65536 = 7.9e5) and Venus's disc (84 · 65536) both clip in the probe. Today's night endpoint is only safe for a moonless, Venus-less sky.
3. Everything the placement needs is either analytic (bodies) or already in numpy (planes). No new GPU work.

### 1. Auto Range — `camera_range_auto` (Bool, default ON for new scenes) {#auto-exposure-1-auto-range-camerarangeauto}

Peak radiance `L*` = max over:

| candidate | when counted | value |
|---|---|---|
| sun disc | disc direction inside the rect frustum (`_STATE["rect_view"]`, overscan included) and elevation > −1° | `max(sunRadianceRgb) · T_dir(μ₀)` (the lamp's Beer/KY twin; clear-sky, clouds ignored = conservative) |
| moon disc | above the horizon and visible (`cel_cfg.w`, `cel_mnp.w`) | `196·(0.12/π)·kph(phase)·T_dir(μ_moon)·2` (×2 = Hapke centre over the disc mean) |
| planet discs | above the horizon and visible | `sunRad · Ω₁AU/π · A · phase / d²` per body in `_CEL_PLANETS` (albedo table: Venus 0.7, Mars 0.15, Jupiter 0.5, Saturn 0.5 + rings) |
| measured rect | fresh `rect_stats` (serial + pose match) | max of `B·T + S` on a stride-8 grid of the last published planes — clouds, aureole, mirage sun at the limb, sunlit snow |
| measured equirect | `PA2_ATMOSPHERE_SKY` exists and is > 4×2 | its max (what the probe actually holds) |
| floor | always | starlight/airglow → no constraint; the +16 clamp holds |

Placement: `stops = clamp(log2(46 318 / L*), −20, +16)` (46 318 = ceiling/√2 — reproduces today's −6 for the sun exactly), **quantised to whole stops** and applied only when it differs from the current value by ≥ 1 stop (hysteresis: an EEVEE restart + probe rebake per change is the only cost; brightness never moves because the CM policy compensates in the same sync).

Expected placements: sun in frame −6; sun up but out of frame, clear noon ≈ +4 (aureole/cloud peak ~1e2–1e3); sunset out of frame ≈ +6; full moon up ≈ +11; Venus up ≈ +9; moonless, planet-less night +16 (today's endpoint).

Hook: `celestial_math.sync_camera_exposure`, before `_apply_exposure_policy` — writes `camera_world_output_stops` through the existing property so the node, CM compensation, compositor post-exposure, sun lamp (`oscale` read live from the node) and Cycles reference all follow as they do for a manual drag. Render path: the same call from a `render_pre` handler so F12 and animation frames evaluate the placement for **their** frame (the sun crossing the frame edge mid-animation changes the storage window; the picture does not change).

UI: Specialist/Scientist Range row = `[Range slider][Auto ☑]`; with Auto on the slider is greyed and the info box shows `World offset: +11 st (auto: moon)` — the binding candidate's name is worth printing. Simple tier: no row, Auto on silently (the slider was never shown there).

Specular caveat: a mirror-like scene object reflects the **sun lamp**, which is not in `L*`. A dielectric highlight is `F·L_sun ≈ 0.04 · 2.9e6 = 1.2e5` units — at the +4 placement a clear noon would get with the sun out of frame that is 1.9e6, far over the ceiling; only the sun's own −6 window holds it. Hence a second toggle, `camera_range_sun_safe` (Bool, default ON, "Keep the sun's window while the sun is up, so specular reflections of the sun lamp on objects never clip"): with it on, the sun counts whenever it is above the horizon, and Auto only moves the window at twilight and night — exactly the case the slider was invented for. Turning it off makes the frustum test the rule, for pure sky shots without reflective geometry.

### 2b. The curve, the ramp and the band (2026-09-07, after the first field look) {#auto-exposure-2b-the-curve-the-ramp-and-the-band}

User: "the night seems to be always too bright. also it is a little choppy" +
"check if there is an auto exposure method used in industry that just works."
There is, it has three parts, and we were missing one of each.

**The curve.** Metering every scene to middle grey IS "night as bright as day".
Unreal ships an Exposure Compensation Curve against measured scene EV; Unity
HDRP a Curve Mapping mode. Ours is that curve in two parameters. With `x` =
the scene's own EV100 (`SIMPLE_BASE_EV100 - metered_ev`, the number the info
box prints):

```
EC(x) = max( -(1 - strength) * softplus(knee - x, 1 stop), -8 )
ev    = metered_ev + EC + compensation
```

`strength` (Adaptation, default 0.7), `knee` (Full Adaptation Above, default
EV100 10). The softplus makes the bend ~2 stops wide, so a setting sun crosses
it without a kink and daylight (EV100 13.7) gets EC ~ -0.008. Landing points at
the defaults: twilight EV100 5 -> -1.5; night street 3 -> -2.1; moonlit -3 ->
-3.9; starlit -8.6 -> -5.6 (the floor bites below ~EV100 -16). One-sided by
design: a snow scene reading too grey is the Compensation knob's job.

**The ramp.** Exponential easing UNDER a rate cap in EV/s -- 5 EV/s toward less
exposure (light adaptation), a 2.5x lower cap toward more (dark adaptation),
the same asymmetry as Unreal's SpeedUp 3 / SpeedDown 1 and Unity HDRP's Speed
Dark-to-Light / Light-to-Dark. The asymmetry rides the CAP ONLY: stretching the
easing constant with it made the last two stops of a 10-stop change take 13 of
its 16 seconds, a stall rather than an eye. The ramp lands at 0.02 EV (1.4% of
a stop, invisible) instead of crawling asymptotically. A plain 0.35 s exponential
covered 2.5 stops of a 10-stop change on its first tick, which at the old 10 Hz
sync cadence is the reported chop; the cap makes the same change cross at a
quarter stop per tick at the watcher's 20 Hz, and the watcher now syncs every
tick while the exposure travels. Renders never ease -- they take the settled
target for their own frame.

**The band.** The key is a percentile band of the log-luminance histogram, the
metering law every engine ships (Unreal Low/High Percent: 10/90 today, 80/98.3
in the UE4 default it replaced; Unity HDRP the same pair). Ours is 50-98%:
bright-biased because the SKY is the subject here, with the top 2% trimmed so a
sun disc or specular hit cannot drag the key down. Edge entries count
partially, so the key moves continuously instead of flickering as cells cross
the boundary.

Sources: Epic's "How Epic Games is handling auto exposure in 4.25" and the
Unreal Auto Exposure docs (defaults: 64-bin histogram, low 10% / high 90%,
min/max brightness 0.03/8, SpeedUp 3 / SpeedDown 1).

### 2. Auto Exposure — button `world.pa2_auto_exposure` {#auto-exposure-2-auto-exposure-button-world-pa2autoexposure}

Simple mode only (the request). Metering = the display composite the world shows, `D = B·T + S`, from the last published rect planes:

```
Y      = 0.2126 R + 0.7152 G + 0.0722 B          (stride-8 grid)
L_key  = exp(mean(log(Y + 1e-9)))                (log-average: robust to the sun's few pixels)
ev_new = ev_cur + log2(0.18 / (L_key · exposure_scale_cur))
```

`exposure_scale_cur` is the value `compute_camera_exposure` already returns; the world-stops term is brightness-neutral so it never enters. Clamp to the property range (−21 … 32). The report line prints the resulting EV100 and the scene label (`_ev100_scene_label`).

No fresh planes (viewport in Solid, or a different pose): fall back to the **incident-light meter**: `E = sunRad·Ω·T_dir(μ₀)·max(μ₀,0) + bands_cos(μ₀, h)` (same illuminant as §3), `L_key = 0.18·E/π`. Check: clear noon → EV100 ≈ 15 (the sunny-16 rule), which is the number the formula returns with these constants.

Night: the log-average of a sky-only frame drives EV toward the deep-night operating point (≈19 EV simple = EV100 −6.4); this is what a camera does and the user dials back. No special casing.

Physical mode: not requested; the same delta could land on `camera_exposure_bias_ev` rounded to its ½-stop items — cheap to add later.

### 2c. The Meter choice — Sky / Viewport / Incident (2026-09-10) {#auto-exposure-2c-the-meter-choice-sky-viewport-incident}

Status: BUILT 2026-09-10 (`camera_auto_meter`, `exposure_auto.metered_reading`, `core/view_meter.py`). User question: "about the auto exposure — does it also take into account the 3D scene?" It did not, and the answer is now a choice.

#### What the shipped meter sees

The rect meter reads the addon's own composed planes, `B·64 + S` — sky, clouds, celestials, addon ground/water. Nothing EEVEE draws on top is in it: **meshes, lamps on meshes, emission shaders**. Point/Spot lamps enter only through what they add to the addon ground and haze (`sky_lights`). A camera on a wall or in an interior meters the sky *behind* the geometry. Auto Range and Auto WB share the same blind spot; WB is incident-light by design so it is correct regardless, and Auto Range's peak is deliberately about what the **world** stores (a lamp on a mesh never passes through the world scale) — both stay on the rect meter. Only Auto Exposure gets the choice.

#### Why not read the viewport back

Checked in the Blender source (`draw_context.cc`, `view3d_draw.cc`), not assumed:

| callback | framebuffer bound | contents |
|---|---|---|
| `PRE_VIEW` / `POST_VIEW` | `dfbl->overlay_fb` | the overlay colour, never the scene |
| `POST_PIXEL` | region window | **after** the display transform (AgX/Filmic + CM exposure) — not invertible |

So the scene-linear picture is not readable from any draw handler. The sanctioned path is an **off-screen draw**: `GPUOffScreen.draw_view3d(scene, view_layer, space, region, rv3d.view_matrix, rv3d.window_matrix, do_color_management=False)`. Two properties of that loop matter and were verified: `DRW_draw_render_loop_offscreen` constructs its `DRWContext` with a null `bContext`, and every `ED_region_draw_cb_draw` call is guarded on `evil_C` — **PA2's own draw handlers do not re-enter**; and the mode is `VIEWPORT_RENDER`, so EEVEE runs `draw_viewport_image_render` — every viewport TAA sample in one call. That is the whole cost.

#### The three meters

| meter | reading | stand-in | where it is wrong |
|---|---|---|---|
| **Sky** (default, shipped behaviour) | rect meter key | incident until a frame was metered | anything in front of the sky |
| **Viewport** | offscreen key, fresh (< `VIEW_METER_STALE_S` = 3 s) or during a render job | Sky | Solid/Material-preview views (stale → Sky); renders re-use the last viewport reading |
| **Incident** | `incident_ev` — the §3 illuminant on a horizontal grey card, sunny-16 at clear noon | Sky below `ILLUM_FLOOR` (moonlight; starlight is noise) | lamps and emissive surfaces (it never looks at the frame) |

Every branch ends at the Sky/incident pair, so Auto never goes dead. `_STATE["auto_meter_src"]` → `scene["pa2_auto_meter_src"]` names the meter that delivered; the info box prints `Metered (viewport): EV100 …` so a fallback is visible.

#### Viewport meter mechanics — `core/view_meter.py`

- Runs from the watcher timer (the same block that syncs Auto at 10 Hz), never in a render job, at `_PERIOD_S` = 0.5 s, 160 px wide at the region's aspect, `RGBA32F` (the sun disc and a mirror highlight must not clip in the meter).
- View = the first **RENDERED**-shading 3D view (the one the user judges in). None → no reading → stale → Sky.
- Readback `texture_color.read()`, luminance, then **÷ 2^stops**: the offscreen holds render units — the world already carries the placement pre-scale and the lamps their `lamp_exposure` delta — so dividing by `2^stops` puts the composite in the meter's physical convention: the sky reads what the rect meter reads, and lamps/emission land where they appear on screen against it. Then the same `percentile_key` band law.
- Failure latch after 8 consecutive failures (a backend that refuses the offscreen must not cost a traceback per tick).

Measured (GUI smoke, Blender 5.2.1, factory scene → +2000-strength emissive cube):

| step | viewport key | sky key | src | EV |
|---|---|---|---|---|
| Viewport, plain cube | 1.64 | — | viewport | +0.34 |
| Viewport, emissive cube | **5.69** | 4.68 (unmoved) | viewport | −1.41 |
| switch to Sky | | 4.68 | sky | −1.15 |
| switch to Incident | | | incident | +1.87 |

#### What the first build read wrong (same day, user: "viewport metering is either very bright or not bright enough")

Bisected by dumping the meter's own offscreen image and drawing mini worlds into it. Three independent faults, each verified with a control:

| fault | evidence | fix |
|---|---|---|
| **The draw ran the viewport compositor.** The offscreen satisfies every condition in `DRWContext::is_viewport_compositor_enabled` (v3d, rv3d, RENDERED shading, a compositing node group), so in compositor mode PA2's post stage — `PA2_POST_EXPOSURE` (the full exposure) then the tonemap — ran inside the meter's draw: the meter read its own output back and hunted. A tonemapped reading is not invertible anyway. | compositor on: key tracked EV; off: key 1.64 constant across EV | `space.shading.use_compositor = 'DISABLED'` for the one draw, restored in `finally`; its RNA update is a notifier only (`rna_SpaceView3D_shading_use_compositor_update`, no depsgraph tag). Overlays (`space.overlay.show_overlays`) likewise — the grid, axes and motion paths are bright lines, not scene light. |
| **The rect planes had no mip chain.** GPU-direct publishes render into level 0 of the images' live textures and nothing fills the rest. The viewport never notices (Window-mapped 1:1 → level 0), but a 160 px offscreen of a 1568 px plane samples level ~3 = zeros: the sky read **black** and the "sky" the meter had seen was the overlay grid. | mini world `Image(rect) ← Window`: `Linear` black, `Closest` (no mip) mean 1.78 with the sun at 94; attributes, `Window` coords and the equirect (CPU-uploaded, mipped) all verified fine first | `view_meter._ensure_rect_mips()` before every metering draw: level L-1 → scratch (2×2 box, `texelFetch` — sampler state irrelevant) → level L via a `GPUFrameBuffer` `mip` slot; through a scratch texture so no texture is ever sampled while another level of it is the attachment. Level 0 is never touched. |
| **Compositor mode has no sky in the film.** PA2 renders the film transparent there and composes the world from AOVs later, so the offscreen background is rgb exactly 0 — with alpha still 1 (`draw_background=False` changes nothing; no depth texture in the Python API). Key ≈ 1e-9 → EV ran to +23: the "very bright". | `rgb == 0` on 98.8 % of a sky view, alpha min/max 1/1 | `fold_view`: sky pixels = alpha < 0.5, plus (film transparent) rgb exactly zero; they take the **rect meter's own 48×27 cells** — `fold_meter_cells` now stashes `(max, Σlog2, n)` per cell in `_STATE["rect_meter_cells"]` — for their window position; object pixels stay the offscreen's. A truly black object pixel reads as sky (bias toward the sky's level; far smaller than no sky). In camera view the reading is cropped to the camera frame (`_frame_px`, the `_camera_frame_px` projection), where the rect lives. |

After: compositor mode view key 4.73 vs sky key 4.64, CM mode 4.87 vs 4.73, EV settles at −1.2 without hunting, the emissive cube still lifts the key to 14.7. Unit tests: `ViewMeterFoldTests` (CM = offscreen alone; transparent film → cells; no cells → None).

#### The crash that shaped the lifetime rule

The first smoke run died on quit: `BPyGPUOffScreen__tp_dealloc → GPU_viewport_free → eevee::Instance::~Instance → LookdevWorld::~LookdevWorld → id_free(Image) → IMB_cache_free → MEM_CacheLimiter_unmanage` reading `0x…FFF8`. `WM_exit_ex` frees Blender's data (`BKE_blender_free`, line ~593) **before** `BPY_python_end` (~638): a `GPUOffScreen` still referenced from a module dict is deallocated during Python finalization, after the image cache is gone. The offscreen therefore must die while Blender is alive:

1. **idle**: released after `_IDLE_RELEASE_S` = 5 s without a metering draw (meter switched away, mode left Auto);
2. **file load**: `load_pre` (the EEVEE instance references the old world);
3. **quit**: `bpy.app.handlers.exit_pre` — `BKE_CB_EVT_EXIT_PRE` fires at the top of `WM_exit_ex`, before any teardown; present in 5.2.1 (checked at runtime), registered in `__init__.register`.

Both the idle path and a quit-while-metering run exit 0 with no crash file since.

#### Companion fix, same day — lamps follow the placement (`core/lamp_exposure.py`)

The neutrality law (§Laws) held only for what received the world's `2^stops` pre-scale: sky, synced sun lamp (`oscale` in its energy), lamps on the addon ground (`sky_lights._lamp_scale`). A user's Point/Spot/Area lamp on a **mesh** lives in raw scene units and saw only the CM compensation: Day → Night dimmed it 22 stops, and Auto Range did the same silently at dusk ("the sky stays consistent, but the lights are not"). Every non-managed lamp in an enabled scene now carries `Light.exposure = user value + (stops − (−6))` — zero at the day default — stamped on the datablock (`pa2_exposure_applied`) so only the delta's *change* is ever written and removal subtracts exactly it (Remove Atmosphere, addon disable). `sky_lights` reads the same field, so ground/air/clouds follow. Emission shaders cannot be compensated this way; the Range tooltip says so. This is also why the Viewport meter's ÷ 2^stops is exact for lamps and not only for the sky.

### 3. Auto White Balance — button `world.pa2_auto_white_balance` {#auto-exposure-3-auto-white-balance-button-world-pa2autowhiteba}

Physical illuminant, not grey-world (grey-world neutralises the blue sky itself — the classic landscape AWB failure):

```
E_rgb = sunRad_rgb·Ω · [ T_dir(μ₀)·max(μ₀,0)·fade(el)            direct, horizontal surface
                       + bands_cos_SS(μ₀,h) + bands_cos_MS(μ₀,h) ]  diffuse sky (atlas rows 32 / 96, per unit sun)
      + moon term (E_rel from pa2MoonSkyE's twin · T_dir(μ_moon) · μ_moon · mean moon-map tint)
      + night-lights term when light pollution is on (cel_lp colour · gain)
wp    = E_rgb / max(E_rgb)
```

Write `vs.white_balance_whitepoint = wp` (+ `use_white_balance = True`); Blender derives temperature and tint. Then set `camera_white_balance_k = "CUSTOM"` — a **new enum item** — and `_apply_white_balance` leaves the CM alone in CUSTOM (today it re-writes the temperature from the preset on every sync and would fight the button). The panel shows the derived value next to the button: `Auto (4 870 K, tint 6)`. Bonus: a manual edit of the CM temperature in CUSTOM is respected, which it is not today.

Strength: full neutralisation kills a sunset's warmth; cameras keep some. Optional preference `auto_wb_strength` (0…1, default 1 = physical): `wp = illuminant^s` in linear RGB. Not in v1 unless wanted.

Sanity number for the live scene (sun at 5°, clear): direct beam transmittance (0.36, 0.17, 0.03) → beam alone ≈ 2 000 K; with the horizontal sky term the mix lands ≈ 3 500–4 500 K, i.e. the "Sunset" preset's neighbourhood.

### Shared core — `core/exposure_auto.py` (new, ~200 lines) {#auto-exposure-shared-core-core-exposureauto-py}

- `body_discs(scene)` → list of (name, radiance, above_horizon, in_frame) from the PA2_DATA\_\* idprops + `_STATE["rect_view"]`.
- `sun_transmittance(scene, mu0)` → factor the lamp twin out of `shadow_plane._lamp_physical` so lamp, range and WB share one Beer/KY line (the lamp keeps its behaviour bit-for-bit).
- `sky_irradiance_bands(mu0, h)` → CPU tap of the ambient atlas (`_STATE["ambient_lut"]["tex"].read()`, cached by dep_key); zeros when unbaked.
- `rect_stats()` → `{serial, pose, max, log_mean}` stamped by the publish block in `sky_rect.py` (stride-8 numpy over arrays it already holds; < 2 ms at 3152×1851).
- `auto_range_stops(scene)`, `meter_key(scene)`, `illuminant_rgb(scene)`.

Touch list: `sky_rect.py` publish block (+15), `celestial_math.sync_camera_exposure` (+10) and `_apply_white_balance` (CUSTOM branch), `config/properties.py` (`camera_range_auto`, `camera_range_sun_safe`, CUSTOM item), `interface/operators.py` (2 operators), `interface/panels.py` (3 rows), `__init__.py` (`render_pre` hook), CHANGELOG.

### Laws to keep {#auto-exposure-laws-to-keep}

- The placement is storage only: every auto write goes through `camera_world_output_stops` so the CM compensation, compositor post-exposure and lamp `oscale` stay in the same sync (the 2026-08-21 neutrality law).
- The mirror check in `sync_camera_exposure` runs before the policy re-stamps: an auto stops change must never be read as a manual CM edit — keep the order (auto → policy → stamp).
- Never write the planes' stats from a render job's timer; the publish block is already inside the render-safe path.
- Bands rows are per unit sun; multiply by `sunRad·Ω`, never by the lamp energy (which carries `oscale`).
- The neutrality law covers the scene's lamps too (2026-09-10): `lamp_exposure` writes the placement delta into `Light.exposure`; the synced sun lamp is excluded (it carries `oscale`), the delta is stamped and only its change is written — never fight a user's edit, never leave the delta behind on removal.
- A `GPUOffScreen` never outlives Blender's data: `view_meter.release()` after idle, on `load_pre` and in `exit_pre`. Left to Python finalization it crashes on quit (§2c).
- Only Auto Exposure reads the Viewport meter. Auto Range keeps the rect peak — the fp16 window is about what the world stores, and a lamp on a mesh is not in the world.

### Open questions for the user {#auto-exposure-open-questions-for-the-user}

1. Sun-safe default ON (auto moves only at night/twilight) or the frustum test as default (bigger wins in daylight sky shots, specular-clip risk on mirrors)?
2. WB strength knob in v1, or physical only?
3. Auto Exposure as a button only, or also a live "Auto" toggle for animations (the measurement is already per tick; it would add a smoothed EV track)?


## KSA/KSP-style LUT atmosphere for PA2 {#lut-atmosphere}

`shipped:`{: .label-fixed } Shipping · the default sky since 3.0.0-beta · 05.09.2026 · `docs/design-ksa-lut-atmosphere-2026-09.md`

**In this document:** [1. Decision](#lut-atmosphere-1-decision) · [2. Why this design, not a direct port](#lut-atmosphere-2-why-this-design-not-a-direct-port) · [3. Goals and non-goals](#lut-atmosphere-3-goals-and-non-goals) · [4. Current cost and prototype evidence](#lut-atmosphere-4-current-cost-and-prototype-evidence) · [5. Resources](#lut-atmosphere-5-resources) · [6. Transmittance LUT](#lut-atmosphere-6-transmittance-lut) · [7. Multiple-scattering LUT](#lut-atmosphere-7-multiple-scattering-lut) · [8. Combined sky-view integrator](#lut-atmosphere-8-combined-sky-view-integrator) · [9. Resolve passes](#lut-atmosphere-9-resolve-passes) · [10. Aerial perspective](#lut-atmosphere-10-aerial-perspective) · [11. Cloud split-pass integration](#lut-atmosphere-11-cloud-split-pass-integration) · [12. Refraction compatibility](#lut-atmosphere-12-refraction-compatibility) · [13. Dynamic occlusion](#lut-atmosphere-13-dynamic-occlusion) · [14. Invalidation and scheduling](#lut-atmosphere-14-invalidation-and-scheduling) · [15. Blender GPU implementation](#lut-atmosphere-15-blender-gpu-implementation) · [16. Failure model](#lut-atmosphere-16-failure-model) · [17. Migration plan](#lut-atmosphere-17-migration-plan) · [18. Acceptance gates](#lut-atmosphere-18-acceptance-gates) · [19. Open decisions](#lut-atmosphere-19-open-decisions) · [20. Recommendation](#lut-atmosphere-20-recommendation) · [21. Amendments](#lut-atmosphere-21-amendments) · [22. Source anchors](#lut-atmosphere-22-source-anchors) · [23. Implementation ledger](#lut-atmosphere-23-implementation-ledger)

Status (2026-09-10): MERGED AND SHIPPING — the default visible sky of
3.0.0-beta and later (`atmosphere_lut_rect`, on for new scenes; off = the
analytic reference march), the LUT Lighting Sky feeding the probe, the
Reflections category, F12 and Cycles paths. Still open from §17/§19:
the equirect's own interleaved cloud history (phase 3's "equirect cloud
buffers", decision 6) and the 96→64 aerial depth count (decision 3).
The limb over-read "NOT landed" below is CLOSED (2026-09-05, the
reference was under-resolved; docs/KNOWN_ISSUES.md).

Status at the 2026-09-05 review (end of day): LUT ATMOSPHERE IS THE
DEFAULT VISIBLE SKY on `codex/ksa-lut-atmosphere-clouds` (0381b1a; option
`atmosphere_lut_rect`, Rendering Settings > Visible Sky; off = the analytic
reference march). Landed: the 256x64 transmittance, 192x256 sky-view and
96x96x96 aerial producers with the shared phase-free integrator; the
rectangle's air pass resolves the aerial planes and the sky-view atlas
(phase applied per pixel, a night radiance scale on the 16-bit planes);
KSA's cloud pipeline ported exactly (K1 centroid composite, K2 godray pass,
K3 3x3 interleave with motion-vector dilation, K4 two-segment shell and
mip rule; section 21.9); Phase 5 walked generations under refraction; the
F12 render path; the Reflections category with a cloudless or disabled
probe. Measured against the converged analytic reference: clear sky 0.5%
P95, anti-solar 0.7%, twilight 4.5% (256-step reference), refraction on
2.9%, clouds on 18 to 20% (KSA leaves the multiple-scattering coupling out
by design). The equirect lighting sky resolves the LUT chain too since
the same evening (LUT Lighting Sky, section 9.1: 0.47% P95 against the
converged analytic equirect at 4.9 ms a bake; the shipped "simplified"
march it replaces was 2.3x dark at the zenith). NOT landed: from space the
aerial planes over-read the limb haze within two degrees
(docs/KNOWN_ISSUES.md). Section 17 carries the per-phase status,
section 18 the measured gates, section 23 the ledger and section 23.1 the
compile-time findings.

Amended 2026-09-05 after review: section 21. The body keeps the original
proposal text; a bracketed pointer marks each statement section 21
supersedes.

### 1. Decision {#lut-atmosphere-1-decision}

PA2 should adopt the *shape* of KSA's Hillaire pipeline while keeping PA2's
optical model:

1. bake clear-air transmittance over `(radius, ray zenith)`;
2. bake the all-orders multiple-scattering closure over `(altitude, sun
   zenith)`;

3. integrate single and multiple scattering together into a small,
   horizon-focused sky-view LUT;

4. integrate finite-distance haze into an aerial-perspective LUT by marching
   each angular ray once and storing every intermediate depth slice;

5. keep PA2's cloud march as a separate pass which produces cloud radiance,
   transmittance and representative distance, then place that result into the
   clear atmosphere with aerial-LUT samples;

6. make the equirectangular and camera-rectangle passes resolve those LUTs
   instead of marching the atmosphere again;

7. keep sharp celestials, ground, scene geometry, eclipses, cloud density and
   dynamic shadows outside the smooth clear-air LUT.

The decisive optimization is items 3--5. A transmittance LUT by itself is not
the performance architecture.

```text
optical parameters
       |
       +--> transmittance 256x64 --------+
       |                                  |
       +--> Psi MS 64x64 -----------------+--> sky view 192x256 ----+
                                          |                          |
observer + sun + moon --------------------+--> aerial 96x96x96 -----+--+
                                          |                          |  |
cloud density + shadow volumes ---------> cloud march/temporal L,T,d   |
                                                                     |
dynamic occlusion residual ------------------------------------------+
                                                                     v
                                                        atmosphere/cloud merge
                                                           |              |
                                                           +--> equirect resolve
                                                           +--> camera rect resolve

celestials + ground --------------------------------> full-resolution B plane
```

### 2. Why this design, not a direct port {#lut-atmosphere-2-why-this-design-not-a-direct-port}

KSA's supplied shaders implement Hillaire's production model:

- `AtmosphereLuts.glsl`: Bruneton transmittance mapping and a horizon-focused
    sky mapping;

- `AtmosphereFunctions.glsl`: one forward march which accumulates view
    transmittance and samples transmittance/MS LUTs;

- `MultipleScatteringLut.comp`: 64 directional rays per texel, a shared-memory
    reduction and the geometric-series `1/(1-f_ms)` closure;

- `SkyLut.comp`: a 50-step clear-air march per angular texel;
- `AerialPerspectiveLut.comp`: one march per XY direction which stores all Z
    slices;

- `Atmosphere.comp`: normally two sky texture reads, or an aerial lookup, at
    display resolution;

- `Godrays.comp`: a low-resolution, temporally accumulated occlusion residual
    which is subtracted from the clear LUT result;

- `RaymarchCloud.comp` + `UpscaleCloud.comp`: a separate low-resolution cloud
    march and full-resolution temporal reconstruction. The cloud march samples
    transmittance, aerial, MS/ambient and shadow-volume resources, evaluates
    expensive atmospheric placement once at its transmittance-weighted cloud
    centroid, and publishes premultiplied cloud color plus transmittance.

The accompanying KSA research records 256x64 transmittance, 192x256 sky-view
and 96x96x96 aerial LUTs. KSA rebuilds the LUT chain every frame; its reported
RTX 2080 Super timings at 1440p were about 0.01 ms transmittance, 0.05 ms sky,
0.05 ms aerial and 0.2--0.3 ms final sampling.

PA2 cannot copy the shader literally. PA2 also carries an aerosol boundary
layer, spectral ozone, OPAC aerosol phase, airglow, moonlight, eclipses,
ground ambient, optional refraction, a world-lighting equirect and a separate
camera fovea. Those features determine the storage, precision and cache keys
below.

### 3. Goals and non-goals {#lut-atmosphere-3-goals-and-non-goals}

#### Goals

- The normal equirect and camera-rectangle shaders contain **no atmosphere
    integration loop**.

- Camera rotation resolves the existing LUT without rebaking it.
- Sun motion or observer-altitude changes rebuild only the small camera-
    dependent LUTs.

- Atmospheric parameter edits rebuild the complete dependency chain safely.
- Day, twilight, space limb and deep night retain PA2's current optical model.
- The same `S + T * B` law remains valid for EEVEE, Cycles publication,
    reflections and the compositor.

- The analytic march remains available as the reference and automatic
    fallback until the LUT path has shipped successfully.

- Normal-tier atmosphere work should become nearly independent of output
    resolution.

- The existing rectangle cloud split, interleave and temporal history remain
    independent of the atmosphere LUT cache and keep their own update cadence.

- The same cloud/atmosphere ordering equation works for the camera rectangle,
    the equirectangular lighting sky and finite scene depth.

#### Non-goals

- No change to cloud density, cloud phase, light marching, noise or temporal
    reconstruction in the atmosphere prototype.

- No cloud density, cloud lighting or cloud temporal resolve inside any
    clear-air LUT builder. This design does define the split-pass interface,
    dependency graph and composition law they must use.

- No removal of the analytic reference during the first release.
- No attempt to reproduce KSA's simplified optical coefficients.
- No CPU readback in the interactive LUT chain.

### 4. Current cost and prototype evidence {#lut-atmosphere-4-current-cost-and-prototype-evidence}

With the fovea disabled, PA2's Normal equirect is 2048x1024. The property
defaults are 8 single-scattering and 8 multiple-scattering view samples, so a
single full bake starts at roughly 33.6 million atmosphere iterations before
ground, shadow and feature overhead. The camera rectangle may repeat much of
that work at view resolution.

The 2026-09-04 transmittance prototypes showed why the complete architecture
matters:

| variant | warm Blender 5.2 result | conclusion |
|---|---:|---|
| analytic reference | 39.9 ms in the final validation run | baseline |
| LUT sun + endpoint-ratio view LUT | 24.3 ms vs 17.3 ms reference in its repeated run | dependent view texture reads made it about 40% slower |
| LUT sun + forward Simpson view column | 38.2 ms vs 39.9 ms reference | approximately break-even; correct foundation, not the large win |

The hybrid's 95th-percentile relative scatter error was 0.83%; only 0.005%
of active channel samples exceeded 1%. Transmittance error was negligible.
The evidence supports KSA's choice: use the transmittance LUT for the sun path,
accumulate the view path forward, and amortize the *completed radiance* in a
sky-view LUT.

### 5. Resources {#lut-atmosphere-5-resources}

Initial fixed dimensions deliberately match the known KSA layout. Quality
scaling should be added only after image-error and timing sweeps establish
where it helps.

| resource | initial size / format | contents | dependency class |
|---|---|---|---|
| `transmittance` | 256x64 RGBA16F | RGB sample-to-top transmittance | optical-static |
| `psi_ms` | 64x64 RGBA16F | RGB all-orders isotropic source, A=`f_ms` diagnostic | optical-static |
| `sky_scatter` | 192x256 RGBA32F | RGB integrated radiance; A reserved | camera-light |
| `sky_transmit` | 192x256 RGBA16F | RGB view transmittance; A validity/debug | camera-light |
| `aerial_scatter` | 96x96x96 RGBA32F | RGB finite-distance radiance | camera-light |
| `aerial_transmit` | 96x96x96 RGBA16F | RGB finite-distance transmittance | camera-light |
| `aerial_range` | 96x96 R32F | ray range used by the Z mapping | camera-light |

The atmosphere resources do not store clouds. Existing rectangle cloud
history stays projection-local:

| cloud resource | format | contract |
|---|---|---|
| `cloud_L_d` | RGBA16F | RGB premultiplied intrinsic cloud radiance, A representative distance in km |
| `cloud_T` | RGBA16F | RGB cloud transmittance; A reserved |
| `cloud_history_aux` | existing A/history format | motion, sample count and centroid/depth data owned by the temporal cloud resolve |

`cloud_L_d` and `cloud_T` are not LUT-generation outputs and do not count
toward the warm atmosphere-LUT memory gate. Their semantic contract must be
identical for fragment and compute paths.

Why PA2 initially keeps scatter at 32-bit: existing testing found deep
twilight radiance can underflow RGBA16F. Transmittance is bounded and remains
16-bit. The aerial pair costs about 21 MiB at 96 cubed; sky + transmittance +
Psi add about 1.3 MiB. A later log-radiance or exposure-relative encoding may
halve this, but it is not part of the correctness prototype.

If Blender's backend cannot expose a writable 3D image consistently, use a
96x(96\*96) or tiled 2D texture. The algorithmic invariant is one invocation
per angular coordinate writing all depth slices, not the physical texture
shape. [Amended 2026-09-05: writable `FLOAT_3D` image stores are proven on
Vulkan by the shadow volume; see section 21.6.]

### 6. Transmittance LUT {#lut-atmosphere-6-transmittance-lut}

Retain the implemented Bruneton/Hillaire `(r, mu)` mapping and half-texel
reciprocity. It already supports PA2's spherical geometry.

The stored quantity is full RGB extinction from a point to the top boundary:

```text
T_top(r, mu) = exp[-tau_R - tau_M - tau_O3]
```

PA2 may continue using analytic Rayleigh, aerosol-shell and ozone integrals
when generating each texel. KSA's 50-step numerical bake is simpler, but the
LUT is tiny and changes rarely in Blender. Generation cost is less important
than agreement with the analytic reference.

Rules:

- the sampler exists only in shaders which explicitly declare it;
- every auxiliary builder owns a complete, explicit feature mask;
- rays intersecting the solid planet return zero direct-sun transmittance;
- top radius is stored or derived by one shared helper in producer and
    consumer;

- the LUT is invalidated by radius, Rayleigh/aerosol/ozone parameters,
    component toggles and aerosol-bump parameters, never by camera or sun pose.

### 7. Multiple-scattering LUT {#lut-atmosphere-7-multiple-scattering-lut}

PA2 already owns the core Hillaire solution in the 64x64 Psi band of the
ambient atlas. The new pipeline should promote that band to a dedicated
`psi_ms` resource rather than copying it out of a multi-purpose 64x256 atlas.
The cloud/ground ambient atlas can continue consuming it. [Amended
2026-09-05: not promoted, builders bind the atlas; see section 21.4.]

Axes:

```text
x = sunCosZenith * 0.5 + 0.5
y = nonlinear altitude over [Rground, Rtop]
```

Each texel uses full-sphere directional quadrature, integrates second-order
isotropic luminance and the re-scatter fraction, then applies:

```text
Psi = L_second / max(1 - f_ms, epsilon)
```

PA2's existing Fibonacci quadrature should remain; it was introduced to
remove the striping and forward-lobe bias of an 8x8 grid. Ground-albedo bounce
remains part of the closure. The resource depends on optical parameters and
ground albedo, but not observer position or the actual sun direction because
sun zenith is an axis.

### 8. Combined sky-view integrator {#lut-atmosphere-8-combined-sky-view-integrator}

Create a new clear-air integrator; do not call the existing
`atmosphere_clouds()` function from the LUT builder. Its single loop evaluates
both SS and MS at each sample. [Amended 2026-09-05: the stored quantities
are phase-free integrals, section 21.2; one integrator serves both LUTs,
section 21.5.]

For a step of length `ds` at the representative position:

```text
rhoR, rhoM, rhoO3 = local density profiles
sigma_t           = beta_eR*rhoR + beta_eM*rhoM + sigmaO3*rhoO3
T_step            = exp(-sigma_t*ds)
W                 = T_view * (1 - T_step) / max(sigma_t, epsilon)

T_sun = sample transmittance(r, dot(up, sunDir))
L_ss += W * T_sun * shadow_smooth
        * (beta_sR*rhoR*phaseR + beta_sM*rhoM*phaseM)

Psi  = sample psi_ms(altitude, sunCosZenith)
L_ms += W * Psi * (beta_sR*rhoR + beta_sM*rhoM)

L_emission += W * airglow_emission
T_view     *= T_step
```

Use a stable `expm1`-style limit so `W -> T_view*ds` when extinction tends to
zero. Compute phases once per ray when refraction is off. With deterministic
refraction, update the phase from the bent direction only at the same sparse
stations used by the reference path.

Suggested sample ladder for the small LUT, subject to measurement:

| tier | sky steps |
|---|---:|
| Potato | 16 |
| Low | 24 |
| Normal | 32 |
| High | 48 |
| NASA | 64 |

These counts are intentionally higher than the current per-output-pixel
defaults because 49,152 sky texels are far cheaper than millions of output
pixels. [Amended 2026-09-05: one fixed count for every tier; see section
21.5.]

#### 8.1 Angular mapping

Adopt KSA's modified Hillaire mapping:

- X is full `[-pi, pi]` azimuth around the local zenith, with zero facing the
    projected sun;

- Y is split at the geometric horizon;
- both halves square the inverse coordinate, concentrating rows at the limb;
- outside the atmosphere, restrict the upper range to the visible atmosphere
    cone;

- apply the same half-texel transform in both directions.

At the zenith and when the sun is parallel to the zenith, cross products are
ill-conditioned. Fall back to PA2's observer north/east basis, not an arbitrary
world axis, so the LUT does not spin between frames.

The resolve must never bilinearly blend across the ground/sky horizon. Compute
the ground-intersection class from the exact output ray and clamp Y to the
matching half by at least half a texel. This follows KSA's aerial horizon fix.

#### 8.2 Night and secondary lights

The mapping covers the complete sphere, so broad moon-scattered light,
airglow and light-pollution emission can be baked despite the coordinate frame
being sun-relative. Sharp stars, the moon disc, sun disc and planets remain in
the full-resolution background plane.

The first milestone may include solar SS, Psi MS and airglow, then add lunar
SS as a separate acceptance item. It must not silently remove the existing
night sky.

### 9. Resolve passes {#lut-atmosphere-9-resolve-passes}

Both output domains consume the same sky LUT. [Amended 2026-09-05: the same
builder, but two generations when refraction is on; see section 21.3.]

#### 9.1 Equirectangular lighting sky

[Implemented 2026-09-05 (LUT Lighting Sky, `probe_lut`, on by default):
the equirect build takes the LUT (`_build_shader(lut=)` and the draft
compute twin), sky rays read the sky-view atlas, ground rays the aerial
planes, and the KSA cloud arm runs inline at probe resolution with the
centroid composite; no godray pass, no object shadows, no interleave; the
render bake takes the same path with the arm per sample. Measured
(`scripts/probe_equirect_lut.py`, 1024x512, sun 20 degrees, clear):
0.47% P95 against the converged analytic equirect (64 view + 256 MS
steps; sky half 0.62%, transmittance 0.29%) at 4.9 ms a bake against that
reference's 36 ms and the shipped "simplified" march's 4.3 ms. The
simplified march it replaces sat 2.3x dark at the zenith (the 8 + 8
estimator verdict of 21.5, halved again), so world lighting brightens
where it was wrong. With clouds both cost about 20 ms: the inline cloud
arm is the bake. Cold compile of the variant 5 to 18 s (the fallback
march is still compiled in), 1.5 s with Reflect Clouds off.]

For every equirect direction:

1. reconstruct the world ray;
2. map it into the sky-view LUT;
3. fetch clear-air `S_D` and `T_D` to the ground hit or infinity;
4. when clouds are enabled, consume the equirect cloud pass and merge it by
   the depth-resolved equation in section 11 [Amended 2026-09-05: `S_d, T_d`
   come from the sky-mapped aerial; see section 21.1];

5. compute cheap ground-only lanes (`INDIRECT`, direct-sun shadow and ground
   distance) from the transmittance and ambient LUTs;

6. compose full-resolution ground/celestials with `S + T*B`;
7. publish the one combined lighting texture as today.

This resolve is output-resolution work, but contains no atmosphere loop.
The first parity implementation may run the equirect cloud pass at its full
target resolution and existing low bake cadence. Its projection differs from
the rectangle, but it uses the same `L,T,d` contract and cloud-march library.
Temporal/interleaved equirect clouds are a later optimization, not a reason to
put clouds back into the atmosphere march.

#### 9.2 Camera rectangle

The rectangle performs the same lookup using the camera ray. For sky pixels it
uses the sky-view pair. For finite scene depth it uses the aerial pair. It then
consumes the existing temporally reconstructed cloud pair and merges it at the
stored representative depth. Ground, celestials and the existing AOV rules
remain full resolution.

Camera rotation changes only this resolve. Camera translation which changes
observer altitude or the local zenith invalidates the camera-light LUTs.

#### 9.3 Ground support planes

`FragIndirect` and `FragShadow` should stop being by-products of the expensive
sky march:

- ground ambient: one lookup in the existing measured ambient atlas;
- clear-air direct shadow: one transmittance lookup at the ground point;
- ground distance and hit mask: analytic or refracted ray geometry;
- cloud opacity affects a ground/geometry target only when its validated
    front or centroid distance is in front of that target;

- cloud shadows on the ground remain in the existing receiver/shadow path.

This makes their cost independent of sky sample count and prepares those MRTs
for later removal or lower precision.

### 10. Aerial perspective {#lut-atmosphere-10-aerial-perspective}

[Amended 2026-09-05: the XY domain is the sky-view angular mapping of
section 8.1, not the camera frustum; see section 21.1.]

The current parked PA2 atlas evaluates the complete atmosphere/cloud composite
separately for every slice. That repeats nearly all work and should not be
reactivated as-is.

The replacement dispatches one invocation per XY angular texel. Its loop has
exactly `depthSlices` iterations and writes accumulated `S` and `T` after each
iteration. Thus 96 slices cost 96 steps, not 96 independently truncated
marches.

Use KSA's depth mapping:

```text
inside atmosphere: distance = range * z^2
outside atmosphere: distance = range * z
```

Store the exact per-direction range in `aerial_range`. Runtime sampling uses
bicubic XY and linear Z; do not use tricubic filtering. Clamp bicubic samples
to the same side of the horizon. Before the first slice, interpolate from
`S=0, T=1`.

The initial 96 cubed target is a parity target, not a permanent minimum. A
48/64-slice low tier should be tested after the correct one-march/many-write
implementation exists.

### 11. Cloud split-pass integration {#lut-atmosphere-11-cloud-split-pass-integration}

This is part of the atmosphere architecture even though cloud rendering is a
separate project. The contract follows KSA's useful separation:

1. clear atmosphere is generated without cloud density;
2. clouds march in their own projection-local, low-resolution pass;
3. the cloud pass consumes atmosphere lighting resources rather than calling
   the sky-view builder;

4. a transmittance-weighted cloud centroid defers atmosphere placement,
   motion and other expensive position-dependent work to one evaluation;

5. cloud history is reconstructed independently;
6. the final resolve orders reconstructed clouds inside the clear atmosphere.

PA2 already implements the rectangle form of steps 2, 4 and 5 in
`sky_driver.glsl` and `sky_rect.py`: the dedicated pass publishes cloud
radiance, transmittance and centroid/front distance, and the air pass consumes
those textures. The LUT migration must preserve that path, not replace it
with a combined atmosphere/cloud shader.

#### 11.1 Buffer semantics

Use these unambiguous quantities for one effective cloud layer:

```text
L_c = intrinsic premultiplied cloud radiance before view-air placement
T_c = cloud transmittance
d   = transmittance-weighted representative cloud distance
f   = conservative cloud-front distance, when available (cloud_T.a, 21.7)
```

The temporal history stores `L_c`, `T_c`, `d` and its reprojection metadata.
It must not store the final atmosphere/cloud composite. This keeps the clear
atmosphere fresh while a 3x3 cloud history is deliberately several rounds old
and avoids feeding smooth atmospheric gradients through the cloud history
clamp.

KSA applies aerial perspective once at the weighted centroid inside its cloud
pass. PA2 should perform the equivalent operation immediately *after* cloud
temporal reconstruction. This is algebraically the same split, but better
matches PA2's existing raw `uCloudL/uCloudT` history and lets one fresh
atmosphere generation serve old and new cloud samples consistently.

#### 11.2 Ordered composition

For a target at distance `D` (scene depth, ground, or infinity), fetch:

```text
(S_D, T_D) = clear atmosphere from camera to D
(S_d, T_d) = clear atmosphere from camera to cloud centroid d
```

When the cloud is in front of the target, compose without reconstructing or
dividing by the behind-cloud segment:

```text
C_cloud_at_eye = T_d * L_c + (1 - T_c) * S_d
S_out          = C_cloud_at_eye + T_c * S_D
               = T_d*L_c + (1-T_c)*S_d + T_c*S_D
T_out          = T_c * T_D
```

This is the depth-resolved form of KSA's transparent cloud composite and the
same factorization already used by PA2's analytic split path. It correctly
retains clear-air radiance in front of an opaque cloud, attenuates the air
behind it, and attenuates the final background by both media. It also avoids
the numerically unsafe `(S_D-S_d)/T_d` division near an opaque horizon.

If `f >= D`, or the cloud interval does not overlap the target ray, use the
clear result unchanged. Use `f` for the conservative visibility decision and
`d` for atmosphere placement/reprojection. A single centroid is an accepted
approximation for overlapping layers; if horizon-separated layers visibly
misorder, extend the contract to near/far `L,T,d` slices before considering a
general per-pixel layer list.

#### 11.3 Cloud inputs from the LUT system

The cloud pass may sample, but never write or invalidate:

- `transmittance` for sun/moon-to-cloud extinction;
- `psi_ms` and the ambient LUT for broad skylight;
- `aerial_scatter`, `aerial_transmit` and `aerial_range` only in the post-
    temporal placement/merge stage;

- cloud shadow and ambient volumes for local lighting and long-range light
    extinction.

The sky-view LUT is not a cloud-lighting lookup. It is observer/view
directional radiance and would couple cloud lighting to camera orientation.
Cloud ambient continues to use its dedicated measured/angular resources.

#### 11.4 Pass order and cadence

```text
dirty physical state:
    transmittance -> psi/ambient -> sky + aerial

each cloud update:
    shadow/ambient volumes -> low-res cloud L,T,d -> cloud temporal resolve

each output resolve:
    clear S_D,T_D + clear S_d,T_d
    -> apply dynamic SS residuals at D and d
    -> cloud/atmosphere ordered merge
    -> ground/celestial background: S_out + T_out*B
```

Atmosphere and cloud generations are independently publishable. A cloud
history reset does not discard valid atmosphere LUTs; a new atmosphere
generation does not erase cloud history. The merge records both generation
IDs so it never samples partially published resources. When an atmosphere
build fails, the cloud pass uses the last good generation or the analytic
placement fallback along with the rest of the renderer.

#### 11.5 Dynamic cloud shadows and godrays

KSA keeps cloud density out of the sky LUT and represents its effect on air as
a separate, low-resolution temporally accumulated *shadowed single-scatter
residual*. PA2 should retain this model. Let `G_D` and `G_d` be removed clear
single scattering to the target and cloud centroid. Before the ordered merge:

```text
S_D' = max(S_D - G_D, 0)
S_d' = max(S_d - G_d, 0)
```

Use `S_D'` and `S_d'` in the equation above. Multiple scattering is not
subtracted, so shafts do not turn unnaturally black. Cloud self-lighting still
uses the cloud shadow volume. The first LUT milestone can set both residuals
to zero, but the resource slots, depth convention and merge API must exist so
godrays can be added without changing the base LUT formats. [Implemented
2026-09-05 as KSA's godray pass (21.9 K2): scene casters and the cloud
shadow volume, half resolution, its own history; the 5% aerosol damp KSA
applies is removed, see 23.1.]

### 12. Refraction compatibility {#lut-atmosphere-12-refraction-compatibility}

[Amended 2026-09-05: superseded by section 21.3. No `ray_geometry` table;
the builders run the shared refraction walk per texel, and the sky LUT is
baked in two generations when refraction is on. The shimmer paragraph
stands.]

Deterministic atmospheric refraction must be part of the ray used to generate
sky and aerial LUT texels; otherwise the horizon color, ground hit and body
positions disagree.

Spherical refraction geometry depends on observer altitude and apparent
zenith, not azimuth. Add a camera-height-dependent 1D `ray_geometry` table
which stores, per apparent zenith:

- accumulated bend / exit direction parameters;
- ground-hit distance and angular travel;
- atmosphere entry/exit distance;
- a validity/fold classification for mirage cases.

The sky/aerial builders and the full-resolution background/ground resolve read
the same table. This keeps sharp celestials full resolution while sharing the
same bent path used by atmospheric radiance. Apparent-ray to physical-path is
single-valued even when the inverse true-angle mapping folds in a mirage.

Shimmer is deliberately not baked into the low-resolution LUT. Apply its small
direction perturbation when mapping the output ray and when placing
celestials. Large shimmer amplitudes must trigger a wider reconstruction
filter or fall back to the reference path.

Until `ray_geometry` passes its alignment tests, enabling the LUT renderer with
ray-marched refraction should select the analytic reference automatically.

### 13. Dynamic occlusion {#lut-atmosphere-13-dynamic-occlusion}

The clear LUT contains the planet's smooth self-shadow and celestial penumbra
which are representable at its resolution. High-frequency mesh/cloud shadows
must not force the base atmosphere back into a full-resolution march.

Residual pass (implemented 2026-09-05: `godray_lib.glsl`,
`godray_driver.glsl`):

```text
S_final = max(S_clear - S_occluded_single, 0)
```

Only single scattering is subtracted; multiple scattering continues lighting
the shadowed volume. The residual may use the existing caster map and cloud
shadow volume at reduced resolution with temporal history. Section 11.5
defines the two depth samples needed for correct ordering with the split cloud
pass. The residual implementation belongs after the clear-air migration.

Eclipses with a large, smooth penumbra may be baked into the sky LUT. Small or
moving occluders use the residual path. The boundary is selected by projected
angular frequency, not by object type.

### 14. Invalidation and scheduling {#lut-atmosphere-14-invalidation-and-scheduling}

Use explicit generations rather than one monolithic source key.

| generation | invalidated by | does not depend on |
|---|---|---|
| optical | radii, scale heights, beta coefficients, aerosol bump, ozone, component toggles | camera, sun pose, exposure |
| MS | optical generation, ground albedo, MS controls | camera, actual sun direction |
| ray geometry (removed, section 21.3) | observer altitude, refraction profile/toggles | sun, atmosphere radiance |
| camera-light | optical/MS/ray generation, observer position, sun/moon state, emission parameters | camera orientation, output resolution |
| cloud lighting | cloud parameters, cloud animation, optical/MS generation, sun/moon state, cloud shadow/ambient volumes | atmosphere output resolution |
| cloud history | cloud-lighting generation, projection/camera discontinuity, history dimensions | sky/aerial rebuild when raw history semantics are retained |
| resolve | camera matrices, output dimensions, background/ground state, exposure, published atmosphere/cloud generations | optical or cloud integration |

Unlike KSA, PA2 does not need to rebuild everything every frame. A stationary
Blender camera with a rotating view reuses all physical LUTs. Scene animation
may rebuild the small camera-light generation each frame.

Physical build and per-view order:

```text
transmittance -> psi_ms -> ray_geometry -> sky_view -> aerial
                                       cloud volumes -> cloud march/history
atmosphere generation + cloud generation ------------> ordered resolve
```

Only rebuild dirty suffixes. Render into staging resources and publish/swap a
generation only after every required pass succeeds. Never expose a mixture of
old Psi and new sky radiance.

### 15. Blender GPU implementation {#lut-atmosphere-15-blender-gpu-implementation}

Recommended ownership:

```text
_STATE["atmosphere_luts"] = {
    "generation_keys": ...,
    "transmittance": ...,
    "psi_ms": ...,
    "ray_geometry": ...,
    "sky": ...,
    "aerial": ...,
    "last_good": ...,
}
```

One owner makes purge and context loss atomic. It avoids adding more unrelated
top-level keys to the existing hand-maintained GPU reset list.

Cloud history remains owned by the rectangle/equirect projection cache, not
by `atmosphere_luts`. The resolve receives an immutable view of one complete
atmosphere generation and one complete cloud-history generation.

Shader layout:

- `atmosphere_lut_integrator.glsl`: clear-air combined SS/MS march;
- `sky_view_lut_driver.glsl`: angular reconstruction and two outputs;
- `aerial_lut_driver.glsl`: angular reconstruction, depth loop and stores;
- `atmosphere_lut_resolve.glsl`: equirect/rect lookup and support lanes;
- `atmosphere_cloud_merge_lib.glsl`: shared equation, front-depth test and
    optional godray-residual inputs for fragment and compute resolves;

- retain `sky_driver.glsl` as the analytic reference during migration.

Each builder declares a minimal sampler set and constructs its compile defines
from a local allowlist. Do not derive auxiliary builders by taking the main
shader's global toggle tuple and trying to pin individual entries afterward.
That pattern caused the transmittance sampler to leak into the ambient shader.

Use compute shaders and GPU-only scratch textures where supported. Keep the
existing fragment fallback for backends where writable image formats are not
reliable. Publication to Blender images happens after resolve, not between LUT
passes.

### 16. Failure model {#lut-atmosphere-16-failure-model}

Priority order on a failed build:

1. keep and use the last complete LUT generation;
2. if no complete generation exists, compile/use the analytic reference;
3. only use black scatter/unit transmittance for an explicitly disabled
   atmosphere.

A failed ambient or MS bake must not replace valid lighting with zero. Record
the failed stage and source key, log it once, and retry only when that key or
the GPU context changes.

Modes exposed during development:

- `REFERENCE_MARCH`: current analytic renderer;
- `LUT_EXPERIMENTAL`: complete LUT path;
- `AUTO`: LUT when a valid generation exists, otherwise reference.

Do not expose individual internal LUT toggles in normal user modes. Scientist
mode may show them for A/B validation.

### 17. Migration plan {#lut-atmosphere-17-migration-plan}

Status per phase (review 2026-09-05):

| Phase | State | Where |
|---|---|---|
| 0 harness | done; the three prototype toggles retired (5176cab) | `probe_lut_parity`, `_diag`, `_ms_trend`, `_rect`, `probe_viewport_shot` |
| 1 foundations | done: owned `atmosphere_luts`, last-good generations, keyed rebuilds | `core/sky_luts.py` |
| 2 sky-view | done, go: 0.4% P95 vs the 256-MS-step march, 2 to 4x on GPU time | dbecafc, 21.5 |
| 3 aerial + cloud contract | aerial builder done; the merge helper superseded by KSA's centroid composite (K1); equirect cloud buffers NOT done | 466274b, 21.9 |
| 4 production | rect done and DEFAULT (0381b1a); equirect done the same evening (LUT Lighting Sky, on by default) | 9.1, 23 |
| 5 refraction | done: walked generations, the gate removed, 2.9% residual | 11792e8, 21.9 |
| 6 dynamic residuals | done as KSA's godray pass (scene casters + cloud shadow volume); the eclipse penumbra stays in the base generation | 466274b, 856ec40 |
| 7 default switch | rect default on; verified on Vulkan / RTX 4080 only; the analytic march stays as the option-off referee | 0381b1a |

#### Phase 0 -- measurement harness

- Extend the existing Blender 5.2 probe to capture reference S/T images,
    per-pass GPU timings and cache-rebuild timings.

- Alternate variant order and report medians to control warm-up and clock
    variance.

- Capture every acceptance altitude/sun condition before changing the main
    renderer.

- Capture three matched cloud cases from the existing split path: clear sky,
    one opaque layer and two separated/horizon-grazing layers. Save raw
    `L_c,T_c,d`, final S/T and timing independently.

- [Amended 2026-09-05: report atmosphere GPU time apart from the image
    publish and measure the clouds-on share; see section 21.5.]

#### Phase 1 -- foundations

- Keep the transmittance LUT experimental.
- Add mapping reciprocity, horizon, finite-value and component-toggle tests.
- Extract the Psi band into a dedicated resource without changing its math.
    [Amended 2026-09-05: dropped; see section 21.4.]

- Introduce the owned `atmosphere_luts` state and last-good generation logic.

#### Phase 2 -- sky-view prototype

- Implement the clear-air combined SS/MS integrator.
- Bake 192x256 S/T with clouds and dynamic casters compiled out.
- Add a diagnostic equirect resolve beside, not instead of, the reference.
- Compare day, terminator, night and space-limb images.

This phase is the go/no-go point. Do not continue if it does not deliver a
clear speedup over the full-output march.

#### Phase 3 -- aerial perspective and cloud contract

- Replace the parked aerial atlas with the one-march/many-slice builder.
- Add the shared cloud/atmosphere merge helper and validate its algebra using
    synthetic constant `L_c,T_c,d` buffers.

- Feed the existing rectangle split-cloud history into the diagnostic LUT
    resolve; do not change the cloud march or history algorithm.

- Add full-resolution equirect split-cloud buffers for parity with the camera
    path while retaining the analytic inline renderer as reference.

- Validate cloud-before-ground, cloud-before-space-background and
    geometry-before-cloud ordering.

#### Phase 4 -- production equirect and rectangle

- Route both output domains through the shared sky/aerial LUTs and cloud
    merge.

- Rebuild cheap ground ambient/shadow/distance lanes independently.
- Preserve exact full-resolution celestials, ground composition and existing
    cloud temporal cadence.

- Add `AUTO` fallback, generation mismatch and context-loss tests.

#### Phase 5 -- refraction parity

- Implement/share the 1D ray-geometry table. [Amended 2026-09-05: no table;
    walked LUT generations instead, section 21.3.]

- Validate atmosphere, ground and celestial alignment from ground and orbit.
- Enable LUT + refraction in `AUTO` only after parity.

#### Phase 6 -- dynamic residuals

- Move mesh/eclipse high-frequency occlusion to the subtractive residual.
- Feed the cloud shadow volume into `G_D/G_d` and validate shafts both in
    front of and behind opaque clouds.

- Keep cloud density/lighting improvements in the separate cloud branch.

#### Phase 7 -- default switch

- Make `AUTO` the default after the acceptance matrix passes on Vulkan,
    DirectX/Metal paths available through Blender, and at least one integrated
    GPU.

- Keep `REFERENCE_MARCH` for one release as a regression referee.

### 18. Acceptance gates {#lut-atmosphere-18-acceptance-gates}

Measured so far (2026-09-05; the reference is the converged analytic march,
64 view + 256 MS steps, 256 view steps at twilight):

- Daylight sky pixels: 0.50% P95 sun-facing, 0.73% anti-solar (the 1% gate
    is met). Transmittance MAE 6e-4, anti-solar 0.8% (the 5e-4 P99 gate is
    not met as written; the MAE sits at it).

- Twilight (sun -8 degrees): 4.5% P95, centre column within 4%.
- Night (moon 40 degrees, the factory lamp removed): 1% at the horizon.
- Refraction on: 2.9% P95 (the LUT 1 to 3% brighter, more in blue).
- Clouds on: sky pixels 18 to 20%, opaque cloud 16 to 18%, clear air
    between clouds 24% sun-facing and 6% anti-solar; centre-column cloud
    rows within 4%. Expected: KSA occludes single scattering only.

- Space: the sunlit limb haze is present again (856ec40) but over-reads
    the reference two to three times within two degrees under the limb,
    equal by four degrees (docs/KNOWN_ISSUES.md).

- Seams: the anti-solar atlas seam and the pack offset are fixed
    (5176cab); no NaN / Inf in any probe.

- Performance: atmosphere GPU time 2 to 4x faster than the 8 + 8 march
    and 5 to 6x faster than the 64 + 32 march (equirect probe); rect air
    pass 11 -> 2 ms clear and 14 -> 5 ms with clouds at 1920x1080; a
    rotation rebuilds no generation; the interleave is untouched by the
    LUT. Not measured: the 4K resolve scaling, the warm-resource budget,
    DirectX / Metal / integrated GPUs.

- Cold shader compile with clouds (23.1): rect air compute 15 s, its
    fragment twin 15 s, equirect 4.6 s after the cut guard, cloud pass 2 s;
    the driver caches them afterwards.

#### Correctness matrix

- Sun elevations: `90, 45, 15, 5, 1, 0.25, 0, -1, -6, -12, -18` degrees.
- Observer altitudes: `1 m, 2 km, 10 km, 50 km, 100 km, 400 km`.
- View cases: zenith, anti-sun, solar aureole, both sides of horizon, ground
    hit, tangent limb and atmosphere entry from space. [Amended 2026-09-05:
    add the earth-shadow / Belt of Venus edge; the aureole is exact under
    section 21.2.]

- Components: Rayleigh-only, aerosol-only, ozone-only, all enabled, each
    disabled in turn.

- Extremes: smallest/largest supported planet, scale heights, turbidity,
    ozone and ground albedo.

- Night: airglow, moon above/below horizon and light-pollution map.
- Refraction: off, standard, inferior mirage, mock mirage and orbital limb.
- Clouds: none, thin, opaque, one layer, two separated layers, horizon
    grazing, cloud behind geometry, cloud over ground and orbit view.

#### Image thresholds

- Daylight active pixels: relative RGB error P95 <= 1%, P99 <= 3%.
- Twilight: absolute radiance error and log-luminance delta are primary;
    relative error is not meaningful near black.

- Transmittance: absolute error P99 <= 5e-4.
- No one-texel horizon seam, concentric station bands or NaN/Inf values.
- Ground, atmosphere and celestial refracted edges agree to <= 0.5 output
    pixel at the target view resolution.

- With a frozen cloud history, LUT versus analytic split composition agrees
    within the daylight S/T thresholds; cloud edges show no clear-air halo or
    dark fringe.

- Updating an atmosphere generation while reusing cloud history produces no
    one-frame flash, double haze or cloud-shaped discontinuity.

#### Performance thresholds

- Phase-2 sky-view bake plus resolve is at least 2x faster than the reference
    full-output atmosphere at Normal 2048x1024 on the development machine.

- At 4K, changing only output resolution adds resolve cost but does not change
    integration cost.

- A camera rotation performs no LUT integration rebuild.
- Cloud interleave remains independently measurable: enabling a clean-sky
    LUT does not trigger a full-resolution cloud march or reset its history.

- Warm LUT resources stay below 32 MiB at Normal excluding temporary staging;
    below 64 MiB including staging.

- No synchronous CPU readback on viewport updates.

### 19. Open decisions {#lut-atmosphere-19-open-decisions}

1. Whether 32-bit scatter is required for the aerial LUT after exposure-
   relative encoding is tested. [Answered 2026-09-05: section 21.6.]

2. Whether lunar scattering joins the first sky-view milestone or the night
   parity follow-up. [Answered 2026-09-05: first milestone; section 21.5.]

3. Whether the normal aerial depth count can fall from KSA's 96 to 64 without
   visible near-camera or horizon artifacts. [Open 2026-09-05: 96 kept, 64
   untested; the limb over-read from space argues for a limb-aware slice
   distribution before any reduction.]

4. Whether dynamic eclipses belong in the base sky generation or the
   subtractive residual, based on their angular frequency. [Answered
   2026-09-05: the base generation carries the eclipse penumbra (the
   integrator's `pa2EclipseShadow`) and the godray pass applies it to what
   it subtracts; there is no eclipse residual.]

5. Whether to retain four published PA2 support images after the resolve or
   collapse internal S/T/support lanes before publication. [Answered
   2026-09-05: the four rect planes stay; the sky-view planes travel as one
   RGBA32F atlas, the aerial as six 3D planes plus a range plane.]

6. Whether equirect clouds should remain full-resolution/low-cadence or gain
   an independent interleaved history after parity. [Open 2026-09-05: the
   equirect still marches its clouds inline and analytically; the
   Reflections category can drop them (Reflect Clouds).]

7. Whether two separated PA2 cloud layers require the near/far two-slice
   contract at Normal quality, or whether the existing weighted centroid is
   visually sufficient. [Answered 2026-09-05: KSA's two shell segments (K4)
   with the optical-weight distance blend, one centroid per segment.]

### 20. Recommendation {#lut-atmosphere-20-recommendation}

Proceed with Phase 0 and Phase 1, then build the 192x256 clear-air sky-view
prototype. Do not spend more time micro-optimizing the isolated
transmittance-only path: the measured gain is too small. The first engineering
checkpoint is a sky-view result which is visually within the thresholds and
at least twice as fast as the current full-output atmosphere. [Amended
2026-09-05: judged on the equirect alone; section 21.8.]

If that checkpoint fails, retain the analytic renderer and reconsider the
mapping/precision before implementing aerial perspective. If it passes, build
the aerial LUT and immediately validate it through the existing rectangle
cloud split. That is the first end-to-end checkpoint: a fast clean-air LUT,
temporally reconstructed clouds and correct depth-ordered composition, with
no cloud march inside the atmosphere pass.

[Executed 2026-09-05: both checkpoints passed (sky-view 0.4% P95 and 2 to
4x on GPU time; the rect end to end with KSA's cloud composite) and the LUT
is the default rectangle sky. The equirect checkpoint of 21.8 closed the
same evening: the lighting sky resolves the LUT chain (LUT Lighting Sky,
section 9.1).]

### 21. Amendments (2026-09-05 review) {#lut-atmosphere-21-amendments}

Reviewed against the tree at `adb7553`, the first implementation commit
`5aef8c8` (staged transmittance + 192x256 sky-view producers, diagnostic
equirect resolver, `atmosphere_luts` owner) and the in-progress aerial
producer (`aerial_lut_driver.glsl`). Each item states the finding, the
resolution and what it supersedes. The body above keeps the original text;
bracketed pointers mark the superseded statements. "As built" notes record
where the implementation already differs from either text.

#### 21.1 Aerial parameterization and the equirect cloud merge

Finding. Section 10 inherited KSA's camera-frustum aerial. Section 14 lists
the camera-light generation as independent of camera orientation and 9.2
says rotation touches only the resolve; a frustum LUT rotates with the
camera and must rebuild per rotation, which is why KSA rebuilds it every
frame. Section 9.1 merges equirect clouds by the 11.2 equation, but the
equirect had no source of `(S_d, T_d)`: a frustum LUT does not cover the
sphere.

Resolution. The aerial XY domain is the sky-view angular mapping of 8.1 plus
the depth axis of section 10. It is then orientation-independent, one
builder serves both output domains, and the equirect merge has its
`(S_d, T_d)`. Bicubic XY / linear Z and the horizon clamp stand. XY
resolution is a measurement item: 96 columns of sky-view mapping are 3.75
degrees per column; raise XY before considering a frustum variant. The
uniform-source split `S_d ~= S_D * (1 - T_d) / (1 - T_D)` with `T_d` from the
transmittance LUT is the fallback for a backend without 3D image stores.

As built: implemented in `aerial_lut_driver.glsl` and
`sky_view_lut_lib.glsl`: 96x96 XY through `pa2SkyDirectionFromLut`, 96 depth
slices, per-direction range, and `z^2` inside the atmosphere. The consumer is
diagnostic-only until the production resolve route is complete.

#### 21.2 The aerosol phase leaves the LUTs

Finding. Section 8 folds `phaseM` into the stored radiance. KSA can, because
its Mie is Cornette-Shanks at g = 0.8, tens of degrees wide. PA2's OPAC phase
is a three-lobe Draine with a forward lobe at g 0.97-0.99 (`opac_phase_coef`),
about one degree wide, against 1.9 degree azimuth columns at 192 and 3.75 at
the aerial's 96. The sun and moon aureoles smear and fail the 1% daylight
gate; section 18 lists the aureole as a view case with no strategy.

Resolution. Along a straight ray the scattering angle is constant, so single
scattering factors:

```text
L_ss = phaseR(theta) * I_R + phaseM(theta) * I_M
I_x  = sum W * T_sun * shadow_smooth * beta_sx * rho_x      (phase-free)
```

Store per LUT texel the phase-free integrals `I_R`, `I_M` for the sun, the
same pair for the moon, and the isotropic term `L_ms + L_emission`. The
resolve evaluates the exact Rayleigh and OPAC phases per output pixel (the
moon with its own phase angle). The aureole is then exact at any LUT size and
the column count stops being an aureole constraint. `T_sun`, `shadow_smooth`
and Psi carry no view-phase dependence, so the factoring is exact for them.
Planes: the sky-view grows to three RGB planes (five with the moon), trivial
at 192x256; the aerial doubles, which the EV pre-scale of 21.6 absorbs. With
refraction the angle drifts along the bent path by at most the total bend;
use the angle of the apparent direction and record the residual error in the
last degree above the horizon as a known limit, not a station scheme.

Supersedes: the section 8 pseudo-code (phase inside the sum), the plane
counts in section 5, the aureole case in section 18.

As built: the shared integrator stores phase-free sun/moon Rayleigh and aerosol
terms; the exact PA2 Rayleigh/OPAC phase is applied at resolve. The aureole is
therefore no longer limited by LUT azimuth resolution. Production image gates
still need to validate the resolve route and the refraction residual.

#### 21.3 Refraction: the shared walk, no 1D table, two sky generations

Finding. The camera-height `ray_geometry` table of section 12 re-introduces
the altitude-keyed table that `docs/design-refraction-2026-09.md` (4.1)
retired for its flicker while flying ("the camera altitude is NOT an input
any more"). Section 9's "both output domains consume the same sky LUT"
contradicts the equirect-straight law (refraction design 4.5; changelog: the
equirect never refracts view rays).

Resolution. The sky-view and aerial producers run the shared walk
(`pa2RfPrepare` / `pa2RefrTrace` / `pa2RfAdvance` in
`atmosphere_refraction_lib.glsl`) per texel, exactly as the rect air pass
runs it per pixel today; 49k + 9k texels cost less than any rect pixel count.
The full-resolution BG/ground compose keeps its own per-pixel walk. With
refraction on, bake two sky-view generations, STRAIGHT (`PA2_REFRACTION` 0,
equirect) and WALKED (rect), and the same for the aerial when the rect's
aerial is walked. Shimmer stays out of the LUT, as section 12 says. The
`ray geometry` row of section 14 and the Phase 5 table are gone; Phase 5
becomes "walked generations + alignment tests". Mirage folds: their sharp
per-channel edges are B-plane content under the horizon-line law (the BG
pass writes verdict-matched S minus plain S into B, 2026-09-04); the LUT
holds the smooth part.

#### 21.4 Psi stays in the ambient atlas

Finding. Section 7 and Phase 1 promote the 64x64 Psi band to a dedicated
resource. Every Psi consumer (`pa2PsiMS4` in the sky march, `uPsiScratch` in
the ambient band builder, the cloud march) would move to a new sampler slot;
the transmittance-sampler leak cited in section 15 is that class of change.

Resolution. No promotion. Builders bind `uAmbientLUT` and read rows
[128, 192) as today. The owner's `psi_ms` entry is an alias to the published
atlas generation, not a copy. The Phase 1 bullet is dropped.

As built: correct. Both producers bind `uAmbientLUT`; the owner aliases the
scratch texture.

#### 21.5 Steps, one integrator, units, harness, gates

- Steps are free. 49,152 sky texels x 64 steps is 3.1 M iterations, under a
    tenth of one 2048x1024 x (8 + 8) bake. The producers use one fixed count
    (the NASA row) for every tier; the section 8 ladder is gone. Once the LUT
    path is production, `atmosphere_steps`, `atmosphere_ms_steps` and the
    fractional air resolution (`sky_air_resolution`) lose their arm and go,
    together with the parked aerial atlas (`_AERIAL_ATLAS_ENABLED`,
    `_ensure_aerial_atlas`, the ATLAS_S/T images): retire the knob and its
    losing arm together. As built: the sky and aerial producers use the shared
    `atmosphere_lut_integrator.glsl` with deterministic 64/96-step checkpoint
    schedules; no per-pixel property-count jitter is carried into the LUTs.

- One integrator. Section 8 asks for one clear-air integrator for both LUTs.
    The prototype now has both producers call
    `atmosphere_lut_integrator.glsl` (section 15), with matched transport terms
    and explicit 64/96-step checkpoint schedules. This removes the former
    `S_D`/`S_d` estimator mismatch; the remaining halo risk is in the not-yet-
    implemented cloud merge and production resolve.

- Units. All published radiance planes use one convention and are EV-scaled
    at store; the resolve unscales before composition. The sky-view radiance is
    RGBA32F and the aerial radiance/transmittance planes are RGBA16F.

- Harness (Phase 0). Report atmosphere GPU time apart from the Blender image
    publish: `foreach_set` of one 2048x1024 RGBA32F plane is tens of
    milliseconds and caps the apparent speedup. Measure the clouds-on share:
    the KSA cloud march (768-sample cap at Normal) dominates a cloudy bake, so
    the atmosphere share bounds what this project returns. As built:
    `scripts/probe_sky_view_lut.py` records statistics, errors and cache reuse
    but no timings; add medians with alternated variant order per Phase 0.

- Gates (section 18). The 2x threshold is stated on atmosphere GPU time. The
    twilight view cases gain the earth-shadow / Belt of Venus edge, the
    sharpest smooth-sky gradient and the test of the row count at the horizon.
    The aureole case is exact under 21.2.

- Lunar SS joins the first milestone (8.2, open decision 2): one extra
    transmittance tap and one Psi tap per step; `AUTO` would otherwise regress
    every night scene. As built: the shared integrator includes sun and moon
    single/multiple-scattering terms; the factory probe keeps the moon disabled,
    so a dedicated night matrix remains TODO.

- Airglow. The aerial excludes emission: the cut column already omits it
    because the 90-250 km layers sit behind every mesh. The sky-view includes
    it. As built: the sky-view adds direct airglow; the aerial intentionally
    excludes direct airglow because finite mesh/cloud ranges end below the
    emission shells.

- Scene-lamp air (`pa2LightsAir`, Scene Lights 2026-09-03) is per-pixel,
    additive and independent of the march. It stays in the resolve for both
    domains; it is not bakeable.

- Cloud shadows on air. Today the march shades every air sample through the
    cloud shadow volume; in LUT mode that exists only through the 11.5
    residuals, zero until Phase 6. Phase 4 therefore ships an interim mode
    without crepuscular rays. The Phase order (6 before 7) is the guard: `AUTO`
    does not become default before Phase 6.

#### 21.6 Precision, storage, generations

- Open decision 1 is answered by existing machinery: the scatter EV scale
    (`u_pa2.ozone2.z`, the World Output fp16 window placement) pre-scales at
    store and the resolve unscales, so the aerial planes are RGBA16F. The
    sky-view stays 32-bit; 1.3 MiB is irrelevant.

- Writable `FLOAT_3D` image stores are proven on Vulkan by the shadow volume
    (`sky_luts.py`: compute dispatch + `info.image(..., "FLOAT_3D", WRITE)`).
    The tiled-2D hedge of section 5 is dropped. A fragment fallback cannot keep
    the one-march/many-slices invariant without image stores either, so the
    fallback on a backend without them is `AUTO` -> reference march for finite
    depth, not a fragment aerial.

- Generations (section 14): three rows suffice. Static (optical + MS, keyed
    as today), per-bake (sky-view + aerial, rebuilt whenever the camera-light
    key changes, which in fly mode is every draw and is cheap), resolve. The
    ray-geometry row is gone (21.3); the cloud rows stand (section 11).

- Horizon line. The LUT-side clamp (8.1) handles the LUT tap. The published
    S plane still gets a bilinear world tap, which the horizon-line law already
    solves in B (BG pass, 2026-09-04). Do not re-solve it in the resolve.

#### 21.7 Cloud contract details (section 11)

- `f`, the conservative front distance, has a home: `cloud_T.a`, written as
    zero today and marked reserved in section 5.

- The 11.2 equation is verified identical to the live composite in
    `pa2ColumnComposite` (`L_cloud * T_cam_to_cloud + S_front * (1 - T_c) +
    S_full * T_c`, `T = T_air * T_c`) and exact: `T_c * (S_D - S_d)` is the
    attenuated behind-cloud air. The merge helper is a refactor of proven code.

- Open decision 7: `pa2CloudArm` composites the flat far deck behind the
    volumetrics and the single centroid follows the volumetric layer; a
    two-slice contract first needs the deck's own `d`. Note it when it shows.

#### 21.8 Process

- The Phase 2 go/no-go is judged on the equirect alone: the role law makes
    it lighting and reflections only, simple and fast, with no direct-view
    risk. The rect follows once 21.2 is in.

- Branch: `codex/ksa-lut-atmosphere-clouds`, off `celestials-rect` at
    `adb7553`.

#### 21.9 The KSA cloud pipeline, ported exactly (2026-09-05)

User direction: implement KSA's cloud rendering exactly (compositing,
sampling, upsampling), then deviate for PA2's own shading; the
analytic march stays as the reference sky. The port runs in stages,
each measured with `scripts/probe_lut_rect.py` against the jitter-free
64 + 256 march (sun 20 deg, 60 deg FOV, 1920x1080, clouds on).

**K1, compositing (RaymarchCloud.comp:377-442).** The cloud pass
composites each layer at its own weighted centroid: the aerial LUT
gives the eye-to-cloud transmittance and the in-scatter in front, the
transmittance LUT the sun transmittance at the centroid
(`march_cloud_segment_ksa` under `PA2_TRANSMITTANCE_LUT`), and the
layer leaves as the premultiplied `cloud * T_eye + inscatter *
(1 - T)` (`pa2CloudLayerAerial`). Layers blend front to back as
`prev + prev.T * cur`, the stored distance follows
`GetCloudDataInterpolationWeight` (`pa2CloudLayerWeight`). The air
pass is UpscaleCloud's last line, `main * T_cloud + cloudColor`: no
front tap, the history holds the composited colour. The cloud compute
build is keyed on the LUT option and binds the aerial samplers.
Clear sky unchanged (0.55% P95); the cloud pass 8.9 ms at full res.

**K2, godrays (Godrays.comp / Godrays.glsl, Atmosphere.comp:242-266,
RaymarchCloud.comp:399-430).** `godray_lib.glsl` marches the SHADOWED
single scattering with PA2's optics: what the LUT integrator gave a
sample (transmittance LUT, planet penumbra, eclipse) times the
fraction the LUT does not know is shadowed, `1 - casters * cloud`,
the cloud factor from the shadow volume (Beer, plus PA2's
delta-Eddington downflux behind `PA2_GODRAY_DOWNFLUX`), aerosol phase
damped 5% as KSA [damp removed 2026-09-05: PA2's planes are phase-free,
so it only leaked 5% of the aureole into object shadows; 23.1].
`godray_driver.glsl` is the low-res pass (half the
air dims, 50 uniform steps, dithered start) with KSA's flip/flop
history: the density-weighted sample distance reprojects through
the previous frustum (the cloud resolve's dual basis, push constants
grH0..3), the signed distance separates sky from terrain, the
terrain/sky disocclusion thresholds and velocity powers are KSA's.
The air pass subtracts the bilinear tap (`PA2_GODRAY_TAP`, slot 28);
the cloud pass marches its own 25 steps to the centroid
(`PA2_GODRAY_CLOUD_STEPS`). The pass runs per round and per draw
(`_godray_pass`, no compiles in the draw). Only single scattering is
occluded, on purpose (KSA): the LUT's multiple scattering keeps
lighting the shadowed air. The PA2 coupling of 11.5 is off
(`PA2_LUT_COUPLING_PA2 0`), kept as the own-shading option.

Measured, clouds on, vs the converged reference (P95 rel): sky
pixels 19.6%, opaque cloud 17.9%, clear air between clouds 24%
(the coupling had 18.5 / 18.5 / 15 at 65 ms); K1 alone, no godrays,
sat at 60 / 63 / 15. Centre-column cloud rows within 4%. Cost at
1920x1080 full-res cloud pass: cloud pass 13.2 ms (+4.3 for the 25
steps; 1/9 of that interleaved), godray pass 4.0 ms, air pass 17.5 ms
(7.5 of it the LUT resolve, the rest the ground cloud-shadow arm that
the march path pays too), resolve 3.5 ms: ~38 ms against the 8 + 8
march's ~70 and the reference's 182. The remaining error is the
multiple-scattering coupling KSA leaves out by design (the ground
row under an overcast deck reads 3x the reference's 0.009).

**K3, upsampling (UpscaleCloud.comp, UpscalingFunctions.glsl,
DilateMotionVectors.comp), landed.** The interleave is 3x3
(`_CLOUD_ILV` / `PA2_CLOUD_ILV`, a 9-cell spread order) with the
block-centre convention; the cloud pass writes KSA's motion vectors
itself (`GetMotionVectors` of the centroid through the history
frustum: the round UBO's clh1..3 rows carry that dual basis on
interleaved rounds, clh0.z flags it, clh0.w stays 0 so the round's sky
pass keeps its identity tap; a transparent march marks HALF_MIN); a
jump-flood dilation (`cloud_mv_dilate_lib.glsl`, three passes at
steps 1/2/4, the last with KSA's mid-layer fallback, depth parity by
the viewgeo map) runs over the low MV plane before the resolve, which
reads the dilated vectors instead of deriving them (the crH push
constants are gone). Deliberate deviation: the depth-aware
neighbourhood and the nearest-depth fallback exist because KSA clips
the cloud march at the terrain per low-res pixel; PA2's pair is never
clipped (the per-fragment coverage cut of the air pass owns
silhouettes, the 2026-09-03 law), so those branches have nothing to
protect and stay out. `probe_cloud_resolve.py` (headless: twins
bit-identical, MV plane carried, invalid vectors never win, the
dilation fills one step) is green; `probe_cloud_interleave.py`
(windowed, still camera, deterministic clouds, 14 interleaved rounds
against the full-res pair) measured 3x3 vs the committed 4x4: cloud
pixels 13.7% vs 19.2% P95 after 14 rounds, T 21% vs 35%; dilate 0.2
ms, resolve 1.1 vs 2.0 ms, the low pass 17 ms for 1/9 of the rays vs
13 for 1/16. FINDING: both drift from the full-res pair over rounds
(round 1 exact, then the neighbourhood clamp bites a little more each
round). That is KSA's design: the clamp is the content tracker for a
DITHERED march, and against a deterministic one it can only pull
history toward the coarse taps. The 3x3 halves it; the right metric
for the shipped (jittered) path is a converged average of many
full passes, a later probe. Also measured: the low pass costs 5-7x
more per ray than the full pass (sparser rays, colder noise caches),
and the tricubic shadow-volume tap made the 25-step godray march the
cloud pass's whole cost (full res 28 -> 102 ms), so the godray
marches now take KSA's trilinear fetch (`PA2_GODRAY_TRICUBIC 0`).

**Phase 5, the walked generations, landed (2026-09-05).** The sky-view
and aerial producers compile the refraction walk in (`PA2_REFRACTION`
1 in `_sky_view_toggles`, the runtime strength lane arms it, the dep
key carries `_refraction_key`) and march the BENT path per texel
(`lut_walk_lib.glsl`: `pa2RefrTrace` at the LUT origin with the
float64 altitude lane, `pa2RfAdvance` per sample, the fast branch's one
rotation, MISS / GROUND / EXIT / CAP as in the air pass), so the planes
stay keyed by the apparent direction and hold what that direction
sees; the aerial range becomes the path length and the consumer reads
the range plane for every ray while refraction is on. Sun paths take
the per-sample effective sphere (`pa2AtmosphereLutAdvanceSun`), the
sky-view's airglow rides the walk's exit pose, and the world shimmer
stays out of the LUT (`PA2_RF_NO_TURB`: no turbulence volume in the
producer builds). The refraction gate on the option is gone. Kept
straight, by design: the godray pass and the cloud pass's centroid
march (the KSA cloud march never walked), and the phase at the
consumer, which rides the apparent direction (the aureole shifts by the
ray's bend at the horizon; mirage folds are B-plane content under the
horizon-line law, 21.3). The equirect keeps no LUT consumer, so the
second (straight) generation of 21.3 is not needed yet. Measured
(`PA2_PROBE_REFRACTION=1`, sun 20 deg, the march walking its own bent
path as the reference): clear sky 2.9% P95 (the LUT 1-3% brighter,
more in blue; the aureole-side phase at the apparent direction and the
planet-sphere ground bounce are the suspects), transmittance 0.8%,
clouds on 19%; refraction off stays at 0.5% / 18%. The march itself
costs 69 ms clear and 198 ms with clouds while walking, the LUT path
is unchanged.

**K4, sampling, landed.** (a) `FindCloudLayerIntersections`: the arm
intersects the band's inner sphere (`LAYER_BASE_H`, the lowest enabled
layer base; the planet while the rain layer carries mass, since the
shafts hang under the band) and marches the one or two shell segments
as KSA layers, front then back: the front's transmittance drives the
back's in-march early exit (`g_pa2KsaPrevT`, RaymarchCloud.comp:202)
and the KSA layer blend with the optical-weight distance; each
segment gets its own aerial composite. Rays under the band no longer
march the gap. (b) `GetMipLevels`, analytic instead of
finite-differenced (compute has no derivatives; KSA's groupshared
trick is exactly the per-pixel footprint): mip = log2(0.25 · distance
· pixel angle · volume texels per noise repeat), the tap's own repeat
added per shape / detail tap (`PA2_KSA_LOD`), mapped onto PA2's
fine / 4x-pooled volume pair as LOD = mip / 2. The pixel angle is the
consuming pass's own (`g_pa2LodPixelAngle`: the rect's display pixel,
the equirect's column; the volume bakes keep the old 10-60 km ramp).
(c) The temporal noise slices and the golden-ratio light dither were
already PA2's blue-noise equivalents. Rect LUT parity unchanged (sky
17.9%, opaque cloud 16.0% P95; the reference march shares the
sampling). FINDING: KSA's mip bias keeps far clouds four texels per
pixel finer than PA2's ramp did (fine detail to ~70 km instead of
coarse from 10 km), and the still-camera drift of the deterministic
interleave grew with it (20% / T 53% P95 after 14 rounds vs 14% /
21%): sub-pixel detail is what the neighbourhood clamp cannot hold.
KSA pairs that detail with a dithered march and the reduceFlickering
relax; the shipped path (jitter on) is the one to judge, visually.

### 22. Source anchors {#lut-atmosphere-22-source-anchors}

KSA reference tree:

- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/AtmosphereLuts.glsl`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/AtmosphereFunctions.glsl`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/TransmittanceLut.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/MultipleScatteringLut.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/SkyLut.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/AerialPerspectiveLut.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/Atmosphere.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Atmosphere/Godrays.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Clouds/RaymarchCloud.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Clouds/Upscaling/UpscaleCloud.comp`
- `D:/Dropbox/Projects/PSA2/source_shaders/ksa/Core/Shaders/Clouds/ShadowVolume/ShadowVolume.comp`

PA2 baselines:

- `shaders/atmosphere_15/atmosphere_cloud_march_lib.glsl`
- `shaders/passes/sky_driver.glsl`
- `core/sky_luts.py`
- `core/sky_bake.py`
- `core/sky_rect.py`
- `docs/design-cloud-temporal-upscale.md`
- `docs/research-ksa-cloud-teardown-2026-08.md`
- `docs/research-temporal-upscaling-2026-07.md`

### 23. Implementation ledger (2026-09-05) {#lut-atmosphere-23-implementation-ledger}

This section is the current execution record for the branch. It supersedes
older phase wording where it conflicts with the prototype state above.

#### Done

- Created branch `codex/ksa-lut-atmosphere-clouds` and landed the prototype in
    commits `5aef8c8`, `820e409`, and `fce7d69`.

- Added staged/last-good `atmosphere_luts` ownership and cache-safe generation
    handling. The transmittance LUT is 256x64; the diagnostic sky-view LUT is
    192x256.

- Added a progressive 96x96x96 aerial LUT. One XY invocation walks one ray and
    writes all depth slices, with per-direction range, horizon handling, and
    bicubic XY / linear-Z sampling.

- Unified sky-view and aerial transport in
    `shaders/passes/atmosphere_lut_integrator.glsl`. LUTs store phase-free sun
    and moon Rayleigh/aerosol terms plus isotropic/multiple-scattering and
    transmittance; the resolve applies the exact PA2 OPAC/Rayleigh phase.

- Preserved PA2 optical behavior, including lunar/night terms and the existing
    airglow policy: direct airglow is in sky-view, intentionally omitted from the
    finite-depth aerial volume.

- Added the `atmosphere_aerial_lut` opt-in property/panel control and diagnostic
    equirect sky/aerial resolvers. The production rectangle/equirect paths still
    default to the reference march.

- Verified Blender 5.2 Vulkan support for writable `FLOAT_3D` images and ran
    the existing suite: 81 tests passed.

- Takeover 2026-09-05 (Claude): the shared integrator gained the planet
    penumbra on the sun path and the reference's ground-bounce arm (direct sun
    plus the measured sky bands, light pollution as ground emission; aerosol
    weight `exp(-h/Ha)` as in the reference), plus probe-only
    `PA2_LUT_DEBUG_NO_BOUNCE` / `PA2_LUT_SKY_STEPS` defines; the sky-view key
    carries the bounce scale; three probes added (parity + timing, term
    isolation, MS-step trend). Suite 81/81.

- Phase 4 rect (2026-09-05, Claude): `atmosphere_lut_rect` ("LUT
    Atmosphere (Rect)", Scientific > Atmosphere). The rect AIR build
    compiles `PA2_ATMOSPHERE_LUT_RECT` and declares the seven aerial
    samplers on the celestial slots it never uses (15-20, 27); the column
    composite in `sky_driver.glsl` resolves `S_D, T_D` to the segment end
    and `S_d, T_d` to the cloud front from the aerial (the 11.2 equation,
    lamp air added per pixel) and returns before the march when runtime
    bit5 (`PA2_RT_ATMO_LUT`) is set. The round march arms the bit after
    ensuring the chain at the round origin (compiles allowed); the per-draw
    air pass ensures with `allow_compile=False` and falls back to the march
    for a cold producer. The bake warms the producers when the option is
    on. `pa2AtmosphereLutCompose` moved into `sky_view_lut_lib.glsl` so a
    consumer needs no integrator. Only the aerial is consumed by the rect:
    its last slice IS the full column, so sky, geometry and cloud-front
    taps come from one source and cannot seam (the sky-view LUT stays for
    the equirect). Refraction: the LUT is read on the straight ray with
    the walk's segment end (Phase 5 bakes walked generations).

- Fast Lighting Sky (user request 2026-09-05): `sky_lighting_fast` drops
    the scene lamps (lt_cfg.x = 0) and the 3D object shadows
    (cs_center.w = 0) from every equirect gather, renders included, through
    a "fast" lighting tier.

- Fixed on the way: the per-draw air pass gate compared a 2-tuple
    against the 3-tuple compute cache key (formats joined it 2026-08-21)
    and bailed to the warp on every draw; one key builder serves both now.
    The runtime bitfield readers isolate their bit (`PA2_RT_NO_GROUND` read
    every bit above 4, the caster jitter test every bit above 0).

- Commit trail after the rect option (2026-09-05): 841cc67 coupling
    ratios (kept off); 466274b K1 + K2; 1782ccf K3; 0381b1a K4, the F12
    pair, the night scale, DEFAULT ON; c060098 per-sample LUT arm in
    renders, the sky-view atlas tap; 86d9c45 twilight verdict; 11792e8
    Phase 5 walked generations; 5176cab atlas pack offset, exact sky-ray
    test, Phase 0 toggles retired; 856ec40 the cut guard, the Reflections
    category, Reflection Probe / Reflect Clouds, the Atmosphere Resolution
    ladder, the godray damp removal, the space-limb scale, the air warp
    switch (off); 6b9ef4a / e5186e2 the space verification and its to-do.

#### Findings

- The Vulkan LUT probe passed with finite outputs, zero aerial transmittance
    depth delta, and a zenith transmittance error of 0.001953125 versus the
    exact transmittance LUT.

- Shared sky/aerial transport is numerically aligned: resolved-scatter P95
    relative error is 0.0021126 (0.21%), and resolved-transmittance MAE is
    0.0004902 (max 0.001648) on the parity probe. Cache reuse and generation
    stability also pass.

- Estimator verdict (2026-09-05, `scripts/probe_lut_ms_trend.py`, sun 20
    degrees, 2048x1024, scene lights off): the production march converges
    ONTO the LUT as its MS step count rises past the property ceiling. Sky-wide
    P95 relative error of the LUT resolve against the reference at 64 view
    steps and 8 / 16 / 32 / 64 / 128 / 256 MS steps: 45% / 24% / 11% / 4.1% /
    1.0% / 0.40%; zenith radiance at 256 MS steps [1.4949 2.2106 4.1168]
    against the LUT's [1.4955 2.2106 4.1188]. The LUT itself is converged (64
    vs 256 steps: 0.09% P95). Single scattering alone agrees to 0.42% P95 at
    any MS count; the whole gap was the reference's MS quadrature
    under-resolving the aerosol layer on steep rays. Consequence for
    production: the Normal tier (8 + 8) is 45% dark at the zenith and 6% high
    in blue transmittance against PA2's own converged model; even the NASA row
    (64 + 32) is 11% off. The acceptance target is the converged reference
    (256 MS steps) or the LUT itself, not the property defaults.

- Phase-free storage removes the OPAC aureole from the LUT-resolution
    constraint. Exact per-output phase is now independent of the 192/96 angular
    column count, subject to the documented refraction-angle residual.

- Timing (2026-09-05, `scripts/probe_lut_parity.py`, RTX 4080, Blender 5.2
    LTS Vulkan, fenced warm medians, Normal 2048x1024, clouds off): march draw
    5 to 11 ms at 8 + 8 and 13 to 18 ms at 64 + 32; readback of the four
    planes 21 ms; Blender image pixel upload 53 to 57 ms; whole equirect bake
    82 to 97 ms. LUT chain (transmittance + sky-view + aerial, forced rebuild)
    2.5 to 2.9 ms, of which about 0.7 ms per pass is the Python/driver floor;
    sky-view resolve 0.8 to 1.0 ms and aerial resolve 0.9 to 1.0 ms at
    2048x1024. Verdict on the section 18 gate: on atmosphere GPU time the LUT
    is 2 to 4x faster than the 8 + 8 march and 5 to 6x faster than the 64 + 32
    march it actually matches; on bake wall time it moves 90 ms to about 85,
    because readback plus pixel upload is 75 ms of the bake. The equirect
    publish path, not the atmosphere, bounds the lighting sky.

- Night: the factory scene's default point lamp lights the air through
    Scene Lights (about 7e-5 at the zenith, flat, blue); it is per-pixel
    resolve content and must leave the parity scene. With it removed and the
    moon at 40 degrees the LUT matches the 64 + 32 reference to 1% at the
    horizon and is brighter only by the same MS deficit at the zenith.

- Dusk (sun -4 degrees): LUT vs the 64 + 32 reference 6% P95, the same MS
    deficit; the horizon band agrees within 2%.

- Rect (2026-09-05, `scripts/probe_lut_rect.py`, 1920x1080 air planes, 60
    degree FOV 10 degrees up, sun 20 degrees, scene lights off): clear sky,
    the LUT resolve vs a jitter-free rect march at 64 view steps with the
    MS lane forced to 256: scatter 0.62% P95 on sky pixels (transmittance
    MAE 6e-4), while the production 8 + 8 jittered march is 46% off the
    same reference. Air pass (compute publish, fenced medians): 11.3 ms at
    8 + 8, 56 ms at 64 + 256, 1.8 ms with the LUT. With clouds: 14.4 / 181
    / 4.9 ms; transmittance matches, radiance under decks does not (79%
    P95): the reference march shadows and feeds the AIR through the cloud
    field per sample (bit2 cloud shadows, the MS cloud mix and downflux),
    none of which is in the clear-air LUT. That coupling is the section
    11.5 residual work; until then LUT mode renders cloudy skies with
    clear air between the clouds and no godrays. The remaining 5 ms with
    clouds is the ground shadow walk and the cloud ambient lanes, not
    atmosphere.

- Fast Lighting Sky measured on a one-lamp scene: equirect march 28.0 ->
    26.1 ms; the option pays off with many lamps or a dense caster set.

- Cloud-to-air coupling, first cut (2026-09-05,
    `atmosphere_lut_residual_lib.glsl`): a difference march (coupled minus
    clear source) over-subtracted, because it paired an 8-sample estimate
    of the clear source with the LUT's converged one and the coarse
    cloud-front snapshot landed on one bin. The RATIO form fixed it: the
    march estimates coupled / clear of the single-scatter and of the
    isotropic source from the same samples (quadrature bias cancels, a
    clear sky is exact by construction), split at the cloud front, bounded
    at the ray's exit from the cloud layer sphere with the tail above taken
    straight from the LUT (`pa2SampleAerialPerspectiveParts` returns the
    single-scatter and isotropic parts apart). It reproduces the reference
    march's coupling terms exactly: sun-column Beer + delta-Eddington
    downflux on SS, the zenith column's AO / mix / field AO on the Psi MS,
    the ground bounce under the deck, and the scene casters. Rect, clouds
    on, deterministic cloud pair, vs the jitter-free 64 + 256 march: sky
    pixels 79% P95 without coupling -> 18% with 8 samples; clear air
    between clouds 26% -> 15% (8) -> 11% (16) -> 8% (32); opaque cloud
    pixels 69% -> 18%, centre-column cloud rows within 1%. Cost is the
    verdict: 8 samples make the LUT air pass 50 to 65 ms with clouds against
    the march's 45, because the coupling's per-sample work (shadow-volume
    tap, coarse zenith walk, two transmittance taps, Psi and band taps) IS
    the expensive part of the march. Kept behind `PA2_LUT_COUPLING_PA2`
    (interim 1 until the KSA godray pass lands, then 0) as the future
    own-shading option; the shipping path is KSA's.

#### TODO / next gates (rewritten at the 2026-09-05 review)

Landed since the original list (details in Done, 21.9 and 23.1): the rect
default, the fragment / F12 pair, the night radiance scale, the sky-view
atlas tap, K1 to K4, Phase 5, the atlas pack and sky-ray fixes, the Phase
0 toggle retirement, the godray damp removal, the space-limb scale fix,
the compile guard, the Reflections category with Reflection Probe /
Reflect Clouds, the air warp switch (off by default).

Open, in priority order:

1. Equirect production resolve (section 9.1): DONE later the same day
   (LUT Lighting Sky). Remaining there: the equirect variant still
   carries the fallback march (item 3), and the inline cloud arm is the
   whole bake with clouds (about 20 ms at 1024x512).

2. Space views: CLOSED (2026-09-05, evening). Against a converged
   analytic reference (256 view + 256 MS steps) the aerial planes read
   the limb haze to 1.5% half a degree under the limb at 600 km and
   within 4% down the profile; the "over-read" was the 16-step tier
   reference missing the boundary layer on grazing paths. No LUT change
   was needed; the lesson is in KNOWN_ISSUES.

3. Compile cost of the rect pair (23.1): DONE for the fallback march
   (2026-09-05, evening): LUT builds compile the analytic column march
   out (`pa2ColumnComposite` is LUT-only under `PA2_ATMOSPHERE_LUT_RECT`,
   the cloud arm composites KSA-style unconditionally) and a pass the
   chain cannot serve is skipped by its caller (round, per-draw air,
   render sample, probe bake). Cold builds, EEVEE-contended: rect air
   compute 17.6 -> 5.1 s, fragment twin 17.3 -> 5.0 s; parity unchanged.
   Still open in the same item: the cut still runs the LUT resolve twice
   (a single-instance cut would halve what is left), and the equirect
   variant stays at 17 s because its bulk is the inline cloud arm (1.5 s
   with Reflect Clouds off).

9. Refraction and the LUT lighting sky: RESOLVED (user 2026-09-05,
   "the equirect does not need atmosphere refraction"): the probe reads
   a second, STRAIGHT generation of the chain (owner slots
   `sky_view_straight` / `aerial_straight`, the refraction lane zeroed,
   keyed on a constant; design 21.3), baked only while refraction is on
   and shared with the rect otherwise. Verified: refraction on, the rect
   at 2.05% P95 against the walking reference, the probe at 0.47% against
   the converged straight one, both generations resident (about 50 MB
   more while refraction is on).

4. Clouds against the reference (18 to 20%): KSA's design leaves the
   multiple-scattering coupling out. PA2's own coupling
   (`PA2_LUT_COUPLING_PA2`, 21.9) reproduces it at the march's price; a
   cheaper form (a ratio from the godray march's own samples) is the
   own-shading follow-up.

5. Interleave drift: judge the shipped (jittered) 3x3 path against a
   converged average of many full passes; the deterministic comparison
   only shows the clamp pulling history toward the coarse taps (21.9 K3).

6. Acceptance breadth: DirectX / Metal / integrated GPUs, the
   warm-resource budget, 4K resolve scaling, 48 / 64 aerial depth tiers,
   a night matrix (moon phases, light pollution).

7. Keys: the sky-view generation carries the ground-bounce scale and the
   refraction key; the albedo colour (`cl_galb`) and the starlight gain
   lanes are still not keyed.

8. Object-compositing probe: the scripted viewport composite carried no
   cut haze on the object in `probe_viewgeo_aureole.py` (the user's
   viewport does); the probe's compositor setup is unchecked.

- LUT Lighting Sky (2026-09-05, evening): the equirect resolves the LUT
    chain (section 9.1 note). Finding: the shipped simplified lighting sky
    was 2.3x dark at the zenith against the converged model, so every
    scene's world lighting brightens under the LUT probe; against the
    converged 64 + 256 equirect the LUT reads 0.47% P95.

- Fallback march removed from the LUT builds (2026-09-05, evening; item
    3 of the to-do): rect air compute 5.1 s and fragment 5.0 s cold
    (contended), from 17 s each; rect clear-sky parity 0.50% P95 and the
    equirect 0.47% unchanged; a LUT pass without a generation is skipped
    (the pair keeps its planes, the probe its last bake) instead of
    marching.

- Straight probe generation under refraction (2026-09-05, evening):
    see to-do item 9; the equirect never bends.

- Cycles viewport (2026-09-05, night; user: "PA2 does not really work on
    Cycles — the Updating Lights loop, and the rect is wrong"): the rect's
    CPU-publish arm had failed on EVERY watcher tick since the R3 buffer
    split — the legacy 5-plane with_b march produced B at the air dims
    (1920x1024) and foreach_set it into the display-sized background image
    (3840x2071): a size TypeError, swallowed by the fovea-tick handler with
    no print. Measured (scripts/probe_cycles_viewport.py, OptiX, 40 s):
    189 failures in 30 s; no rect ever published (a fresh Cycles session
    drew black sky — v18 camera rays never see the equirect), rectCam never
    written (an EEVEE-then-Cycles session kept the EEVEE basis: the rect as
    a flat quad in the old view direction), and the four air planes were
    foreach_set + tagged before the failure ~6x/s — every tag bumps the
    image's depsgraph update count, Cycles re-adds the texture, the world
    shader re-syncs and the light manager rebuilds its importance map:
    "Updating Lights" without end. Fix: with_b is False on every path; the
    Cycles viewport publishes like F12 (LUT air pair at air dims + the BG
    pass at display dims, film-multisampled by Render Samples). After: rect
    live from the first tick, publish 0.33-0.38 s (16 samples at 3840x2071),
    the depsgraph silent in a still view for 20 s, ONE publish (earth +
    world + 5 image tags) within a second of a 35-degree yaw, then silent
    again. The tick handler now prints a failure once per distinct message.
    Blender facts that bound the Cycles path (source, 2026-09-05):
    Cycles samples Image datablocks through BlenderImageLoader =
    BKE_image_acquire_ibuf, the CPU ImBuf only (never our GPU textures);
    the loader's equals() compares the image's runtime update_count, which
    graph_id_tag_update bumps on ANY tag of an Image ID — so pixels alone
    are invisible and every update_tag is a re-upload; the world shader
    re-syncs on a World/Scene/Camera recalc (image tags reach it through
    the image -> nodetree -> world relation), and its VIEW_LAYER Attribute
    nodes (rectOn / rectCam0..2 via the objects[...] RNA path) are
    CONSTANT-FOLDED at that sync — an object tag alone never refreshes
    them, the image tags of the same publish do; the world MIS map is
    1024x512 by default (Environment Texture nodes size it, our Image
    Texture nodes do not). Blender's own Sky Texture: Cycles bakes a
    512x128 (Nishita) texture on the CPU into an ImageManager slot
    (SkyLoader, re-added when node inputs change) and samples it in SVM by
    direction; EEVEE precomputes the same pixels per material compile and
    binds them as a material-owned texture (GPU_image_sky, linear /
    repeat-x / extend-y). Nothing of that is reachable from Python except
    what PA2 already does: Image datablocks + update_tag. The with_b
    build went the same night (next bullet). Left over: a Cycles view
    move shows the stale rect (directionally registered) with v18 black
    outside it
    for up to the 1 Hz publish gap — a Cycles-only equirect fallback for
    camera rays is the candidate if that reads badly in the field.

- with_b build removed (2026-09-05, night; user: "remove the with_b
    build then"): the 5th render target, the E3 celestial splice
    (`_CEL_COMPOSE` / `_CEL_ANCHOR`), the star/moon sampler set
    (`_SAMPLERS_RECT`), the compute publish's 5-target branch, the CPU
    ground fold of the legacy publish and the `with_b` parameters of both
    shader builders. Every rect build is 4-MRT air-only; the compiled key
    is `(shader_key, split, lut)`. The compute prelude no longer declares
    FragBackground and the main template lost its store placeholder.
    Verified: suite green, probe_refraction's rect builds compile,
    probe_cycles_viewport unchanged (publish, quiet still view, one
    publish per move), probe_dirty_images (EEVEE viewport, F12, save).

- Cloud pass census (2026-09-05, night; user: "make the clouds pass
    faster, taking KSA as a reference"; `scripts/probe_cloud_perf.py`,
    1920x1080, sun 20 deg, 61% cloud pixels, Normal, fenced medians):
    full-res cloud pass 52 ms; the four light samples 38 ms of it (4 -> 2
    samples 33 ms, 4 -> 1 24 ms: each sample is a whole weather + media
    evaluation, exactly KSA's GetDensityToLight); the in-pass 25-step
    godray march 11 ms; half the view steps (140 m + 0.012/m) 23 ms; the
    shape volume size (64 vs 32) nothing. The interleaved low pass is
    5.1 ms for 1/9 of the rays — the per-ray efficiency is back (the 5-7x
    of K3 was the tricubic tap). And the SHADOW VOLUME rolled a slice
    band every round whatever the scene did: 6.7 ms of a 17 ms
    interleaved round, 11-13 of a 70 ms full-res one — KSA rolls because
    everything in KSA animates. Landed: the roll is gated on a signature
    (cloud clock, sun at ~0.3 deg, origin at 500 m inside its 5 km cell)
    compared at cycle boundaries; a still scene rolls nothing, a moving
    one rolls as before and settles within two cycles; the clock left the
    warm-bake key (animated clouds re-baked the whole volume every round);
    the published frame rows follow the content instead of the live
    camera. After: interleaved round 17.2 -> 10.0 ms, full-res 70 -> 43,
    shadow volume baked in 0 of 6 still rounds, 6 of 6 under a stepping
    sun, 9 of 10 after it stops (the cycle it interrupted plus one).
    Tried and REVERTED, both measured slower on the RTX 4080 (register
    pressure in a kernel this size beats the taps saved): a weather cache
    reusing the anti-tiled tap within a quarter texel (exact, rel95 0.000,
    yet 37.6 -> 48.5 ms) and lite light samples (coarse volume, no
    turbulence, expected detail: 55 ms, and L rel95 0.59 — a look change).
    Also measured and left: 12 instead of 25 godray steps in interleaved
    rounds saves 0.45 ms of a 10 ms round for a 3-point P95 cost.
    FINDING: the Clouds quality ladder (`_QUALITY_CLOUDS`: cap, min/max
    step, growth) feeds only the retired house march — the KSA lanes
    (`ksa_step_initial` 70 m, `ksa_step_factor` 0.006, 4 light samples)
    ignore it, so Potato..NASA change the cloud march cost by nothing but
    the shape volume size; wiring the ladder to the KSA lanes is the next
    cost lever (half the steps = 2.2x), and the light-sample count is a
    look parameter (Jensen: fewer samples read brighter), not a free one.
    Structural KSA gap left: its density is ~5 taps of light ALU per
    sample, PA2's ~10-15 taps with the anti-tiling, skew and chart math —
    the per-evaluation ALU is where the remaining factor lives.
    Ladder wired (same night, user): `_QUALITY_CLOUDS` carries the KSA
    base step + growth (Potato 280/0.024, Low 140/0.012, Normal 70/0.006
    unchanged, High 50/0.0042, NASA 35/0.003), matched for the Custom
    readout like the legacy columns; the six KSA lanes joined
    `_CLOUD_KEY_SUNPROPS` so a manual edit re-marches at once.

- Ground check (2026-09-05, night; user: "check the ground shader since
    the atmosphere lut changes"; `probe_lut_rect.py` grew ground-row
    metrics for S, T, SHADOW, INDIRECT and the composed B, and a march8
    comparison): the LUT's own ground inputs are right — T at the ground
    0.05% P95, S 2.2% clear (absolute 1e-4), SHADOW bit-identical (the
    ground sun-transmittance and cloud-column arm carries no LUT
    conditional). The composed ground read 11% dark clear and 28% under
    clouds — but the production 8+8 march read exactly the same, through
    INDIRECT: the ambient bands atlas re-baked at the viewport's
    `atmosphere_steps` (its dep key carried the knob), and at the Normal
    tier's 8 view steps the bands came out 21-28% dark against the 64-step
    bake (ref [3.19 4.17 6.45] vs [2.51 3.16 4.67]) — the same 52%-P95
    under-convergence the 8-step sky has, inherited by every ground pixel
    while the LUT sky itself is converged. Fix: `_ensure_ambient_lut`
    bakes at fixed 64 view + 32 MS steps (the reference bake of the parity
    probes) whatever the tier, and the knob left its dep key. After:
    INDIRECT identical across march8 / LUT / reference, B[ground] 0.05%
    P95 clear and cloudy; and the sky parity moved with it — clear 0.50% ->
    0.37%, clouds 14.7% -> 8.8% P95 — the sky-view producer's ground
    bounce and the cloud ambient read the bands too.

- 1:1 cloud composite (2026-09-05, night; user: "what if I want 1.0x
    upscaled clouds on top of 0.5x atmosphere?"): the pair marches at
    display res, but the air pass composites it into S/T at the AIR res,
    so the world showed clouds at the composite's resolution. The 1:1
    background compose — the stage that already hands the world a per-
    pixel correction over its plain bilinear S tap (the horizon verdict)
    — now carries the cloud edge too (`gcAir1x`, ground_compose.frag):
    from the four air texels under the footprint it recovers the clear
    air the pass folded (S_i = L_i + Sair_i Tc_i, the pair tapped where
    the pass tapped it, reprojected through the same clh rows on air
    draws) as one verdict-weighted quotient, rebuilds the composite with
    THIS pixel's cloud, and B carries (that - plain); T for ground and
    celestials takes the same recovery; an opaque or cloud-free footprint
    keeps the plain gather. Viewport only (renders keep the multisampled
    air-res composite: the pair is one sample, the planes the sum);
    knobs.z flags it, slots 24/25 carry the pair. `probe_cloud_1x.py`
    (1920x1080, 0.5x air, 60% cloud, world-equivalent S + 64 B against
    the same round at 1.0x air): cloud edges rel95 0.53 -> 0.012, cloud
    pixels 0.34 -> 0.20, clear sky next to clouds 0.17 -> 0.07; compose
    0.5 -> 0.6-0.9 ms. Probe lessons: outside the tick the BG compute
    twin must be pre-warmed or the compose bails silently (B blank, every
    config identical); and the FIRST configuration of a run is the
    fastest — a 20 ms "cloud pass slowdown" that tracked the pair binding
    across three runs vanished when the configurations were reordered.

- Ground atmosphere reflection from the LUT (2026-09-05, night; user):
    `gcSkyReflect` marched the reflected sky 6 steps x 3 directions per
    ground pixel (coarse HG phase, Chapman airmass, the Psi MS band). Now
    a SURFACE generation of the sky-view LUT (`\_ensure_sky_view_lut(...,
    surface=True)`: the chart at the ground point under the camera,
    straight, keyed on a 1 km ground track + the sun) publishes one
    composed plane (`sky_view_compose_driver.glsl`: every texel composed
    with the exact phase for its direction) that the compose taps once
    per ground pixel through a twin of the lib's chart at viewHeight = R
    (slot 26, knobs3.x = the generation's scale; 0 = the march). Exact for
    every ground point at any camera altitude — a camera-altitude atlas
    is the wrong sky for a ground point 10 km below it. Viewport and
    renders. `probe_surface_reflect.py` (reflections on, 15 deg down
    toward the sun): composed B within 5.5% P95 of the analytic march,
    means 2% darker, compose 3.2 -> 3.0 ms; the composed plane finite,
    the aureole at its max. (Found and fixed on the way: sky_luts never
    imported `time`, so its atlas-pack failure print raised.)

- **Horizon line at coarse air scales — the film paired past
    corrections with today's plane** (2026-09-05, user screenshot at
    0.25x Atmosphere Resolution: a dark line under the horizon). The
    law of 2026-09-04 stands (B carries verdict-gathered S minus plain
    S, the world's bilinear tap cannot know the boundary), but the BG
    film averaged that correction across rounds, and at 4-px air texels
    the jittered march flips a boundary texel between sky and ground
    round to round: a round where the last ground texel came out SKY
    wrote a −3..−5 correction into every ground pixel under it, and the
    film kept feeding it to rounds where the texel was ground again.
    Measured (`probe_air_scale_artifacts.py`, world-equivalent
    S_bilinear + 64B across the horizon, 0.25x): rows 1094-1097 at 1.15,
    0.74, 0.32, −0.09 against a 1.3 ground, then 1.13, 3.13, 5.18, 5.76,
    6.15 (overshoot) above. Diagnostic lanes in the compose
    (PA2_BG_LANE comp / free / gnd: the current correction alone, the
    correction-free film mean, the film-averaged ground-verdict
    fraction) showed the second half: at the horizon row the film's
    ground fraction was 0.69 but the correction was applied with the
    LAST round's single verdict (world 0.95 in a 1.3 row; the sky
    verdict's would have read 6.3). Fix, `ground_compose.frag` film
    tail: the history holds the correction-free mean plus the ground
    fraction (packed as count + fraction/2 in the RGBA32F alpha), and
    the output adds `mix(compSky, compGnd, fG)` with BOTH corrections
    evaluated against the CURRENT plane (the other verdict's gather runs
    only where 0 < fG < 1, a pixel within the jitter of the 1:1
    horizon). Result: 1.0x 1.46 → 4.08 → 5.52, 0.5x 1.37 → 4.09 → 5.52,
    0.25x 1.32 → 2.63 → 4.05 → 5.51 — a monotonic antialiased step,
    no dip, no overshoot.

- **Object cut halo at coarse air scales — inpaint per side (graph
    v27)** (2026-09-05, same screenshot: a gap around the cube). The
    composited image is not capturable in a scripted session under
    Vulkan (screenshot, a POST_PIXEL framebuffer read, an offscreen
    draw_view3d, render.opengl and an F12 with compositing all came
    back black: the EEVEE beauty is black by design in compositor mode
    and the composite lives only in the viewport compositor), so the
    hybrid cut was TWINNED in numpy over the live planes with the
    cube's silhouette from its projected hull (RGBToBW luminance, the
    square Dilate/Erode window, the band gate, per row through the cube
    centre / a sky row 300 px up / a ground row 300 px down). Facts:
    the air pass stores a COVERAGE MIX of the cut and full columns per
    texel (`pa2ColOut = mix(col, colCut, pa2GeoCov)`), so no verdict
    gather can un-mix a straddling texel; the shipped ±2 px min/max
    recovery reads −46% at the silhouette on a sky row at 0.25x (−36%
    at 0.5x, −25% at 1.0x in the 1-px AA band), fading over ~8 px: the
    gap. Scaling the window by the air fraction (v26, built and
    measured the same day, never shipped) closes the sky-row gap (−1%)
    but the MAX of S across the horizon rows is the sky glow, 27x the
    ground's: +554% around an object 6 px under the horizon. v27 fills
    each side by INPAINT from its own clean pixels instead: zone =
    fractional EEVEE alpha dilated by 2 display px per air texel,
    `SetAlpha(plane, valid_side)` → `Inpaint(zone + 2)`, valid_sky =
    outside the zone and alpha < 0.5, valid_obj = outside and alpha ≥
    0.5; the band mix keeps the plane outside the zone. Twin: sky row
    −1..−4% (the row's own gradient; 5.4% max), horizon row 6.5% (the
    pre-v27 figure was 8%), identical at 1.0x. `refresh_values()`
    pushes the zone radius and the three fill distances from the S / B
    image size ratio (sig-guarded). Real-viewport verdict pending the
    user (no capture route).

- **The probe's own cloud pass** (2026-09-05, user: "give the probe
    its own cloud pass, as the rect has"). The equirect pair mirrors the
    rect pair over the equirect driver: `_eq_split_wanted` (split iff
    the build carries USE_CLOUDS; `_EQ_SPLIT_FORCE` for probes),
    `_draft_cloud_compute_shader_cached` (PA2_CLOUD_PASS compute twin),
    `_draft_compute_shader_cached` → from_tex (its cache carries the
    split flag), `bake_now` builds the fragment pair
    (`_STATE["eq_cloud_shader"]`), and `_eq_cloud_pass` runs the pass
    into a cached RGBA16F triple at probe dims ahead of every sky pass
    (`_draft_direct` compute / fragment / reduced-draft branches,
    `_accum_pass_gpu` both branches, `_render_mrt(pre=)` for the
    synchronous readback path), appending (uCloudL, uCloudT) to the sky
    pass's extras; the tap is identity (clh0.w = 0 in every probe UBO).
    The aerial-LUT extras bind on the cloud pass too (a LUT build
    composites each layer at its centroid). `probe_equirect_cloud_pass.
    py` (1024x512, clouds, sun 20°, LUT on): parity S rel95 0.05% / T
    0.07% / INDIRECT + SHADOW identical; forced bakes 40.2 / 43.0 / 40.8
    ms split vs 40.2 / 39.1 / 39.5 inline; cold compiles (salted
    source, inline first): inline frag 4.64 + compute 4.67 s = 9.3 s,
    split from_tex 1.33 + pass 2.55 (frag) + 1.35 + 2.57 (compute) =
    7.8 s. No runtime change; the sky program is the clear-sky build.
    Probe trap recorded: a bake right after a cold compile stall lands
    in the image-churn window (1 ms bakes, stale planes) — the probe
    waits 30 s after invalidating when cold.

- **KSA density model** (2026-09-05, user: "lets bake the weather per
    layer as ksa does, and lets also do the KSA weather/coverage ... use
    the shape noise like ksa ... mirror the ksa approach completely,
    then we can go our way; discard everything rain related"). The
    census answer to "why is KSA real-time and PA2 not": the evaluation
    COUNT per pixel was already KSA's (step schedule, 4 + 1 light
    samples, 3x3 interleave), the cost of ONE density evaluation was
    not — 3 authored-map taps + 1 LUT + 3 R8 Worley taps there, against
    the chart projection, the Keinert lattice (log/pow/atan, 4 x
    sin/cos/sqrt), 1-8 anti-tiled weather taps, vec4 pow, three Fewes
    sculpts, the rain branch, 2 turbulence taps and 4-8 RGBA16F volume
    taps here, and the light march repeating all of it 4x per lit step
    (73% of the pass; the kernel register-bound, so caching inside it
    made it slower). Built as a compile variant, PA2_KSA_DENSITY
    (`cloud_density_model`, KSA default / PA2 procedural):
    `sampleCloudWeather` / `sampleCloudMedia` twins in the model lib
    (helpers before `sampleCloudWeatherWd`, twins after the procedural
    media sampler, the ground-AO column and the analytic shadow column
    have twins too). Weather: `weather_bake_driver.glsl` (compute,
    2048² RGBA16F) runs the PROCEDURAL `sampleCloudWeatherWd` (the
    refactored weather returning its pre-sculpt coverage) at each
    layer's mid altitude over a gnomonic chart about the sub-camera
    direction (cl_grid = n.xyz + half-extent; east from a fixed
    reference so bake and march agree), half-extent = 1.15 x the
    ground-arc horizon of the highest top plus the camera's (40-600 km;
    ~360 km here = 350 m/texel); keyed on the cloud param key WITH the
    clock, the camera's 10%-of-extent chart cell and the extent, ~1 ms
    a bake. Vertical profile: the Fewes sculpt of the baked coverage,
    analytic (KSA's LUT would have been a 3rd sampler). Noise:
    `worley_gen_driver.glsl` = KSA's GenerateWorleyNoise (their
    tileable Cellular3D, 8 octaves, persistence 0.57, inverted,
    range-stretched on the CPU), 128³, four mean-pooled mip levels
    stacked along z in ONE volume (each padded by a wrap texel for the
    EXTEND sampler), R16F (the GPU module only takes FLOAT buffers — R8
    would halve it again); tapped through KSA's octahedral 3-tap
    anti-tiling at the analytic pixel-angle mip, FLOORED, one level per
    tap; `ApplyErosion` (max depth 0.65, Shape Amount = edge sharpness).
    NO NEW SAMPLERS: the bake rides the iChannel0 slot and the atlas the
    uCloudShape3D slot — the procedural slots a KSA build never reads —
    through `_cloud_channels_live()` at the three bind sites
    (`_draw_pass`, `_rect_compute_pass`, the shadow-volume and density
    bakes), so every builder and call site is untouched and the sampler
    budget (30 of 32 in the fullest rect build) stays. The bake binds
    the procedural inputs directly. Measured (`probe_cloud_perf.py`
    PA2_CLOUD_MODEL, 1920x1080, 61% cloud px, Normal, same session
    order): full-res cloud pass 13.2 ms (KSA) vs 69.2 median / 44.9 min
    (procedural); interleaved pass 3.3-3.6 vs 6.1-20.0; the interleaved
    round is now the resolve (5.5 ms). Equirect forced bake 9.3 ms vs
    ~40. Same coverage field (61.2 vs 61.4% cloud px, T 0.40 vs 0.41);
    L mean 11.0 vs 19.1 — KSA's dark-edge term takes the sculpted
    coverage as the depth proxy where the procedural DP was the
    post-density profile (0.7 vs ~1 in bodies), and KSA balances its
    darker MS with a per-type brightness and CLOUD_BRIGHTNESS 8. The
    look is the user's call from here ("then we can go our way").

- **The chart must not follow the camera** (2026-09-05, user: "when
    the camera moves the clouds seem to shift around"; "the clouds do
    not reach the planet end"). First cut: the bake re-anchored on the
    LIVE camera direction at every re-bake, and the half-extent followed
    the camera altitude (sqrt(2R h): ~200 m of extent per metre near
    the ground, quantized to 5 km) — so a few metres of climb re-baked
    the coverage onto a grid that had slid with the eye: the clouds
    swam. And the 600 km cap ended the coverage in a square from orbit
    (KSA never has this: a planet-wide coverage map + sphere-wide
    detail tiling). Fix in `_ensure_ksa_density`: the anchor is the
    CENTRE of a fixed cell on the sphere (10% of the extent, the
    quantized n renormalized), the camera altitude enters the extent
    only above 500 m and then on a x2 ladder, the extent snaps to a
    x1.25 ladder, no cap short of 4000 km. `probe_cloud_model_view.py
    PA2_PROBE_WALK=1`: the chart row is identical through 20 m, 30 m up,
    500 m and 2 km moves (no re-bake); 400 km up re-anchors once at a
    2220 km half-extent (2.2 km texels — from orbit a texel is a few
    pixels; supersample the bake if it ever reads speckled). The same
    probe's per-bake sky rel95 at the SAME spot is 11%: the KSA march's
    frame dither (ray + light seeds), not the chart.

- **Shadow volume: the KSA audit and the resample** (2026-09-05, user:
    "cloud shadow volume is flickering when camera moves", "can you check
    if the shadow volume matches ksa?"). Against `ShadowVolume.comp` /
    `ShadowVolume.glsl` / `ResampleVolumes.comp`: SAME dual-paraboloid x
    altitude mapping (Zink), R16F, density/100 storage, tricubic B-spline
    in 8 bilinear taps (byte-for-byte: the `svsample` shared block now
    lifts it into the resample), 40-step sun march through the cloud
    band, 3x4 ambient directions x 7 samples x 0.1 capped at 4x the band
    thickness, amortized `sliceToUpdate`, per-layer accumulation
    (their first-pass clear = our one march over all layers). DIFFERENT
    by design: our anchor is the sub-camera SURFACE point (theirs the
    camera; ours keeps the band in the live hemisphere from altitude),
    our slice axis is altitude Z (theirs the paraboloid Y strip), our
    build noise is the KSA Worley at mip level 2 (their fixed mip 3), we
    add the rim trust fade and a trilinear twin for the godray taps
    (they tap tricubic everywhere), and the out-of-band sun projection
    is theirs (Godrays.glsl). MISSING until tonight: the RESAMPLE. Their
    volume never lags its frame — `ResampleVolumes.comp` re-projects both
    volumes into the new frame whenever the camera moves. Ours moved the
    frame rows in 500 m jumps at a cycle start (the morning's roll
    gating) while the slices caught up over six rounds: the flicker.
    Now `sv_resample_driver.glsl` (compute, 8 push-constant rows = old +
    new frame, the bake's own ray-sphere rule, tricubic taps of the old
    frame, ping-pong textures) runs before every rolling refresh whose
    frame moved (> 1 m / 1e-4 basis), the published rows always describe
    the content, and the origin left the whole-volume-bake key (5 km
    cells). SECOND ROUND (same evening, user: "the lighting on clouds
    still flicker from the shadow volume"): a frame that follows the
    camera every round is resampled every round — each tricubic pass
    blurs the volume a little and the roll re-sharpens 8 of 48 slices a
    round, so the far light term pulsed with a six-round period while
    moving. The anchor is now the centre of a fixed 1 km cell on the
    sphere (the weather chart's rule; the basis from the quantized
    direction): inside the cell the frame, the content and the rows do
    not move at all and nothing rolls unless the sun or the clock move;
    a cell change resamples once and runs one refresh cycle. KSA's CPU
    side is not in the sources, so whether they threshold the resample
    is unknown — the physics is: the volume is a function of world
    position, the paraboloid only a parametrization, and re-projecting a
    parametrization every frame buys nothing but blur.

- **Object shadows on clouds** (2026-09-05, user: "make the 3d objects
    drop shadow on clouds"). KSA (`RaymarchCloud.comp`): `sunToCloud-
    Transmittance *= getSunShadowFiltered(terrainShadowUbo,
    averageCloudPosition, ...)` — ONE PCF tap of the terrain cascade at
    the transmittance-weighted centroid, scaling the whole sun-driven
    colour. PA2's caster sun-depth map (`caster_shadow_lib.glsl`,
    `pa2CasterShadowSoft` = 4 jittered taps) already shadowed the air
    march per sample (godrays) and the ground; the retired house cloud
    march had the per-sample tap too and the KSA port dropped it. Now
    `march_cloud_segment_ksa` multiplies `scatteredLight` (the sun-lit
    single + multiple terms; the sky ambient stays) by
    `pa2CasterShadowSoft(ro + rd * t)` per LIT step under
    `PA2_AIR_CASTERS` (rect builds only — the probe's role law) and the
    runtime bit6 `PA2_RT_CASTER_CLOUDS` (`shadow_casters_clouds`, no
    recompile). Per sample rather than KSA's centroid: a caster's shadow
    cuts INTO the deck with the correct volumetric edge instead of
    dimming the pixel flat; 4 texel fetches of a 2D map per lit step next
    to 15 volume taps. `probe_caster_clouds.py` (a 2 km cube placed on
    the sun ray 2 km sunward of the deck over the camera, sun 25°, the
    view straight up): with the toggle on the cloud radiance under the
    cube reads 0.23x the toggle-off plane, 91% of the cloud pixels
    darkened by more than 30%, 61% by more than 60%, the 5th percentile
    ratio 0.09 (the sky ambient stays, as designed). A first run with a
    600 m cube showed nothing: its shadow fell on clear sky (31% cover),
    a reminder that the probe must aim the shadow at cloud. The toggle
    rides `_CLOUD_KEY_SUNPROPS` so a flip re-marches while still.

- **Scene lamps on the clouds** (2026-09-05, user: "add also blender
    light source interaction with clouds"). No KSA reference (their
    clouds know only the sun). The Scene Lights arc (2026-09-03) put
    Blender Point/Spot lamps on the ground and in the air with EEVEE's
    light law through `scene_lights_lib.glsl`, included by the DRIVERS
    (after the libraries). The cloud march lives in the libraries, so
    the light LAW (count / window / spot / point) became a guarded
    shared block (`lightbase`, `#ifndef PA2_LIGHT_BASE`) that
    `_assemble_fragment_source` splices ahead of the libraries next to
    the caster helpers; the drivers' own include then skips it and the
    ground compose (no atmosphere blob) still compiles it. In
    `march_cloud_segment_ksa`, per lit step: `pa2KsaLampStep` = per lamp
    EEVEE's volume-light irradiance (`color*power/4pi * volume factor *
    Yuksel * spot * window`, the air's exact form), the KSA phases for
    THAT lamp's direction (per step — the sun's are per ray), and a
    two-sample density march toward the lamp over min(distance, light
    window) for `exp(-d) * phD + BeerMS(d) * phI * msEdge`; accumulated
    with the integration weight (and the early-exit tail), added as
    `lampColor * PA2_KSA_BRIGHTNESS` without the sun transmittance.
    Compile toggle PA2_LIGHTS_CLOUDS (the Scene Lights property; pinned
    0 in the LUT / SV / weather bakes), runtime lane `lt_cfg.w` (Light
    Clouds, `scene_lights_clouds`, in the light key). Lamps beyond their
    EEVEE volume influence sphere skip before any tap.

- **Refraction shimmer split** (2026-09-06, user: "separate the shimmer
    into two parts", "the near shimmer needs to be part of the refraction
    pipeline... like 1 km from the camera"): the world-space tier's
    per-step kicks, Eddy Size and the camera-side tilt retired;
    **temperature masses** scale G(h) inside `pa2RfPrepare` (one volume
    tap per sub-step below 4 × 1.5 km, `rf_shim2`, amount = RMS fraction
    of the gradient, default 1, clamped at 0); the **near shimmer** kicks
    at eight fixed stations across the first kilometre of the trace walk
    (gradient of the field by central differences over ±1/24 period,
    `_turb3d_diff_rms`; camera-relative positions in the walk plane's
    terms; the field slides at Boil Hz/12 and rides the updraft; ψ/ψ_S
    out-of-plane), star scintillation `pa2CelScint` in the rect compose
    (`rf_wind.y`, airmass-scaled lognormal, chromatic at the horizon).
    Default amount 1 → 0.3 (1′ over 3′ cells folded the mapping and tore
    the disc; `probe_shimmer_view.py` shows the limb from the B plane).
    Traps: per-sub-step kicks streak rows (the schedule's step count
    changes with elevation); fp32 world positions snap 0.87 m eddies.

- **Mirage horizon hole** (2026-09-06, user: "hole peeking through
    transmittance and earth horizon... where the real horizon would
    be"): the rect LUT arm's atlas-vs-aerial choice took the STRAIGHT
    shell chord, so an inferior-mirage reflection (a walked EXIT from
    below the geometric horizon) fell to the aerial's ground column — a
    flat grey T under the sun = the white band. The walk's verdict
    (`g_pa2RfKind`) chooses now, and such rays take the horizon ray's
    atlas column (the atlas rows a dozen arcminutes down are ground
    columns 3–5′ apart). `probe_horizon_hole.py`: 18 white px → 0; the
    horizon lift measured 2.0′ (60 m) / 2.8′ (70 m), inferior mirages
    lower it 8–13′.

- **Mirage sun sliced into bands** (2026-09-06, user: "I think it might
    be the raymarch steps" — it was): the walk's shell-top exit clip was
    a linear ratio on the full step's midpoint rate + the commit used the
    unclipped rates: 6″/180 m lost on the last step, ±3″ ray-to-ray,
    ×30 under a duct = 2′ slices. Fix in `pa2RfPrepare` + the twin: the
    top crossing's quadratic, clipped steps recompute their midpoint
    rates, Simpson over the step's gradient; MAX_STEPS 512. Standard air
    jitter 13.6″ → 1.3″ (Normal); GPU-twin bend agreement 0.36″. The
    user's scene reproduced in `probe_horizon_hole.py` (eye 2 m, +5 K
    50–60 m, sun −0.52°, strength 1.2): sliced before, smooth after.

- **Shimmer under a duct** (2026-09-06, user: "the bands reappear when
    shimmer is added"): the near field's sub-step cap re-phased the walk
    per row (twin 0.12″ → 1.68″ with a zero field) and the masses
    point-sampled a 3 km field per 3–8 km step (7.9″) while scaling the
    duct's own gradient (39″). Both are fixed STATIONS now: the near
    field kicks every station inside a step; the masses kick the
    standard-gradient offset A·n·e^{−h/H}·g₀ (lane rf_shim2.w = g₀ ×
    strength) integrated over half-cell stations (≥ 1.25 km), never
    inverting the local gradient. Twin: duct 0.6″, clear air 0.2″; the
    masses' wander is ~0.2′ across azimuth at amount 1. Then (user: "the
    masses need to change the temperature, so the IOR changes"): the
    masses are a temperature field, Masses ΔT (K, default 2); δn = N δT/T
    and the stations kick by δn's transverse gradient (central
    differences, vertical + sideways, ψ/ψ_S), lane rf_shim2.x = 2 N ΔT/T
    × min(st/c, √(st/c)) / RMS. Twin with the real volume: 2 K / 3 km →
    0.12′ sideways, 0.01′ vertical; 2 K / 1 km → 0.45′ sideways. Then
    STRATIFIED (user: "more flattened, the coordinate the normalized up
    vector"): the field's frame = the camera's up + a fixed horizontal
    pair, vertical cell = Mass Thickness (300 m), horizontal = × Mass
    Aspect (20), lane rf_shim2.w = 1/horizontal period (= on); 100 m
    isotropic masses had torn a sub-duct sun. Design doc §4.6.1 / §4.7.1
    written once the Mac's celestials commit (e16e734) landed.

- **Spectral dither, two fixes** (2026-09-06): the BG compose never
    bound uBlueNoise (only the ground draw did) → one wavelength per
    pass for every pixel, the sun swept through the spectrum; bound at
    both `_rect_background_rt` sites. T(λ) from the bands = a piecewise
    power law in log λ (the free quadratic in λ⁻⁴ bent up at the blue end
    with aerosols → violet far-blue samples, banded sun).

- **Mirage layer waves** (2026-09-06, user: "build the layer undulation
    on the Mirage Layers block, the physical way"): an internal
    gravity-wave train (dominant + two companions at ±25/35°, one
    interfacial phase speed √(g ΔT/T z_base) from the layer itself)
    displaces the profile above the ground layer in every rect walk,
    `pa2RfWaveEta` + `h − η` at the three table reads. Knobs Waves (m) /
    Length (m) / Dir (°) on the Mirage Layers block; lanes rf_cfg2.w,
    rf_shim2.z, rf_wind.w, rf_shim.y (three constants moved into the
    shader to free them). Sub-duct sun stacks into rippled bands. Suite
    86.

- **Air masses retired** (2026-09-06, user: "the waves do their job"):
    knobs, lanes (rf_shim2.x/y/w free), the walk's mass stations, the
    twin's `masses`, tests and probe sections removed; the near shimmer
    and the layer waves remain. Suite 85.

- **Heat blur + internal gravity waves** (2026-09-06 evening, user:
    "more like the heat blur" / "internal gravity waves ... double check
    the math and lets implement"): the BG compose tilts every film
    sample's ray by a Gaussian of σ = Blur × Kolmogorov's sub-cell share
    (2.5× the ripple at 3′) × the near amplitude (`pa2RfBlurDir`,
    blue-noise Box-Muller, lane rf_shim2.x); the layer waves are six
    internal gravity waves with ω = N k_h/√(k_h²+m²), N from the layer's
    own lapse, a Vertical wavelength knob, Gain + Steepness (Gerstner
    orbit, optional) packed on rf_wind.w, N/m on rf_shim2.y/w
    (`gravity_wave_eta` twin, probe section 6). The proposal's density
    warp ρ(z − ξ) is the tracer form, 10× too strong for ρ and T
    (design-refraction §4.7.2 rev. 2). Suite 86. Then 1-D in height
    (user: "mapped to the planet's up axis"): ξ(h, t) at the camera's
    phase for the whole ray, Dir retired, rf_shim.y free (rev. 3); then
    along the line of sight, ξ(s, h, t) (rev. 4: a uniform lift did
    nothing visible — "the eye moved"), Vertical default 200 m, an
    overturning guard on the amplitude.

- **Shimmer on turbulence physics** (2026-09-06 late, user: "a more
    physically accurate way"): a Kolmogorov phase screen in uBlueNoise.y
    (FFT bake), the walk's eight stations reading its footprint-averaged
    tilt × √(C_n²(h) Δs) with C_n² ∝ h^(−4/3) from the Cn² knob, windows
    drifting with the log-profile wind (Wind / Wind From knobs) and the
    updraft, the heat blur = the sub-footprint tilt band 1.95 I Δκ^(1/3)
    gathered along the whole low path (design-refraction §4.6.3).
    Amount / Scale / Boil retired. Suite 88.

- **Spectral dispersion dither** (2026-09-06, user proposal): the rect
    compose's celestial arm draws one wavelength per pixel per film
    sample (blue noise .w + the pass shift), walks it with Ciddor's
    ratio, weights the RGB by Planck × sRGB CMF (mean 1) and holds the
    three-band convention through T(λ)·T_c/E_c[w_c T] (16-point mean
    per pixel). One walk per sample instead of three; the film converges
    to a continuous rim. Step-phase dithering of the walk assessed and
    declined. CPU twins `spectral_weight` / `ciddor_dispersion_ratio`,
    unit-tested; suite 85.

#### 23.1 Compile-time census (2026-09-05)

`scripts/probe_shader_compile.py` wraps `gpu.shader.create_from_info` and
the first draw / dispatch of every PA2 program (fenced). Findings on the
RTX 4080, Blender 5.2 Vulkan:

- SPIR-V generation is negligible (about 300 ms for all 25 programs).
    The time is the driver's pipeline build, and Blender's Vulkan backend
    defers part of it: compute programs build at `create_from_info`,
    fragment programs pay a first build there (default state) and a second
    at their first real draw.

- The NVIDIA disk cache serves identical SPIR-V across sessions in well
    under a second. `__GL_SHADER_DISK_CACHE=0` does NOT disable it for
    Vulkan, so any "cold" number must come from a source that never
    compiled before (the bisect probe injects a unique literal).

- True cold costs with clouds on, LUT Atmosphere: rect air compute 15 s,
    its fragment twin 15 s, the equirect lighting program 14 s (measured
    while EEVEE's own world compile job held the CPU; 30 s uncontended
    before the guard), cloud pass 2 s, everything else under 0.2 s. Clouds
    off: every program together 0.4 s.

- `scripts/probe_compile_bisect.py` on the equirect program: base 30.6 s;
    the light march stubbed 20.6 s; the cloud arm stubbed 16.5 s; the
    geometry-cut composite dead 4.6 s; arm + light march stubbed 2.5 s;
    clouds off 1.2 s. The second inlined instance of the cloud arm and the
    air march (the coverage cut) is what the driver chokes on, not the
    cloud model per se.

- Applied: the cut composite is compiled into RECT builds only (opaque
    bodies clamp the equirect's column up front instead); the probe never
    taps the scene casters in its air (`PA2_AIR_CASTERS`, rect-only); the
    Reflections category can march the probe cloudless (`USE_CLOUDS 0`
    variant, about 1 s) or skip it entirely (Reflection Probe off).

- Open: the rect LUT air build still carries the fallback march and its
    own cut instance (15 s cold); the fragment twin doubles that. A LUT
    build without the fallback march and a single-instance cut (record the
    partial sums at the cut distance during one march) would bring the
    rect's cold compile to the cloud pass's 2 s class.

- Runtime under the LUT with clouds: the per-draw air pass ran under an
    EMA hold-off (2x its cost) with the warp bridging the skipped draws and
    ghosting composited objects; it now runs on every moved draw while it
    stays under 25 ms (clouds keep their temporal reprojection).

- Object compositing repro (`scripts/probe_viewgeo_aureole.py`, a 4 km
    cube at 10 km in turbidity-6 air, sun 8 degrees up behind it, casters
    on, `PA2_AUREOLE_DUMP=1`): the viewgeo depth at the sun pixel is
    7981 m (correct), and the rect S plane there reads 6.02 with KSA's
    0.95 aerosol damp in the godray pass against 5.28 with the damp at
    1.0; the sky 14 degrees off reads 6.3. The unshadowed single
    scattering at the sun pixel is the aureole (about 15 on a 5.3
    isotropic background), so the damp leaked 5% of it into every
    object shadow covering the sun. KSA needs the damp because its LUT
    stores phase-applied radiance; PA2's planes are phase-free, so the
    damp was removed (the consumer's per-channel clamp at zero guards
    over-subtraction). Screenshot luminances were useless for this: the
    scripted viewport composite carried no cut haze on the object at
    all (its compositor setup is still to be checked), so the numbers
    were the cube's own shading. Multiple scattering stays unshadowed in
    the godray pass (KSA), which keeps a shadowed path at the isotropic
    floor rather than dark.

- Space view (`scripts/probe_space_limb.py`, camera 2000 km up, the sun
    just above the limb): `_lut_radiance_scale` rated the sun by its
    elevation at the CAMERA's horizontal (-40 degrees there) and every
    generation took the 2^18 night scale. The sky-view atlas is fp32 and
    survives it; the aerial planes are fp16 and overflow, so ground-hitting
    rays over the sunlit disc lost their haze toward the sun. The rule now
    adds the horizon depression acos(R / r), which leaves ground views
    unchanged (an airliner gains about 3 degrees).

- Air Reprojection Warp: a runtime switch, OFF by default (user verdict
    2026-09-05): draws the fresh air pass cannot serve keep the planes at
    the last pose; only the clouds reproject.

- Space view after the scale fix (probe_space_limb.py, sun 12 degrees
    above the limb, rect S plane, R / G / B): the haze under the limb is
    back, but the LUT over-reads the analytic reference at grazing
    ground-hitting rays. 2000 km: half a degree under the limb LUT 11.3 /
    6.4 / 7.6 vs reference 3.5 / 3.7 / 7.1; one degree 2.5 / 1.3 / 2.1 vs
    1.5 / 1.1 / 2.0; two degrees equal. 600 km: half a degree 19.3 / 12.0
    / 13.5 vs 5.6 / 6.2 / 11.9; two degrees 4.7 / 2.5 / 3.5 vs 1.8 / 1.7 /
    3.5; four degrees equal (0.43). The excess is red-heavy and confined
    to the first two degrees under the limb: the aerial planes' angular
    and depth resolution at rays that graze the dense shell (OPEN, the
    "space views" item). The scripted viewport itself displayed black in
    BOTH modes from space while the planes held the content; the probe's
    display side is unchecked.

- Metal field log (2026-09-05, after the review): the sky-view producer
    and its atlas pack were fragment passes over their own framebuffer and
    ran inside EEVEE's draw callback from the per-draw LUT arm; Metal
    refuses the framebuffer exit there and burns a stack slot per pass
    (four, then the pipeline stood down). Transmittance, sky-view and the
    pack are compute dispatches now; the whole LUT chain is
    framebuffer-free, on every backend. The same mid-frame render-pass
    switch is the suspect for the Vulkan device losses reported since the
    LUT rect; to be confirmed in the field.


## Atmospheric Refraction — ray-marched, one law for sky, ground and celestials {#refraction}

`design:`{: .label-research } Shipping · every stage landed · amended 10.09.2026 · 03.09.2026 · `docs/design-refraction-2026-09.md`

**In this document:** [1. What exists today, and why it is "not functional"](#refraction-1-what-exists-today-and-why-it-is-not-functional) · [2. Requirements → design decisions](#refraction-2-requirements-design-decisions) · [3. Physics](#refraction-3-physics) · [4. Architecture](#refraction-4-architecture) · [5. Data, UI, keys](#refraction-5-data-ui-keys) · [6. Stages](#refraction-6-stages) · [7. Verification](#refraction-7-verification) · [8. Risks and known limits](#refraction-8-risks-and-known-limits) · [9. What we take from the references, and where we depart](#refraction-9-what-we-take-from-the-references-and-where-we) · [10. Open questions for the user](#refraction-10-open-questions-for-the-user)

<figure class="pa2-fig pa2-fig--flat">
<svg viewBox="0 0 720 340" role="img" aria-label="A camera above a curved planet. A dashed straight ray reaches the geometric horizon; a solid bent ray curves down and touches the surface further away; a dotted line shows the apparent direction, higher than both.">
  <defs>
    <clipPath id="rf-above"><rect x="0" y="0" width="720" height="340"/></clipPath>
  </defs>
  <circle cx="360" cy="1180" r="960" class="rf-sky-a" clip-path="url(#rf-above)"/>
  <circle cx="360" cy="1180" r="930" class="rf-sky-b" opacity="0.55" clip-path="url(#rf-above)"/>
  <circle cx="360" cy="1180" r="900" class="rf-ground" clip-path="url(#rf-above)"/>
  <line x1="360" y1="262" x2="537" y2="298" class="rf-straight" stroke-width="1.6" stroke-dasharray="6 5" fill="none"/>
  <line x1="537" y1="298" x2="700" y2="331" class="rf-straight" stroke-width="1" stroke-dasharray="2 5" fill="none" opacity="0.7"/>
  <path d="M 360 262 Q 487 276 630 321" class="rf-bent" stroke-width="2.4" fill="none"/>
  <path d="M 630 321 Q 690 340 720 351" class="rf-bent" stroke-width="1" stroke-dasharray="2 5" fill="none" opacity="0.6"/>
  <line x1="360" y1="262" x2="720" y2="301.7" class="rf-apparent" stroke-width="1.4" stroke-dasharray="1.5 4" fill="none"/>
  <circle cx="684" cy="297.5" r="9" class="rf-sun"/>
  <circle cx="360" cy="262" r="4.5" class="rf-ink"/>
  <line x1="360" y1="266" x2="360" y2="280" class="rf-ink-stroke" stroke-width="1.4"/>
  <circle cx="537" cy="298" r="3" class="rf-mut"/>
  <circle cx="630" cy="321" r="3" class="rf-bent-fill"/>
  <g class="rf-label">
    <text x="366" y="250">eye · h = 2 m</text>
    <text x="470" y="245" class="rf-mut">straight ray · geometric horizon at 5.05 km</text>
    <text x="500" y="318" text-anchor="end" class="rf-bent-fill">bent ray · lifted horizon at √(2Rh/(1−k)) = 5.54 km</text>
    <text x="600" y="282" text-anchor="end" class="rf-apparent-fill">apparent direction · +34′ at sea level</text>
    <text x="80" y="330" class="rf-mut">k = −R · G(h),  G = (1/n)·dn/dh,  standard air k = 0.17</text>
  </g>
</svg>
<figcaption>The ground viewer's horizon ray. Refraction is exaggerated for the drawing; the real bend is 34′ at the horizon and the lifted horizon is 10 % further. Everything the design does follows from walking that curve step by step and asking, at every consumer, "where am I and which way am I looking".</figcaption>
</figure>

Status: SHIPPING — in 3.0.0-beta and later (written 2026-09-03 as a
design; amended as stages landed). As built by 2026-09-10, beyond the
list below: the near shimmer rebuilt on turbulence physics, heat blur
as fixed TAA-style taps, the mirage layers riding 1-D internal gravity
waves (Waves / Length / Vertical / Gain / Steep on the Mirage Layers
block), the optional sub-frame phase dither of the walk, and the tuned
mirage layer shipped as the default. The temperature-field AIR MASSES
of 2026-09-06 (their toggle, ΔT / Thick / Aspect, lanes, stations,
twin, tests) were RETIRED the same day — the layer waves carry the
structure (CHANGELOG, Removed). §10's questions were settled in the
field: refraction ships ON with the tuned layer, dispersion ON, the
inversion as an enum with presets. Every stage has landed in the tree: the LUT generations walk the
bent path (0381b1a, 11792e8, a6ebfb4); the stage-1 batch — bent view rays,
shimmer, dispersion, North Offset, presets (adb7553); the shimmer split
into temperature masses + a near field inside the walk (cec18cd); the
walk's end-step clip (984808b); shimmer under a duct (ba67fbb); spectral
dispersion by wavelength dither in the celestial arm (c444b61); the
temperature masses as a temperature field (7ecb762); the sun's chromatic
limb law (2026-09-06, §4.7). Open: the LUT sky's horizon-band
transmittance (§8). Supersedes the 2026-07 effective-sphere stub (2.6.1
"Atmospheric Refraction", off by default since f459319). User direction
(2026-09-03):

- one refraction for celestials, ground and atmosphere at the same time;
- bending from the air's pressure and temperature gradient;
- a smooth-noise shimmer when zoomed in (the high-frequency boil on the
    sun's edge);

- ray-marched per step so rays bend realistically, lifting ground,
    atmosphere and celestials (see behind the geometric horizon);

- works for a viewer inside the atmosphere (ground and aerial) and from
    space (ray enters the atmosphere, traverses it, exits again);

- the green flash: wavelength-dependent refraction (added 2026-09-03,
    Young's simulations as the reference).

References: W. Bislin, *Deriving Equations for Atmospheric Refraction*,
*Simulation of Atmospheric Refraction*, *Source Code: Refraction
Simulator* (walter.bislins.ch); A. T. Young, *Green Flash Simulations*
(aty.sdsu.edu/explain/simulations: standard-atmosphere, inferior-mirage,
mock-mirage, ducted and sub-duct sunsets, `how.html`, Wegener's
principle); H. Neckel & D. Labs (1994), *Solar limb darkening 1986–1990
(λλ 303 to 1099 nm)*, Solar Physics 153, 91–114 — the per-channel limb
law of the sun's disc, which the mirage folds slice (§4.7). What we take
from them and where we depart is listed in §9.

### 1. What exists today, and why it is "not functional" {#refraction-1-what-exists-today-and-why-it-is-not-functional}

Three disconnected mechanisms, none complete:

1. \*\*`core/refraction.py` bakes `PA2_REFRACTION_LUT`\*\* (2048x2 float
   image: ODE-exact deviation vs apparent elevation, mirage-aware, plus
   a limb-traversal row) on every `ensure` tick from
   `celestial_math.py:1341`. **Nothing reads it.** Its consumer, the
   node-side direction squish (`PA2_REFRACT_DIR`), retired with the node
   celestials (world group v16, `atmosphere_world.py:1504`). Celestials
   therefore have NO refraction at all: the sun sets ~34′ early
   relative to a lifted horizon, and from orbit the limb does not squish
   the stars. The bake still costs image churn per tick and drags a
   fake-user datablock plus an `operators.py:340` cleanup path around.

2. **The view-ray "refraction" is the effective-radius trick**
   (`_refraction_boost`, k/(1-k) in `cl_skew2.y`), applied with an
   ad-hoc graze⁸ weight in four copies: `sky_driver.glsl:290`,
   `sky_luts.py:1016` (aerial atlas, disabled), `ground_compose.frag:810`
   and the numpy twin `sky_ground.py:530`. It moves the horizon LINE and
   makes the whole column run on a bigger sphere, but it is not a ray
   model: no mirage fold, no limb lensing from orbit, no per-step
   bending, no coupling to the celestials, and k is clamped to the
   calculator's range [-0.5, 0.78]. The graze⁸ weight has no physical
   meaning; it exists to hide the seam between "lifted" and "not".

3. **The Psi MS driver's terminator shift** (`psi_ms_driver.glsl:85`):
   `dipEdge = -sinDip - 0.0105 * clamp(k/0.206)` — a constant tuned so
   the lighting terminator roughly follows the lifted horizon.

Field verdict since 2.6.1: the horizon rises but nothing else agrees
with it, so the toggle stayed off.

### 2. Requirements → design decisions {#refraction-2-requirements-design-decisions}

| Requirement | Decision |
|---|---|
| One refraction for everything | ONE shared GLSL integrator (`refraction_lib.glsl`) run identically by every pass that owns a ray: the rect air pass, the cloud pass, the BG/ground compose. Same inputs → same path → same horizon in all planes. |
| Pressure & temperature gradient | The bending coefficient G(h) = (1/n)·dn/dh comes from hydrostatics through an ISA-layer T(h) anchored to the scene's surface temperature, with the surface thermal layer and an elevated inversion, scaled by the Ciddor N₀ the sky already uses (the same P, T, RH, CO₂ knobs). Baked on the CPU into a 512-entry altitude table that rides the UBO. |
| Per-step ray bending | A deterministic geometric march in a 2-D (altitude, travel angle, zenith angle) state — Bouguer's planar reduction — with an RK2 "circular arc" step (Bislin's scheme), analytic ground/shell crossing inside each step, and a step schedule keyed to the table's altitude resolution. Consumers walk their radiometric samples along that path. |
| Shimmer when zoomed in | A sky-fixed, scene-time-driven tilt of the initial direction from the EXISTING 3-D turbulence volume sampled on the sphere (one fetch, no new texture), amplitude ∝ the ray's own astronomical refraction (1′ at the horizon by default, 2″ at 45°), rising with an updraft; wind-map drift postponed (§4.6). Applied inside the shared helper so every pass sees the same tilt. |
| Ground, aerial and space viewers | The march starts at the camera when it is inside the shell and at the shell entry point when it is outside; ends at ground, shell exit or a path cap. Limb lensing, the flattened orbital sunset and the ground displacement at the limb fall out of the same code. |
| Green flash | Refractivity is dispersive (N_B/N_g = 1.009, N_R/N_g = 0.995 at the project's 445/535/615 nm). The table is one profile; per-channel bending is the same walk with G scaled by N_λ/N_g. Outside mirage conditions one walk plus a per-channel rotation of the exit direction is exact to first order; inside a mirage/duct fold the three channels fold at different elevations, so the horizon band traces R, G and B separately (§4.7). An elevated inversion layer joins the profile knobs, because the mock-mirage, ducted and sub-duct flashes (Young) need one. |
| Not in scope | Scene meshes (Blender renders them with straight rays — mismatch < 1′ at 15 km, §8), the equirect (lighting/reflection role law: straight rays), second-bounce refraction of water reflections, radio-band refractivity. |

Law (new): \*\*the sun direction `u_pa2.sun` stays TRUE.\*\* The apparent
lift of sun, moon, stars and planets is produced by bending the VIEW
rays. Nothing on the CPU pre-lifts a celestial direction for the march
(the managed sun LAMP is the one exception, §5.4, because it lights
straight-ray meshes).

### 3. Physics {#refraction-3-physics}

#### 3.1 Refractivity and the bending coefficient

- n − 1 = N(h) = N₀ · ρ(h)/ρ₀ (Gladstone–Dale). N₀ from `ciddor_n_air`
    at 550 nm: 277.8 ppm for 15 °C, 1013.25 hPa, dry air (humidity moves
    it by 0.01 ppm at 15 °C).

- Which T(h) (stage-0 finding, 2026-09-03): the sky's fit-shaped curve
    (`temperature_profile_fit_k`) has a −9.7 K/km surface lapse; through
    hydrostatics that is k = 0.150 and a 31.9′ horizon, 12 % and 6 %
    under the textbook 0.171 / ~34′. The refraction profile therefore
    uses ISA layers (−6.5 K/km to 11 km, then the standard lapses)
    anchored to the scene's T₀, with the surface layer and the elevated
    inversion on top: k = 0.170, horizon 33.0′ at 15 °C. The sky's
    density model is untouched (§4.1).

- Eikonal equation for a unit direction d in a medium n(h):
    d(d)/ds = G · (û − (d·û) d), G = (1/n) dn/dh [1/m]. G < 0 in normal
    air (rays bend toward the planet).

- Hydrostatics through T(h): dN/dh = −N · (g/(R_s T) + T′/T), so
    G(h) = −N(h) · (g/(R_s T(h)) + T′(h)/T(h)) with g/R_s = 0.0343 K/m.
    This is Bislin's eq. 38/39; scaling by R gives his refraction
    coefficient k = 503 · P/T² · (0.0343 + dT/dh) (P in hPa): k = 0.170
    for the standard atmosphere, k = 0 at dT/dh = −34.3 K/km, k = 1 (ray
    follows the surface) at +129 K/km, k < 0 (inferior mirage) for hot
    ground.

- The surface thermal layer already in the codebase
    (`atmosphere_ground_temp_delta_k`, `atmosphere_ground_layer_m`:
    ΔT·exp(−h/L)) puts gradients of several K/m into the first metres:
    ΔT = +10 K, L = 2 m gives G(0) = +4.8e−6 /m (curvature radius 208 km
    upward, k = −33). That is the desert mirage, and it needs cm-scale
    altitude resolution near the ground (§4.1).

- Bouguer's invariant for a spherically symmetric medium,
    n(h)·(R+h)·sin z = const, is exact along the path and is the accuracy
    check for the integrator (§7).

#### 3.2 The ray ODE (planar)

A spherically symmetric n keeps the ray in the plane of the planet
centre, the start point and the initial direction. State per ray:
h (altitude), φ (angular travel about the plane normal), z (local zenith
angle of the direction), s (arc length), β (accumulated refractive
bend). With r = R + h:

    dh/ds = cos z
    dφ/ds = sin z / r
    dz/ds = −sin z · (1/r + G(h))        (1/r = the local vertical rotating; G = refraction)
    dβ/ds = −sin z · G(h)

The world direction changes ONLY by refraction (the 1/r term is the
frame turning), so d_exit = Rot(n̂, β)·d₀ exactly — which is what makes
dispersion a one-line rotation (§5.6).

Ground viewer at the horizon: z = 90° → dz/ds = −(1−k)/R: the ray rises
relative to the ground at (1−k) times the straight-line rate, i.e. it
follows the curvature partially. k = 1: ducting.

#### 3.3 Sun paths from each sample (where the effective radius IS right)

The radiometric march needs, per sample, the transmittance toward the
sun and whether the sample is in the planet's shadow. Marching every
sun path is out of the question (NUM_STEPS × another march). Sun paths
that matter for refraction are near-horizontal (the terminator), and
for near-horizontal straight-line integrals Bislin's effective radius
R′ = R/(1−k) IS the right tool: the straight path against the enlarged
sphere has the same altitude profile as the bent path against the true
one. So per sample: k(h) = −R·G(h)·strength (clamped ≤ 0.9), R′ =
R/(1−k), centre shifted along the SAMPLE's nadir (tangent at the
sample), and the existing `density_integral` / ozone / shadow tests run
unchanged against (c′, R′). This replaces the psi driver's 0.0105
constant with the same law the view rays use, so the ground goes dark
at the same sun elevation the sky shows it setting.

#### 3.4 Closed forms (fast path and tests)

- Two-term tan law for apparent zenith angle z at an observer with
    refractivity N_obs and density scale height H:
    δ = A tan z − B tan³ z, A = N_obs(1 − H/R), B = N_obs(H/R − N_obs/2).
    57.3″·tan z at 15 °C (58.2″ is the 10 °C constant); 57″ at 45°, 3.5′
    at 15° elevation; within 0.5 % of the ODE above 10°.

- Bennett (all elevations, apparent altitude h_a in degrees):
    δ′ = cot(h_a + 7.31/(h_a + 4.4)) arcmin at 1010 hPa, 10 °C, scaled by
    (P/1010)·(283/T): 34.0′ at the horizon for 15 °C. It runs 2–3 % above
    the hydrostatic ISA model at every altitude (its fit carries the
    observed tables' excess), so it is a loose anchor (±3.5 %) and the
    panel readout's cross-check, not a render path.

- Dispersion (Ciddor at the project's 445/535/615 nm): N_B/N_g = 1.009,
    N_R/N_g = 0.995 → 0.5′ (≈ 30″: 33.38′ vs 32.87′ measured) red–blue
    split at the horizon: the green rim, and with a mirage fold, the
    green flash. The ratios are wavelength-only
    (Ciddor's dispersion factor is the same at every pressure), so
    G_λ(h) = G_g(h) · N_λ/N_g everywhere — one table serves three
    channels. The project's RGB sampling wavelengths
    (`SAMPLING_WAVELENGTHS_NM`) define the ratios; Young traces five
    (470/510/550/580/650 nm) and notes a real sunset spectrum has a hole
    near 600 nm from ozone and water vapour — our spectral T along the
    bent path carries that.

#### 3.5 Mirage regimes (Young's cases, the numbers we must reproduce)

| case | profile | observer | what happens |
|---|---|---|---|
| standard atmosphere | ISA lapse | any | green rim ≈ 4″ wide (Young: "not much greater than a 3.75″ scale bar"), most prominent with the sun at 1–2° altitude; invisible without ~20–30× magnification |
| inferior mirage (Ω sunset) | sea warmer than air; Young uses Monin–Obukhov similarity with L = −10 m | near sea level | the disc's reflected image joins the erect one ("feet"); the flash appears when the upper rim sinks to the join line, ~2 min after the feet form |
| mock mirage, weak inversion | +0.8 K between 30 and 50 m | 60 m (10 m above the top) | the lower limb flattens and pauses at the inversion top, then pops off as a blob; spikes on the upper limb become a green plume; observer MUST be above the inversion |
| mock mirage, ducted | +2 K over 50–60 m (ray curvature ≈ 2× the planet's → duct) | 70 m | rectangular then hourglass sun, prominent RED flash from the enlarged lower blob, hardly any green (extinction) |
| sub-duct flash | +15 K inversion, base 200 m, top 250 m (duct base ≈ 130 m) | 100–136 m, BELOW the duct | the biggest direct flash: a triangular green flash lasting 2–3 s (≈ 3× normal); 3 m of eye height changes everything |

Consequences for the design: (a) the profile needs an ELEVATED
inversion (height, thickness, ΔT), not just the surface layer;
(b) the table must resolve 10–50 m thick layers at 30–250 m: 512
entries (cells ≈ 1.2 m at 50 m); (c) the camera altitude is already
float64-exact (`cl_ground.z`) — the 3 m sensitivity is real physics,
not a precision problem; (d) Wegener's split — refraction ABOVE eye
level is the same for rays at ±el around the astronomical horizon, only
the structure BELOW the eye differentiates them — is a free
integrator test (§7); (e) Young's inferior mirage uses a logarithmic
(Monin–Obukhov) surface layer whose gradient diverges toward the
surface; our ΔT·exp(−h/L) layer is the first shape, the M-O form can be
a later profile option with no shader change.

### 4. Architecture {#refraction-4-architecture}

    CPU  core/refraction.py         profile bake: T(h) + hydrostatics + Ciddor N0
           │                         → G[256] on an asinh-warped altitude axis
           ▼
    UBO  rf_cfg, rf_cfg2, rf_shim, rf_disp, rfg[64]      (+272 floats, +1 KB)
           │
           ▼
    GLSL shaders/atmosphere_15/atmosphere_refraction_lib.glsl
         pa2RefrG(h)                 table fetch (all passes)
         pa2RefrTrace(ro, rd, …)     full geometric walk → end kind, s_end, p_end, d_end, β
         pa2RefrAdvance(state, s)    incremental provider: position/direction at arc length s
         pa2RefrShimmer(rd, phase)   sky-fixed noise tilt of rd
         pa2RefrSunSphere(h, û)      per-sample (c′, R′) for sun paths
           │
           ├── rect AIR pass (sky_driver.glsl): segment end + ground verdict from Trace;
           │     radiometric samples walk the path via Advance; sun paths via SunSphere
           ├── rect CLOUD pass + inline cloud arm: KSA march positions via Advance;
           │     2-D deck crossing from Trace
           ├── rect BG / ground compose (ground_compose.frag): Trace → ground hit point
           │     + arrival direction; sky texels → celestials at (p_end, d_end)
           ├── psi MS driver (equirect lighting): SunSphere only (no view bending)
           └── equirect / lib passes: PA2_REFRACTION pinned 0 (straight rays)

#### 4.1 The profile table (CPU → UBO)

- Bake: `refractivity_profile` (stage 0: non-uniform grid from 5 cm at
    the surface to 50 m aloft, hydrostatic pressure through
    `temperature_profile_isa_k` — ISA layers anchored to the scene's
    surface temperature, plus the ground layer and the elevated
    inversion; N₀ from Ciddor) →
    G(h) = (dn/dh)/n resampled onto 512 texel centres of
    u = asinh(h/h₀)/asinh(h_max/h₀), h₀ = min(1 m, L/2), h_max = 100 km.
    The asinh knee resolves the surface mirage layer (≈ 60 entries in
    the first 2 m for h₀ = 1 m), elevated inversions (cells ≈ 1.2 m at
    50 m, 6 m at 250 m — Young's 10–50 m layers get 4–8 cells) and still
    gives ~1 km spacing at 50 km; G is 1e−13 /m at the top (inert).

- The temperature model gains the elevated inversion:
    T(h) += ΔT_inv · smoothstep over [h_inv, h_inv + w_inv] (a tanh
    ramp; the hydrostatic integration makes it a duct automatically when
    the layer's ray curvature exceeds the planet's).

- Packed 4 entries per vec4 into `rfg[128]`; the shader fetch is two
    vec4 reads + a one-hot `dot(v, vec4(equal(...)))` select (no dynamic
    component index — Metal-strict) + linear interpolation.

- Below h = 0 the table clamps (bottomless / below-surface cameras get a
    constant bend, no NaN). Above h_max: 0.

- Key: (T, P, RH, CO₂, ΔT_ground, L, h_inv, w_inv, ΔT_inv, planet
    radius). The camera altitude is NOT an input any more — the old LUT's
    hysteresis dance (`ensure_refraction_lut`, flicker while flying) goes
    away with the altitude dependence. Re-bake cost: ~1 ms numpy.

- No image datablock: the table is 2 KB of UBO floats. Retires
    `PA2_REFRACTION_LUT`, its per-tick ensure, the image-churn mark and
    the Remove-Atmosphere cleanup.

- Why a UBO table and not a texture: no new sampler slot in five shader
    builds (the undeclared-sampler → Vulkan OOB class), no binding
    plumbing, and the fetch is two uniform reads. If the UBO ever gets
    tight, the same table fits a 256×1 R32F texture.

- Why not analytic in the shader: N(h) needs the hydrostatic pressure
    integral through the fit-shaped T(h) (no closed form), and the sky's
    own Rayleigh density (exp(−h/Hr), viewer-derived Hr) is the wrong
    profile for bending at the 20 % level (k = 0.21 isothermal vs 0.17
    with the lapse). The two density models stay separate on purpose:
    radiometry is untouched; refraction takes its own exact profile.

#### 4.2 The integrator (`refraction_lib.glsl`)

Frame per ray, built once at the start point p₀ (camera inside the
shell, else the shell entry): û₀ = normalize(p₀ − C), ê = the unit
horizontal component of rd in the ray plane, n̂ = û₀ × ê. Reconstruction:
û(φ) = cos φ û₀ + sin φ ê; p = C + (R+h) û(φ); d = cos z û(φ) + sin z ê(φ).
Rays within 0.05° of the zenith/nadir never enter the integrator (fast
path). Integrating (h, φ, z) instead of a world position keeps the
state small (fp32 h has cm resolution at 100 km; φ ULP is 0.4 m at
4000 km) and avoids the |ro − C|² − R² cancellation the codebase
already fights with `pa2CamSphere`.

Sub-step (RK2 midpoint = Bislin's rotate-half / step / rotate-half arc,
exact for constant curvature):

    z_m = z − ½Δs · sin z · (1/r + G(h))
    h_m = h + ½Δs · cos z,  G_m = G(h_m),  r_m = R + h_m
    h  += Δs · cos z_m
    φ  += Δs · sin z_m / r_m
    z  −= Δs · sin z_m · (1/r_m + G_m)
    β  −= Δs · sin z_m · G_m
    s  += Δs

Crossings inside a step are solved analytically, not by bisection: with
h(σ) = h + σ cos z + ½ σ² sin²z (1/r + G) the ground (h = 0) and the
shell top (h = h_top) are a quadratic in σ — this is the effective
radius applied per step, where it is exact. Ground hits report the
crossing σ, the hit point and the arrival direction; the ground test is
skipped when the bottomless bit (cl_uflags bit4) is set.

Step schedule — deterministic, never jittered, so neighbouring pixels
and successive TAA samples walk the same schedule and integration error
is a smooth field, not noise:

    Δh_max = c_h · h_cell(h)                   h_cell = the table's local cell height
    Δs = min( Δs_max,                           40 km cap
              Δh_max / max(|cos z|, ε),         altitude-change limiter
              sqrt(2R · Δh_max),                planet-curvature limiter (horizontal rays)
              c_θ / max(|G| sin z, ε) )         bend-per-step limiter, c_θ = 3e−4 rad
    Δs = max(Δs, 2 m)

c_h = 4 cells (Normal), 2 (High/NASA), 8 (Low). Because the asinh axis
already encodes both scales (the mirage layer near the ground, the
scale height aloft), "four cells per step" is a sound altitude limiter
everywhere. Expected sub-step counts per trace: 40–80 typical, ~120 for
a ground horizon ray (1300 km to the shell exit), ~60 for an orbital
limb ray, 20–40 with a strong mirage layer.

Termination: GROUND, EXIT (h ≥ h_top ascending), CAP (s ≥ 4000 km,
bottomless only). Outputs: kind, s_end, p_end, d_end, β, plus s_deck
(first crossing of the 2-D cloud deck altitude, or INF).

##### 4.2.1 Revision 2026-09-06: the end-step clip and Simpson

A per-step comparison of the Normal-tier walk against a 12,000-step
reference (one horizon ray, standard air, eye 2 m) tracked to 0.1″
until the last step and then lost 6.5″ and 180 m of path there: the
shell-top exit was a linear clip (h_top − h)/(h_new − h) using the
full 40 km step's midpoint rate, whose elevation sits ~11 km further
along the path (1 % in sin el, 190 m of clipped length), and the commit
applied the unclipped midpoint rates to the clipped step. The clip
fraction varies with the ray, so the error jittered ±3″ between
neighbouring rays. Invisible in clear air; a duct (5 K over 10 m, eye
below it) maps 0.35° of apparent elevation onto 0.65′ of the sun's
disc — a 30× magnification that showed the jitter as 2′ horizontal
slices of the sun (user report, atmospheric_refraction2.blend). Now:
the top crossing solves the ground's quadratic h + σ cz + ½ σ² sz²
(1/r + g) = h_top (stable root), every clipped step recomputes its
midpoint rates, and the gradient across a step is Simpson's
(g₀ + 4 g_m + g₁)/6 with g₁ at the step's end (one more table read;
it halves the residual). Twin numbers (jitter = max second difference
of the exit elevation over 0.15′ samples, bias vs the reference):
standard air 13.6″/6.9″ → 1.3″/0.6″ at Normal, 0.2″/0.08″ at High;
the duct scene 0.69″ → 0.12″. Two rules that did NOT help, recorded:
refining the step where the table's G varies across a cell (it
refined only once inside the ramp) and a look-ahead RK2 error bound
(it re-phased the steps and doubled the jitter) — the error was never
in the gradient's averaging. Step budget 512 (was 256).

#### 4.3 Two APIs, no polyline storage

Consumers need two things: the END of the path (celestials, ground hit,
segment length) and positions ALONG it (radiometric samples, cloud
samples). Storing a polyline in registers (K knots × 6 floats) inside
the KSA march is the wrong trade; instead:

- `pa2RefrTrace` walks the whole path once and returns the end state.
- `pa2RefrAdvance(inout state, sTarget)` re-walks the SAME deterministic
    schedule incrementally: the caller's loop asks for monotonically
    increasing arc lengths and gets position/direction by linear
    interpolation inside the current sub-step. A 2-state window covers
    the KSA march's one-coarse-step refinement step-back.

- Cost: the geometric walk runs twice per air pixel (trace, then the
    fused radiometric walk), once per cloud-pass pixel, once per BG pixel.
    Each walk is ~60–120 sub-steps of ~40 flops + 2 UBO reads ≈ 3–6 kflop
    — against a radiometric march of 100+ kflop per pixel. Budget: ≤ 10 %
    on the air pass, negligible on the cloud pass, +20–40 % on the (cheap)
    BG pass. Most sky pixels never enter it (§4.4).

#### 4.4 Fast path (steep rays)

For |apparent elevation at the start point| ≥ el_fast (default 15°) the
path is not marched: rd is rotated once by the two-term tan law
δ(z, N(h_start), H) about a pivot at the ray's half-refractivity point
(s_half = H ln 2 / |sin el| from the dense end), then everything is
straight. Celestials get the exact astronomical refraction (≤ 2″ off
the ODE at 15°); the ground/cloud hit displacement error is metres
(19 m at 38 km for an aircraft looking down 15°). A 15°–18° blend band
between the two models hides the residual step. Cameras outside the
shell use the elevation at the entry point and N(h_top) ≈ 0, so steep
rays from orbit correctly get no refraction at all (a symmetric shell
crossing deflects nothing).

el_fast rides the UBO: sin(el_fast) = −1 makes every ray fast (the
Potato tier = "rotate once, then straight": celestials + horizon
consistent, no mirage, no limb lensing), +1 marches everything.

#### 4.5 Consumers, one by one

\*\*Rect AIR pass (`sky_driver.glsl`)\*\*

- Lines 283–318 (effective sphere) → `pa2RefrTrace`: seg.y = s_end,
    ground verdict = kind == GROUND, `pa2GroundKm` = s_end (arc length;
    the inverse-km lane and the fold gate keep their meaning), `pg`/`pAmb`
    = the bent hit point (SHADOW and INDIRECT evaluated where the ray
    really lands — the ground shadow walk, the caster taps and the scene
    lamps all take that point).

- `atmosphere_clouds` (the SS/MS loop, `atmosphere_cloud_march_lib.glsl:194`):
    `r = ro + rd*t` → `r = pa2RefrAdvance(t)`; the camera→sample optical
    depth becomes piecewise-analytic — `density_integral` over the
    straight sub-segment from the previous sample, accumulated (same call
    count as today's from-origin integral; the chord-vs-arc sagitta
    within one sample step is < 1 m). Sun paths via `pa2RefrSunSphere`
    (§3.3). The OPAC phase, per-ray today, is evaluated at three stations
    (entry/mid/exit directions) and lerped by t: the local direction turns
    by up to 1° along a horizon path and the aerosol forward lobe is
    sharper than that.

- Geometry cutout (`pa2TGeo`): scene meshes are straight-ray objects;
    the cut distance stays the straight t along rd and clamps the marched
    column at arc length s = t (arc ≈ chord to 1e−5).

- Airglow and the moon body-distance test take (p_end, d_end): beyond
    the shell the ray is straight from the exit state.

**Rect CLOUD pass and the inline cloud arm**

- `march_cloud_segment_ksa` (6 `ro + rd*t` sites) and
    `integrateCloudDensityAlongLight`'s START point take positions from
    `pa2RefrAdvance`; the light march itself stays straight (sun path).

- `pa2Cloud2DShell` intersects the deck at the trace's s_deck instead of
    the analytic sphere hit.

- The temporal resolve's centroid distance (km) is unchanged: arc ≈ chord.
- Cloud GEOMETRY does not bend — the bent ray samples the same world
    cloud field at bent positions. The old "clouds stay on the true
    sphere" exception disappears (it existed only because the effective
    sphere was a geometry hack).

\*\*Rect BG / ground compose (`ground_compose.frag`, 1:1)\*\*

- Lines 810–840 (effective sphere) → `pa2RefrTrace`: tg = s_end (arc
    length), the hit point drives the chart/height/water lookups, the
    arrival direction d_end drives Fresnel/GGX/`refract()`; sky texels
    evaluate `pa2RectCelestials(p_end, d_end, thetaPix)`. The moon picks
    up the real parallax of the displaced exit point (≤ 0.75′ for a
    horizon ray; physical).

- The terrain heightmap walk (`earth_terrain_height`) marches the same
    provider — looming mountains for free (stage 2b).

- The fold gate (SHADOW.a = the air pass's verdict) is unchanged in
    meaning; both passes run the same deterministic walk, so the verdicts
    agree up to the existing fractional-air resampling.

- `_ground_fold_cpu` (equirect render fold) drops its refraction block:
    the equirect is straight (role law).

**Equirect / lighting builds**

- `PA2_REFRACTION` pinned 0 in every non-rect build (the lib-pass pin
    list in `sky_luts.py:350`, the draft/phase compute builds); the stage F
    lighting tier zeroes `rf_cfg.x` on the float list (replaces the
    `cl_skew2.y` zeroing in `_apply_lighting_tier`).

- The psi MS driver keeps `pa2RefrSunSphere` (k(h) per sample) so the
    lighting terminator matches the visible one; the psi bake key already
    rides the refraction toggle (d0723dd).

#### 4.6 Shimmer (stage 4)

- Model: a small time-varying tilt of the initial direction,
    rd′ = normalize(rd + A · (n₁ t̂₁ + n₂ t̂₂)), t̂₁/t̂₂ = the tangent basis
    at rd. Sampling a 3-D field ON the unit sphere (at rd · S) gives an
    isotropic angular correlation 1/S with no seams or poles; the pattern
    is sky-fixed (pans with the camera, magnifies with zoom).

- Noise source = the EXISTING 3-D turbulence volume (user 2026-09-03:
    "no new samplers, reuse"). `uCloudTurb3D` is a 65³ RGBA16F periodic,
    divergence-free curl-noise vector field (2-octave value-noise
    potential, pre-baked `_TURB3D_NPY`, loaded independently of the cloud
    toggle, wrap-padded for seamless trilinear filtering via the
    (t·N + 0.5)/(N+1) remap — `sampleCloudTurbulence3D`). ONE trilinear
    fetch at p = rd · S gives a smooth 3-vector; its tangent projection is
    (n₁, n₂). Curl fields have no sources, so the tilt field reads as
    ripples rather than blobs — closer to real index fluctuations than
    value noise, and ~12× cheaper than the procedural fBm it replaces. A
    periodic 64-cell volume cut by a sphere of radius S ≈ hundreds of
    periods never shows its tiling: every pass through the lattice is at
    a different phase. `S` maps the Shimmer Scale (arcmin) to volume
    periods through the potential's cell count.

- Bindings: the air and cloud passes already declare the volume
    (`_CLOUD_AUX_SAMPLERS`); the BG/ground compose does not, and it is
    where shimmer shows most. It gets the SAME texture object on its free
    slot 23 — no new texture, one new declaration + bind in
    `_rect_ground_draw` / `_rect_background_rt`. The zero-binding
    alternative is the procedural noise (option B, not preferred).

- Drift v1 = rigid translation of the periodic volume: p = rd · S +
    V · t / d_ref with V a CONSTANT world-space velocity (m/s) and d_ref
    a fixed reference distance (2 km). The tangential part of V moves the
    pattern, the normal part evolves it (boiling) — both from one
    constant vector, no per-ray projection, and a rigid translation
    never shears the field, so no phase crossfade is needed. v1 exposes
    ONE knob: Updraft (m/s, default 1) → V = (0, 0, w_up)·up_world: the
    slow upward creep of heat haze (1 m/s at 2 km = 1.7′/s), on every
    ray, with the pattern boiling as it rises. Time = scene time.

- POSTPONED (user 2026-09-03: "let's postpone it, add into the doc"):
    wind-map-driven drift. Spec, ready to slot in: the CPU samples the
    clouds' georeferenced wind map (`uCloudWindFlow`, shipped GFS default
    when empty, decoded east/north in [−1, 1]) ONCE per bake at the
    camera's lat/lon (from orbit: the sub-camera point), scales it by a
    "Surface Wind" knob (m/s at full map value, default 10), converts
    (u, v, w_up) to world space with the scene's east/north/up at the
    camera and writes V to `rf_wind` — still a constant per bake, so the
    rigid-translation drift above absorbs it unchanged. Taylor's
    frozen-turbulence hypothesis then gives the boil RATE for free: a
    10 m/s crosswind at 2 km moves a 3′ pattern 17′/s, i.e. ~6
    replacements per second (the observed 5–10 Hz boil); along the wind
    it crawls, crosswind it races. Needs: the map read + ENU→world on the
    CPU, the wind-map selection in the state key, one property. NOT in
    scope even later without a reason: per-pixel map fetches inside the
    helper (spatially varying drift across an orbital limb; a per-ray
    Ω(rd) = (V − (V·rd)rd)/d_eff(rd) would then shear the field and
    need the two-phase flow-map crossfade) and camera motion through the
    turbulence (aircraft, ISS).

- Amplitude: A = a₀ · shimmer · δ_fast(el, h_cam)/δ_horizon, i.e. ∝ the
    ray's own astronomical refraction, from the pre-trace closed form
    (§3.4). a₀ = 1′ at the horizon → 2″ at 45° (real seeing), 3′-scale
    ripples around a 32′ disc when zoomed in. From orbit A follows the
    straight ray's perigee altitude (exp(−h_p/H)) so limb stars shimmer.
    The wind does NOT drive the amplitude: turbulence strength is mostly
    surface heating (calm air over hot ground boils the most), so
    strength stays on the shimmer knob and the Ground Temp Offset.

- Applied INSIDE the shared helper, before the trace, so the air pass,
    the cloud pass and the BG/ground compose see the same tilt: a tilt
    applied only to the BG pass would break the fold gate at the horizon
    line (a shimmered BG ray landing on ground the air pass called sky —
    the exact seam the gate exists to prevent). The ground hit inherits
    it: heat haze on distant terrain and water, rising with the updraft.

- Time = SCENE time. A static viewport is a frozen ripple field that
    converges under the rect TAA and the BG film; playback and F12
    animations boil deterministically. Wall-clock shimmer is a non-goal
    (non-deterministic renders, permanent TAA rejection).

- Skipped when A < 0.1 · thetaPix (wide FOV: the sub-pixel warp is
    invisible; the volume is bandlimited so it never aliases).

- Cost: one trilinear fetch + a tangent projection, only where it
    matters.

##### 4.6.1 Revision 2026-09-06: two parts, both inside the walk

User verdicts on the first build: the world-space tier at Eddy Size
3000 m "looks more like what I see in nature", the small shimmer "just
looks weird", and the near shimmer "needs to be part of the refraction
pipeline, not an overlay post-fx glass filter over everything — like
1 km long from the camera". Two parts, both kicking inside
`pa2RfPrepare` of the TRACE walk (the providers keep the smooth path):

- **Temperature masses — RETIRED the same evening** (user: "do we need
    the air masses now that we have waves? the waves do their job").
    Three forms were built and measured in one day: a gradient scale
    (1 + A n) of the local table value (tore a duct's fold), a fraction
    of the standard surface gradient at fixed stations, and a stratified
    TEMPERATURE field δn = N δT/T kicked by its transverse gradient at
    fixed stations (Thickness × Aspect cells in the camera's up frame).
    With the real volume, 2 K over 3 km moved the horizon 0.12′ sideways
    and 0.01′ vertically; the arcminute boil is the near field's and the
    stacked, rippled images are the layer waves' (§4.7.2). Two laws
    survive: nothing inside the walk may change the step SCHEDULE per
    ray, and no world field may be point-sampled per sub-step — fixed
    stations only. The lanes `rf_shim2.x/y/w` are free.

- **The near shimmer** (the small, fast part): N = 8 stations at fixed
    arc lengths (i + ½)·L/N along the first L = 1 km of the ray; every
    station inside a sub-step is kicked from it, the schedule itself
    never changes (capping the sub-step at L/N re-phased the rest of the
    walk per row — 8 to 40 capped steps depending on elevation — and a
    duct's 30× image compression showed the walk's phase-dependent
    residual as bands again: twin 0.12″ → 1.68″ with a ZERO field). Each
    station kicks the direction by the transverse GRADIENT of the field's
    x channel (central differences over ±1/24 period — a quarter fine
    cell — along the in-plane and out-of-plane normals: curl-free, as the
    angle of arrival through a phase screen is; the curl components
    swirled the image like wavy glass), with N kicks of A/√N summing to
    the amplitude A = min(A₀, A_H·N_cam·tan z) (the one-term tan law
    clamped at the horizon: 1′ there at amount 1, 2″ at 45°, skipped when
    sub-pixel). The eddy = Scale × L, so the far end of the field shows
    the Scale and nearer air coarser, slower waves — the "view-aligned
    layers summing to an fBm" for free. Positions are CAMERA-relative in
    the walk plane's own terms ((h − h₀) − (R+h)φ²/2 along u₀, (R+h)φ
    along e₀): the world position has half a metre of fp32 resolution at
    earth scale against 0.87 m eddies, which snapped neighbouring rows to
    different cells (horizontal hair on the limb); kicking at every
    sub-step instead of fixed stations did the same. Time: the field
    rides the updraft and slides along world X at the Boil rate (Hz / 12
    periods per second — the value noise decorrelates over half a fine
    cell). The out-of-plane kicks accumulate into ψ and its first moment,
    applied at the end (exit direction turned toward the plane normal,
    landing point slid by ψ·s − ψ_S). Steep rays (the fast path, |el| ≥
    15°) take none: 2″ of seeing at most. Star scintillation
    `pa2CelScint` in the rect compose: I → I·exp(σn − σ²/2), σ =
    0.8·amount·airmass (cap 1.5), a 3′ correlation between stars, three
    times the boil rate, chromatic by the dispersion split over 10″.
    Lanes `rf_shim` = (A/diff_rms, A_H/diff_rms, 1/period, time),
    `rf_wind` = (boil, σ₀, updraft, L), `rf_cfg3.zw` = (1/σ_vol, diff_rms).

- **Default amount 1 → 0.3.** The probe view (`probe_shimmer_view.py`,
    the low sun's limb from the rect's B plane) showed the real fault of
    the first build: 1′ RMS tilt over 3′ cells gives dt/dθ ≈ 1 and the
    mapping folds — the sun tore into detached blobs. At 0.3 (20″) the
    edge is wavy and whole; the walk-integrated field at amount 1
    deforms the disc strongly but no longer tears it.

##### 4.6.2 Heat blur (2026-09-06)

User: "the heat shimmer in real world more like blurs the air, not
displaced like a single glass sheet ... i want it to look more like the
heat blur" (a telephoto video of a low sun: a fluffy, boiling disc, its
edge smeared rather than bent). A single ray per pixel through a single
field realisation IS a glass sheet. Two physical facts turn it into
blur: (1) Kolmogorov's angle-of-arrival spectrum puts the larger share
of the tilt variance below the field's finest cell — with l^(-1/3)
weighting, the band from the inner scale l₀ ≈ 5 mm up to the finest
cell l_c against the band the field resolves (l_c to its period, N
cells): σ²_sub/σ²_res = [l₀^(-1/3) − ⟨l_c^(-1/3)⟩] / [⟨l_c^(-1/3)⟩ (1 −
N^(-1/3))], with ⟨l_c^(-1/3)⟩ = 1.5 (θ_c L)^(-1/3) the path mean of an
angular cell over the near field — 2.46 at 3′ over 1 km, N = 6; (2)
those eddies are centimetres and cross the line of sight hundreds of
times per exposure (and the aperture averages the rest), so the camera
never sees one realisation: it sees their distribution. The first
build drew that distribution by Monte Carlo — every film sample tilted
its ray by an independent Gaussian angle (blue-noise Box-Muller,
advanced per pass) before the trace, so the walk, its ground verdict
and the celestial all took the tilted ray — exact, and rejected the
same evening: "too noisy for use — add multiple heat haze layers on top
of each other TAA style". The blur is a convolution of the final image
I(r̂) in camera-direction space (I(r̂ + δ) averaged over δ), so it can
be drawn as a fixed quadrature instead of a random one: the BG compose
draws the discs N = 6..16 times (N ∝ σ/θ_pix), each through its own
tilt of the EXIT direction on a Gaussian-quantile spiral — radius σ√(−2
ln(1 − u_i)), u_i = (i + s)/N, golden-angle azimuths — equal weights,
the spiral's rotation and the quantile shift s advanced per
accumulation pass (golden-ratio sequences), so the film converges on
the Gaussian with no per-pixel noise and a single frame at the default
amount is already smooth (taps half a pixel apart). The starfield,
whose gather is the expensive part, is drawn once with its Airy PSF
widened to θ = √(θ_pix² + (2.3σ)²) (a Gaussian of σ, flux-conserving)
and composited under the taps' mean transmittance (`g_pa2CelSkipStars`,
`g_pa2CelBgT` in the celestial lib). Tilting the exit direction rather
than re-walking is exact wherever the mirage mapping has unit
magnification; a fold's compressed bands take the blur at their
compressed magnification (less than the eddies' true one) and the
horizon's cut of the disc stays sharp (the centre ray's verdict) —
re-walking every tap would be exact at N times the walk. Achromatic to
the 2 % dispersion of the tilt; the same sub-pixel gate and tan-law
clamp as the near field (`pa2RfNearAmp`). Not in the air pass (the sky
is smooth; the far ground's texture stays sharp — a known gap), not in
the LUT producers. Knob Heat Blur (default 1), lane `rf_shim2.x` =
Blur × ratio, CPU `shimmer_blur_ratio`. Per-λ shimmer, asked in the
same breath: the near kick is a gradient of n − 1, so the dispersion
re-walk now scales it by the wavelength's ratio — a 2 % effect; the
coloured fringe of the reference is the dispersion split displaced by
the ripple, which the walk already does.

##### 4.6.3 The shimmer on turbulence physics (2026-09-06, late)

User: "the heat haze shimmer is much better, but still needs some work.
can you think of a more physically accurate way to do it?" — then
"sounds good" to the plan below. The stand-ins of §4.6.1–4.6.2 (a
two-octave value-noise volume at one angular scale, a tan-law
amplitude, a frozen screen sliding at a fixed rate, and a Kolmogorov
band ratio for the blur) are replaced by the model the imaging-through-
turbulence literature reduces to (Fried 1966; Tatarskii 1971; Schmidt
2010, *Numerical Simulation of Optical Wave Propagation* §9; Chimitt &
Chan 2020, *Opt. Eng.* 59(8)): a tilt field with Kolmogorov statistics
plus a blur from the unresolved band, both driven by C_n².

- **The screen.** ψ = φ/k for a unit path integral I = ∫C_n² ds = 1
    m^{1/3}, so ∇ψ is the angle of arrival in radians per √I: the von
    Kármán PSD Φ_ψ(κ) = 0.207 (κ² + κ₀²)^{−11/6} e^{−κ²/κ_m²} (0.49·0.423:
    Fried's r₀^{−5/3} = 0.423 k² I in the κ form, over k²), outer scale
    L₀ = 2 m (κ₀ = 2π/L₀), inner scale l₀ = 5 mm (κ_m = 5.92/l₀),
    FFT-synthesised on 1023² texels of 8 mm (an 8.18 m period, periodic
    by construction), padded to 1024 with the wrap texel and written ×32
    into `uBlueNoise.y` — the reserved channel, so no new sampler (the
    fullest rect build sits at 30 of 32 slots). σ_ψ ≈ 0.34; the tilt is
    achromatic (φ ∝ k cancels).

- **The stations.** The same eight fixed stations over the first
    kilometre (the schedule law of §4.6.1 stands). Station i reads the
    screen on a cylinder of radius s about the camera, u = s·az, v =
    s·el in metres (az from the rect camera's forward, `cam2`, so the
    seam sits behind the camera), in its own turned (0.7 i rad) and
    offset (golden fractions of the period) window, so no two stations
    share a period; the kick = the central difference of ψ over the pixel
    footprint D = max(θ_pix s, texel) — the footprint-averaged tilt —
    × √(C_n²(h_i)·Δs) × the wavelength's refractivity ratio. Near
    stations give broad coherent waves, far ones fine detail:
    anisoplanatism for free.

- **C_n²(h).** The knob is C_n² at 2 m in units of 1e‑14 (calm night
    0.1, typical day 1, strong sun 10 = the default, hot road 100),
    falling as (h/2)^{−4/3} above a 0.5 m floor — free-convection
    similarity in the sunlit surface layer (Wyngaard, Izumi & Collins
    1971). The elevation dependence follows: a 10° ray leaves the layer
    in tens of metres and takes under a fifth of the horizon ray's I; a
    −1° ray hugging the ground takes stronger air.

- **Frozen flow.** Each station's window drifts with the wind at its
    height, the neutral log profile U(h) = U₁₀ ln(h/z₀)/ln(10/z₀), z₀ =
    3 cm: the component across the view streams the pattern sideways,
    the component along it slides the window on a per-station diagonal
    (new air replacing the slice — a 2-D screen cannot advect through
    itself, this stands in for it), and the updraft lifts it (read at
    p − v t, the sign law). The boil is the stations' differential
    motion. Knobs Wind (m/s) and Wind From (°, a compass bearing under
    the North Offset; the CPU folds it into an angle from the rect's
    forward, `_wind_angle_from_view`).

- **The blur.** Per axis, the eddies between wavenumbers κ₁ and κ₂
    leave the tilt variance π∫κ³Φ_φ/k² dκ = 1.95·I·(κ₂^{1/3} − κ₁^{1/3}).
    The band below the footprint, from 2π/D to κ_m, is the heat blur's
    variance, gathered at every station and — because a grazing ray
    stays in the surface layer for kilometres — along the far path below
    300 m at every walk step (its resolved remainder, arcseconds of slow
    wander from metre-scale eddies, is dropped). The trace hands the sum
    to the compose (`g_pa2RfBlurVar`), Heat Blur multiplies it, the taps
    of §4.6.2 draw it. Numbers: a grazing kilometre at C_n² 1e‑13 (I =
    1e‑10) has r₀ = 5.7 mm and λ/r₀ = 20″ FWHM; the band formula gives
    8.4″ σ below a 0.7 m footprint, the same figure; the horizon ray's
    full low path (the near field plus ~15 km of grazing air before the
    curvature lifts it) gives ~18″ σ; a hot road (1e‑12) five times that,
    the arcminutes of the reference video.

- **Stars.** The scintillation σ at the zenith is 0.8·√(C_n²/1e‑13)
    capped at 1.2, boiling at the wind's rate; the free-atmosphere
    profile (Hufnagel–Valley) for zenith twinkling is the open item.

- **Retired:** Amount, Scale, Boil; the tan law; the volume's
    difference RMS; `shimmer_blur_ratio`; `pa2RfNearAmp`, `pa2RfTurb`.
    Twin: `cn2_profile`, `tilt_variance_band`, `residual_tilt_variance`,
    `fried_r0`, `wind_log_profile`, `trace_ray_table(near=dict(cn2, …))`
    → `blur_var`; the screen's tilt RMS is checked against the band
    formula (`test_turbulence_screen`); `probe_refraction.py` section 5
    reads the GPU blur variance per ray.

- **Open:** deriving C_n² from the Ground ΔT knob through Monin–Obukhov
    similarity (a hot ground would then give the inferior mirage and the
    strong shimmer together); the aperture (a real lens averages the
    tilt below its diameter into the same blur); the along-view
    advection.

#### 4.7 Green flash: per-channel bending (stage 3)

- Everywhere: one walk (green); the exit direction per channel is
    d_λ = Rot(n̂, β · N_λ/N_g) · d₀ — exact to first order because the
    world direction changes only by refraction (§3.2). Ground and clouds
    are not split (a chromatic ground edge is invisible); only the
    celestial arm takes three directions.

- Horizon band (|el| < el_disp, default 3°, UBO) with dispersion on:
    three full walks with G scaled per channel. This is where the fold
    lives — the turning point n(h)·r = const sits at a different
    elevation per wavelength, which is exactly why the flash is green: the
    blue/green image of the upper rim folds while red has not (inferior
    mirage), or a green plume detaches from the strip (mock mirage), or a
    triangular green blob survives below the duct (sub-duct). A scaled
    rotation cannot represent that; three walks can.

- Gate by visibility: only when the R–B split |β·(N_B − N_R)/N_g|
    exceeds 0.1·thetaPix — at wide FOV the split is sub-pixel and the
    three walks are skipped. At 500 mm the 30″ rim is ~3 px.

- Extinction does the rest for free: the B plane is celestial × T with
    spectral T along the bent path (Young: optical depth ≈ 10 at 550 nm
    vs ≈ 9 at 610 nm on a horizon path — the aerosol slope that turns the
    rim from blue-green to green and, in ducts, kills the green entirely
    while the red flash survives).
    AS SHIPPED (audit 2026-09-06, prompted by mock-mirage sunset photos
    with dark bands across the disc): the BG pass multiplies the
    celestial sampled along the walked exit direction by the AIR pass's T
    plane at the pixel's apparent direction (`ground_compose.frag`,
    `gcAir1x`). What that plane holds depends on the sky: the analytic
    march samples T along the bent path per pixel; the default LUT sky
    takes the sky-view atlas, whose texels are walked (Phase 5) but whose
    rows above the horizon sit at 0.3′, 3′, 8′, 16′, 27′ and 40′ — a 1–3′
    mock-mirage strip's extra extinction is bilinearly smeared, and walked
    rays exiting below the geometric horizon take the horizon row's column
    (the 2026-09-06 white-band fix). So in the LUT sky only the folded-limb
    half of a dark band exists (§8).

- The folded limb: a mock-mirage band is a slice of the sun's edge, so
    the disc's limb law decides the band's darkness and colour. The port's
    grey 555 nm quadratic (the outer 2 % of the radius 1.5–2.5× too bright,
    no limb reddening) was replaced 2026-09-06 by the Neckel & Labs 1994
    5th-order polynomial per channel (615/535/445 nm: limb 0.38/0.32/0.22
    of centre, 1.76× redder than the centre), normalized to the disc mean
    — `sunrad` is the AM0 irradiance over the disc's solid angle, and the
    drawn disc had integrated to 0.776 of it (`pa2CelSolarLimb`).

- Cost: 3 walks on ≤ 5 % of the BG pixels at telephoto only, ~2–5 ms
    at 4K.

##### 4.7.1 Revision 2026-09-06: the spectral dither

Three fixed wavelengths are gone from the celestial arm. Where the
split shows (the same 0.1 px gate), each film sample draws λ ∈ [400,
700] nm from blue noise (`uBlueNoise.w`, the pass-advanced R1 shift the
caster jitter uses — bound at BOTH background-compose dispatch sites;
the first build bound it only in the ground draw, so every pixel of a
pass shared one wavelength and the sun swept through the spectrum),
walks it once with Ciddor's ratio N(λ)/N(535) (dry-air dispersion
shape; T, P, humidity cancel in the ratio, verified against the R/B
lanes to 5e−6) — the re-walk in the 3° band, the first-order rotation
elsewhere — and composites the celestial's RGB along that direction.
Two normalisations keep it honest: the colour-matching weight w(λ) =
S₅₇₇₈(λ)·max(sRGB(CMF(λ)), 0) over its per-channel mean on [400, 700]
(E[w] = 1: the disc's average colour is the three-band one), and the
transmittance T_sample = T(λ)·T_c / E_c[w_c T] with E_c the pixel's own
16-point mean — the film's mean image equals the band result exactly,
only the rims carry the spectrum. T(λ) from the three band values is a
piecewise POWER LAW (log T linear in log λ between the band points,
the end segments' exponents carried outward): a free quadratic in λ⁻⁴
bent back UP at the blue end whenever the bands were aerosol-laden
(log T is concave in λ⁻⁴ there), T(400) above T(535), and the sun
banded. The raw weights alone brightened a low sun 25 % and yellowed
it: the red lobe reaches 700 nm where the fitted T is far above the
615 nm band's. Cost: one walk per sample where three ran, plus ~40 exp
for the weights. Star scintillation (§4.6.1) and the sky in-scatter
stay three-band. Not done, on purpose: dithering the walk's step phase
(the per-ray error is 1″ after §4.2.1, the TAA jitter dithers the fold
edges, and a compose-only dither breaks the air-pass/compose walk
agreement).

##### 4.7.2 Mirage layer waves (2026-09-06)

User: "are the air masses added to the mirage layers? ... build the
layer undulation on the Mirage Layers block, the physical way". The
air masses add a temperature deviation on top of the profile but never
move the layers; the stacked, rippled images of real sub-duct sunsets
come from the inversion itself undulating under internal gravity
waves. Model: a wave train η(x, t) = A·[cos(k(x·d̂ − ct)) + 0.5·cos(1.7k
(x·d̂₊₂₅° − ct) + 1.9) + 0.3·cos(2.9k(x·d̂₋₃₅° − ct) + 4.1)] with k =
2π/Length, d̂ the Dir knob's horizontal direction (the camera's up and
a fixed horizontal pair seeded by world X, as the masses), and the
phase speed c = √(g'·z_base), g' = g·ΔT/T, from the inversion's own
strength and base height (a shallow warm layer over the ground: the
interfacial wave is non-dispersive, one c for the train; floors keep a
wave moving with no elevated layer). The profile above the ground layer
rides η: every table read of the walk takes h − η·smoothstep(5, 20, h)
below 2 km — the trace and the providers alike, so the air march and
the verdict agree; the LUT producers (PA2_RF_NO_TURB) keep the smooth
profile, as with the masses. One η per sub-step for its three reads.
Lanes: `rf_cfg2.w` = A (0 = off; the path cap became a constant),
`rf_shim2.z` = 1/Length (the masses' scale height became a constant),
`rf_wind.w` = c·t (the near field's length became a constant),
`rf_shim.y` = the direction (the horizon-normalised shimmer amplitude
is derived in-shader from `rf_cfg3.x`). Rect-only, in the shimmer key
(no table bake); scene time flows while A > 0. Twin: `undulation=
dict(field(s, h) -> η)`; `layer_wave_speed(ΔT, z_base, T)`.

**Revision 2 (the same evening): internal gravity waves.** User, in
three steps: "the wave undulations are more than just 3 waves, there
are the large masses and really small ones too", "since these are
gravity waves, lets implement gerstner wave summing with frequency and
amplitude like we do for water", then a derivation — internal gravity
waves as a vertical displacement ξ_z(x, z, t) = Σ Aᵢ cos(k_h,i·x + mᵢ z
− ωᵢ t + φᵢ) with ω = N k_h / √(k_h² + m²), the atmosphere evaluated at
z − ξ — "double check the math, references and lets implement".

*The math, checked.* (a) The dispersion relation is the Boussinesq,
non-rotating, no-mean-flow internal-wave relation: Gill, *Atmosphere–
Ocean Dynamics* (1982) §6.4–6.5; Nappo, *An Introduction to Atmospheric
Gravity Waves* (2002) §2.2; Sutherland, *Internal Gravity Waves* (2010)
§3.3. ω ≤ N, so periods are ≥ 2π/N (9 min at N = 0.012 s⁻¹); the
hydrostatic limit k_h ≪ m gives ω = N k_h/m, periods of tens of minutes
for the 20–200 km / 5–30 km waves seen from orbit. The non-Boussinesq
term adds 1/(4H_ρ²) under the root — 1 % for λ_z = 10 km, ignored. (b)
N ≈ 0.01 s⁻¹ in the troposphere, 0.02 in the stratosphere (Holton &
Hakim 2013 §2.7.3): N² = (g/T)(dT/dz + Γ_d), Γ_d = g/c_p = 9.8 K/km,
−6.5 K/km gives 0.0106. (c) T′ = −ξ (dT/dz + Γ_d) is the adiabatic
parcel displacement, right (Nappo §2.2, the polarization relations of
Fritts & Alexander 2003, *Rev. Geophys.* 41, eqs. 20–23). (d) "Evaluate
ρ_base(z − ξ)" is NOT: it is the passive-tracer form, right for
potential temperature, humidity and aerosol mixing ratio, but density
and temperature adjust adiabatically as the parcel moves through the
pressure field, so ρ′/ρ = ξ N²/g = −T′/T — the derivation's own T′
formula — which is g/(H N²) ≈ 10 times smaller than the ξ/H the warp
gives (100 m: 0.12 % of density, not 1.25 %). The snippet's `hWave =
height − displacement` for the Rayleigh density therefore overstates
the molecular effect tenfold; for aerosol, haze and humidity layers it
is right, and those are where the bands show. (e) For refraction, n − 1
∝ ρ, so free-air internal waves perturb the bending gradient by
(N²/g) m A ≈ 0.6 % of the standard gradient for A = 100 m, λ_z = 10 km,
alternating in sign along the ray — an arcsecond at the horizon,
invisible. Inside a sharp inversion the environmental gradient
dominates the adiabatic one (Γ_d against 40 K/km), so the profile warp
h − η the mirage layers use is within ~20 % of the exact adiabatic
displacement there, and is what moves the mirage. The tracer warp is
therefore kept for the layers (the pressure part of n̄(z − ξ) is the
remaining approximation) and documented; a Rayleigh/aerosol density
warp of the sky itself would be a separate feature (the LUT sky is
horizontally homogeneous by construction).

*Implemented.* `pa2RfWaveEta(pRel, e1, e2, h)` = six waves, horizontal
wavelength Length / 1.887ⁱ, amplitude A Gainⁱ, directions fanned ±0.45
i rad about Dir, phases 1.9 i, ONE vertical wavenumber m = 2π/Vertical
(the phase tilts with the read height h), ωᵢ = N kᵢ / √(kᵢ² + m²) with N
= `layer_brunt_vaisala(ΔT, thickness)` from the inversion's own lapse
(the ISA value with no layer). The user's Gerstner request survives as
the Steepness knob: Q > 0 adds the trochoid's horizontal orbit as a
stand-in for finite-amplitude steepening (Dᵢ = Q Aᵢ / Σ Aⱼ kⱼ, no loops
for Q ≤ 1, the lost Eulerian mean Σ Aᵢ Dᵢ kᵢ / 2 put back so Q never
moves the layer, two fixed-point inversions x₀ = x + D(x₀)); Q = 0 is
the linear sum exactly as proposed. Speeds: with Vertical 10 km the
3 km wave runs at 0.96 N — c = 19 m/s for the 0.8 K / 20 m layer, a
160 s period, ripples that visibly travel; Vertical 40 m gives the
trapped wave at N/m ≈ 0.3 m/s. Lanes: N on `rf_shim2.y`, m on
`rf_shim2.w`, gain + steepness packed on `rf_wind.w` (floor/1000,
fract), time from `rf_shim.w`; the c·t lane and the two-layer speed are
gone. Twin `gravity_wave_eta`; the GPU sum matches it to 2 cm on 5 m
waves (`probe_refraction.py` section 6).

**Revision 3 (the same night): 1-D along the up axis.** User: "the
gravity waves i think should be 1D - mapped to the planet's up axis"
(asked which reading: altitude only). The horizontal structure is no
longer drawn: ξ(h, t) = Σ Aᵢ cos(m h − ωᵢ t + φᵢ), evaluated for every
point along the ray at the camera's horizontal phase — the crest taken
as long across the line of sight — so the whole low profile rises and
falls with the wave and the stacked images of a sub-duct sun move
vertically rather than breaking up along the horizon. Each wave keeps
its own frequency from its horizontal wavelength through the dispersion
relation (with Vertical 10 km ≫ Length all six run near N and the sum
is one oscillation at ~N with slow beats; a short Vertical spreads the
periods and corrugates the profile vertically). Gerstner's steepening
reduces to the phase: one inversion step θ₀ = θ + Qᵢ sin θ with Qᵢ =
Q Aᵢ kᵢ / Σ Aⱼ kⱼ, ξᵢ = Aᵢ (cos θ₀ + J₁(Qᵢ)) — the one-step trochoid's
Eulerian mean is exactly −Aᵢ J₁(Qᵢ) (Jacobi–Anger), put back exactly at
every steepness, where the converged fixed point's −Aᵢ Qᵢ/2 had left
0.6 m on 5 m waves at Q = 1 (the cusp does not converge in two steps).
The Dir knob and its lane (`rf_shim.y`, free again) retired
with the horizontal coordinate; `pa2RfWaveEta(h)` and
`gravity_wave_eta(h, t, …)`.

**Revision 4: along the line of sight.** User: "the large gravity waves
undulations now dont seem to do much." They could not: a lift uniform
along the ray moves the whole low profile by one η(t), and a uniformly
lifted profile is optically the eye lowered by η — five metres out of
sixty changes a sub-duct sun very little. What restacks a mirage is the
layer height varying ALONG the path: a grazing ray crosses crests and
troughs over tens of kilometres and each part of the path bends
differently (the stacked, rippled bands of rev. 1 came from that). So
the wave travels along the line of sight, ξ(s, h, t) = Σ Aᵢ cos(kᵢ s +
m h − ωᵢ t + φᵢ) with s the distance from the camera: the displacement
stays vertical and one-dimensional in the sense the user asked for,
the crests run across the view — circles about the camera, which are
planes to any field narrower than a degree — and no direction knob
returns. Gerstner's steepening is then the trochoid along s. The
pattern moves with the camera (its origin is the camera), as the first
build's did; a world-fixed origin would need one more lane.
`pa2RfWaveEta(s, h)`, `gravity_wave_eta(s, h, t, …)`; the probe's
section 6 reads the GPU sum over 30 km of s. Two more things from the
same exchange: Vertical's default drops from 10 km to 200 m (at 10 km
the phase changed 0.03 rad across the layer, one more reason nothing
showed; at 200 m the layers compress and stretch by ±15 % for 5 m
waves, the direct lever on a mirage's gradients), and the amplitude
lane is held back so the sum's vertical strain Σ Aᵢ m (1 + Q) stays
below 0.8 — past 1 the warped profile h − η(h) folds on itself, an
overturning wave the table cannot represent (`wave_amplitude_guard`).

#### 4.8 Space views

- Camera above h_top: the trace starts at the shell entry (sa.x) with
    d = rd; the frame is built there. h_cam → h_top hands over
    continuously (sa.x → 0): no seam when flying out.

- Limb: straight-line perigee h_p → traversal bend ≈ 2·δ_horizon·
    exp(−h_p/H): 1.10° for a grazing ray, 0.41° at 10 km. Rays with small
    positive h_p bend down into the ground; the apparent limb is thinner,
    the setting sun seen from orbit squashes into the classic lens (the
    lower limb lifts ~1° more than the upper), stars within ~1° of the
    limb are compressed — all from the same walk, no special case.

- Ground seen through the limb lands at the bent hit point (displaced
    up to ~20 km along the surface at the limb; zero at nadir).

- The old LUT's limb row (`dev_space`) survives only as the test anchor.

### 5. Data, UI, keys {#refraction-5-data-ui-keys}

#### 5.1 UBO (appended after `lt[96]`, layout of every existing slot unchanged)

| lane | x | y | z | w |
|---|---|---|---|---|
| `rf_cfg` | strength (0 = off, 1 = physical) | N₀ = n₀−1 at 550 nm | sin(el_fast) | h₀ (table knee, m) |
| `rf_cfg2` | walk ceiling = the march's shell top (m) | asinh(h_max/h₀) | c_h (cells/step) | s_max (m) |
| `rf_shim` | a₀·shimmer (rad) | S (volume periods per rad) | scene time (s) | d_ref (m) |
| `rf_wind` | V_world.x (m/s) | V_world.y | V_world.z (v1: updraft × up; later: + map wind × s_w) | spare |
| `rf_disp` | N_R/N_g | N_B/N_g | sin(el_disp) (0 = dispersion off) | N(h_cam) (fast-path tan law) |
| `rfg[128]` | G(h) ×4 per vec4, 512 entries on the asinh axis | | | |

`_UBO_FLOATS` += 532. `cl_skew2.y` becomes a zeroed spare (its consumers
are all retired). Compile-time `PA2_REFRACTION` (pinned 0 off the rect;
1 on the rect builds) keeps the integrator out of lighting builds; the
USER toggle is `rf_cfg.x` (no recompile on flip — the recompile-from-UI
law).

#### 5.2 Properties (Atmosphere tab)

Existing, kept: `atmosphere_refraction` (default ON once stage 2 lands —
user call), `atmosphere_refraction_strength`,
`atmosphere_ground_temp_delta_k`, `atmosphere_ground_layer_m`.
New: `atmosphere_refraction_shimmer` (0..2, 1 = 1′ at the horizon,
default 0.3 since 2026-09-06), `atmosphere_refraction_shimmer_scale`
(arcmin at the far end of the 1 km near field, default 3),
`atmosphere_refraction_boil_hz` (default 4),
`atmosphere_refraction_mass_amount` (the temperature masses, default
1) and `atmosphere_refraction_mass_size_m` (default 3000),
`atmosphere_refraction_updraft` (m/s, default 1; the wind-map
"Surface Wind" knob joins it when the postponed drift lands),
`atmosphere_refraction_dispersion` (bool, default ON with refraction —
it costs nothing until the split is visible),
`atmosphere_inversion_height_m` / `_thickness_m` / `_delta_k` (default
0 = no layer) — the elevated inversion for mock-mirage, ducted and
sub-duct sunsets and for Fata Morgana; the table absorbs it with no
shader change. Presets for Young's cases as a small enum or preset
buttons ("Mock mirage 0.8 K @ 30–50 m", "Duct 2 K @ 50–60 m",
"Santa Ana 15 K @ 200–250 m") so the flashes are one click away.
Panel readout (label): "k = 0.17 · horizon 34.4′" derived from the
table — the number people can check against a textbook.

#### 5.3 Keys, presets, tiers

- `_state_key` already carries the toggle and strength; add the shimmer,
    updraft, dispersion and inversion knobs (the wind-map selection joins
    when the postponed drift lands — it is already keyed for the clouds).
    The shimmer TIME rides the animation-time lane (like `_cloud_time_s`):
    frame changes re-march, static views do not.

- Quality presets own c_h and el_fast: Potato sin(el_fast) = −1 (fast
    path everywhere, shimmer off), Low c_h = 8, Normal 4, High/NASA 2.

- The status readout gets a "refr n/px" profiler tag (mean sub-steps).

#### 5.4 CPU

- `core/refraction.py`: keep `temperature_profile_k`,
    `_refractivity_profile`, `_integrate_bend` (the reference ODE, tests +
    readout); add `refraction_profile(sun_props, radius_m)` → (G[256],
    h₀, h_max, N₀, k₀, δ_horizon) with a raw-parameter cache; delete
    `ensure_refraction_lut`, `_fill_grounded`, the LUT constants, the
    `celestial_math.py:1341` call, the `operators.py:340` cleanup.

- `sky_params.py`: `_refraction_boost` → retired; `_refraction_rows()`
    fills the new lanes; `_apply_lighting_tier` zeroes `rf_cfg.x`.

- The managed sun lamp (lights straight-ray meshes): its elevation is
    lifted by Bennett's δ(P, T) so it stays on until the APPARENT sun
    sets, matching the sky. The march itself never sees a lifted sun.

### 6. Stages {#refraction-6-stages}

Each stage ships alone; the branch is `celestials-rect`.

0. **Prep** — stop baking the dead LUT (image, ensure, cleanup); keep the
   ODE as the numpy reference; add the ODE anchor tests (§7). Small.
   DONE 2026-09-03, committed a36ca04 (changelog entry in 1862e39):
   `core/refraction.py` rewritten as the
   reference (ISA profile + surface layer + elevated inversion, RK2
   planar walk, closed forms, `release_legacy_lut`); the ensure call in
   `celestial_math.py` releases the legacy image's fake user instead of
   baking; 13 tests in `RefractionReferenceTests`, suite 68/68 green in
   1.1 s. Finding: the sky's fit-shaped T(h) under-refracts (§3.1), so
   the reference — and the stage-1 table — use the ISA lapse.

1. **Integrator + air + BG** — profile bake → UBO lanes → `refraction_lib.glsl`
   (G fetch, Trace, Advance, SunSphere, fast path) → the AIR pass
   (segment end, ground point, fused radiometric walk, per-sample sun
   sphere, 3-station phase) → the BG/ground compose (celestials at the
   exit state, ground hit, arrival direction). Retire the four
   effective-sphere copies and the psi constant. Interim known
   artefact: clouds still ride straight rays, so a deck reaching the
   horizon sits ~34′ low against the lifted sea until stage 2.
   DONE 2026-09-03 (uncommitted). As built: the library is
   `shaders/atmosphere_15/atmosphere_refraction_lib.glsl` (inside the
   atmosphere blob so the march lib can include it; the compose
   includes it across the blob boundary) with the walk in a
   prepare/commit pair shared by the trace and the incremental
   provider; the walk state keeps the ELEVATION, not the zenith angle
   (fp32 precision on grazing rays); the aerosol phase is a per-sample
   ratio (the start and exit-direction stations interpolated in
   cos θ) instead of a 3-station lerp in t; the driver hands the walk
   to `atmosphere_clouds` through globals (its signature is shared by
   every lib pass). UBO: `rf_cfg2.x` carries the march's shell top (the
   walk ceiling), not h_max. Verified by `scripts/probe_refraction.py`
   (windowed Vulkan run — Windows has no GPU context in --background):
   every rect build compiles with the walk (frag + compute, sky + cloud
   pass, both compose variants); a compute kernel running
   `pa2RefrTrace` on 256 rays across the horizon band matches the
   numpy twin on the SAME lanes — kinds 256/256, bend ≤ 0.72″, path
   ≤ 5e−4, end altitude ≤ 1 m; the apparent dip from a 6 m eye is 4.24′
   against 4.70′ geometric; strength 0 lands on the analytic chord. Unit
   suite 74/74 with `RefractionTableTests` (twin vs reference: horizon
   ≤ 20″, 45° ≤ 1″, dip ≤ 2″, limb ≤ 0.02°, mirage fold ≤ 1.5′). Also
   fixed on the way: `_CEL_ANCHOR` had drifted from the driver's
   coverage-mix rename (the Metal/CPU-publish with-B build could not
   compile at HEAD). Field verdicts pending.

2. **Clouds + the rest of the ray owners** — KSA march + inline arm on
   Advance, 2-D deck via s_deck, terrain heightmap walk, airglow and
   moon occluder from the exit state, psi driver SunSphere, sun-lamp
   apparent elevation, `_ground_fold_cpu` cleanup.

3. **Green flash** — per-channel exit rotation everywhere, three walks
   in the horizon band gated by the visible R–B split, the elevated
   inversion in the profile bake, Young's case presets. Acceptance =
   Young's four sunsets (§7).
   DISPERSION DONE 2026-09-03 (user: "can you add spectral response?";
   uncommitted). As built: `rf_disp` = (N_R/N_g, N_B/N_g, sin 3°, N(h_cam))
   with the ratios from Ciddor at the march's 615/535/445 nm and the
   scene's T/P/RH/CO₂ (0.9951 / 1.0093 standard); a per-walk scale
   `g_pa2RfGScale` on the table fetch (and on the fast path's ΔN) so
   one table serves every channel; `pa2RefrDisperseDir` rotates green's
   exit by β·(N_λ/N_g − 1) about the ray plane's normal — the fast
   path now reports its rotation as β and both branches set the plane
   axis; `pa2RectCelestialsRGB` evaluates the celestial arm once per
   channel only where the R–B split exceeds 0.1·θ_pix (a landed channel
   is occluded). The compose re-walks R and B in the |el| < 3° band on
   EXIT rays (the fold sits at a different elevation per wavelength);
   the render/CPU-publish splice uses the rotation only. Ground and
   clouds stay green. Property `atmosphere_refraction_dispersion`
   (default ON; it costs nothing until the split is visible).
   Measured (probe, 256 horizon rays): the blue re-walk bends 1.0100×
   green against the 1.0093 lane — the more-refracted path sits deeper
   in dense air, a real 7 % second-order excess; the first-order
   rotation matches the re-walk to < 3″ outside a fold. Suite 75/75.
   PRESETS + TOGGLES DONE 2026-09-03 (user: "add these presets - and the
   refraction settings needs its own tab inside the atmosphere tab in
   UI ... make all the refraction features togglable, so if everything
   is disabled, it runs fast"): the elevated inversion rides three
   properties (`atmosphere_refraction_inversion_height_m /
   \_thickness_m / \_delta_k`) driven by an enum preset
   (`atmosphere_refraction_inversion_preset`: None, Mock Mirage +0.8 K
   30–50 m, Duct +2 K 50–60 m, Sub-duct / Santa Ana +15 K 200–250 m,
   Custom) whose update writes the layer into the values; the bake
   reads them through `scene_refraction_inputs`, which also carries the
   new **Mirage Layers** toggle (`atmosphere_refraction_mirage`, default
   off: the surface layer and the inversion are ignored → the clean ISA
   profile). Feature toggles: **Ray March** (`_march`, default on; off =
   sin(el_fast) = −1, every ray takes the one-rotation fast path, no
   walk anywhere, the world shimmer tier falls back to the sky tilt,
   the mirage block greys out), **Mirage Layers**, **Shimmer**
   (`_shimmer_enabled`), **Dispersion**. The fast path is now capped at
   the horizon refraction scaled by the ray's refractivity share
   (`rf_cfg3.x` = δ_horizon; `_UBO_FLOATS` +4), so it is valid at every
   elevation, and `pa2RefrSunSphere` returns the true sphere without a
   table fetch when the strength is 0 — with the master off nothing
   refraction-related runs per sample. UI: the toggle is followed by a
   boxed group (Strength, Ray March, Mirage Layers → Ground ΔT / Layer /
   Inversion preset + Base / Thick / ΔT, Shimmer → Amount / Scale /
   Eddy / Updraft, Dispersion). Tests: `test_feature_toggles`,
   `test_inversion_presets` (real scene props); suite 77/77, probe
   46/46.

4. **Shimmer** — the turbulence volume sampled on the sphere (one
   fetch; the compose binds the existing texture on slot 23), rigid
   updraft drift on `rf_wind`, amplitude law, time lane, knobs, cutoff.
   Wind-map drift stays postponed (§4.6) until asked for.
   DONE 2026-09-03 (pulled ahead of stage 2 by the user; uncommitted).
   As built: `pa2RefrShimmer` in the refraction lib, called by the air
   pass and the compose right before the trace (the tilted direction
   feeds the walk, so the ground hit and the exit pose both carry it);
   the amplitude law is the ONE-term tan law N·tan z clamped at the
   horizon value — the two-term form's cubic goes negative past ~85°
   and zeroed the shimmer exactly at the horizon in the first probe;
   lanes `rf_shim` = (A/RMS_volume, A/(RMS·δ_horizon), S = 1/(scale ×
   6 fine cells), scene time) and `rf_wind` = (0, 0, updraft, 2 km);
   the compose gets `uCloudTurb3D` on slot 23 in both builders, bound
   at all three dispatch sites; three properties (Shimmer, Scale ′,
   Updraft m/s) on the Atmosphere tab; the state key carries the knobs
   always and scene time only while the shimmer animates (`with_time`).
   Measured (chord metric, 256 horizon rays): in-kernel tilt 1.41′ RMS
   total = 1.0′ per axis at amount 1; the exit direction moves 0.99′
   RMS (the refraction gradient damps the input tilt by ~0.7); t = 4 s
   vs t = 0 differ by 1.56′ RMS (decorrelated), and with the updraft
   zeroed the two are bit-identical. Metric trap recorded: acos(dot) on
   fp32 unit vectors has a 1–2′ floor; small angles are chords.
   Equirect fold: the compose's walk (and so the shimmer) is gated to
   rect mode (`sz.z`) — the equirect never bends.
   HIGH TIER, world-space (user 2026-09-03: "this is good for low tier,
   make the high tier, where the shimmer is sampled in world space").
   Presets HIGH / EPIC / CUSTOM (`_shimmer_world`): the turbulence is a
   refractive-index FIELD in space — the same curl volume, now indexed
   by the sub-step's world position over a period of 6 × Eddy Size
   (new knob, metres, default 20) plus the updraft drift — and every
   sub-step of the TRACE walk kicks the direction by
   A_step·√ds·exp(−h/H_T)·v (H_T = 1 km; a random walk whose variance
   is step-size independent, so quality tiers agree statistically).
   The in-plane component turns the walk itself (`el`), so a boiling
   horizon can land or escape a ray (the probe sees kind flips at the
   dip); the out-of-plane component accumulates into ψ and its first
   moment, applied at the end as an exit-direction turn toward the
   ray plane's normal and a sideways landing offset ψ·s − ψ_S. Eddies
   smaller than the pixel footprint at the sample average out
   (foot = min(1, L/(θ_pix·s))): no far-field grain. The provider
   walks (SS/MS samples) skip the field — metres apart, invisible —
   so the cost is one fetch per sub-step of the trace, and only below
   8·H_T (≈ the first 30 sub-steps of a horizon ray). Calibration:
   A_step = A₀/(σ_vol·√D_eff), D_eff = √(π R′ H_T)/2 with R′ =
   R/(1−k₀), so a surface horizon ray accumulates 1′ per axis at
   amount 1; the twin sums k² for the check (`shim_var`). Distance
   weighting comes free: a ground camera's near ground barely shimmers
   (√(100 m/77 km) → 2″ at 100 m), the far ground and the horizon do.
   Lanes `rf_shim2` = (A_step, 1/period, H_T, mode); `_UBO_FLOATS` +4.
   Measured (probe, HIGH lanes, 256 horizon rays): exit direction 1.80′
   RMS at amount 1, t = 4 s vs 0 decorrelated 1.64′, bit-identical
   without drift, one kind flip at the dip. Unit suite 75/75.
   REVISED 2026-09-06 (§4.6.1): the world tier, Eddy Size and the
   camera-side tilt `pa2RefrShimmer` are gone; the temperature masses
   (Masses, Size m) modulate G in the trace walk at every tier, the
   near shimmer kicks at eight fixed stations across the first
   kilometre of the same walk (camera-relative positions, gradient
   kicks, Boil Hz) with star scintillation in the compose; default
   amount 0.3. Probe: near exit 2.2′ RMS at amount 1, masses 0.78′ exit
   RMS at amount 1 and +45 % bend under a +1 field; view probe: 0.3
   keeps a wavy whole edge, 1 deforms without tearing. Suite 82.
   Same day, the mirage horizon hole: the LUT arm's atlas/aerial choice
   follows the walk's verdict, and a walked exit from below the
   geometric horizon takes the horizon ray's atlas column
   (`probe_horizon_hole.py`).

5. **UI, presets, docs** — panel rows and readout, preset tables,
   CHANGELOG, pipeline doc, default-ON decision.

### 7. Verification {#refraction-7-verification}

Unit (headless, `blender --background --python tests/run.py`; a numpy
twin of the GLSL schedule sits next to the fine-step ODE — the
Saturn-ring "numpy twin from the live UBO" idiom):

Reference-tier values MEASURED 2026-09-03 with the stage-0 numpy walk
(ISA-hydrostatic, 15 °C / 1013.25 hPa / dry, eye 1.5 m unless noted);
they are the unit-test anchors (RefractionReferenceTests) and the
targets for the GPU walk:

| anchor | expected | tolerance |
|---|---|---|
| N₀, Ciddor, 15 °C / 1013.25 hPa / dry | 277.8 ppm | ±0.5 |
| k(0) standard atmosphere | 0.170 (Bislin closed form 0.1706) | ±0.005 |
| k(0) at dT/dh = −34.3 K/km | 0 | ±0.005 |
| horizon refraction | 33.0′ (Bennett 34.0′; 34.5′ is the 10 °C classic) | ±1′ |
| 45° apparent | 57.3″ = N₀·tan z | ±1″ |
| 10° / 5° / 1° apparent | 5.22′ / 9.66′ / 23.5′; two-term tan law ±0.5 % above 10°, Bennett ±3.5 % everywhere | |
| Bouguer n·r·sin z drift over a horizon path | < 1e−7 relative (measured 1e−9…1e−8) | |
| horizon dip / distance from a 2 m eye | 2.48′ / 5.59 km (2.72′ / 5.05 km straight; the constant-k formula says 5.54) | ±0.1′ / ±0.1 km |
| dip from 10 km | 3.01° (3.21° straight) | ±0.05° |
| limb traversal, perigee 0 / 10 km | 1.10° / 0.41° | ±0.05° / ±0.03° |
| reversibility: out to the top, back to the eye | bend equal within 0.1″; landing within 20 m over a 1400 km path | |
| inferior mirage, ΔT = +10 K, L = 2 m, eye 1.5 m | rays above −11.1′ escape upward, below hit the ground; the horizontal ray refracts LESS than in standard air (21′) | ±2′ on the fold |
| duct, +2 K over 50–60 m (Young) | k(55 m) ≈ 2.0; a horizontal ray at 55 m never exits or lands (trapped between 45 and 65 m over thousands of km) | k > 1.5 |
| dispersion, horizon, 445 vs 615 nm | R–B split 31″ (33.38′ vs 32.87′); rim most visible at 1–2° (Young) | ±6″ |
| fast-path handover at 15° (GPU) | march − closed form | < 3″ |
| strength 0 / zero refractivity | hit distance = the analytic sphere chord (`pa2CamSphere` on the GPU) | 1e−6 relative |

GPU (the live GLSL hot-swap + pixel-crop recipe):

- Sunset over sea: the disc sets ON the lifted horizon; disc
    height/width ≈ 0.82 at the horizon (34.5′ vs 28.7′ limb lift); the
    sea-horizon row moves by 34′/thetaPix pixels vs refraction OFF; stars
    next to the sun lift by the same amount.

- 10 km camera: dip ≈ 3.0° (3.21° straight).
- Orbit: the limb's star compression and the lens-shaped sunset.
- Desert scene (ΔT = +10 K): the fold line, the sky "water" below it.
- Young's four sunsets at 500 mm, sun stepping through the last
    degree: (1) standard atmosphere — green upper rim, red lower rim,
    ~4″ wide; (2) inferior mirage from 2 m over warm sea — the Ω, the
    feet joining, the flash when the upper rim reaches the join line;
    (3) mock mirage, +0.8 K at 30–50 m from 60 m — the lower limb pausing
    at the inversion top, the blob, the green plume on the spikes;
    (4) sub-duct, +15 K at 200–250 m from 133 m — the triangular green
    flash surviving ~3× longer. Compare frame sequences side by side
    with Young's GIFs.

- Fractional air (0.5) + 1:1 BG: no seam at the lifted horizon (the
    fold gate under the coverage-AA cut).

- Status-readout frame times before/after on the standard scene.

Field: the user's verdicts on the sea sunset, the mirage and the ISS
sunset.

### 8. Risks and known limits {#refraction-8-risks-and-known-limits}

- **Scene meshes are not refracted** (Blender's cameras are straight). A
    hull-down ship at 20 km appears ~0.9′ lower than it should; the
    compositor's ground-km compare still resolves it correctly against
    the bent sea (sub-pixel at normal FOV). Documented, not fixable here.

- **Register pressure** in the cloud pass: the provider adds ~15 floats
    of state to the KSA loop. Watch the Metal compile (the framebuffer /
    leak-budget history) on the Mac before merging stage 2.

- **Fold-gate agreement** between the fractional air pass and the 1:1
    BG pass at the lifted horizon: same class as today, verified per §7.
    FIELD 2026-09-03 (the user's first sunset frames): two horizon
    defects, both in this class. (1) A white line on the disc's bottom
    row, refraction on OR off, any Air Resolution — found 2026-09-04 by
    `scripts/probe_horizon.py` driving the REAL TAA rounds on the live
    planes (a single march never shows it). The rect film resolve
    (`rect_taa_resolve.frag`) gathered its 3×3 gaussian footprint and
    ran its capped mean across the sky/sea boundary: the boundary air
    texel's T averaged the jittered rounds' sky samples (0.005 at the
    horizon) with their sea samples (0.9) and settled at 0.41 under a
    ground mask, and the BG pass premultiplied the disc by it (1.0e6
    against 1.3e4 one row up). Fix: the resolve is VERDICT-PURE — it
    gathers only sample texels sharing the centre sample's ground mask
    (INDIRECT.a, sampler `smp2`) and restarts a texel's film when its
    verdict flips (history lanes: hs.a = verdict, ht.a = count). The
    boundary then carries a pure, young mean and the anti-aliasing
    happens where EEVEE puts it: in the BG pass's own film over the
    per-round verdicts. A second, fainter mechanism on the SEA side at
    fractional air: the S-plane consumers — the world tree's Linear
    image node and the compositor's AOV tap — upsample S with a plain
    bilinear at the display pixel centre, blending the sky column's
    horizon glow (S ≈ 38) into the sea column's 0.9. No consumer can
    know the boundary; the BG pass is the only 1:1 stage that does:
    `gcAirGather` (a 2×2 gather over the air taps sharing THIS
    fragment's verdict, the nearest matching texel of the 4×4 block when
    the bilinear footprint has none, plain bilinear only when the block
    has none; a tap is PURE-verdict only — mask 0 or the full sample
    count, so the F12 render's SUMMED planes skip their mixed boundary
    texels too) feeds T, INDIRECT and SHADOW, and `gcAirSComp` writes
    (verdict-matched S − the plain S the consumers will add) into B on
    both sides of the boundary — exactly zero away from boundaries,
    negative on the sea side, so the BG film no longer floors B at zero.
    Laws: the air-plane film must never mix verdicts; B = everything the
    display pixel needs minus what the world will add. Measured after
    16 rounds: bright boundary columns 55/56 → 0/56 (1x and 0.5x air,
    refraction on), boundary texel T 0.41 → 0.89 ground / 0.006 sky,
    disc bottom row within 20 % of the rows above. (2) With
    refraction on, the sun through a band just above the lifted horizon:
    the air pass and the compose each fed the trace their OWN pixel
    angle (the air pass runs at a fraction of the display resolution),
    so the world shimmer's footprint factor — and with it the kicks and
    the ground verdict near the dip — differed between the two walks;
    where the air said ground and the compose said sky, the compose kept
    the sun. Fixed by ONE display pixel angle on `rf_cfg3.y`, filled by
    the gather from the stashed B dims (`_STATE["rect_b_dims"]`), read
    by every pass (their own value only as the fallback when the lane is
    0, i.e. no rect). Law: anything the trace consumes that could differ
    between passes must come from the UBO, never from a pass-local
    quantity.

- **Ducting / k ≥ 1**: the view march handles it (rays never exit); the
    sun-path effective sphere clamps k ≤ 0.9. Strong inversions render a
    trapped, extended horizon — physically right, visually unfamiliar.

- **Bottomless / below-surface** cameras: table clamped at h = 0, no
    ground test, 4000 km cap. NaN guards on sin z / sqrt args.

- **TAA / reprojection**: sky content is still a function of (pose,
    direction); the navigation reprojection's assumptions hold; ground
    reprojection uses the bent hit distance.

- **Reflections in materials** (equirect) show an unrefracted horizon:
    ≤ 34′ mismatch in a reflection — accepted under the role law.

- **Teeth at a duct fold's neck** (2026-09-06, user render): the step
    schedule's phase-dependent residual, magnified by the fold. Twin vs a
    fine-step reference, Duct preset from 70 m: Medium (4 cells/step,
    ~1.2 km steps, ~3 across the 10 m inversion) 1–4″ row to row → 1–6 px
    teeth at the neck; High 2 cells halves it; 1 cell (4× the steps)
    leaves 0.5″ / 1 px; a 300 m cap everywhere would need 2500 steps.
    Shipped: the sub-frame phase dither (the first sub-step's fraction per
    accumulation frame, `PA2_RF_PHASE` = rf_shim.y, toggle Sub-frame
    Dither) — a 16-frame film cuts the teeth 3–4×; the mean bias (~10″ at
    Medium) stays. Open: a layer-aware refinement — 1 cell or
    ds ≤ thickness/8/|cz| only while |ΔG| across the cell is large (the
    `table_g_var` input) — costs tens of steps per crossing and removes the
    residual and the bias; with the layer waves on, ds ≤ L/10 inside the
    inversion band (the 1.2 km steps alias a 3 km wave: 66″ row to row in
    the twin, 10″ with the cap).

- **Mock-mirage dark bands in the LUT sky** (2026-09-06): the extinction
    half of a band (the strip's grazing rays run tens of km farther in the
    low haze) needs T along the pixel's own walked path; the atlas rows
    near the horizon (0.3′/3′/8′/16′) cannot carry it, and the below-horizon
    exits take the horizon column. Options: a finer horizon band in the
    atlas, or a per-pixel walked T correction in the horizon band
    (|el| < el_disp) riding the dispersion walks. The analytic reference
    sky has both halves; the folded-limb half is right in both (§4.7).

### 9. What we take from the references, and where we depart {#refraction-9-what-we-take-from-the-references-and-where-we}

Bislin — taken: the k-coefficient closed form
(503 · P/T² · (0.0343 + dT/dh)) as the surface/test anchor; "curvature
scales with sin of the angle to the vertical" (his k′ = k·sin α — our
sin z factor); the piecewise circular-arc integrator (rotate half, step,
rotate half); the effective radius R/(1−k) — used ONLY for the
near-horizontal sun paths (§3.3), never for view geometry; the
"horizon distance" cap → our shell top and s_max.
Young — taken: the per-wavelength tracing (five wavelengths there, our
three RGB), the fact that the flash lives in the fold and so needs
per-channel paths, the inversion-layer cases and their numbers as the
acceptance suite, Wegener's above/below-eye split as a test, the
extinction argument for why rims are green rather than blue, and the
Auer–Standish / Bouguer framing (the invariant is our drift check).
Neckel & Labs — taken: the wavelength-parametrized 5th-order limb
polynomial, evaluated at the march's three sampling wavelengths and
normalized to the disc mean (the disc integrates to the AM0 irradiance
the sky already uses).
Departed: a 2-D (h, φ, z) state marched in arc length instead of world
coordinates or a refraction integral (precision at earth scale, and it
walks straight through turning points, which the integral form must
special-case); ISA layers anchored to the scene's surface temperature
with the surface layer and the elevated inversion, plus Ciddor N₀,
instead of Bislin's full barometric tables or Young's Monin–Obukhov
surface layer (refraction responds to the scene's humidity/CO₂ knobs
like the sky colour does; M-O is a later profile option); an
asinh-warped altitude table with a table-cell step schedule
instead of a fixed segment length; analytic ground/shell crossings
inside a step; a fast path for steep rays; per-pixel ray tracing of
the whole scene instead of Young's transfer curve + Wegener outline
tracing of the disc (we get the transfer curve implicitly, per pixel,
for ground, clouds and sky alike).

### 10. Open questions for the user {#refraction-10-open-questions-for-the-user}

1. Default ON at Normal quality once stage 2 lands (strength 1)?
2. Shimmer defaults: 1′ amplitude, 3′ scale, 1 m/s updraft, scene-time
   only — agreed? Should the updraft follow the Ground Temp Offset
   (0 over cold ground) or stay a plain knob? And is binding the
   existing turbulence volume into the compose (one new declaration,
   same texture) acceptable under "no new samplers", or should the
   compose use the zero-binding procedural noise?

3. Dispersion default ON with refraction (it gates itself off until the
   split is visible) — agreed?

4. Inversion presets as buttons (Young's three cases) or a plain enum?
5. The "k = 0.17 · 34.4′" readout row on the panel — keep?
6. Monin–Obukhov surface-layer shape (Young's inferior mirage) as a
   later profile option, or the exp layer stays the only shape?


## 1:1 Window-mapped sky — design & stage plan {#window-sky}

`shipped:`{: .label-fixed } Shipped · amended 10.09.2026 · 04.08.2026 · `docs/design-1to1-window-sky.md`

**In this document:** [Target architecture](#window-sky-target-architecture) · [Amended 2026-09-03 — sizing law, hybrid cut](#window-sky-amended-2026-09-03-sizing-law-hybrid-cut) · [What this retires](#window-sky-what-this-retires) · [Stages](#window-sky-stages) · [Traps carried from the prototype](#window-sky-traps-carried-from-the-prototype)

Status: SHIPPED (2026-08-04 → 09-03) and current in 3.0.7-beta. Since the
2026-09-03 amendment below: the world fovea group is ONE variant for
both engines again (Window 1:1 for Cycles too, laid out left to right,
with the direction arm and a Closest draft per tier, 2026-09-10), the
Cycles rect is tier-sized (tiny preview, 1:1 settled image), and the
"clouds keep the equirect/low-res path" line of the opening paragraph
is superseded — clouds composite at 1:1 in the background compose
whatever the Atmosphere Resolution (2026-09-05; see the LUT atmosphere
design §21.9 and the cloud design's stage 2b-vii).

User direction (2026-08-04): atmosphere + composed ground render 1:1
pixel-perfect like the prototype — Window-coordinate mapping ("much more
elegant") and the prototype's EEVEE-exact TAA ("it matches Blender
EEVEE"). Clouds keep the equirect/low-res path; the 1/4-1/16 upscale
route is reserved for when clouds join the rect.

Evidence base: PA2_prototypes README/INTEGRATION.md (proto_compute_grid
proved every mapping law below on 5.2/Vulkan + Metal).

### Target architecture {#window-sky-target-architecture}

- The rect pair (S/T + SHADOW/INDIRECT for the compose fold) is marched
    at EXACT view resolution: free view = region backing pixels; camera
    view AND F12 = render resolution (Window maps across the CAMERA FRAME
    in camera view — prototype law, note 30).

- World graph: `Is Camera Ray ? rect[Window.xy] : equirect(d)`. No
    direction math, no dual basis, no overscan, no blend band — the CLIP
    extension's zero-alpha outside [0,1] IS the fallback mask (camera-view
    surroundings outside the frame border show the equirect; accepted).

- Sampling: Linear, never Closest (Metal TAA moiré law), extension CLIP
    (EXTEND smears the border into the passepartout / Cycles tint).

- Equirect stays the lighting/IBL/probe/off-view source (foveated
    premise unchanged); MIS map cadence unchanged.

- TAA: the prototype's EEVEE-verbatim recipe on the rect march replaces
    Trust Fade on this path — Halton(2,3) + (1/2,2/3) shifts, disk jitter
    below radius sqrt(1/2), Blackman-Harris-fitted gaussian sigma=0.284,
    3x3 gather at |ofs+jitter|; history: Catmull-Rom fetch, YCoCg rounded-
    bbox CLIP, velocity blend 5-20%, luma weights; REGIME SPLIT:
    reprojection is navigation-only display (analytic reprojection, (d,0)
    through prev VP — no motion vectors), on settle discard history and
    re-converge. Film filter_size softness (~1px) is EEVEE's own film
    filter and is left alone — "pixel-perfect" means phase/period exact.

- Renders: rect rides render frames at render res (existing
    \_foveated_render_frame), F12 Window domain = render res = exact 1:1.

### Amended 2026-09-03 — sizing law, hybrid cut {#window-sky-amended-2026-09-03-sizing-law-hybrid-cut}

What shipped differs from the target list above in three places
(commits aee02d0 … 3e16693; measured live and in fresh instances):

- **Surface sizing.** Free view serves the FULL window region at 1:1
    with no cap beyond the GPU texture ceiling — the 4608×2592 viewport
    cap is gone (user: "dont clamp rect planes; if 1:1 is used, use the
    full buffer; Sky Resolution should only influence the texture
    size"). Camera view serves the camera FRAME's on-screen pixel size
    LIMITED to the render resolution (user: "if the view is in camera
    mode, the textures are limited to the render output resolution") —
    not the render resolution outright, which blurred every cut edge on
    a screen larger than the render. `sky_depth._camera_frame_px`
    projects the view_frame corners through the region view; the
    viewgeo cut map shares the same surface (display-sized, non-square,
    dims on the UBO, exact pose key). A new surface size is adopted only
    after it has HELD 0.3 s (`_settled_surface`), so a drag stretches
    the old planes instead of re-scaling them per step; the image-churn
    time gate after a real re-scale is 0.35 s off Metal.

- **How objects meet the atmosphere** (compositor graph v25, AOV group
    v8). The march decodes the cut map as a bilinear COVERAGE and mixes
    the full and the truncated column by it (the one-texel erosion sat
    2.8 px inside the silhouette and aliased). The compositor's terrain
    test is per fragment on an INVERSE ground-distance lane
    (`SHADOW.a` = 1/km on rect builds; a bilinearly interpolated km lane
    fired on the limb row). The composite is the HYBRID CUT: silhouette
    from EEVEE's alpha, haze and transmittance from the cut column, the
    edge band recovering both sides from a 5×5 luminance min/max of the
    planes (S_full ≥ S_cut, T_full ≤ T_cut per channel), gated to
    fractional-alpha pixels dilated 2 px:
    `out = mix(B_T + S_sky, obj·T_obj + S_obj, α·(1−G))`. Composite edge
    within 0.7 px of the alpha edge, 1 px ramp, no rim. An "Object Haze"
    switch (Alpha Only) lived for an afternoon and was removed.

- **Retired since.** `rect_bg_film.frag` is a film tail inside
    `ground_compose`'s BG variant; `rect_taa_resolve.frag` lost its dead
    mode-1 arm; the aux pass films `SHADOW.a`; the compositor is AOV-only
    (no image nodes, MapUV or view carriers) with node-group
    tonemappers. Publish path: compute + imageStore on Vulkan and Metal
    (within 10 % of fragment + framebuffer, measured).

The architecture reference (artifact "Physical Atmosphere² Pipeline")
and `docs/CHANGELOG.md` (Unreleased, 2026-09-03 batch) carry the
details.

### What this retires (rect path only) {#window-sky-what-this-retires}

- The dual-basis direction math in the world fovea group (rectCam0..2
    attributes become compositor-only carriers until stage C).

- \_RECT_OVERSCAN, \_FOVEA_BAND\_\* (band fade), \_FOVEA_NDC_CLAMP (the
    Cycles INT_MAX crash guard — moot: Window lookup has no divide).

- Trust Fade + per-draw warp on the rect (stage B; the warp's job is
    taken by TAA reprojection in navigation regime).

- 32-px quantization and the HALF default sizing indirection for the
    FULL setting (HALF/QUARTER divisors stay as options; Linear + Window
    keeps them correctly mapped, just softer).

### Stages {#window-sky-stages}

- **A — mapping + sizing** (this branch): march frustum from
    \_view_from_r3d (camera-frame in camera view; region in free view),
    exact-resolution allocation, world fovea group vNext = Window +
    Is Camera Ray + CLIP-alpha mix, rectCam idprop writes kept for the
    compositor consumer. Verifiable headless: sizing/key unit tests;
    GUI checks queued.

- **B — prototype TAA port**: jitter injection into the rect march UBO
    seed, RGBA32F ping-pong history, resolve shader (Catmull-Rom/YCoCg
    clip/luma weights), analytic reprojection UBO (two mat4, std140),
    regime split wired to the existing settle detector; Trust Fade
    retired on the rect. Compare smear/sharpness against Trust Fade
    before deleting (rect-taa arc precedent).

    Port architecture (decided 2026-08-04; foundations in core/taa.py):

    - EEVEE's SPLIT, not the prototype's: the prototype gathered 3x3
    SCENE evaluations per pixel (its world was a cheap plane test) —
    9x a real march. EEVEE renders ONE jittered sample buffer per
    step, then the film/resolve pass gathers each pixel's 3x3
    NEIGHBORHOOD of that buffer weighted at |ofs + jitter|
    (film_filter_weight, sigma 0.284). March cost stays 1x/tick.

    - Jitter enters the MARCH's ray setup as a sub-pixel offset uniform
    (real ray offset, not a noise seed — that is what makes stars/limb
    converge like EEVEE), from taa.pixel_jitter at the step index.

    - March lands in a scratch sample buffer; order per tick:
    march(jittered) -> ground-compose fold -> TAA resolve -> publish.
    S and T get the full recipe (they are what the eye sees, ground
    included after the fold); SHADOW/INDIRECT keep plain capped-weight
    film accumulation with reset-on-move — low-frequency signals, no
    YCoCg/velocity machinery, half the history memory.

    - History: RGBA32F ping-pong pair per TAA'd plane (mean.rgb,
    weight.a); manual bilinear/Catmull-Rom via texelFetch on the
    fragment path, imageLoad on the Metal compute path (int2 loops are
    MSL-safe; keep vec compares as all(equal(...)) — Metal law).

    - Reprojection: (d,0) through the previous view-projection
    (sky/atmosphere is translation-invariant); ground pixels reproject
    as (p,1) using the compose's own hit distance if silhouette
    ghosting shows up — try (d,0)-only first, the prototype's sky
    verdict. Two mat4s exceed the push-constant budget: std140 UBO
    (typedef_source + uniform_block, column-major = rows of
    transposed()) — prototype 52df54c.

    - Regimes (EEVEE film.bsl.hh): reset (pose/content change with no
    usable history) | interactive (navigation: Catmull-Rom history at
    reprojected px, YCoCg rounded-bbox CLIP toward src, velocity blend
    5–20% at 0.02/px, luma weights 1/(4+luma), offscreen -> blend 1) |
    static film accumulation (weighted mean, weight cap 32, count to
    the AA-dropdown target). On settle: discard history, re-converge —
    smear cannot bake in by construction.

    - The existing rect_reproject/rect_rectify warp chain and Trust Fade
    stand down on this path once the resolve lands (the warp's display
    job IS the interactive regime); keep them compilable until the
    side-by-side verdict.

- **C — compositor placement**: replace the compositor's rect direction
    math with direct Image placement (bare Image node identity in free
    view; camera-frame domain in camera view — prototype compositor
    laws; NO Scale node "Render Size" in free view). Domain-invalidation
    signature must include the camera frame rect (prototype bdc3d36).

- **D — renders + polish**: animation-render cadence audit on the new
    path (probe/latch from Phase 1 already covers no-context jobs),
    HiDPI budget re-check on the CPU-publish branch (the \_RECT_CPU_MAX_PX
    cap breaks FULL exactness on Metal/Cycles paths — decide budget vs
    1:1 there), Metal verification deferred to a Mac session (MSL-strict
    GLSL law).

- **F — tiered shader quality per path** (user direction 2026-08-04:
    "the equirectangular map should use simplified shaders while view
    ray — full quality"). The equirect serves LIGHTING, so its tier must
    be cheaper without being dimmer — energy-preserving knobs only:
    reduced march/light step counts, refraction off, sharp cloud shadows
    off, fewer cloud-noise octaves, no AA passes; radiometry (betas,
    phase, MS) untouched or scene ambient light shifts. The rect tier
    keeps everything. Implementation is a per-path UBO gather tier — the
    step counts and refinement toggles are already UBO-driven (no
    recompile, 2026-07-17), so this is a parameter set chosen at gather
    time by pass kind, landing together with the B-resolve work (same
    UBO/orchestration region, same live lighting verification session).
    The equirect is already probe-sized + quiescent under the fovea;
    this adds the shader-work tier on top.

- **E — celestials into the rect** (user question 2026-08-04, agreed
    direction): march stars/sun/planets into the FBO for CAMERA rays —
    full TAA on stars, march-side refraction/scintillation of the disc,
    near-empty camera-path world graph. Node-side celestials STAY for
    non-camera rays (probes/reflections/MIS need analytic all-direction
    evaluation; the equirect sun is 3 texels) and as the animation-render
    fallback when Blender withholds the GPU context. Cost: position/
    radiance parity between GLSL and node celestials — build behind a
    toggle, compare side by side.

- **E3 — the background plane** (user direction 2026-08-05: "one rect
    texture for stars, moon, sun and planets and ground — then one
    transmittance texture to multiply it and one scatter texture to add
    over that"). The display contract becomes `out = B x T + S` with
    three PURE planes:

    - **B** (new, PA2_ATMOSPHERE_RECT_BACKGROUND, RGBA32F — the sun
    disc's star-convention radiance overflows fp16): every SURFACE.
    Sky rays carry the depth-sorted celestial chain (the E2 layer,
    moved out of S); ground rays carry the composed ground radiance
    (the fold WRITES B instead of folding into S).

    - **T**: pure camera-to-surface transmittance. The fold's
    "S += T*ground, T -> 0" contract DIES — no more ground zeroing,
    aerial perspective on the ground becomes the same multiply as on
    the celestials. (This also makes the sunset horizon-line class
    debuggable: T carries no occlusion tricks.)

    - **S**: pure inscatter (the march's col before any fold).
    Plumbing: 5th MRT out on the rect driver (FragBackground; equirect
    keeps 4), 5th slot through scratch/fb orders, B gets the full film
    treatment (scratch + RGBA32F history pair + resolve outs — resolve
    grows to 8 attachments, exactly the API max). World graph v12: the
    fovea group samples rect B; the E2 kill (scale + depth-to-INF)
    becomes a MIX — vm_mul's celestial input = mix(node sun/moon chain,
    rect B, fac) — probes keep the node pair, camera rays get B.
    SHADOW/INDIRECT keep publishing (compositor + compose inputs).
    Memory note: +1 image + scratch + history pair at RGBA32F ~= +250 MB
    at a 3K rect — acceptable per the user's direction, revisit with a
    half-float encode if it bites.

    SAME TRIO FOR THE EQUIRECT (user 2026-08-05: "and same for the
    simplified sky equirect textures"): the lighting path gets its own
    B plane (PA2_ATMOSPHERE_BACKGROUND, probe-sized) — the equirect
    march gains the celestial layer + ground in B, pure T/S. END STATE:
    the node sun/moon retire COMPLETELY — probes, reflections and every
    fallback consume B_eq x T_eq + S_eq, and the entire sky (both
    paths) runs in the offscreen renderer. The world graph collapses to
    two sampling formulas blended by fac. Accepted trade: reflections
    show the probe-res marched sun disc (soft at 512-class) instead of
    the analytic node disc — revisit resolution if chrome-ball suns
    matter. Cost: celestials at probe res are noise-level cheap.

- **G — cloud buffer split** (user question 2026-08-04, agreed
    direction; the deferred "1/4–1/16 upscale" plan made concrete). The
    clouds leave the 1:1 march for their own low-res buffer with the
    contract (L_c cloud radiance, T_c cloud transmittance, d_c
    representative depth). Composite by transmittance factorization:
    S = S_atm(0→d_c) + T_atm(0→d_c)·L_c + T_atm(0→d_c)·T_c·S_atm(d_c→∞),
    T = T_atm·T_c — the depth-resolved atmosphere terms come from the
    aerial-atlas machinery, evaluated at cloud-buffer res. Bilinear +
    independent temporal accumulation upscales the clouds (their own
    clock/cadence, decoupled from the atmosphere's converge-and-hold).
    Known approximation: one representative depth per texel misassigns
    aerial perspective on horizon-grazing interleaved layers; escalation
    path is a near/far two-slice split before anything exotic. The 1:1
    atmosphere pass never marches a cloud step — that is the entire
    performance win.

    KSA reference (source_shaders/ksa, read 2026-08-04 — ARCHITECTURE
    REFERENCE ONLY, clean-room the ideas, never copy the code): their
    cloud pass is a LOW-RES buffer whose sample position CYCLES through
    the upscaling block per frame (upscalingMultipliers/PixelIndices,
    e.g. 3x3 = the "9x" setting) — a hybrid of fixed-low-res and
    interleave that converges to full res on stills. The march writes
    color + MOTION VECTORS (real cloud motion, then dilated) + cloud
    DISTANCE (half-encoded); aerial perspective is applied INSIDE the
    cloud march from Hillaire-style 3D aerial LUTs at cloud distance
    (confirms the stage-G factorization). UpscaleCloud.comp per full-res
    pixel: fresh-this-frame pixels blend low-res sample with rectified
    history (weight 1-1/sampleCount capped 0.9; R8 sample-counter
    texture); others reproject history (bicubic Catmull-Rom) rectified
    by a neighborhood color clamp from the fresh low-res ring, with
    BOTH velocity and cloud-distance disocclusion tests, nearest-depth
    fallback at depth discontinuities, and a 0.5-capped fallback mix to
    limit trails vs reintroduced noise. Composite = transparency over
    (separate r11f transmittance target). Their high-camera guard
    (ignore craft depth far above the cloud ceiling to avoid history
    streaks) is a good trick for our orbit views.

### Traps carried from the prototype {#window-sky-traps-carried-from-the-prototype}

- Image datablock resize NEVER mid-draw — defer to timers (existing
    churn-guard machinery already does this).

- Closest + TAA jitter = moiré on Metal; Linear only.
- Cycles restarts on every image update_tag the compiled graph REACHES:
    the rect image nodes must stay behind Is Camera Ray so the lighting
    graph never depends on them (restart-free law only applies to
    UNREACHABLE branches — verify the world compile keeps the rect
    reachable from camera rays only, and keep the ~1 Hz flush cadence).

- Region-resize churn: pause fills during domain-change grace before
    recomposite (existing \_image_churn machinery). 2026-09-03: a 0.3 s
    surface settle precedes any re-scale, and the time gate is 0.35 s
    off Metal — the two-clean-draws counter is the guard.


## Optimized cloud rendering: interleaved low-res march + temporal upscale {#cloud-upscale}

`shipped:`{: .label-fixed } Shipped · superseded in part · interim system · 05.08.2026 · `docs/design-cloud-temporal-upscale.md`

**In this document:** [Why this is possible cheaply here](#cloud-upscale-why-this-is-possible-cheaply-here) · [Architecture](#cloud-upscale-architecture) · [Non-goals](#cloud-upscale-non-goals) · [Risks](#cloud-upscale-risks) · [Companion feature: separate preview vs render graphics settings](#cloud-upscale-companion-feature-separate-preview-vs-render-gra) · [Stage 1 / C2 wiring map](#cloud-upscale-stage-1-c2-wiring-map) · [Stage 2a decision](#cloud-upscale-stage-2a-decision) · [Stage 3: KSA 1:1 march port](#cloud-upscale-stage-3-ksa-1-1-march-port) · [Stage 4: KSA shadow volume + sharp godrays](#cloud-upscale-stage-4-ksa-shadow-volume-sharp-godrays) · [Shadow-volume FIDELITY AUDIT vs the real sources](#cloud-upscale-shadow-volume-fidelity-audit-vs-the-real-sources) · [What actually blocks retiring the LIGHT GRID](#cloud-upscale-what-actually-blocks-retiring-the-light-grid) · [DIRECTION SET 2026-08-07: the KSA march is the one that ships](#cloud-upscale-direction-set-2026-08-07-the-ksa-march-is-the-on) · [Stage 2b: the KSA MV-reproject resolve](#cloud-upscale-stage-2b-the-ksa-mv-reproject-resolve)

Status: SHIPPED, then SUPERSEDED IN PART (as of 2026-09-10). Stages 1–4
and 2b landed in 2.8.x; 2b-vii made the primary march 1:1 always. Since
then: the house march and the LIGHT GRID are deleted outright
(2026-08-10 — the KSA march is the only transport), the cloud density
model is the ported one with a baked per-layer weather chart and a
Worley mip atlas (2026-09-05, ~5x faster passes), the composite/godray/
interleave/shell pieces are K1–K4 of the LUT atmosphere design (§21.9),
scene objects shadow the clouds and scene lamps light them. The
"companion feature" below shipped as Viewport TAA Samples / Render
Samples. THE CLOUDS ARE AN INTERIM SYSTEM: the real cloud renderer is
in development and will replace this pipeline; this document is the
record of what runs today. Original header: DESIGN (2026-08-05). Research base: research-ksa-cloud-teardown-2026-08.md
(ACTUAL KSA sources — primary reference now) + research-temporal-upscaling-2026-07.md
(Three Geospatial, corroborating). User: "next big thing is get the optimised
cloud rendering in".

REVISION after the KSA teardown: adopt KSA's scheme over takram's where they
differ — host-driven NxM interleave (3x3, `upscalingPixelIndices` UBO field,
no baked Bayer table), transmittance-weighted CENTROID as the reprojection
anchor and the single evaluation point for ambient/aerial/shadow terms,
heaviest-cloud MV pick, dual (velocity-continuous + distance-boolean)
disocclusion, R8 sample counter with 0.9 cap, and the reduceFlickeringDistance
clamp relaxation (mandatory at 8:1). Stage 1's split pass should bank the
centroid deferral immediately (it pays even before interleaving). The
shadow-volume light-march split and KSA-grade subtractive godrays are staged
AFTER upscaling lands (they reuse its volume + resolve machinery).

### Why this is possible cheaply here {#cloud-upscale-why-this-is-possible-cheaply-here}

The rect march already contains the separation seam. pa2ColumnComposite
(sky_driver.glsl:50) computes the HQ cloud march and composes it as

    SCATTER = L_cloud * T_cam_to_cloud
            + sunIrr * (Sca_front * alpha + Sca * (1 - alpha))

i.e. cloud radiance and camera->cloud transmittance are ALGEBRAICALLY separable
from the air. The `cloud_shadows_only` runtime bit (cl_uflags bit3) already
proves the atmosphere-without-cloud-march path works and is cheap. And the rect
already has jitter lanes, reprojection matrices (Stage B TAA), Trust Fade
history, and the resize-hard-reset law — most of the temporal machinery exists.

### Architecture (three stages, each shippable) {#cloud-upscale-architecture}

#### Stage 1 — split the cloud march into its own rect pass (full res)

STATUS: CODE-COMPLETE 2026-08-05 (steps A e412e8d, B 00d6773, C1 6ba10c8,
C2 0b3740d). Behind the Split Cloud Pass toggle (cloud_split, default OFF).
FIELD-VERIFIED 2026-08-05 (user: "looks good") — default flipped ON.
Bonus finding: the celestial compose (\_CEL_COMPOSE) injects at the
FragScatter anchor inside the !PA2_CLOUD_PASS branch, so the cloud pass
never compiles it — the pass is ray setup + arm only, no gating needed.
NEXT: stage 2 (3x3 interleave + temporal resolve).

IMPLEMENTATION MAP (2026-08-05, from the driver read):

- The march to extract is sky_driver.glsl:64-110 (HQ shell march + 2D far
    deck inside pa2ColumnComposite), plus its runtime gate PA2_RT_CLOUD_RENDER.

- TWO call sites consume it: the full column (main, :336) and the
    GEOMETRY-CUTOUT column (:423, segment clamped to pa2TGeo). The cutout must
    NOT re-march: composite from the same taps with the depth test
    `pa2TGeo < frontDepth ? (L=0,T=1) : tapped values` — mesh-inside-cloud
    becomes approximate, the same class of approximation KSA ships.

- Mechanism: ONE source file, compiled variants.
    \* Cloud pass: sky_driver compiled with PA2_CLOUD_PASS — full ray setup
    (window mapping/refraction/seg all reused), runs ONLY the march block,
    writes MRT C0 = L_cloud.rgb + frontDepth\*0.001, C1 = T_cloud.rgb +
    centroid-dist\*0.001 (centroid banked for Stage 2; march_cloud_segment
    must start accumulating transmittance-weighted position).

    * Sky pass: compiled with PA2_CLOUD_FROM_TEX — pa2ColumnComposite reads
    uCloudL/uCloudT samplers (screen UV) instead of marching; everything
    from atmosphere_clouds(:121) down unchanged.

- Host: two RGBA16F rect textures ping-less (rebuilt per round), builders
    frag + compute twin, samplers declared in ALL sky builders and PINNED OFF
    (define PA2_CLOUD_FROM_TEX 0) in grid/LUT/shadow-plane/psi builders —
    compile probe for every surface before commit (shadow-plane lesson).

- Equirect keeps inline marching (no define = current behavior). Renders
    (F12/CPU fold) unchanged this stage — the render path can keep the inline
    variant until Stage 3 wires rounds.

- New pass `cloud_march` (frag + COMPUTE TWIN — registration law, 5th surface):
    outputs MRT: C0 = L_cloud (rgb) + alpha, C1 = T_cam_to_cloud (rgb) +
    frontDepth (a). Runs the existing HQ march code (pa2ColumnComposite's cloud
    arm extracted; same jitter lane bit0).

- The sky march pass drops its inline cloud march (compile-time: the
    cloud_shadows_only path becomes the ONLY path) and composites from the two
    new samplers per pixel with the formula above.

- Acceptance: A/B against pre-split frames (same seed) — differences at noise
    level only. Cost neutral this stage.

#### Stage 2 — low-res Bayer interleave + temporal resolve
- Cloud pass renders at ceil(W/4) x ceil(H/4); per TAA round exactly one of the
    16 Bayer cells is "current" (bayerIndices table from the research doc,
    frame % 16). Projection jitter = the Bayer subpixel offset (the low-res
    render IS the jittered sample — no second jitter sequence).

- New `cloud_resolve` pass (full res, ping-pong A/B):
    - current cell -> texelFetch from the low-res target, no accumulation;
    - other cells -> reproject history through the prev view-proj (rect already
    stores it; velocity from 3x3 closest-fragment dilation on frontDepth),
    variance-clip (3x3 mean +/- gamma\*stddev AABB, gamma ~2) toward current.

    - outside-frustum / disocclusion -> fall back to the low-res texel.
- The sky pass samples the RESOLVED cloud buffers. Expected cloud cost /16 per
    round at slightly softer convergence; the existing Trust Fade handles the
    rest.

- Front depth for reprojection = the march's first-scatter depth (the
    anti-smear work already banked a depth-like tap; reuse).

#### Stage 3 — lifecycle integration
- Hard resets: surface resize (existing law), sun-direction quantum, cloud
    param key change -> resolve history invalidated (reuse the rect round's hard
    key; add the cloud param key).

- F12/render: sync-loop 16+ rounds before first frame (the render path already
    loops TAA rounds; raise the floor when upscale is on).

- Equirect/lighting path: KEEPS the inline full march (it is 512x256 and baked
    at low cadence — interleaving would add latency to lighting for ~no win).

- Toggle: `cloud_temporal_upscale` (default ON for LOW/MED quality, maybe OFF
    for NASA preset), rebake key bit. Mac/Metal: compute twins declared from day
    one; harness = fold/cel-style compile probe for BOTH new passes.

### Non-goals {#cloud-upscale-non-goals}
- No change to cloud lighting content (grid, ambient, shadows stay as-is).
- No KSA-style per-layer pipelines (their changelogs, not their code).
- Fogbow/droplet-LUT disc convolution is a separate parked item.

### Risks {#cloud-upscale-risks}
- Ghosting behind fast sun changes (variance clipping mitigates; takram ships
    gamma 2 and calls the residual invisible on clouds).

- The B-plane premultiplied composite (fovea v15/v16) consumes SCATTER after
    clouds — verify the fold's inputs still see a consistent T (the split keeps
    T_cam_to_cloud separate, so the fold contract is unchanged).

- Two more compile surfaces (frag+compute x2 passes) — probe scripts mandatory.

### Companion feature: separate preview vs render graphics settings {#cloud-upscale-companion-feature-separate-preview-vs-render-gra}
(user 2026-08-05: "what people are asking are separate preview graphics
settings and render graphics settings")

- Toggle `use_render_quality` + render-side copies of the quality props
    (atmosphere steps, MS steps, cloud quality/steps, jitter, upscale mode —
    Stage 2's interleave should default OFF for renders, ON for viewport).

- User examples: "sky resolution 1/2 for preview but 1/1 for render",
    "potato for preview, high for render" — so the override set includes the
    RECT RESOLUTION SCALE (preview can run the rect at 1/2 and let the world
    shader upsample; render forces 1/1) and the whole QUALITY PRESET enum
    (one render-side preset dropdown mirrors the preview one; picking a
    preset writes the whole render prop set, same as the preview preset UX).

- Host-side only: the gather/bake path already knows \_rendering (render_init
    latch) — select the prop set there; bake keys already fingerprint the
    values, so switching re-bakes automatically. Panel: a "Render Overrides"
    sub-box, greyed until the toggle is on.

### Stage 1 / C2 wiring map (2026-08-05, from the \_rect_direct read) {#cloud-upscale-stage-1-c2-wiring-map}
- Shaders: \_foveated_bake builds \_STATE["rect_shader"] (10338); with the
    split toggle ON build it cloud_mode="from_tex" + a second
    \_STATE["rect_cloud_shader"] cloud_mode="pass" (same key discipline via
    rect_shader_key). Toggle prop: cloud_split (default ON later; OFF = inline
    A/B path).

- Textures: 2x RGBA16F at the MARCH dims - \_rect_direct has FOUR fb branches
    (scratch sdims / compute_direct / gpu_direct / render 9100-9142); the cloud
    pass must size to the branch's march dims (sdims in scratch mode). Cache as
    cache["cloud_split_tex"]/size.

- Frag dispatch: before each \_draw_pass site (9174 scratch, 9194 gpu_direct,
    9218 render loop), run the cloud pass into a 2-slot FB (locations 0/1 =
    FragScatter/FragTransmit; unbound 2-4 fine). Cloud shader needs its OWN
    batch (batch_for_shader per shader). Then bind uCloudL/uCloudT on the sky
    pass - read \_draw_pass (8389) for the declared-samplers mechanism
    (\_SAMPLERS_RECT tuple) and extend it.

- Compute dispatch (9183): cloud twin via \_rect_compute_pass with
    [cloudL, cloudT, dummy, dummy, dummy] (all 5 uOut\* images must bind;
    with_celestials build). NOTE the celestial driver marches stars/moon
    around pa2SkyMain OUTSIDE the PA2_CLOUD_PASS gate - wasteful in the cloud
    pass; correctness first, gate the celestial wrapper with
    !PA2_CLOUD_PASS as an optimization once A/B passes.

- UBO: share cache["rect_ubo"] (gather already done per round) - the cloud
    pass must run AFTER the gather (9169) and BEFORE the sky march.

- Render/CPU path (9218 multisample loop): cloud pass per AA sample inside
    the loop (jitter seed moves per sample).

### Stage 2a decision (2026-08-05): scatter-resolve first, MV-resolve later {#cloud-upscale-stage-2a-decision}
The rect TAA already reprojects the COMPOSITED sky (clouds included)
across camera motion — so the cloud pair itself can start with a
hold-resolve, no motion vectors:

- Persistent full-res uCloudL/uCloudT pair (no ping-pong needed).
- COMPUTE path: the low-res cloud dispatch imageStores each texel
    directly at its full-res cell position — no resolve pass at all.

- FRAG path: low-res pass to a small RT, then a full-res discard-resolve
    (pixel not in the current cell -> discard; no-clear FB keeps history).

- Host rotates cl_upscale (new UBO vec4: multipliers.xy, pixelIndices.zw)
    through the 3x3 cells per round; driver remaps uvInterp under
    PA2_CLOUD_PASS when multipliers > 1.

- Staleness bound: any texel is at most 9 rounds old; cloud-field changes
    (sun quantum, params) already hard-reset the rect. If lag/flicker shows
    in the field, stage 2b = KSA's MV reproject + variance clip + counter.

### Stage 3: KSA 1:1 march port (user 2026-08-05: "make our cloud sampling match the KSA, also compute shader wise. I want it to be 1:1") {#cloud-upscale-stage-3-ksa-1-1-march-port}
New `march_cloud_segment_ksa`, same signature as the house march, gated
PA2_KSA_MARCH (prop cloud_ksa_march joins \_toggles -> re-keys). Loop is
RaymarchCloud.comp:136-217 VERBATIM structure:

- step = stepSizeIncreaseFactor\*distanceFromCamera + initialStepSize,
    min(maxStep), recomputed FRESH each iteration (not compounded);
    first step x dither; fractional last step; guardrail iterations only.

- Earth production constants: initial 70 m, factor 0.006, max 1500 m;
    light march 1200 m / 4 samples (cirrus: 110 m/0.0044/4500 m, 1400 m/2).

- density > 0 gate -> light + scatter; integrationWeight = T\*(1-stepT);
    early exit T\*prevLayer <= 1/255 with the infinite-series tail.
CONTENT MAPPING (KSA -> ours):

- GetCloudDensity -> sampleCloudWeather + sampleCloudMedia (scalar rho;
    step T scalar via dot(Bsc+Bac, 1/3)\*rho; publish spectral T_cloud via
    (Bsc+Bac)\*rho accumulation).

- GetDensityToLight -> cloudSunDensityHybrid IS already the KSA shape
    (live full-detail steps + light-grid tail as the shadow-volume tap);
    widen the live window to lightRaymarchingDistance with N samples and
    the golden-ratio dither advance (fract(+0.61803398875)).

- Scattering: BeerAbsorption + MS rational fit 1/(1+0.35d+0.065d^2);
    phases ONCE per ray: direct 0.2\*HG(0.8), indirect 2.5\*HG(0.2)+
    0.7\*HG(-0.4); MS edge = Remap(DP,0,1,0.05,1) (their noiseProfile arg
    is dead code - port the shipping behavior, not the intent).

- skyCloudComponent (occlusion BeerMS(DP\*3)) accumulated in-loop,
    multiplied ONCE at the transmittance-weighted CENTROID by our ambient
    LUT (cloudAmbientLUT SS+MS at centroid coschi/h) - the teardown's #1
    priority (centroid deferral) lands here.

- Units: stay sun-normalized like the house march (composite applies
    sunIrr); calibrate a CLOUD_BRIGHTNESS analog against the house look.
COMPUTE-WISE: golden-ratio light dither in both builds now; groupshared
finite-difference mips (8x8 shared UV arrays, mips at ray start/end,
lerped, floored) as the compute-only follow-up once the march lands.
RISK: different transport = different look than the Fewes-calibrated
house march - ship as a TOGGLE for field A/B; the ambient-band
calibration may need a revisit under the KSA transport.

### Stage 4: KSA shadow volume + sharp godrays (user: "does the KSA core say anything regarding the light grid? and can we continue with the godrays?") {#cloud-upscale-stage-4-ksa-shadow-volume-sharp-godrays}
KSA has NO light grid - the dual-paraboloid shadow volume plays that role
for three consumers at once (cloud light-march far tap, cloud self-shadow,
godray occluder), which is why their shafts are sharp AND agree with the
cloud shadows. Port plan:
4a. VOLUME: R16F 3D (paraboloid XY x altitude Z, camera-anchored),
    ShadowVolume.glsl:57-88 forward map + the 8-tap tricubic B-spline;
    build = compute pass, 40-step sun march per texel over OUR density
    (cloud_density_scalar), sliceToUpdate row rotation per round;
    v1 re-centers on big camera moves with a rebuild sweep (KSA's
    ResampleVolumes reprojection = v2 if the sweep shows).
    Density stored /100 (their storage scale), fp16.
4b. CONSUMERS: (1) the KSA march far tap (replaces the grid tail when
    the volume is live); (2) the atmosphere march's cloud-shadow term
    (PA2_RT_CLOUD_SHADOWS path) - THIS is where godrays sharpen: the
    km-soft grid texels become tricubic paraboloid taps; (3) later the
    dedicated low-res subtractive godray pass (Godrays.comp port) if
    in-march godrays still limit quality.
4c. Ambient volume (12 dirs x 7 taps x0.1) - BUILT, not deferred (this
    line said "deferred" until 2026-08-07 and was simply stale). It
    bakes in the SAME dispatch as the sun volume (uSvAmbOut: 3 azimuth
    x 4 zenith = 12 directions, 7 samples each, density x0.1, capped at
    4x band thickness) and the KSA march consumes it at the centroid as
    `ambient *= BeerMS(D) * 0.7 + 0.3`. Verified on GPU by
    scripts/probe_shadow_volume.py: a DISTINCT 48x192x192 R16F volume
    with 109,992 non-zero texels against the sun volume's 6,044 - the
    ratio 12 directions vs 1 predicts. That probe checks distinctness
    on purpose: \_sv_extra falls back to the SUN volume when "amb" is
    missing, so an aliased ambient would look like a working feature
    while feeding the sun term into the ambient consumer.

### Shadow-volume FIDELITY AUDIT vs the real sources (2026-08-07, user: "i want to know how faithful of implementation we have") {#cloud-upscale-shadow-volume-fidelity-audit-vs-the-real-sources}
Audited against ksa/Core/Shaders/Clouds/ShadowVolume/{ShadowVolume.glsl,
ShadowVolume.comp, ResampleVolumes.comp}, line by line.

FAITHFUL 1:1 (the numerics that matter):

- Tricubic B-spline sampler: identical math — weights, pair weights,
    p0/p1 offsets, and the mix() ORDER (their backwards-looking
    mix(t111, t110, s0.x) form, which is correct because the weights sum
    to 1). Only difference: dims passed explicitly (the no-textureSize
    Metal law) instead of textureSize().

- Paraboloid map both ways: same -normalize(x,y,1) + reflect trick,
    same x/(z+1) forward form, same [0,1] packing, same outside-disc
    zero. Same storage scale (100), same R16F, same planet-centred
    height fraction, same 40-step direct march, same 7-sample ambient
    march with the same 0.1 scale, /12 and 4x-band-thickness cap, same
    8-wide slice-rotation amortization.

- Basis transport: their mat3 worldToShadowVolume = our sv1/sv2/sv3 dot
    rows; build uses the transpose. Orthonormal, mutually consistent.

DELIBERATE deviations (each field-driven and commented at the site):

- ORIGIN: KSA anchors the volume at volumeOrigin (host-side, unknown —
    their .comp only receives it); we anchor at the SUB-CAMERA SURFACE
    point, because the single +z paraboloid hemisphere otherwise kills
    the whole feature above the deck (field 2026-08-06: godrays only at
    low altitude). Our disc centre rides the ground track.

- OUT-OF-BAND SUN PROJECTION in the sampler: not in their
    ShadowVolume.glsl — it is their Godrays rule (Godrays.glsl:164-177),
    folded into our one sampler so every consumer gets it. In-band
    positions behave identically to theirs.

- MARCH SEGMENT: they advance to the cloud-layer slab and march its
    FIRST chord only (a grazing sun ray that dips below the band and
    re-enters loses the second crossing); we march pos -> band-top exit,
    which integrates both crossings but spends steps on the empty dip.
    Ours is the more correct integral, theirs the more step-efficient.

- LAYER ACCUMULATION: their firstPass/append protocol exists because
    they bake per cloud layer; our density field is already the union of
    layers, one pass, no append. Equivalent by construction.

- ResampleVolumes.comp NOT ported (v1 design decision: re-centre with
    a rebuild sweep on origin-key change; their reprojection is v2 if
    the sweep shows in the field).

- DENSITY SOURCE: they sample noise at a FIXED MIP 3 (coarse, cheap);
    we run full-detail cloud_density_scalar. Sharper and costlier per
    texel — flip to the LOD volume if the bake ever shows in profiles.

UNINTENTIONAL divergences (found by this audit; small, listed in
order of likely visibility — none rises to a bug):

1. AMBIENT DIRECTION SET: KSA uses u=i/3, v=j/4 with NO half-texel
   offsets — cosPolar in {1, .5, 0, -.5}, so THREE of their 12
   directions are the exact vertical (a deliberate-or-not 25% up
   weighting) and straight down is never sampled. Ours uses (i+.5)/3,
   (j+.5)/4 — symmetric, no duplicates, cosPolar {.75, .25, -.25,
   -.75}. Ours is the better estimator; theirs is the look we claimed
   to port. Their ambient reads ~brighter-from-above.

2. AMBIENT TANGENT FRAME: KSA builds it around the PER-TEXEL local
   vertical (worldPosition - planetPosition); ours reuses the volume
   basis (the origin's vertical) for every texel — a few degrees off
   at horizon-distance texels.

3. AMBIENT MARCH DOMAIN: KSA marches the min(layer chord, cap) so all
   7 samples land in cloud; ours marches to the band-TOP sphere exit,
   so downward directions spend most samples below the band (zeros) —
   our ambient occlusion from below is systematically weaker.

4. SLICE ROTATION AXIS: KSA rotates a PARABOLOID row (y, group 8x1x8)
   — every refresh touches all heights of a sky strip; we rotate the
   HEIGHT axis (z) — every refresh touches all of the sky at 8 of 48
   heights. Full-volume cadence 6 rounds (ours) vs 24 (theirs).
   Different staleness pattern, same steady state.

5. SLICE-SPHERE ROOT: KSA takes the FAR intersection (.y) always; we
   prefer the NEAR positive root. Identical while the origin is under
   the slice sphere (always true for our surface anchor + band radii
   unless the camera dives below the cloud base into a valley... the
   surface anchor keeps o inside minR, so ours is the .y case too in
   practice). Recorded because the code DIFFERS even though the
   behaviour coincides under our anchoring.

VERDICT: the sampler and the volume parameterization are a faithful
port; the build marches are faithful in structure with three
field-driven improvements and four small unintentional divergences,
all in the AMBIENT half. If the ambient look ever needs to match KSA
exactly, items 1-3 are the knobs, in that order.

### What actually blocks retiring the LIGHT GRID (2026-08-07, user: "can we remove the Light Grid? so we only rely on the KSA lighting implementation?") {#cloud-upscale-what-actually-blocks-retiring-the-light-grid}
SUPERSEDED 2026-08-07 (same day, second read): the "decide what feeds
the MS and zenith terms" step DOES NOT EXIST. Every grid consumer
already carries a compiled non-grid fallback behind its own #if chain:

```
KSA march far tap       #if SV -> #elif GRID              (:5718)
atmosphere shadow term  #if SV -> #elif GRID -> live march (:4728)
atmosphere_clouds MS    #if GRID -> 4-sample coarse vertical march
mainImage Dc_zenith     #if GRID -> estimateCloudVerticalColumnFromWeatherMap
march_cloud_segment x3  -> retire with the house march
```

So flipping USE_CLOUD_LIGHT_GRID off is SAFE TODAY in every config, and
the SV toggle survives the removal: SV off falls through to the live
march - slower, still correct. The actual remaining distance:
 (1) FIELD VERDICT on the shadow volume look (default ON since
     2026-08-07) - gates everything, zero code.
 (2) Retire the house march + cloudSunDensityHybrid - the decision is
     already made ("KSA is the transport"); kills 3 of 5 consumers.
 (3) Flip the grid off -> the fallbacks take over. Known costs: the MS
     zenith tap becomes a 4-sample march per MS step, and the
     2026-07-26 "Grid-G unification" reverses - the AO sites re-derive
     their own columns and can spatially disagree under a broken deck;
     unify the fallbacks on the weather-map column if it shows.
 (4) Delete the machinery: the bake driver + host regen/anchor/cache,
     the 7th channel (uCloudLightGrid) in every builder, 3 props + UI
     + presets, 20 GLSL gate sites collapsing to their #else content.
     Same shape as the lighting-sky removal.
No open design questions - (2)+(3) are one session, (4) the big
mechanical one.
Toggle: cloud_shadow_volume, DEFAULT ON since 2026-08-07 (user: "default
the shadow volume on, I'll test it"). Off falls back to the light grid.

### DIRECTION SET 2026-08-07: the KSA march is the one that ships {#cloud-upscale-direction-set-2026-08-07-the-ksa-march-is-the-on}
User: "I decided to use the KSA lighting and sampling. it feels faster
and looks better. once the KSA cloud sampling and lighting is
integrated we can modify it to my liking." So cloud_ksa_march (already
default ON) is no longer an A/B toggle pending a verdict - it is THE
transport, and the Fewes-calibrated house march is legacy. Two
consequences worth writing down:

- Tuning from here targets the KSA march. Its constants are a faithful
    port, not a calibration, so expect them to move once the look is
    being dialled in - that is the stated plan, not drift.

- This clears step (3) of the light-grid retirement order above. With
    the house march legacy and the shadow volume now default ON, what is
    left is deciding what feeds atmosphere_clouds' MS term and
    mainImage's Dc_zenith, which read the grid's zenith-column channels
    and run regardless of which march is selected.

### Stage 2b: the KSA MV-reproject resolve (user 2026-08-06: "can we do the TAA and upscaling pass that matches KSA?") {#cloud-upscale-stage-2b-the-ksa-mv-reproject-resolve}
GOAL: sharp clouds UNDER MOTION — replace the 2a-lite "refuse stale data"
motion mode (whole field at quarter res) with KSA's "warp stale data into
place".

ENABLING WORK DONE (2b-i, this commit): the cloud pass's depth lane is now
the TRANSMITTANCE-WEIGHTED CENTROID in BOTH marches (the house march
always was; the KSA port published the first hit). That lane is KSA's
`averagePosition` — every downstream piece of their resolve keys off it.

DONE (2b-ii..iv, 2026-08-07) — shaders/passes/cloud_resolve_lib.glsl, one
library behind a frag pass and its compute twin (verified bit-identical
on a synthetic field):

1. PING-PONG. cloud_split_tex is now TWO triples (L, T, A) with a
   per-round flip; the resolve reads one side and writes the other.
   The 2a discard-resolve is gone — it read-modify-wrote a single pair,
   which is only legal while nothing reads history at a WARPED location.
   The pair is also sized to the rect's DISPLAY dims now, NOT the march
   dims: the TAA carve-out marches at half res while moving, and
   following that reallocated the pair (dropping all cloud history) on
   every motion start/stop, exactly when the MV resolve needs it. The
   sky pass taps by normalized UV, so the two resolutions may differ.

2. MOTION VECTORS without matrices, as specced: each 3x3 tap's centroid
   distance turns its ray into a world point, projected through the
   history frustum's sign-fixed dual basis (`cloud_hist_view` /
   `cloud_hist_origin`, the rect TAA's convention). The CURRENT frustum
   is not a push constant either — u_pa2.cam0/1/2 ARE the rows the
   cloud pass built its rays from, so the reconstruction is exact
   (jitter and overscan included). Verified: MV is exactly 0 under an
   identity basis and tan(theta)/2 under a theta yaw.

3. RESOLVE PASS: as specced above, 1:1 with UpscalingFunctions.glsl.
4. COMPUTE TWIN: same library, imageStore instead of MRT. The 2a
   `pOut = p*4 + cell` scatter in rect_compute_main.glsl retired with
   the hold-resolve — low rounds store plainly and the resolve gathers.
BUFFERS: no new textures. The centroid distance already had a lane
(L.a, which the sky pass reads for aerial perspective); the motion
vector, sample counter and a coherent copy of the distance ride ONE new
RGBA16F A plane per side, and a FULL-res cloud round seeds it for free
by binding it to the cloud pass's FragIndirect slot.
DEVIATIONS from UpscaleCloud.comp, both forced by PA2's architecture and
documented at the head of cloud_resolve_lib.glsl: no scene-depth branch (our
cloud buffer is pre-cutout, so it has no terrain discontinuity to
defend against — only a cloud-distance one, which distanceDisocclusion
already handles), and the current cell stores its OWN tap distance
rather than the 3x3 min.

5. RETIRED the lowfull motion mode (2b-v). Motion no longer selects a
   mode at all: a moving round interleaves exactly like a still one and
   shows warped full-res history instead of a 4x bilinear blur — the
   stated goal of 2b. What survives is the
   WARM-START: a CONTENT change (params, sun quantum, shader, surface
   size — the TAA engine's own hard key, which zeroes its round
   counter) re-marches one full-res round, because warping a history
   whose clouds were lit differently drags the wrong radiance across
   the screen. Pose is the resolve's job and is deliberately NOT in
   that key. Landed as its own commit so the field verdict on motion
   can revert it without losing the machinery.
2b-vi (2026-08-07, user: "to me it feels slower than before"): THE
VIEWPORT NO LONGER FULL-RES MARCHES CLOUDS AT ALL — the last real
difference from KSA's frame graph, which has no full-res cloud march
anywhere. The resolve's reset path already builds a COMPLETE frame from
the low pass alone (current cell exact, the rest its bilinear upscale)
at 1/16 the cost and sharpens over the next 16 rounds, so a "warm-start"
never needed a full march. Worse, 2b-v had re-keyed when that spike
fires: the TAA hard key quantizes the view ORIGIN, whose cell churns
*while flying* (see \_KEY_MEMO's own note), so every cell crossing
bought a 16x round mid-navigation. Pre-2b that path was masked because
`_moving` was tested first and won. Renders keep the full-res march
(they are gated out of the interleave entirely).

COST (measured 2026-08-07, RTX 4080 / Vulkan; ca66d8f's commit message
claims 2b-v is ray-count-neutral, which is WRONG — the correction):

- STILL rounds are neutral on the march and pay the resolve. Cloud rays
    are ceil(W/4) x ceil(H/4) before and after; the near-free 2a
    discard-resolve becomes a real full-res pass at 0.38 ms (3152x1859),
    0.17 ms (1920x1080), 0.14 ms (1568x928) — roughly half what the rect
    TAA resolve alongside it already costs every round.

- MOVING rounds cost 4x the cloud march they used to. The retired
    lowfull mode ran off the SAMPLE dims, which the TAA carve-out halves
    while moving, so its quarter-res field was quarter-of-half = W\*H/64
    rays. Interleaving runs off the DISPLAY dims: W\*H/16. At 3152x1859
    that is 91k -> 366k rays per moving round, plus the 0.38 ms resolve.
    Still a cheaper round than a still one overall (the sky march, the
    dominant term, stays half-res while moving), and 366k/round is a load
    the still rounds already sustain — but navigation is measurably
    busier than before. Watch `rect cloud pass (low-res)` in the sky
    profile; if it is too hot, that is what 2b-v bought the sharpness
    with, and reverting 7ab1049 gives it back at the old softness.

- VRAM: +4 full-res RGBA16F (the L/T ping-pong plus the A plane both
    sides) = +187 MB at 3152x1859, +66 MB at 1920x1080, +47 MB at
    1568x928. The Sky Resolution divisor is the lever.

- The FULL-RES round is gone from the viewport (2b-vi). It was 16x an
    interleaved round (5.9M rays at 3152x1859) and pre-2b it fired on
    every motion STOP; 2b-v moved it into navigation itself. Now: never.
WHERE THE REMAINING COST IS: our per-ray march, not the scheme. KSA
interleaves harder than we do (1/9 vs our 1/16) and still runs it every
frame, because teardown priorities 3 and 5 — the density early-out
cascade + the (cloudType, heightFrac) vertical-profile LUT, and the
groupshared finite-difference mips — make each of their rays much
cheaper. Neither is ported. That is the next real speed stage; 2b is a
QUALITY stage and was never going to make navigation faster than
marching 1/64 of the field did.
FIELD VERDICT LANDED (2026-08-07 late): "i am still not satisfied with
the cloud reprojection, upsampling and TAA... i would prefer 1:1 pixel
size always... i would see the dithering pattern" — then the question
that redirected the fix: "how does KSA do it? it looks sharp in the
game." KSA's Atmosphere.comp is full-res, deterministic, temporally
UNFILTERED — the cloud resolve is their ONLY temporal system and it is
the sharp part. Ours wrapped that same resolve in three softeners they
do not have: a HALF-res moving sky march, a second Catmull-Rom history
warp in the rect TAA, and film reconstruction of a stochastic march.
2b-vii (da2dcb8) removed ours and kept theirs: primary march 1:1 at
display resolution always, moving rounds are fresh full-res frames
(film reset, rolling jitter, visible dither — the accepted trade),
stillness accumulates, mode 1 dead in the host (dual-basis machinery
survives only in the PRE_VIEW warp bridge), cloud MV resolve untouched,
cloud resets keyed on the TAA hard-change flag. WATCH: a moving round
costs ~4x the old half-res round; if motion cadence drops to
warp-bridge frames, the KSA-shaped levers are cheaper rays (#11) and
3x3-at-higher-cadence — not resolution drops.


## North Offset — Design (2026-07-31) {#north-offset}

`shipped:`{: .label-fixed } Implemented 04.09.2026 · 31.07.2026 · `docs/design-north-offset.md`

**In this document:** [The shape of the problem](#north-offset-the-shape-of-the-problem) · [Touch points](#north-offset-touch-points) · [Decisions needed before implementation](#north-offset-decisions-needed-before-implementation) · [Exit gate](#north-offset-exit-gate) · [Cost](#north-offset-cost)

**STATUS: IMPLEMENTED 2026-09-04** (user request; deferred 2026-07-31).
`north_offset` lives next to latitude/longitude. The three decisions
below were settled as recommended: (1) sign — scene azimuth = true
azimuth + offset, i.e. scene = Rz(−offset)·ENU, so +30° turns the
environment 30° clockwise seen from above; (2) the azimuth readout
stays astronomical (its description says so); (3) the georeference
follows — the cloud map, the wind, the graticule, the city-light map,
the star sphere, the flight paths and the compass all turn together.
As built: `get_sun_vector`/`direction_vector_to_azimuth_elevation`
take the offset as a third argument, `scene_from_enu_matrix` wraps
every equatorial→ENU matrix (stars, trajectories, body rotation
columns), the shader charts rotate through `pa2NorthToEnu` (UBO lane
`cl_skew2.y`), and the offset is in the bake keys. Exit gate:
`NorthOffsetTests` — bit-identical at 0, the +30° sign, the inverse
round trip, and the matrix/vector agreement.

---

A single angle that rotates the modelled world relative to true north,
so GIS-derived geometry can be used at its imported orientation instead
of being rotated to match the sky. Requested by users migrating from
Blender's Sun Position addon, which has the same control.

Convention, as the requesting user states it: *"A positive north offset
of 30° used to rotate the environment 30° clockwise. This is consistent
with other GIS software convention where true north would be 30°
clockwise from the model's current up direction."*

### The shape of the problem {#north-offset-the-shape-of-the-problem}

One function converts an azimuth into a world-space direction:

```python
def get_sun_vector(azimuth, elevation):   # core/celestial_math.py
    phi = -azimuth
    theta = pi / 2 - elevation
    ...
```

Sun, moon, planets, constellation labels, constellation segments and
the motion-path overlay all reach world space through it — 24 call
sites across `core/celestial_math.py`, `core/atmosphere_world.py` and
`overlay/overlays.py`. Adding the offset to `phi` there rotates every
one of them together, which is most of the feature.

The risk is not those. It is the systems that reach world space by a
DIFFERENT route and would silently stay put while the sky turns.

### Touch points {#north-offset-touch-points}

#### Tier 1 — follows automatically from `get_sun_vector`

- sun, moon, planets (position and the derived world_pos)
- constellation labels and segments
- motion paths overlay
- the synced Blender sun lamp, which consumes the vector rather than
    the angle, so it inherits the rotation for free

#### Tier 2 — separate paths, must rotate in lockstep

1. **The star sphere.** `M_stars` is built from
   `equatorial_to_local_enu_matrix_from_observer(...)`
   (`core/atmosphere_world.py`, near the `_rotation_columns` call), not
   from `get_sun_vector`. Miss it and the constellation OVERLAY rotates
   while the rendered stars behind it do not, which is worse than
   neither moving.

2. **The cloud and ground georeference.** `_observer_latlon_basis`
   (`core/offscreen_sky.py`) feeds `cl_global2`, the ENU->ECEF basis
   that pins the global cloud map and the ground lat/lon graticule to
   real geography. **This is the dangerous one.** It fails quietly: a
   30° offset would decouple the weather and the graticule from the sun
   without any obvious symptom, and the bug report that came back would
   be "the clouds are in the wrong place", not "the north offset is
   broken".

3. **The compass overlay** (`_compass_screen_data`, `overlay/overlays.py`).
   If it does not rotate it stops pointing at true north, which is the
   entire purpose of the feature.

4. **Cloud wind headings.** Wind is expressed in scene ENU. If north
   moves, the headings move with it, or a north-easterly stops being a
   north-easterly. See [[cloud-wind-shear-windmap-todo]] for the planned
   spatially-varying wind map, which would inherit the same question.

5. \*\*`direction_vector_to_azimuth_elevation`\*\* (`overlay/overlays.py`,
   the artistic drag-the-sun inverse). It must subtract the offset, or
   grabbing the sun makes it jump by the offset on the first drag event.

#### Tier 3 — check before shipping

- `core/trajectory.py` (OEM paths) builds directions from its own state;
    confirm whether it needs the rotation or is already in a rotated frame.

- The shadow-caster sun matrix and the cloud shadow plane both derive
    from the sun vector, so they should follow, but verify rather than
    assume: both cache on a key that must include the offset.

- Any bake key that caches on sun direction needs the offset in it, or
    changing the offset will not invalidate the cache.

### Decisions needed before implementation {#north-offset-decisions-needed-before-implementation}

1. **Sign.** `get_sun_vector` already negates (`phi = -azimuth`), so the
   direction of a positive offset must be derived against that, not
   assumed, and then confirmed against the compass overlay and the
   user's stated convention (+30° puts true north 30° clockwise from
   the model's up direction).

2. **What the azimuth readout reports.** True astronomical azimuth, or
   the offset one? The readout is labelled "Rotation angle of the Sun
   from the direction of the north", which becomes ambiguous the moment
   there are two norths. Recommendation: keep the readout astronomical
   and note the offset beside it.

3. **Whether the georeference follows** (tier 2, item 2). There is a
   real argument that it should NOT: the offset is a modelling
   convenience for aligning imported geometry, and rotating the cloud
   map means the weather no longer matches the coordinates the user
   georeferenced against. The counter-argument is that a scene where
   the sun and the cloud map disagree about north is incoherent, and
   the graticule would visibly contradict the compass.
   Recommendation: rotate everything, so the scene stays internally
   consistent, and document that the cloud map rotates with it.

### Exit gate {#north-offset-exit-gate}

An offset of 0° must be **bit-identical** to the current build. That is
the parity test to write first, before any of the rotation goes in: it
catches a sign error in tier 1 and, more usefully, catches a tier 2
system that was wired to the offset when it should have been left alone.

Then, at a non-zero offset, the checks that matter are cross-system
rather than per-system: compass, sun, star sphere and graticule must all
agree about where north is, in one screenshot.

### Cost {#north-offset-cost}

Roughly half a day for tiers 1 and 2 with the parity gate, assuming the
three decisions above are settled first. Tier 3 is verification rather
than new code.

The property itself is trivial (one angle, `unit="ROTATION"`, in the
same block as latitude and longitude). Every hour of this estimate is in
the systems that do not go through `get_sun_vector`.


## Ground Shader — Design (2026-07) {#ground-shader}

`shipped:`{: .label-fixed } Shipped · 2.7 · BRDF superseded 08.2026 · 07.2026 · `docs/design-ground-shader-2026-07.md`

**In this document:** [Why a separate shader](#ground-shader-why-a-separate-shader) · [Data flow](#ground-shader-data-flow) · [Ground-shader samplers](#ground-shader-ground-shader-samplers) · [Requirements → design](#ground-shader-requirements-design) · [8a — the new grid-column arm](#ground-shader-8a-the-new-grid-column-arm) · [8b — the older slab arm was lit by the wrong sun](#ground-shader-8b-the-older-slab-arm-was-lit-by-the-wrong-sun) · [UI](#ground-shader-ui) · [Rebake & cadence](#ground-shader-rebake-cadence) · [Validation](#ground-shader-validation) · [Phases](#ground-shader-phases)

Status: SHIPPED in 2.7, BRDF SUPERSEDED (as of 2026-09-10). The compose
pass, the T→0 fold, water reflections, cloud bounce, night lights,
object shadows, moonlight and the heightmap (`earth_height_image`,
bicubic, normals, Terrain Height) are all live. What §3 recommends is
NOT what runs: the Hapke-lite land BRDF, the Chandra-Hapke branch, the
separate kSpec specular and the Surge knob were retired on 2026-08-26 —
the PRINCIPLED land model is the only one (one GGX lobe for specular,
sky reflection and roughness; water joins the same lobe; LTC disc
specular for sun and moon; real split-sum; MS and ozone in the sky
reflection). Phase 3 (refraction) is owned by the refraction design;
the ground rises with the walked rays there.

A dedicated GPU compose pass that shades the planet surface offscreen
and folds it into the S/T pair, retiring the node-tree `PhysicalPlanet`
shading path (kept behind a toggle). Follow-up to compositor v8: the
world formula `background × T + S` means a texel with the shaded ground
folded into S and T forced to 0 renders the earth with ZERO node-tree
changes — the planet group multiplies itself out.

### Why a separate shader {#ground-shader-why-a-separate-shader}

Sampler limits are per program. The main driver sits at 15/16 slots;
the ground shader is a fresh program that needs none of the cloud
machinery — it consumes the main march's outputs. It compiles in
seconds (not the 9000-line driver), runs as a fullscreen multiply-add
at image resolution (sub-ms), and iterating on surface shading never
touches the march.

### Data flow {#ground-shader-data-flow}

```
main march  ->  S, T, SHADOW(.a = ground-hit/occlusion), INDIRECT
                     |            (post temporal resolve/rectify)
                     v
ground compose  ->  S' = S + T * ground_radiance     (ground texels)
                    T' = 0                            (ground texels)
```

Runs on BOTH pipelines, always as the LAST step:

- equirect: after the accum resolve / roll scatter / draft publish
- rect: after `_rect_rectify` and the idle-AA publish

History/warp machinery therefore operates on pure atmosphere; the fold
is deterministic on top. The compositor needs no change: S/T are the
cut pair, and the compose respects `uViewGeoDepth`, so object pixels
keep truncated columns (no ground bleeding through geometry).

### Ground-shader samplers (own budget, ~10/16 used) {#ground-shader-ground-shader-samplers}

| Slot | Sampler | Content |
|---|---|---|
| 0 | `uSrcS` | scatter (pre-fold) |
| 1 | `uSrcT` | transmittance (pre-fold) |
| 2 | `uSrcShadow` | sun transmittance at ground + hit flag (.a) |
| 3 | `uSrcIndirect` | measured ambient at ground (SS+MS+airglow) |
| 4 | `uEarthDay` | day albedo RGB (user slot; A free) |
| 5 | `uEarthNight` | night-lights emission (user slot) |
| 6 | `uEarthHeight` | heightmap (user slot; water mask = h <= sea level) |
| 7 | `uViewGeoDepth` | scene-geometry camera depth (skip occluded ground) |
| 8 | `uCasterDepth` | scene-geometry SUN depth (object shadows on ground) |
| 9 | `uCloudLightGrid` | cloud bounce + water-reflection modulation |

Six slots spare for normals/detail/seasonal later.

**Shipped numbering (2026-07-29) — the table above is the plan.** What
the program actually declares:

| 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 |
|---|---|---|---|---|---|---|---|---|---|----|
| `uSrcS` | `uSrcT` | `uSrcShadow` | `uSrcIndirect` | `uEarthDay` | `uEarthWater` | `uEarthNight` | `uEnvS` | `uEarthHeight` | `uCasterDepth` | `uCloudLightGrid` |

Two drifts from the plan, both harmless. `uEarthWater` and `uEnvS` are
real slots the plan never listed, which pushed everything down; and
items 10 and 8 were built in parallel, both reaching for "slot 9" — the
caster map got there first, so the light grid took 10. Sampler slots
need no contiguity and there is no gap here anyway. `uViewGeoDepth` is
still unbuilt: the compose inherits the geometry cutout through S/T
instead, since the march already applied it.

### Requirements → design {#ground-shader-requirements-design}

#### 1. Atmospheric refraction (ground rises at the horizon)
Effective-radius model (the k ≈ 7/6 terrestrial-refraction standard):
a shared helper `pa2GroundIntersect(ro, rd)` intersects against
R_eff = k·R for VIEW-ray geometry only; density/optical-depth integrals
keep true R. Strength rides the existing refraction machinery
(core/refraction.py already refracts the celestials), so the sun sets
exactly on the risen horizon — one consistent story. CRITICAL: the
helper lives in a shared GLSL block used by BOTH the main march's
terrain clamp (seg.y) and the compose pass — if only the compose knew
about refraction, the band between true and refracted horizon would
have no SHADOW/INDIRECT content to shade with.

#### 2. Heightmap-ready (and height felt by atmosphere + clouds)
`pa2GroundIntersect` is THE ground interface: today analytic
(refracted) sphere; phase 5 adds heightmap displacement. Two-tier:

- main driver: conservative clamp against R + maxHeight, then the
    shared exact hit (coarse heightmap on its ONE free slot, 15) —
    aerial perspective ends at terrain, cloud shadows land on terrain
    height, the INDIRECT/light-grid columns start at terrain height.
    Everything inherits because the hit function is shared.

- ground shader: full-res heightmap for texel-exact hits + normals
    (central differences).
**Water mask = heightmap**: water where h <= `earth_sea_level` (UI
value, meters). No separate mask texture.
**Water surface = analytic sphere** (user insight): with terrain on,
the water surface is the sphere at R + seaLevel — one quadratic, no
march. Ordering is automatic: intersect the sea sphere at t_w, march
terrain over [t0, min(t1, t_w)] — terrain first = land (mountains
occlude water behind them), else water at t_w.
**Bathymetry = the same heightmap below sea level**: vertical water
depth d = seaLevel - h at the hit; along-path depth d / cos(theta_refr)
(Snell) feeds spectral Beer-Lambert (red dies in meters, green in
tens, blue ~100 m) -> analytic shallow-water color: reef turquoise as
bottom albedo x T^2(d), the shelf turquoise->deep-blue gradient traced
from real coastline bathymetry, and the shoreline froth/wet band keyed
on small d instead of a mask distance. The underwater vector is literally GLSL refract(rd, n, 1/1.33) at the
(wave-perturbed) surface normal — always valid entering water (TIR
only exists water->air), the refracted LANDING point picks the
bottom-albedo texel (view-dependent bottom shift in shallows, and the
wave normal makes the bottom shimmer coherently with the GGX lobe).
(Steep-slope grazing views can later refine the refracted segment
with 1-2 coarse max-mip taps along the SAME vector; the analytic form
is the default tier.)

#### 3. BRDF — Hapke-lite diffuse + GGX water (recommendation)
- LAND: Hapke IMSA reduced to the terms that read from altitude:
    single-scatter albedo from `uEarthDay`, Henyey phase p(g), and the
    OPPOSITION SURGE B(g) = B0 / (1 + tan(g/2)/h) — the real
    "hot spot" glow around the antisolar point in aerial photography.
    B0 default modest (surge is extra-physical vs the Cycles referee —
    keep it a knob, `earth_opposition_surge`).

- WATER: GGX microfacet with Fresnel n = 1.33, roughness knob
    (`earth_water_roughness`), covers the sun glint path by
    construction. Moon glint falls out of the same lobe (see 7).

- Blend land/water by the sea-level mask; wet-sand band near the
    shoreline blends roughness.

#### 4. Water reflections of sky AND clouds (aerial-aware, layered)
The S image is CAMERA-anchored, so a raw S-sample at the reflected
direction is only exact near the surface: from altitude the water
point P sees a different sky (clouds misregister toward the camera;
a grazing reflected ray at sea level crosses thick horizon air while
the same vector from 10 km crosses thin air). Error structure is
benign — Fresnel is ~2% at the steep angles where misregistration is
worst, and at grazing incidence (high Fresnel) both observers'
directions converge on the horizon — but aerial views need the
layered form:

- SHARP term: Fresnel-weighted S-sample at the reflected direction
    (small Poisson blur by roughness). Exact on the beach, decent at
    grazing, camera-flavored in the aerial mid-angles.

- ROUGH/FAR limit: blend toward INDIRECT AT THE TEXEL — it is
    evaluated at the ground hit, from the measured LUT at P's altitude
    with the grid up-column above P: the position-correct hemisphere
    integral of P's own sky (clouds included). At aerial distances the
    mirror detail is sub-texel anyway, so this is also the physically
    right limit.

- Blend driver: distance-to-P x footprint-grown effective roughness
    (LEAN-style); grid up-column modulation covers the transition band
    (distant water under a dark deck must not mirror the camera's
    sunny sky).

- Sun/moon glint: analytic GGX lobes at P with true light directions
    — correct at any altitude, independent of this layering.

#### 5. Ambient from the atmosphere (incl. airglow)
`INDIRECT` already carries the measured ambient: SS + MS ground
bands of the LUT, and airglow rides the MS bucket
(`AIRGLOW_MS_AMBIENT_SCALE` in ms_eval → LUT → INDIRECT). At night
the sun terms vanish and the airglow floor survives — moonless nights
keep a physically-sourced ambient. Compose consumes INDIRECT.rgb
directly; nothing new to build, verify the night floor in the
referee pass.

#### 6. Multiple scattering from the atmosphere
Same story: the MS ground band is already summed into INDIRECT (with
ATMOS_MS_GAIN baked at LUT build). Met by construction; listed for
the validation matrix.

#### 7. Moonlight (new)
- Direction/visibility: `PA2_DATA_MOON` idprops (already in the UBO
    as the eclipse vec4 — extend gather with a moon-irradiance vec4:
    RGB = phase-weighted irradiance, w = visibility).

- Irradiance: from the existing celestial math (phase angle +
    distance), sun-spectrum × lunar albedo tint.

- Transmittance to the moon: the analytic Chapman transmittance
    helpers (cheap, no march); NO cloud shadowing of moonlight in v1
    (the light grid is sun-anchored) — noted as a follow-up.

- Applies to both BRDF lobes: moonlit land + the moon glitter path
    on water.

#### 8. Cloud bounce (user addition) — CLOSED 2026-07-29
Sunlit cloud material re-radiates downward — the bright-underside
gain under broken decks. Source: the cloud light grid's column above
the ground point: occupancy × sun-column brightness integrated down
the B/R channels → a sun-tinted additive ambient term,
`earth_cloud_bounce` knob. This is the ground-side mirror of the
cloud shader's ground-bounce arm — the two together close the
ground↔cloud light loop.

It landed as TWO arms, built independently and merged. Read them
together — the item is only closed because both are in.

### 8a — the new grid-column arm (`gcCloudBounce`, the compose) {#ground-shader-8a-the-new-grid-column-arm}

SHIPPED 2026-07-29 (`gcCloudBounce`). Walks the ACTIVE layer band
(min active `cloudLayerAltitude` → `LAYER_PEAK_H`, so the steps land
in cloud altitudes rather than in empty air below) at the grid's OWN
slice pitch:

    E_down = 1/2 * SUM_k  omega*(1 - exp(-Bec*rho_k*dh)) * T_sun,k * T_down,k

TWO QUADRATURE TRAPS, both caught by probing the live baked grid
rather than by reading the code:

- The step source must be the ANALYTIC within-step integral
    `omega*(1-exp(-tau_step))`, not the rectangle `sigma_s*dh`. Steps
    here are hundreds of meters against `sigma_e ~ 1e-2/m`, so
    `tau_step` is order 1-5 and the rectangle blew past the
    single-scatter ceiling — measured 281 against a 206 sun irradiance.
    The analytic form is bounded by omega for any dh, which also makes
    the result step-count independent.

- The step COUNT must track the grid, not be a constant. The volume
    has 32 altitude samples over `[0, LAYER_PEAK_H]`; finer steps
    resample the same trilinear interpolant, coarser ones alias whole
    cloud layers in and out. On a live 6.75 km band vs a 96-step
    reference: 8 steps was off 142%, a fixed 12 was off 13% with single
    pixels off by the ENTIRE signal, slice-matched lands at 2.0% with
    the worst pixel at 0.66 instead of 5.6. Cost scales with the scene
    as a bonus — one thin stratus deck costs a handful of taps.

`rho` = the grid's baked occupancy (B), `T_sun` = `exp(-Bec*D_sun)`
from the R channel (cloud self-shadowing and Shadow Casters already
in it) × the atmospheric sun transmittance AT THE SAMPLE (the sun
tint), `T_down` = Beer back down the column. The atmospheric factor
uses the one-line Chapman surrogate `1/(mu + 1/chX)`,
`chX = sqrt(pi r / 2H)` — exact at zenith and at the horizon, and it
caps below the horizon instead of exploding. The planet's own shadow
is tested per sample against the ALTITUDE-DIPPED horizon, so cloud
bases stay lit after the ground under them has set (the sunset
underlight falls out of the geometry, no special case). The result
joins INDIRECT, so land diffuse, the water body and the rough-limit
water reflection inherit it consistently, and it fades out past 75%
of the grid's bake radius rather than smearing the rim texel over
the far hemisphere.

NOT the same quantity as the driver's `cloudBounce` already inside
INDIRECT (`cloud_ground_downflux`, "Cloud Bounce" under Clouds):
that one is the delta-Eddington FORWARD-diffused sun through a
saturated overhead slab — the overcast lightbox. This is the
backscatter/side-lit arm the slab model cannot see. They overlap
under thick uniform decks, so both default low and are dialled
independently.

The chart/fetch this arm needs are LIFTED from the shared GLSL
(`// PA2_SHARED_BEGIN <name>` markers + `_shared_glsl_block` /
`_grid_chart_glsl` on the host) rather than hand-copied: a duplicate
would drift the day the sqrt radial warp or the sqrt encoding is
retuned, and the failure mode is a silently mis-registered lookup.
`PA2_GRID_PARABOLOID` and the grid shim dims are baked into the
extracted source, so both are part of the compose shader's key.

GPU only: the render/readback CPU fold would have to read the 3D
volume back per fold. Documented divergence, same class as the GGX
glint and the water reflections.

Live verification (Vulkan, the session's own baked 128³ grid, 1024×512
equirect): additive on ground texels with the sky bit-identical,
exactly linear in the knob, a no-op on the zeroed dummy volume, all
finite, ~9% gain on ground S at gain 1.0. The x8 difference image
shows the intended signature — dappled cloud-gap structure, warm
toward the low sun, zero above the horizon. The 128³ grid's texels are
visible in that amplified diff but add only 4.5% high-frequency energy
to the composed ground, so they are not an artifact at shipping gains.

### 8b — the older slab arm was lit by the wrong sun {#ground-shader-8b-the-older-slab-arm-was-lit-by-the-wrong-sun}

The march has carried a per-ground-texel cloud bounce into INDIRECT
since before this document, and the compose consumes it
(`albedo * ind`): the delta-Eddington forward downflux on the light
grid's G channel, on the `cloud_ground_downflux` knob, eclipse-correct,
correctly bypassing the sky AO. That term was fine. Its **light source**
was not.

It used raw `sunIrr` — top-of-atmosphere, unreddened — so a deck
re-radiated noon-coloured light onto the ground at every sun elevation,
while the direct sun beside it (SHADOW, which does carry the air
column) went orange and dim. The cloud marcher's own ground-bounce arm
has always tinted its side by `sunThroughAtmosphereRGB`; the ground
side now does the same, so both ends of the loop finally use the same
sunlight. Evaluated at the DECK (`LAYER_PEAK_H * 0.5`, the house
representative cloud height): the slab is lit at its own altitude, on
the shorter slant column. Inside the existing `coschi > 0` branch the
sun ray from the deck provably leaves outward, so no planet-occlusion
test is needed. Measured ×0.83 and slightly warm at 60° sun, ×0.55 at
15°, ×0.13 at 3°. Scenes tuned against the old white term want Cloud
Bounce raised.

**Why 8a is a separate arm rather than a rewrite of 8b.** The sketch at
the top of this item — occupancy × sun-column brightness down the B/R
channels — reads like a replacement for the delta-Eddington slab. It
must not be one. That slab's current form IS the fix for "bounce looks
very wrong" (2026-07-09): it takes the VERTICAL column and the
incidence `mu` separately, and feeding it the sun-SLANT column blew up
at low sun and lit the ground as if overcast whenever any cloud sat
sunward. Building the column walk as its own backscatter/side-lit arm
keeps that fix intact and gains what the plane-parallel slab genuinely
cannot see — a cloud sunward but not overhead. The two overlap under
thick uniform decks, so both default low and are dialled separately.

**Why 8b stayed in the march.** Its tint needs `density_integral` /
`aerosol_density_integral` / `ozone_tau` — the air-column library the
compose exists specifically not to carry ("needs none of the cloud
machinery — it consumes the main march's outputs"). It cannot be
recovered from SHADOW either: that buffer is air × cloud column, and
dividing the cloud part back out explodes under a thick deck. 8a
sidesteps this with the Chapman surrogate, which is self-contained.
INDIRECT is the designated transport for ground ambient and both arms
ride it, so every downstream consumer stays energy-consistent.

#### 9. Night lights
`uEarthNight` emission, gated by the sun's ground illuminance
(smoothstep on twilight) so cities fade in through dusk. Additive,
tone follows the map; `earth_night_lights` gain.

#### 10. Object shadows on the baked ground — SHIPPED 2026-07-29
The node path got them via the shadow plane; the compose pass tests
`uCasterDepth` (sun depth map) at the ground hit — same machinery as
cloud-shadow casters.

As built, with two deviations from the sketch above:

- \*\*The march no longer folds `pa2CasterShadow` into SHADOW.\*\* It did
    (that predates this design), but SHADOW rides the temporal
    accumulator — phase frames, reprojection warp, bilinear upsample.
    Clouds tolerate that; a caster silhouette does not, so a moving
    object dragged a lagging, streaked shadow. The compose runs *after*
    the resolve against the current map, so ownership moved there whole:
    one applier, frame-exact, no double-multiply.

- **Soft, not one texelFetch.** `pa2CasterShadowSoft` (4 taps, sun
    angular-radius penumbra floored at ~2 map texels). Nothing downstream
    blurs the compose the way the volumetric marches blur themselves, and
    a single hard 1024² tap aliases on a surface the camera looks
    straight at.

The readback/render fold has no sampler, so `_caster_shadow_cpu` is the
numpy twin of the same helper over a key-cached CPU mirror of the map
(`_caster_depth_cpu`) — without it the F12 path would have lost object
shadows along with the march's term. Gating is free: no casters →
`cs_center.w = 0` → the helper returns 1.

`core/shadow_plane.py` stays as-is and is unrelated: it puts CLOUD
shadows onto scene objects (the other direction).

### UI (user addition: exposed samplers) {#ground-shader-ui}

New "Earth / Planet" surface block (world panel, near the existing
planet section):

- Image slots (PointerProperty, `template_ID`, same idiom as the
    cloud coverage slots): **Day Albedo**, **Night Lights**,
    **Heightmap**. Empty slot = bundled default (current earth texture
    set); heightmap empty = analytic smooth sphere (no terrain, mask
    from the bundled ocean mask fallback... v1: no heightmap = all-land
    unless the day map's A carries the bundled water mask).

- Values: Sea Level (m), Water Roughness, Opposition Surge,
    Cloud Bounce, Night Lights, Terrain Height Scale (phase 5).

- Master toggle: `earth_baked_shading` (default OFF for one release —
    the node path stays the fallback; toggle purely python-side).

### Rebake & cadence {#ground-shader-rebake-cadence}

- Compose inputs change with every bake/slice — compose re-runs after
    each publish (it is sub-ms; no own key needed).

- Earth textures enter `_shader_source_key`-adjacent state: swap =
    re-upload + one compose; sea level / knobs ride the UBO (no
    recompile, next compose picks them up).

- F12: compose runs in the render hook after the multisample resolve
    (CPU-publish path included). Cycles engine: compose applies to the
    full-res equirect exactly like the viewport path.

- The heightmap (phase 5) joins the MAIN bake key (terrain changes
    the march) — coarse map on driver slot 15.

### Validation {#ground-shader-validation}

- P1 exit criterion: toggle ON with flat-albedo Lambert reproduces
    the node planet within noise (same passes, same math) — screenshot
    A/B.

- Referee: extend `cloud_debug_isolate` with GROUND_DIRECT /
    GROUND_AMBIENT / GROUND_SPECULAR; compare against a Cycles ground
    plane with Principled BSDF (Hapke surge OFF for the referee run).

- Night: moonless airglow floor, moon phases, city lights at dusk.

### Phases {#ground-shader-phases}

1. **Infrastructure** — compose shader + T→0 fold, equirect+rect
   integration, viewgeo/caster respect, toggle + Lambert
   look-preserving parity. (decision-free, start immediately)

2. **Lighting** — Hapke-lite + GGX water, sea-level mask, S-sampled
   reflections (+ grid locality), night lights, cloud bounce.

3. **Refraction** — shared effective-radius intersect, march clamp
   alignment, celestial-refraction consistency.

4. **Moonlight** — irradiance gather, transmittance, both lobes.
5. **Heightmap** — shared displaced intersect, coarse map in the
   main driver (slot 15), normals, terrain-aware aerial/shadows.
   March recipe (spherical-terrain optimized):

   - PERIGEE CULL: ray altitude r(t) is a closed-form hyperbola;
     if its minimum exceeds R+hMax the ray provably misses — one
     dot product rejects most of the frame (the spherical win).

   - SHELL BRACKET: [R+hMin, R+hMax] sphere pair -> tight [t0,t1]
     (the cloud-shell idiom).

   - MAX-MIP DESCENT: max-pyramid of the heightmap (Tevs-style
     maximum mipmaps); descend only where the ray's min altitude in
     a cell undercuts the cell max. The COARSE levels alone serve
     the main driver's conservative seg clamp; only the ground
     shader goes to texel level. Slope/step bounds are baked per
     mip cell in METERS (absorbs the equirect cos(lat) distortion —
     never a global Lipschitz constant on a stretched chart).

   - FOOTPRINT LOD: sample height at the mip matching the ray
     footprint (perspective step growth) — stable far silhouettes,
     normals from the same mip.

   - REFINEMENT: f(t) = r(t) - R - h(t) is monotone-bracketed on
     each side of the perigee -> 2-3 secant iterations.

   - TEMPORAL WARM START: store the hit distance in the alpha lane
     (the cloud-front idiom) and start next frame's march at the
     warped previous t minus a margin.
   (Rejected: cone-step maps — fight equirect anisotropy; flat-earth
   flattening — pointless, exact spherical r(t) is one fma.)

6. **Referee + defaults** — isolates, Cycles comparison, energy
   audit, ship defaults.


## Credits & references {#credits}

`reference:`{: .label-improvements } As shipped in the add-on · `CREDITS.md` · `THIRD_PARTY_LICENSES.md`

**In this document:** [Shader code used directly](#credits-shader-code-used-directly) · [Techniques & ideas adapted](#credits-techniques-ideas-adapted) · [Papers & data](#credits-papers-data) · [Blender](#credits-blender) · [Third-party licenses](#credits-third-party-licenses)

Physical Atmosphere² stands on a lot of published work. The
atmosphere/cloud reference implementation (`shaders/atmosphere_15/`) was
developed Shadertoy-first and is hosted in Blender by
`core/offscreen_sky.py`; its atmospheric core grew out of FordPerfect's
single-scattering shader (below), and many further techniques, formulas
and ideas come from — or were validated against — the sources listed
here. Thank you all.

### Shader code used directly {#credits-shader-code-used-directly}

- **Single scattering atmosphere — FordPerfect** (Public Domain /
    Unlicense)
    <https://www.shadertoy.com/view/X3fXRn>
    The foundation the whole atmosphere is built on: the Nishita93-style
    single-scattering integrator design, the fully analytic optical-depth
    approximation (Gaussian-exponent density → Chapman-function-class
    `density_integral`, still present verbatim together with
    `gauss_segment` and `quadratic_solve`), the planet-shadow segment
    splitting, the optimized-offset rectangle rule, the Jendersie–d'Eon
    Mie phase parameterization, the turbidity→Mie conversion, and the
    rigorous units discipline this project inherited.

- **Gaussian Airmass** — <https://www.shadertoy.com/view/4XSGzW>
    The erf/erfcx approximations and Gaussian line-segment integrals —
    essential to the analytic airmass integrals (optical depth, airglow
    line profiles).

- **Bubble integral** — <https://www.shadertoy.com/view/lcByRy>
    Likewise essential to the analytic airmass integral family.

- **CloudShape — Fewes (Felix Westin)**
    <https://www.shadertoy.com/view/7fX3zn>
    The cumulus silhouette sculpt (flat base, waist erosion, tapered crown)
    used by the rain-cloud body. Used with credit, marked in
    `atmosphere.glsl` at the function definition.

- **Moon — Bartosz Ciechanowski**
    <https://ciechanow.ski/moon/>
    The march-side moon (`shaders/passes/rect_celestials_lib.glsl`,
    `pa2CelMoon`) is a port of the interactive article's moon renderer:
    the octahedral color/height maps (with the precomputed cone-ratio
    channel that makes the traces converge), the cone-traced displaced
    surface with bisection refinement, the cone-assisted terrain
    self-shadow march, the octahedral-gradient normal reconstruction,
    and the Hapke-2012 shading (double-lobed Henyey-Greenstein phase,
    opposition surge, multiple-scatter H·H term). Adapted to PA2's
    radiometric units, earth penumbra/eclipse ring and scene-driven
    earthshine.

- **three-geospatial — Shota Matsuda (MIT License, © 2024)**
    <https://github.com/takram-design-engineering/three-geospatial>
    The volumetric cloud pipeline's per-layer media-sample ordering
    (weather → macro shape → detail shape → density profile) follows the
    clouds package's structure; the shape/detail 3D noise atlas layout and
    several parameter conventions (per-layer altitude/height/density
    vectors) originate there.

- **Tileable value + Worley noise — Sébastien Hillaire (MIT)**
    The cloud shape/detail noise stack (`cloud_shape_atlas.glsl`,
    `local_weather.glsl`) is built on his tileable 3D noise utilities
    (`tileableNoise.glsl`, as also used by three-geospatial).

- \*\*Perlin noise — GLM (`gtc/noise`), © G-Truc / Christophe Riccio (MIT)\*\*,
    itself derived from **webgl-noise by Ashima Arts / Stefan Gustavson**
    (MIT) — inlined in `local_weather.glsl`.

- **Saturn textures — Solar System Scope** (CC BY 4.0)
    <https://www.solarsystemscope.com/textures/>
    `blend/textures/saturn_rings.png` (2k radial color strip,
    transparency in alpha) — the `uRingColor` profile behind the
    KSA-ported ring shading — and `blend/textures/saturn_surface.jpg`
    (2k equirect surface map, `uSaturnColor`), mean-calibrated onto the
    geometric albedo.

- **Blue-noise dither texture** — `blend/textures/blue_noise.png`, the
    1024^2 RGBA blue-noise texture distributed as Shadertoy's stock
    blue-noise media asset (void-and-cluster class; four independent
    channels). Bound as the dedicated `uBlueNoise` dither sampler
    (EEVEE-style: one static spatial tap, value-space temporal rotation);
    a 128^2 crop of the same texture remains baked in
    `turbulence.png`'s alpha (legacy, unread).

- **CIE 1931 color-matching fit** — analytic multi-Gaussian XYZ fit after
    **Wyman, Sloan & Shirley** (JCGT 2013), via
    <https://www.shadertoy.com/view/DtlfRX> (`xFit_1931` family in
    `common.glsl`).

### Techniques & ideas adapted {#credits-techniques-ideas-adapted}

- **Kitten Space Agency (KSA) — RocketWerkz** (public development shaders)
    The shipped `blend/textures/saturn_rings.png` is their Saturn ring
    strip (Core/Textures/Planets/Saturn/Rings.png, 16k radial RGBA,
    69,000-313,900 km span) from the same public development files.
    Also the Saturn-ring shading: the analytic constant-density-slab
    scattering (column density from alpha, slanted view/light paths,
    closed-form lit/dark-side inscatter) and the alpha-weighted dual-HG
    phase in `rect_celestials_lib.glsl` are ported from their
    `RingShading.glsl` / `2dRings.comp`.
    Several renderer strategies were studied from and inspired by the KSA
    cloud/atmosphere shaders: the precomputed ambient-irradiance LUT
    (`AmbientLut`), the series-compensated early exit of the cloud march,
    tricubic light-cache filtering, analytic weather-map cloud shadows, and
    the raymarched-to-2D orbit fade (fade windows after
    `RaymarchedTo2DFade.glsl`).
    A Milky Way variant ported from their `Core/Shaders/MilkyWay.frag`
    (simplex fbm domain warp, ridge/soft/colour octave loops, seam patch)
    shipped from 2026-08-21 and was REMOVED on 2026-09-07, when the
    analytic-blob galaxy replaced it; no code from that file remains.

- **Nubis (Andrew Schneider, Guerrilla Games)** — SIGGRAPH "Advances in
    Real-Time Rendering" series, esp. *Nubis³: Methods for Real-Time
    Volumetric Cloudscapes* (2023).
    The shell-conformal precomputed cloud lighting grid (voxelized sun/up
    optical depth), directional ambient occlusion from the up-integral, the
    dimensional-profile ambient probability term, and the relaxed-Beer
    "inner glow" multiple-scattering approximation.

- **Space Glider — Christian Schüler** (Shadertoy)
    The atmospheric **multiple-scattering ideas** the analytic MS
    approximation grew from, and the throughput-driven march "sprint"
    (step growth once a ray is nearly opaque) after his `dulimit`
    adaptive-step idea; his scattering calibration was also used as a
    cross-check of ours.

- **Skybolt Engine — Matthew Paul Reid**
    <https://github.com/Prograda/Skybolt>
    The cloud-coverage remap (`factor = 1 − coverage · heightScale` with a
    filter-width soft knee) used in the weather sampler.

- **Frostbite — Sébastien Hillaire**, *Physically Based Sky, Atmosphere
    and Cloud Rendering in Frostbite* (SIGGRAPH 2016 course).
    Energy-conserving analytic integration of scattering over a march
    segment (the `(1 − e^{−τ})/τ`-family segment integrals).

- **Horizon: Zero Dawn / earlier Nubis talks (Schneider & Vos)** — the
    general weather-map-driven cloudscape model the layer system builds on.

- **Jack Tollenaar** — *Volumetric cloud rendering* article
    (<https://www.jacktollenaar.top/articles/clouds.html>): used to review
    and validate the adaptive-stepping design.

- **Cumulus — rubenaryo** (<https://github.com/rubenaryo/Cumulus>):
    surveyed during the light-grid performance work.

- **Eric Bruneton** — *Precomputed Atmospheric Scattering* (EGSR 2008)
    and its modern implementations: the multiple-scattering model that the
    analytic MS approximation (`ms_precompute` / `ms_eval`) is calibrated
    against, and the sky-irradiance conventions used by the cloud ambient.

- **Unreal Engine auto exposure — Epic Games**
    (<https://www.unrealengine.com/en-US/tech-blog/how-epic-games-is-handling-auto-exposure-in-4-25>,
    <https://dev.epicgames.com/documentation/en-us/unreal-engine/auto-exposure-in-unreal-engine>)
    and **Unity HDRP's Exposure override**
    (<https://docs.unity3d.com/Packages/com.unity.render-pipelines.high-definition@14.0/manual/Override-Exposure.html>):
    the three conventions PA2's Auto exposure follows (`core/exposure_auto.py`)
    — metering a PERCENTILE BAND of the log-luminance histogram rather than
    its mean (Unreal's Low/High Percent, 10/90 today and 80/98.3 in the UE4
    default it replaced; PA2 uses 50–98, bright-biased because the sky is
    the subject), an EXPOSURE COMPENSATION CURVE against the measured scene
    EV so dark scenes are allowed to stay dark (Unreal's curve asset,
    Unity's Curve Mapping mode; PA2 parameterizes it as a soft knee with an
    Adaptation strength), and ASYMMETRIC adaptation speeds, faster toward
    light than toward dark, as the eye behaves (Unreal's SpeedUp 3 /
    SpeedDown 1, Unity's Speed Dark-to-Light / Light-to-Dark; PA2 puts the
    asymmetry on a rate cap in EV/s). The implementation, its units and its
    physical metering fallback are PA2's own.

### Papers & data {#credits-papers-data}

- **Nishita, Sirai, Tadamura & Nakamae** (1993), *Display of the Earth
    Taking into Account Atmospheric Scattering* (SIGGRAPH '93) — the
    foundational single-scattering planetary atmosphere model.

- **B. T. Draine** (2003), *Scattering by Interstellar Dust Grains* — the
    Draine phase function used by the cloud direct/indirect/backscatter
    lobes; hybrid parameterization informed by **Jendersie & d'Eon** (2023),
    *An Approximate Mie Scattering Function for Fog and Cloud Rendering*.

- **Hess, Koepke & Schult** (1998), *Optical Properties of Aerosols and
    Clouds (OPAC)* — the aerosol profile coefficient tables behind the
    turbidity/profile aerosol model.

- **Ciddor** (1996), *Refractive index of air: new equations for the
    visible and near infrared* — air refractive index in the Rayleigh model.

- **H. Neckel & D. Labs** (1994), *Solar limb darkening 1986–1990 (λλ 303
    to 1099 nm)*, Solar Physics 153, 91–114 — the wavelength-parametrized
    5th-order limb-darkening polynomial of the sun's disc, evaluated per
    channel at 615/535/445 nm and normalized to the disc mean
    (`pa2CelSolarLimb`, `shaders/passes/rect_celestials_lib.glsl`).

- **Jarzynski & Olano** (2020), *Hash Functions for GPU Rendering* (JCGT)
    — the `pcg3d` hash behind the white-noise sample jitter.

- **NOAA GFS / NOMADS** — the live weather data (cloud water, cloud
    fractions, precipitation rate) behind the global cloud map generator
    (`scripts/fetch_cloud_grid.py`).

- The droplet-Mie phase LUT (`blend/textures/MIE_LUT_CDFA.exr`) was
    computed for this project from Mie theory (spectral phase + CDF over
    scattering angle, droplet radii 0.02–2000 µm).

### Blender {#credits-blender}

- The offscreen renderer is built entirely on Blender's `gpu` Python API
    (offscreen MRT rendering, compute dispatch, image GPU textures).

### Third-party licenses {#credits-third-party-licenses}

Physical Atmosphere² includes material derived from the following works.
Full provenance and thanks: see `CREDITS.md`.

#### Public Domain / Unlicense {#licenses-public-domain-unlicense}

- **Single-scattering atmosphere — FordPerfect**
    <https://www.shadertoy.com/view/X3fXRn> — released as Public Domain
    under the Unlicense (<http://unlicense.org>). Foundation of the
    atmospheric core in `shaders/atmosphere_15/`.

#### MIT License {#licenses-mit-license}

The following components are used under the MIT License (text below):

- **three-geospatial** — © 2024 Shota Matsuda
    <https://github.com/takram-design-engineering/three-geospatial>
    (cloud pipeline structure; `cloud_shape_atlas.glsl` is ported from its
    `cloudShape.frag` / `cloudShapeDetail.frag`).

- **Tileable value + Worley noise** — © Sébastien Hillaire
    (tileable 3D noise utilities used by the cloud noise stack).

- \*\*GLM `gtc/noise` Perlin noise\*\* — © G-Truc Creation / Christophe
    Riccio, itself derived from **webgl-noise** — © 2011 Ashima Arts /
    Stefan Gustavson (inlined Perlin noise).

> Permission is hereby granted, free of charge, to any person obtaining
> a copy of this software and associated documentation files (the
> "Software"), to deal in the Software without restriction, including
> without limitation the rights to use, copy, modify, merge, publish,
> distribute, sublicense, and/or sell copies of the Software, and to
> permit persons to whom the Software is furnished to do so, subject to
> the following conditions:
>
> The above copyright notice and this permission notice shall be
> included in all copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
> EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
> MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
> NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS
> BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN
> ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN
> CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.

#### Data {#licenses-data}

- **World cities database** — see `data/world_cities_ATTRIBUTION.txt`
    for its attribution terms.

- **NOAA GFS / NOMADS** — live weather data; U.S. Government work,
    public domain.

- **OPAC aerosol tables** (Hess, Koepke & Schult 1998) — published
    scientific data.
