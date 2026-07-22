---
title: Known Issues
---


**3D Object Shadows are unavailable on macOS (Metal)**

Blender's Metal backend currently has broken support for a GPU feature the object-shadow pass needs (uint image atomics). The add-on detects this and quietly keeps `3D Object Shadows` off on Metal. Everything else works. Once Blender fixes it, the feature enables itself again, no add-on update needed.


**OpenGL backend shows a warning**

The add-on is developed and tested against the **Vulkan** backend. On OpenGL you may hit issues we don't see on Vulkan. Switch in `Preferences > System > Display Graphics > Backend` and restart Blender.


**Cloud map generation fails without internet**

Generating cloud maps downloads live GFS weather data. If the newest forecast cycle isn't published yet, the add-on automatically falls back to an older one. With no connection at all, generation can't run. Previously generated maps keep working offline.


--------------------------

**Didn't find your answer?**

Visit our community support [Discord channel](https://discord.gg/wvzPVzj9Vr) for more help.
