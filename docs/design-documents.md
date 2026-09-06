---
title: Design documents
---

# Design documents

How _Physical Atmosphere²_ renders, and why it renders that way: the architecture reference for the rendering pipeline, the engineering design documents behind its major features, and the credits and references the work stands on. Everything is published as written. The design documents are working notes rather than user documentation: each records a direction, the physics and architecture chosen for it and the stage plan, and is amended as stages land with what actually shipped and where it departed from the plan. "User" in them is the add-on's author setting the direction, commit hashes and file paths refer to the add-on's source tree, and dates are when a decision was made. For what the features do, see the [documentation](/physical-atmosphere/documentation/) and the [release notes](/physical-atmosphere/release-notes/).

| Section | Status | Date |
| --- | --- | --- |
| [Rendering pipeline](#pipeline)<br><small>The architecture reference: one atmosphere core compiled many ways, the rect and equirect renderers, the TAA round, shader assembly, every pass and LUT, and how the sky reaches EEVEE and Cycles.</small> | `reference:`{: .label-improvements } Architecture reference | 03.09.2026 |
| [Atmospheric Refraction — ray-marched, one law for sky, ground and celestials](#refraction)<br><small>One ray-marched refraction law for sky, ground and celestials: bending from the air's pressure and temperature profile, the green flash, horizon shimmer and space views. Every stage has landed: bent view rays for sky, ground, clouds and celestials, dispersion, the shimmer split and Young's inversion presets. Amended with the sun's chromatic limb law and the LUT sky's horizon-band transmittance limit.</small> | `design:`{: .label-research } Shipping · every stage landed · amended 06.09.2026 | 03.09.2026 |
| [1:1 Window-mapped sky — design & stage plan](#window-sky)<br><small>The sky and composed ground are marched at exact view resolution through Window-coordinate mapping, with EEVEE's own temporal AA recipe and the hybrid cut against scene geometry. Amended with what actually shipped and where it departs from the plan.</small> | `shipped:`{: .label-fixed } Shipped · amended 03.09.2026 | 04.08.2026 |
| [Optimized cloud rendering: interleaved low-res march + temporal upscale](#cloud-upscale)<br><small>The cloud march leaves the 1:1 sky pass for its own interleaved low-resolution pass with a KSA-style temporal resolve, the KSA march port and the dual-paraboloid shadow volume. Includes the fidelity audit against the KSA sources and the cost measurements.</small> | `shipped:`{: .label-fixed } Shipped · stages 1–4 and 2b | 05.08.2026 |
| [North Offset — Design (2026-07-31)](#north-offset)<br><small>A single angle that rotates the modelled world against true north, so GIS-derived geometry keeps its imported orientation. Scoped and costed, then postponed to a later version.</small> | `deferred:`{: .label-deferred } Deferred | 31.07.2026 |
| [Ground Shader — Design (2026-07)](#ground-shader)<br><small>A dedicated GPU compose pass shades the planet surface offscreen and folds it into the scatter/transmittance pair: Hapke-lite land, GGX water, water reflections, cloud bounce, night lights and object shadows on the ground.</small> | `shipped:`{: .label-fixed } Shipped · 2.7 | 07.2026 |
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


## Atmospheric Refraction — ray-marched, one law for sky, ground and celestials {#refraction}

`design:`{: .label-research } Shipping · every stage landed · amended 06.09.2026 · 03.09.2026 · `docs/design-refraction-2026-09.md`

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

Status: SHIPPING (written 2026-09-03 as a design; amended as stages
land). Every stage has landed in the tree: the LUT generations walk the
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

- **Temperature masses** (the low-frequency part) replace the world
    tier. A slow scalar field n(p) — the same volume, indexed by world
    position over 6 × Mass Size (default 3 km), riding the updraft —
    offsets the STANDARD air's surface gradient g₀ by A·n·e^{−h/H}
    (H = 1.5 km, below 4H), integrated at fixed STATIONS along the ray
    (every half cell, at least 1.25 km) and kicked into the direction
    from the sub-step holding them: Δel = Σ A·n·e^{−h/H}·g₀·Δs·cos el,
    never past inverting the local gradient. Two forms that did not
    survive the day (user: "the bands reappear when shimmer is added"):
    scaling the LOCAL gradient by (1 + A·n) — a +5 K duct is 20× the
    standard gradient and ±100 % of it tore its fold apart (39″ of exit
    jitter) — and point-sampling the field once per sub-step, which
    aliased a 3 km field on 3–8 km steps and jumped with the step count
    (7.9″ under the duct, 2.3″ in clear air; stations: 0.6″ / 0.2″).
    This is what "eddies of 3 km" approximated with random kicks — the
    gradient itself varying along the path — but integrated smoothly in
    the vertical plane. Amount = the RMS fraction of g₀ (1 = the
    standard gradient wanders by its own size: about a fifth of an
    arcminute of horizon wander across azimuth, a few arcseconds across
    elevation — the smooth integral cancels most of what the aliased
    random walk showed as 0.8′). Lanes `rf_shim2` = (A/σ_vol, 1/period,
    H, g₀·strength). Independent of the quality tier; off with Ray March
    off (no walk).

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

`shipped:`{: .label-fixed } Shipped · amended 03.09.2026 · 04.08.2026 · `docs/design-1to1-window-sky.md`

**In this document:** [Target architecture](#window-sky-target-architecture) · [Amended 2026-09-03 — sizing law, hybrid cut](#window-sky-amended-2026-09-03-sizing-law-hybrid-cut) · [What this retires](#window-sky-what-this-retires) · [Stages](#window-sky-stages) · [Traps carried from the prototype](#window-sky-traps-carried-from-the-prototype)

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

`shipped:`{: .label-fixed } Shipped · stages 1–4 and 2b · 05.08.2026 · `docs/design-cloud-temporal-upscale.md`

**In this document:** [Why this is possible cheaply here](#cloud-upscale-why-this-is-possible-cheaply-here) · [Architecture](#cloud-upscale-architecture) · [Non-goals](#cloud-upscale-non-goals) · [Risks](#cloud-upscale-risks) · [Companion feature: separate preview vs render graphics settings](#cloud-upscale-companion-feature-separate-preview-vs-render-gra) · [Stage 1 / C2 wiring map](#cloud-upscale-stage-1-c2-wiring-map) · [Stage 2a decision](#cloud-upscale-stage-2a-decision) · [Stage 3: KSA 1:1 march port](#cloud-upscale-stage-3-ksa-1-1-march-port) · [Stage 4: KSA shadow volume + sharp godrays](#cloud-upscale-stage-4-ksa-shadow-volume-sharp-godrays) · [Shadow-volume FIDELITY AUDIT vs the real sources](#cloud-upscale-shadow-volume-fidelity-audit-vs-the-real-sources) · [What actually blocks retiring the LIGHT GRID](#cloud-upscale-what-actually-blocks-retiring-the-light-grid) · [DIRECTION SET 2026-08-07: the KSA march is the one that ships](#cloud-upscale-direction-set-2026-08-07-the-ksa-march-is-the-on) · [Stage 2b: the KSA MV-reproject resolve](#cloud-upscale-stage-2b-the-ksa-mv-reproject-resolve)

Status: DESIGN (2026-08-05). Research base: research-ksa-cloud-teardown-2026-08.md
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

`deferred:`{: .label-deferred } Deferred · 31.07.2026 · `docs/design-north-offset.md`

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

`shipped:`{: .label-fixed } Shipped · 2.7 · 07.2026 · `docs/design-ground-shader-2026-07.md`

**In this document:** [Why a separate shader](#ground-shader-why-a-separate-shader) · [Data flow](#ground-shader-data-flow) · [Ground-shader samplers](#ground-shader-ground-shader-samplers) · [Requirements → design](#ground-shader-requirements-design) · [8a — the new grid-column arm](#ground-shader-8a-the-new-grid-column-arm) · [8b — the older slab arm was lit by the wrong sun](#ground-shader-8b-the-older-slab-arm-was-lit-by-the-wrong-sun) · [UI](#ground-shader-ui) · [Rebake & cadence](#ground-shader-rebake-cadence) · [Validation](#ground-shader-validation) · [Phases](#ground-shader-phases)

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
    The procedural Milky Way ("KSA" variant in `rect_celestials_lib.glsl`,
    `pa2MwCloud`/`pa2CelMilkyWay`) ports the cloud-noise enhancement stack
    of their `Core/Shaders/MilkyWay.frag` — simplex fbm domain warp, the
    ridge/soft/colour octave loops, seam patch and composite constants
    (including their own alternative hash) — with a procedural band
    standing in for their 320^2 cubemap base, which is not shipped.

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
