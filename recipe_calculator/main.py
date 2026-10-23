# 匯入 Python 內建的命令列參數解析模組（功能類似 C# 的命令列解析套件，如 System.CommandLine）
import argparse

# 匯入 Python 內建的檔案路徑與作業系統互動模組（對應 C# 的 System.IO 與 System.IO.Path）
import json
import math
import os

# 匯入 Python 內建的系統模組（提供類似 C# System.Environment 的環境互動功能）
import sys

# 從 src 資料夾下的 models.py 匯入指定的類別
# 概念類似 C# 的 using，但 Python 是直接指定要匯入哪些類別
from src.models import Item, Recipe, RecipeEntry


def load_item(item_name: str, cache: dict[str, Item]) -> Item:
    """根據物品名稱從 data/items 目錄載入對應的 JSON 檔案，並建立 Item 物件。"""
    # 若快取中已經載入過該物品，則直接回傳（避免重複讀取檔案與重複實例化）
    if item_name in cache:
        return cache[item_name]

    file_path: str = os.path.join(os.path.dirname(__file__), "data", "items", f"{item_name}.json")

    # 若找不到對應的 JSON 檔案，則視為基礎素材（recipes 設為空清單）
    # 對應 C# 的：若檔案不存在則回傳預設無配方的物件
    if not os.path.exists(file_path):
        base_item: Item = Item(name=item_name, recipes=[])
        cache[item_name] = base_item
        return base_item

    # 讀取 JSON 檔案內容
    with open(file_path, "r", encoding="utf-8") as f:
        data: dict = json.load(f)

    item_obj_name: str = data.get("name", item_name)
    raw_recipes: list[dict] = data.get("recipes", [])

    recipes_list: list[Recipe] = []
    for raw_recipe in raw_recipes:
        # 讀取該配方的產出數量，若未指定則預設為 1
        output_qty: int = raw_recipe.get("output_quantity", 1)
        ingredients: list[dict] = raw_recipe.get("ingredients", [])

        recipe_entry_list: list[RecipeEntry] = []
        for entry_data in ingredients:
            sub_item_name: str = entry_data["item_name"]
            sub_quantity: int = entry_data["quantity"]
            # 遞迴載入子物品（對應 C# 的遞迴物件初始化與相依性解析）
            sub_item: Item = load_item(sub_item_name, cache)
            recipe_entry_list.append(RecipeEntry(item=sub_item, quantity=sub_quantity))
        
        recipes_list.append(Recipe(output_quantity=output_qty, entries=recipe_entry_list))

    # 建立物品實例並存入快取
    item: Item = Item(name=item_obj_name, recipes=recipes_list)
    cache[item_name] = item
    return item


def get_recipe_base_materials(
    recipe: Recipe,
    required_qty: int,
    cache: dict[str, Item]
) -> dict[str, int]:
    """計算指定配方所需要的基礎素材統計。"""
    base_materials: dict[str, int] = {}
    batches: int = math.ceil(required_qty / recipe.output_quantity)
    
    for entry in recipe.entries:
        sub_qty: int = entry.quantity * batches
        accumulate_requirements(entry.item, sub_qty, base_materials, cache)
        
    return base_materials


def accumulate_requirements(
    item: Item,
    required_qty: int,
    base_materials: dict[str, int],
    cache: dict[str, Item]
) -> None:
    """遞迴累加基礎素材數量（用於評估哪個配方的基礎素材最少）。"""
    if not item.recipes:
        base_materials[item.name] = base_materials.get(item.name, 0) + required_qty
        return

    best_recipe: Recipe = select_best_recipe(item, required_qty, cache)
    batches: int = math.ceil(required_qty / best_recipe.output_quantity)
    
    for entry in best_recipe.entries:
        accumulate_requirements(entry.item, entry.quantity * batches, base_materials, cache)


def select_best_recipe(
    item: Item,
    required_qty: int,
    cache: dict[str, Item]
) -> Recipe:
    """從多個配方中選出總基礎素材消耗量最少的一個配方。"""
    if len(item.recipes) <= 1:
        return item.recipes[0]

    best_recipe: Recipe = item.recipes[0]
    min_total_cost: float = float('inf')

    for recipe in item.recipes:
        materials: dict[str, int] = get_recipe_base_materials(recipe, required_qty, cache)
        total_cost: int = sum(materials.values())
        if total_cost < min_total_cost:
            min_total_cost = total_cost
            best_recipe = recipe

    return best_recipe


def print_material_tree(
    item: Item,
    required_qty: int,
    indent: int,
    cache: dict[str, Item]
) -> dict[str, int]:
    """遞迴印出素材樹，並回傳各末端素材的需求數量。"""
    prefix: str = "  " * indent
    print(f"{prefix}- {item.name} x {required_qty}")

    # 若該物品沒有配方（recipes 為空），則為基礎素材，停止遞迴
    if not item.recipes:
        return {item.name: required_qty}

    # 自動挑選總基礎素材最少的主配方
    best_recipe: Recipe = select_best_recipe(item, required_qty, cache)
    batches: int = math.ceil(required_qty / best_recipe.output_quantity)
    base_materials: dict[str, int] = {}

    for entry in best_recipe.entries:
        sub_total_qty: int = entry.quantity * batches
        sub_materials: dict[str, int] = print_material_tree(entry.item, sub_total_qty, indent + 1, cache)
        for material_name, material_qty in sub_materials.items():
            base_materials[material_name] = base_materials.get(material_name, 0) + material_qty

    return base_materials


# 對應 C# 的 static int Main(string[] arguments)
# 接收字串清單作為指令列引數，並回傳 int 作為程式結束碼（Exit Code）
def main(arguments: list[str]) -> int:
    # 建立命令列參數解析器
    parser = argparse.ArgumentParser(description="mabinogi-mobile-tools 物品配方計算工具")

    # 新增具名參數（required=True 代表為必填參數）
    parser.add_argument("--item", "-i", required=True, type=str, help="要生產的物品名稱")
    parser.add_argument("--quantity", "-q", required=True, type=int, help="要生產的數量")

    # 解析傳入的指令列引數
    args = parser.parse_args(arguments)

    # 取得解析後的參數值（型別明確）
    target_item: str = args.item
    target_quantity: int = args.quantity

    print(f"欲生產物品: {target_item}, 數量: {target_quantity}\n")

    # 建立快取字典（對應 C# 的 Dictionary<string, Item>）
    item_cache: dict[str, Item] = {}

    # 依照目標物品名稱載入 JSON 並構建關聯樹
    root_item: Item = load_item(target_item, item_cache)

    # 若該物品完全沒有配方
    if not root_item.recipes:
        print("此物品為基礎素材，無須配方。")
        print(f"基礎素材需求總數:\n- {root_item.name}: {target_quantity}")
        return 0

    print("=== 最少基礎素材配方樹狀清單 ===")
    base_materials: dict[str, int] = print_material_tree(root_item, target_quantity, indent=0, cache=item_cache)
    print("\n基礎素材需求總數:")
    for material_name in sorted(base_materials):
        print(f"- {material_name}: {base_materials[material_name]}")

    # 回傳 0 代表程式正常執行完畢
    return 0


# __name__ 是 Python 內建變數；當此檔案被 "直接執行" 時，其值固定為 "__main__"
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))