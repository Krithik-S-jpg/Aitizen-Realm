# Wildlife habitats: first release

- Existing animal aging, reproduction and predator/prey systems remain active.
- Up to four initial songbirds establish tree nests. Simulated birds replace
  decorative flocks when received by the client. They fly tile-by-tile, feed on
  finite plants/crops, drink freshwater, perch at night and shelter in rain.
- Nest progress, food-gated spring broods, juvenile age, tree-loss relocation and
  homes persist in checkpoints. Bird population is capped at 16. A nest currently
  supports one brood; pairing genetics and multi-year repeated broods are not modeled.
- Nearby birds update every two ticks, distant birds every eight ticks.
- Rabbits have burrows; wolves/foxes/bears have dens; other land species have
  resting grounds. These are records of homes, not explorable interiors.
- Seasonal changes trigger existing food/water/prey migration scoring; social
  animals may follow a nearby member's destination. Hunger, thirst, fear and rest
  remain relevant. Grazers consume actual farm crop stock.
- Citizens record visible homes and migration sighting points, not omniscient
  future routes. Open **Wildlife & habitats**, select a **FIELD NOTE** to see its
  observer, location and observation time. Old sightings are explicitly labeled.
- Nests now use layered woven twigs, shaded bowls and speckled eggs. Bird altitude
  interpolates during takeoff/landing and wings fold on approach; reduced motion
  skips altitude interpolation. Artwork is procedural, not a painted sprite sheet.
- Migration field notes show a scaled map of observed locations. Dashed segments
  explicitly indicate that travel between sightings has not been verified.
- Save/restore acceptance uses real HTTP checkpoint routes with isolated compressed
  test storage, then advances the restored habitat state. Hosted Supabase and the
  user's live saved game have not been tested or modified.

Verification: `tests/test_habitats.py`, existing animal routine tests and
`client/tools/TestHabitats.gd` (rendering and journal layout).
`tests/test_habitat_saved_world.py` covers the isolated checkpoint acceptance flow.
