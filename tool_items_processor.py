import json
import re
import os
import requests
import concurrent.futures

def download_image(img_url, local_path):
    """Hàm phụ trách việc tải ảnh để chạy đa luồng"""
    if os.path.exists(local_path):
        return
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(img_url, headers=headers, timeout=5)
        if r.status_code == 200:
            with open(local_path, 'wb') as f_img:
                f_img.write(r.content)
    except Exception:
        pass

def process_tft_items_full(input_file, output_file, image_folder='items_images'):
    try:
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
            print(f"Đã tạo thư mục: {image_folder}")

        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        items_list = raw_data if isinstance(raw_data, list) else raw_data.get('items', [])
        
        # Tạo map apiName -> ID để xử lý component_1, component_2
        api_to_id = {item.get('apiName'): i for i, item in enumerate(items_list, start=1)}

        processed_items = []
        download_tasks = []

        print(f"Bắt đầu xử lý dữ liệu cho {len(items_list)} trang bị...")

        for index, item in enumerate(items_list, start=1):
            api_name = item.get('apiName', '')
            api_lower = api_name.lower()
            composition = item.get('composition', [])
            tags = [t.lower() for t in item.get('tags', [])]
            
            # --- LOGIC PHÂN LOẠI CẢI TIẾN (5 NHÓM) ---
            if api_name.endswith('_Radiant'):
                category = 'radiant'         # Trang bị Ánh Sáng
            elif 'artifact' in api_lower or 'ornn' in api_lower:
                category = 'artifact'        # Trang bị Tạo Tác
            elif 'emblem' in api_lower or 'trait' in tags:
                category = 'emblem'          # Ấn (Emblem)
            elif '_mod' in api_lower:
                category = 'trait_mod'       # Trang bị Tộc/Hệ riêng (Mods)
            elif len(composition) >= 2:
                category = 'normal_completed' # Trang bị thường (Đồ ghép)
            else:
                category = 'normal_component' # Trang bị thường (Đồ lẻ)

            # --- Xử lý Description ---
            desc_raw = item.get('desc', '')
            clean_desc = re.sub(r'<[^>]*>', '', desc_raw)
            
            data_source = {**item.get('effects', {}), **item.get('unitProperties', {})}
            
            def replace_var(match):
                full_key = match.group(1)
                key = full_key.split(':')[-1].split('.')[-1]
                val = data_source.get(key)
                if val is not None:
                    if isinstance(val, float):
                        return str(int(val)) if val.is_integer() else str(round(val, 2))
                    return str(val)
                return match.group(0)
            
            clean_desc = re.sub(r'@([^@]+)@', replace_var, clean_desc)
            clean_desc = clean_desc.replace('&nbsp;', ' ').strip()

            # --- Map Component IDs ---
            c1 = api_to_id.get(composition[0]) if len(composition) > 0 else None
            c2 = api_to_id.get(composition[1]) if len(composition) > 1 else None

            # --- Chuẩn bị tải ảnh ---
            raw_icon = item.get('icon', '')
            local_img_path = f"{image_folder}/{index}.png"
            
            if raw_icon and not os.path.exists(local_img_path):
                img_url = "https://raw.communitydragon.org/latest/game/" + raw_icon.lower().replace('.tex', '.png')
                download_tasks.append((img_url, local_img_path))

            # --- Đóng gói Object ---
            processed_items.append({
                "id": index,
                "name": item.get('name'),
                "category": category,
                "component_1": c1,
                "component_2": c2,
                "stats": item.get('effects'), 
                "icon_path": local_img_path,
                "description": clean_desc
            })

        # Lưu JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_items, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu file database: {output_file}")

        # Tải ảnh đa luồng
        if download_tasks:
            print(f"\nBắt đầu tải {len(download_tasks)} ảnh bằng đa luồng...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(download_image, url, path) for url, path in download_tasks]
                
                completed = 0
                for _ in concurrent.futures.as_completed(futures):
                    completed += 1
                    if completed % 20 == 0 or completed == len(download_tasks):
                        print(f"Tiến độ: {completed}/{len(download_tasks)} ảnh...")
        else:
            print("\nKhông có ảnh mới cần tải.")

        print(f"\n--- HOÀN TẤT XỬ LÝ ---")

    except Exception as e:
        print(f"Lỗi: {e}")

# Chạy tool
process_tft_items_full('tft_filtered_data_1/items.json', 'items_ready_for_db.json')