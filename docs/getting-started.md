---
title: Getting started
---

# Getting started

_Physical Atmosphere²_ (PA2) is a Blender add-on that puts a complete, realistic sky into your scene: atmosphere, sunlight, volumetric clouds, sun, moon, planets and stars. Pick a real place, date and time on Earth, or simply drag the sun where you want it, and the add-on lights your scene to match. Everything updates live in the viewport.

## Requirements

- [Blender 5.2.0+](https://www.blender.org/)
- The **Vulkan** backend is recommended (`Preferences > System > Display Graphics > Backend`). The add-on works on OpenGL but shows a warning, since it is developed and tested against Vulkan.

|                    | Atmosphere only | Clouds* |
| ------------------ | --------------- | ------ |
| **Specs**          | Any GPU (even integrated) that runs Blender 5.2 comfortably, laptops included. | Desktop-class GPU: RTX 3060 / RX 6600 or better. |
| **What to expect** | **Runs almost anywhere.** Sky, sun, moon, planets and stars update in real time even on modest laptops. Drag the sun, scrub time, it keeps up. | **Working with clouds in the viewport will be slow.** Volumetric clouds are the heaviest part of the add-on, even for high-end GPUs at higher quality settings. Navigate on `Low` quality with `Temporal AA` on: the image refines to full quality the moment the camera rests. Higher presets are for final frames, not for flying around. |

_\*We're currently working on cloud optimisation to make clouds faster in the viewport on lower performing devices._

## Installation

???+ info
    "Physical Atmosphere²" is only available for purchase on [Superhive](https://superhivemarket.com/products/physical-atmosphere/) (formerly Blender Market). Get your latest version there.

Physical Atmosphere² ships as a **Blender extension**:

- Download the `physical_atmosphere2_v[version].zip` file.
- Open Blender.
- **Drag and drop** the .zip file into the Blender window and confirm. That's it.
- Alternatively: go to `Edit > Preferences > Get Extensions`, click the dropdown arrow in the top-right corner, choose `Install from Disk...` and locate the .zip file.

!!! note "Permissions"
    During installation Blender will list two permissions the extension asks for:

    - **Network** — used only to download live GFS weather data for cloud maps and to auto-detect your location. Everything else works fully offline.
    - **Files** — used to save generated cloud maps into a folder you choose.

## First Run

- In the 3D Viewport, open the [Sidebar](https://docs.blender.org/manual/en/latest/interface/window_system/regions.html#sidebar) (also called the _N Panel_) and click the **Atmosphere²** tab.
- Click the `+ Add Atmosphere` button.
- The sky appears and the panel fills with settings. The same panel is also available in `Properties > World`.

!!! summary "What happens when the atmosphere is added?"
    The add-on sets up its own World for the active scene. The sky, the sun light and everything you see is rendered and kept up to date by the add-on from then on. `Remove Atmosphere` (at the bottom of the panel) takes it all out again.

## Choose your interface layout

At the top of the panel you can pick how much of the add-on you want to see:

- **Simple** — just a sky: location, time, clouds, exposure and a quality preset. One screen, no science. This is the default.
- **Advanced** — the full working set: physics toggles, individual cloud layers, rendering settings.
- **Scientific** — every knob there is. Meant for research and calibration work; you will likely never need it for rendering.

This documentation covers the Simple and Advanced layouts. The Scientific layout will get its own, more technical documentation later.

## A quick tour (Simple layout)

- **Sky & Observer** — choose `Artistic` to drag the sun and moon wherever you like, or `Earth` to use a real location, date and time. In Earth mode you can search for your city or auto-detect your location.
- **Post Processing** — exposure and white balance.
- **Atmosphere** — how clean or polluted the air is, and how much haze it carries.
- **Clouds** — one slider: cloud coverage.
- **Stars** — star brightness at night.
- **Quality** — one preset dropdown that balances quality against speed.

When you want more control (cloud layers, weather maps, the moon and planets), switch to **Advanced** and head to the [documentation](/physical-atmosphere/documentation/).
