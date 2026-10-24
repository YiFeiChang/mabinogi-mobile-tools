import argparse
import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, urlparse

from main import ITEMS_DIR, load_item, select_best_recipe
from src.models import Item


APP_DIR = Path(__file__).resolve().parent
CATEGORY_ORDER_PATH = APP_DIR / "data" / "category_order.json"
PAGE_PATH = APP_DIR / "web" / "index.html"


def get_category_order() -> list[str]:
    if not CATEGORY_ORDER_PATH.exists():
        return []

    with CATEGORY_ORDER_PATH.open("r", encoding="utf-8") as file:
        data = json.load(file)
    categories = data.get("categories") if isinstance(data, dict) else None
    if (
        not isinstance(categories, list)
        or any(not isinstance(category, str) for category in categories)
        or len(categories) != len(set(categories))
    ):
        raise ValueError("分類排序設定必須包含不重複的字串 categories 清單。")
    return categories


def get_available_items() -> dict[str, list[str]]:
    cache: dict[str, Item] = {}
    categories: dict[str, dict[str, Item]] = {}

    for file_path in sorted(ITEMS_DIR.rglob("*.json")):
        item = load_item(file_path.stem, cache)
        if item.recipes:
            relative_directory = file_path.parent.relative_to(ITEMS_DIR)
            category = " / ".join(relative_directory.parts) or "尚未分類"
            categories.setdefault(category, {})[item.name] = item

    category_order = get_category_order()
    category_positions = {category: index for index, category in enumerate(category_order)}
    return {
        category: [
            item.name
            for item in sorted(
                items.values(),
                key=lambda item: (
                    item.menu_order is None,
                    item.menu_order if item.menu_order is not None else 0,
                    item.name,
                ),
            )
        ]
        for category, items in sorted(
            categories.items(),
            key=lambda entry: (
                0 if entry[0] in category_positions else 1,
                category_positions.get(entry[0], 0),
                entry[0],
            ),
        )
    }


def create_recipe_tree(item: Item, required_quantity: int, cache: dict[str, Item]) -> dict:
    node = {"name": item.name, "quantity": required_quantity, "children": []}
    if not item.recipes:
        return node

    recipe = select_best_recipe(item, required_quantity, cache)
    batches = (required_quantity + recipe.output_quantity - 1) // recipe.output_quantity
    node["batches"] = batches
    node["output_quantity"] = recipe.output_quantity
    node["children"] = [
        create_recipe_tree(entry.item, entry.quantity * batches, cache)
        for entry in recipe.entries
    ]
    return node


def collect_base_materials(node: dict, materials: dict[str, int]) -> None:
    if not node["children"]:
        name = node["name"]
        materials[name] = materials.get(name, 0) + node["quantity"]
        return

    for child in node["children"]:
        collect_base_materials(child, materials)


class RecipeRequestHandler(BaseHTTPRequestHandler):
    def send_json(self, status: int, payload: dict | list) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/api/items":
            self.send_json(200, get_available_items())
            return

        if path == "/":
            body = PAGE_PATH.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_error(404)

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/api/calculate":
            self.send_error(404)
            return

        try:
            content_length = int(self.headers.get("Content-Length", "0"))
            if content_length <= 0 or content_length > 1_048_576:
                self.send_json(400, {"error": "請提供有效的計算資料。"})
                return
            payload = json.loads(self.rfile.read(content_length))
        except (ValueError, json.JSONDecodeError):
            self.send_json(400, {"error": "請提供有效的 JSON 資料。"})
            return

        item_name = payload.get("item") if isinstance(payload, dict) else None
        quantity = payload.get("quantity") if isinstance(payload, dict) else None
        if not isinstance(item_name, str) or not item_name.strip():
            self.send_json(400, {"error": "請選擇要製作的物品。"})
            return
        item_name = item_name.strip()
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity < 1:
            self.send_json(400, {"error": "製作數量必須是大於 0 的整數。"})
            return

        cache: dict[str, Item] = {}
        item = load_item(item_name, cache)
        if not any(item_name in names for names in get_available_items().values()):
            self.send_json(404, {"error": "找不到這個物品的資料。"})
            return

        tree = create_recipe_tree(item, quantity, cache)
        materials: dict[str, int] = {}
        collect_base_materials(tree, materials)
        self.send_json(200, {"tree": tree, "materials": dict(sorted(materials.items()))})


def main(arguments: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Mabinogi Mobile 物品配方計算網站")
    parser.add_argument(
        "--url",
        default="http://127.0.0.1:8000",
        help="網站監聽 URL（預設：http://127.0.0.1:8000）",
    )
    args = parser.parse_args(arguments)

    try:
        url = urlsplit(args.url)
        if (
            url.scheme != "http"
            or not url.hostname
            or url.username is not None
            or url.password is not None
            or url.path not in ("", "/")
            or url.query
            or url.fragment
        ):
            parser.error("--url 必須是有效的 HTTP URL，且不可包含路徑、帳密、查詢或片段。")
        host = "" if url.hostname == "*" else url.hostname
        port = url.port or 80
    except ValueError as error:
        parser.error(f"無效的 --url：{error}")

    server = ThreadingHTTPServer((host, port), RecipeRequestHandler)
    print(f"配方計算器已啟動：{args.url.rstrip('/')}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n配方計算器已停止。")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
