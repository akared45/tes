import json
import re
import os
import time
import requests
import concurrent.futures

def download_image(img_url, local_path, max_retries=3):
    """Hàm tải ảnh an toàn với cơ chế thử lại (Retry) chống đứt cáp"""
    if os.path.exists(local_path):
        return  
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(max_retries):
        try:
            r = requests.get(img_url, headers=headers, timeout=15)
            if r.status_code == 200:
                with open(local_path, 'wb') as f_img:
                    f_img.write(r.content)
                return
            elif r.status_code == 404:
                return 
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2) 

def process_tft_augments_multithread(input_file, output_file, image_folder='augments_images'):
    try:
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)
            print(f"Đã tạo thư mục: {image_folder}")

        with open(input_file, 'r', encoding='utf-8') as f:
            raw_data = json.load(f)

        augments_list = raw_data if isinstance(raw_data, list) else raw_data.get('augments', [])

        processed_augments = []
        download_tasks = []
        
        print(f"Đang xử lý text {len(augments_list)} lõi nâng cấp...")

        for index, item in enumerate(augments_list, start=1):
            desc_raw = item.get('desc', '')
            effects = item.get('effects', {})
            
            def replace_var(match):
                var_name = match.group(1)
                val = effects.get(var_name)
                if val is not None:
                    return str(int(val)) if isinstance(val, float) and val.is_integer() else str(val)
                return match.group(0)

            clean_desc = re.sub(r'@(\w+)@', replace_var, desc_raw)
            clean_desc = re.sub(r'<[^>]*>', '', clean_desc).replace('&nbsp;', ' ').strip()

            rarity = (item.get('rarity') or '').lower()
            api_name = (item.get('apiName') or '').lower()
            raw_icon = item.get('icon', '')
            icon_lower = raw_icon.lower()
            
            if rarity == 'prismatic' or '_iii' in api_name or '_iii' in icon_lower:
                tier = 3
            elif rarity == 'gold' or '_ii' in api_name or '_ii' in icon_lower:
                tier = 2
            else:
                tier = 1

            local_icon_path = None
            if raw_icon:
                img_url = "https://raw.communitydragon.org/latest/game/" + icon_lower.replace('.tex', '.png')
                local_icon_path = f"{image_folder}/{index}.png"
                download_tasks.append((img_url, local_icon_path))

            processed_augments.append({
                "id": index,
                "name": item.get('name'),
                "description": clean_desc,
                "tier": tier,
                "icon_path": local_icon_path 
            })

        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_augments, f, ensure_ascii=False, indent=4)
        print(f"✅ Đã lưu xong Database {len(processed_augments)} bản ghi vào: {output_file}")

        if download_tasks:
            print(f"🔥 Bắt đầu tải {len(download_tasks)} ảnh bằng Đa luồng (10 workers)...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                futures = [executor.submit(download_image, url, path) for url, path in download_tasks]
                
                completed = 0
                for _ in concurrent.futures.as_completed(futures):
                    completed += 1
                    if completed % 20 == 0 or completed == len(download_tasks):
                        print(f"  -> Đã tải {completed}/{len(download_tasks)} ảnh...")
        else:
            print("Không có ảnh mới nào cần tải.")

        print(f"\n--- HOÀN TẤT ---")

    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

# Chạy tool
process_tft_augments_multithread('tft_filtered_data_1/augments.json', 'augments_ready_for_db.json')
