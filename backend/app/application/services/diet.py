"""One food preference rule shared by decisions, meals and exchanges."""

ANIMAL_FOODS = {"meat", "raw_meat", "cooked_meat", "raw_fish", "cooked_fish"}


def accepts(entity, item):
    """Legacy citizens remain omnivorous; gender never changes food or skills."""
    return entity.diet != "vegetarian" or item not in ANIMAL_FOODS


def foods(entity):
    """Prefer cooked meals; raw meat is not a new edible item."""
    return [item for item in ("cooked_meat", "cooked_fish", "fruit", "food", "mushroom", "meat") if accepts(entity, item)]
