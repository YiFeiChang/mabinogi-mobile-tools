class Item:
    """代表遊戲中的物品或材料。"""

    def __init__(self, name: str, recipes: list["Recipe"]) -> None:
        self.name: str = name
        self.recipes: list[Recipe] = recipes


class RecipeEntry:
    """代表配方中的單一項目（包含物品實例與需求數量）。"""

    def __init__(self, item: "Item", quantity: int) -> None:
        self.item: Item = item
        self.quantity: int = quantity


class Recipe:
    """代表生產配方（包含產出數量，以及所需的 RecipeEntry 集合）。"""

    # 對應 C# 的建構子（Constructor），初始化產出數量與材料清單
    def __init__(self, output_quantity: int = 1, entries: list[RecipeEntry] = None) -> None:
        self.output_quantity: int = output_quantity
        self.entries: list[RecipeEntry] = entries if entries is not None else []