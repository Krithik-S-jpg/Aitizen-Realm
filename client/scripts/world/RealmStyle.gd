extends RefCounted
## Shared world-art proportions and sunlight palette; UI portraits are independent.
const SHADOW := Color(0.05,0.10,0.09,0.12)
const ROCK_LIGHT := Color("d7d1bd")
const ROCK_SHADE := Color("9ba18d")
const SOD := Color("78805c")
const BUILDING_HEIGHTS := {
    "shelter":124.0,"house":124.0,"home":124.0,"tent":90.0,
    "storage":96.0,"campfire":32.0,"workbench":43.0,"well":62.0,
    "farm":54.0,"fence":35.0
}
