# World editor

Pause the simulation. Open **World overview → World editor**. Choose a terrain
and brush size, click the surface world to preview, then choose **Apply preview**.
Green brushes can be applied; red brushes explain why they are blocked. The
client reloads authoritative world data after apply/undo.

Seven terrain types and 1/5/13-tile circular brushes are supported. Forest paints
ground type only: it does not spawn trees. Mountains set terrain elevation metadata;
this is not freeform height sculpting.

The whole brush is rejected if it crosses world bounds, resources, entities,
structures, wildlife homes, floodwater, marine/cave sites or ancient discoveries.
Preview tokens reject stale world/tick/revision state. Edits cancel affected paths
and invalidate the bank cache. Twenty undo entries are checkpointed with the world.
Undo refuses newer simulation ticks or changed/occupied terrain.

Choose Resource to place finite trees, stone, bushes, herbs or ore. Each node
contains 30 units; bushes also contain 12 fruit. Occupied/protected tiles and
water reject the entire brush. These nodes use existing harvesting systems.

Choose Weather for local Rain, Snow or Clear patches. Patches last 48 simulation
ticks, with at most four active patches and newest-overlap priority. Their
precipitation is visible on the surface; riverbank flooding and wildlife weather
responses use the local conditions. They do not override temperature or every
citizen need calculation. Clear weather is not instant flood removal.

Scenario presets provide Food grove, Stone outcrop, Rain test and Dry spell using
the same preview, bounded brushes and undo guards. They are small experiments,
not the scenario designer. **Open scenario designer** provides editable goals,
event timelines, deadlines, a library and live results; see SCENARIO_DESIGNER.md.
Resources, weather and undo history
serialize with the world. Undo is only safe before advancing simulation time.

No hosted save is automatically created or overwritten. Use existing Save world
controls when satisfied. Animal placement, experiment comparisons, redo and
editor keyboard shortcuts remain outside this version. Automated checks cover
placement, protection, overlap, expiry, persistence and undo; Godot checks cover
controls and rendered weather. Hosted saved-world acceptance is still manual.
