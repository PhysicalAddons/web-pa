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
