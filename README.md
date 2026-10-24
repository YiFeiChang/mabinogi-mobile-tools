# Mabinogi Mobile Tools

以 Python 製作的《瑪奇 Mobile》配方計算工具，可透過命令列或簡易網站計算製作物品所需的基礎素材。

## 功能

- 讀取 `recipe_calculator/data/items/` 中的 JSON 配方資料。
- 遞迴展開配方，將中間物品換算為基礎素材需求。
- 物品有多個配方時，自動選擇基礎素材總數較少的配方。
- 提供可搜尋物品、輸入製作數量的繁體中文網頁介面，並顯示素材總數與配方樹。
- 未提供配方資料的材料會視為基礎素材。

## 環境需求

- Python 3.10 或更新版本
- 不需安裝第三方 Python 套件

## 網站介面

在專案根目錄執行：

```powershell
python recipe_calculator\web.py
```

預設監聽 URL 為 <http://127.0.0.1:8000>。可使用 `--url` 指定其他 HTTP URL：

```powershell
python recipe_calculator\web.py --url http://127.0.0.1:9000
```

啟動後，在瀏覽器開啟指定的 URL。按 `Ctrl+C` 可停止伺服器。URL 可設定主機名稱與連接埠，不可包含帳密、查詢或片段。使用 `*` 或 `0.0.0.0` 作為主機會監聽所有網路介面，例如 `python web.py --url "http://*:8000/"`；請只在信任的網路環境使用。

## 命令列

在專案根目錄執行：

```powershell
python recipe_calculator\main.py --item "巨木長弓S" --quantity 1
```

也可以使用簡寫參數：

```powershell
python recipe_calculator\main.py -i "焦油" -q 6
```

命令列會列出配方樹，以及各基礎素材的需求數量。

## 配方資料格式

每個物品配方放在 `recipe_calculator/data/items/`，檔名使用物品名稱並以 `.json` 結尾。可在此目錄下建立任意層數的子目錄作為分類；直接放在 `items/` 根目錄的物品會歸類為「尚未分類」。例如 `焦油.json`：

```json
{
  "name": "焦油",
  "menu_order": 10,
  "recipes": [
    {
      "output_quantity": 5,
      "ingredients": [
        {
          "item_name": "原木",
          "quantity": 50
        },
        {
          "item_name": "黏土",
          "quantity": 25
        }
      ]
    }
  ]
}
```

- `name`：物品名稱。
- `menu_order`：選單排序，可省略；數字越小越前，未設定的物品依名稱排序。
- `recipes`：可製作此物品的配方清單。
- `output_quantity`：每批配方的產出數量。
- `ingredients`：每批配方所需材料及數量。

當製作數量無法被每批產量整除時，工具會向上取整批次。

### 分類排序

在 `recipe_calculator/data/category_order.json` 的 `categories` 清單中，依序列出網站選單的分類路徑。此檔案已依現有分類產生範本；清單中未設定的分類會依名稱排序，若設定檔不存在，所有分類皆依名稱排序。

## 專案結構

```text
recipe_calculator/
├── main.py                 # 配方載入、計算與命令列介面
├── src/
│   └── models.py           # 物品與配方資料模型
├── data/
│   ├── items/              # 物品配方 JSON 資料與分類目錄
│   └── category_order.json # 網站分類排序
├── web.py                  # 標準函式庫 HTTP 伺服器與 API
└── web/
    └── index.html          # 網站介面
```
