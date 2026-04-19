import json
import re
import os
import time
import requests
import concurrent.futures

def get_accent_color(cost):
    colors = {
        1: "#808080", 2: "#11B288", 3: "#207AC7", 4: "#C440DA", 5: "#FFB300"
    }
    return colors.get(cost, "#FFFFFF")

def download_image(img_url, local_path, max_retries=3):
    """Hàm tải ảnh an toàn với cơ chế thử lại (Retry)"""
    if os.path.exists(local_path):
        return  # Bỏ qua nếu đã có sẵn
    
    headers = {'User-Agent': 'Mozilla/5.0'}
    for attempt in range(max_retries):
        try:
            r = requests.get(img_url, headers=headers, timeout=15)
            if r.status_code == 200:
                with open(local_path, 'wb') as f_img:
                    f_img.write(r.content)
                return
            elif r.status_code == 404:
                return # Bỏ qua nếu server không có file này
        except Exception:
            if attempt < max_retries - 1:
                time.sleep(2) # Đợi 2s rồi thử lại

def process_tft_core_data(units_file, traits_file):
    try:
        # --- 1. KHỞI TẠO THƯ MỤC ẢNH ---
        folders = ['champions_icons', 'champions_splash', 'skills_icons', 'traits_icons']
        for folder in folders:
            if not os.path.exists(folder):
                os.makedirs(folder)

        # --- 2. ĐỌC DỮ LIỆU ---
        with open(units_file, 'r', encoding='utf-8') as f:
            units_data = json.load(f)
        with open(traits_file, 'r', encoding='utf-8') as f:
            traits_data = json.load(f)
            
        units = units_data if isinstance(units_data, list) else units_data.get('units', [])
        traits = traits_data if isinstance(traits_data, list) else traits_data.get('traits', [])

        champions_db, skills_db, traits_db, champion_traits_db = [], [], [], []
        champ_api_to_id = {}
        download_tasks = [] # Danh sách URL cần tải

        print(f"Bắt đầu xử lý {len(units)} tướng và {len(traits)} tộc hệ...")

        # ==========================================
        # PHẦN 1: XỬ LÝ TƯỚNG VÀ KỸ NĂNG (1-TO-1)
        # ==========================================
        champ_id_counter = 1
        for unit in units:
            cost = unit.get('cost', 0)
            if cost == 0: continue 

            api_name = unit.get('apiName', '')
            ability = unit.get('ability', {})
            stats = unit.get('stats', {})
            skill_id = champ_id_counter
            champ_api_to_id[api_name] = champ_id_counter

            # --- Kỹ Năng (Skill) ---
            desc_raw = ability.get('desc', '')
            variables = ability.get('variables', [])
            
            def replace_ability_var(match):
                var_name = match.group(1)
                for v in variables:
                    if v.get('name') == var_name:
                        vals = v.get('value', [])
                        if not isinstance(vals, list): return str(vals)
                        formatted_vals = []
                        for x in vals[:3]:
                            if x is None: formatted_vals.append("0")
                            elif isinstance(x, (int, float)):
                                formatted_vals.append(str(int(x)) if x == int(x) else str(round(x, 2)))
                            else: formatted_vals.append(str(x))
                        return "/".join(formatted_vals)
                return match.group(0)

            clean_desc = re.sub(r'@(\w+)@', replace_ability_var, desc_raw)
            clean_desc = re.sub(r'<[^>]*>', '', clean_desc).replace('&nbsp;', ' ').strip()

            # URL & Local Path Ảnh Kỹ Năng
            raw_skill_icon = ability.get('icon', '')
            local_skill_icon = f"skills_icons/{skill_id}.png"
            if raw_skill_icon:
                img_url = "https://raw.communitydragon.org/latest/game/" + raw_skill_icon.lower().replace('.tex', '.png')
                download_tasks.append((img_url, local_skill_icon))

            skills_db.append({
                "id": skill_id,
                "name": ability.get('name'),
                "mana_start": stats.get('initialMana', 0),
                "mana_max": stats.get('mana', 0),
                "description": clean_desc,
                "ability_stats": variables,
                "icon_path": local_skill_icon # Đã map về máy
            })

            # --- Tướng (Champion) ---
            raw_champ_icon = unit.get('icon', '')
            raw_splash = unit.get('tileIcon', unit.get('squareIcon', ''))
            local_champ_icon = f"champions_icons/{champ_id_counter}.png"
            local_splash = f"champions_splash/{champ_id_counter}.png"

            if raw_champ_icon:
                img_url = "https://raw.communitydragon.org/latest/game/" + raw_champ_icon.lower().replace('.tex', '.png')
                download_tasks.append((img_url, local_champ_icon))
            if raw_splash:
                img_url = "https://raw.communitydragon.org/latest/game/" + raw_splash.lower().replace('.tex', '.png')
                download_tasks.append((img_url, local_splash))

            champions_db.append({
                "id": champ_id_counter,
                "name": unit.get('name'),
                "cost": cost,
                "accent_color": get_accent_color(cost),
                "skill_id": skill_id,
                "base_stats": stats,
                "icon_path": local_champ_icon, # Đã map về máy
                "splash_path": local_splash    # Đã map về máy
            })
            champ_id_counter += 1

        # ==========================================
        # PHẦN 2: XỬ LÝ TỘC HỆ VÀ LIÊN KẾT
        # ==========================================
        ct_id_counter = 1
        for trait_index, trait in enumerate(traits, start=1):
            api_name = trait.get('apiName', '')
            
            # --- Trait ---
            effects = trait.get('effects', [])
            desc_raw = trait.get('desc', '')
            processed_milestones = [{"min_units": e.get('minUnits'), "max_units": e.get('maxUnits'), "style": e.get('style'), "variables": e.get('variables')} for e in effects]
            clean_desc_trait = re.sub(r'<[^>]*>', '', desc_raw).replace('&nbsp;', ' ').strip()

            # URL & Local Path Ảnh Tộc Hệ
            raw_trait_icon = trait.get('icon', '')
            local_trait_icon = f"traits_icons/{trait_index}.png"
            if raw_trait_icon:
                img_url = "https://raw.communitydragon.org/latest/game/" + raw_trait_icon.lower().replace('.tex', '.png')
                download_tasks.append((img_url, local_trait_icon))

            traits_db.append({
                "id": trait_index,
                "name": trait.get('name'),
                "type": "origin" if "Origin" in api_name else "class", 
                "rank": None, 
                "milestones": processed_milestones,
                "icon_path": local_trait_icon, # Đã map về máy
                "description": clean_desc_trait
            })

            # --- Champion_Traits ---
            for u in trait.get('units', []):
                unit_api_name = u.get('unit')
                if unit_api_name in champ_api_to_id:
                    champion_traits_db.append({
                        "id": ct_id_counter, "champion_id": champ_api_to_id[unit_api_name], "trait_id": trait_index
                    })
                    ct_id_counter += 1

        # ==========================================
        # PHẦN 3: XUẤT FILE & TẢI ẢNH ĐA LUỒNG
        # ==========================================
        with open('db_skills.json', 'w', encoding='utf-8') as f: json.dump(skills_db, f, ensure_ascii=False, indent=4)
        with open('db_champions.json', 'w', encoding='utf-8') as f: json.dump(champions_db, f, ensure_ascii=False, indent=4)
        with open('db_traits.json', 'w', encoding='utf-8') as f: json.dump(traits_db, f, ensure_ascii=False, indent=4)
        with open('db_champion_traits.json', 'w', encoding='utf-8') as f: json.dump(champion_traits_db, f, ensure_ascii=False, indent=4)

        print(f"\n✅ Đã lưu xong 4 file JSON Database!")

        if download_tasks:
            print(f"🔥 Bắt đầu tải {len(download_tasks)} ảnh bằng Đa luồng (Giới hạn 5 workers để tránh lỗi mạng)...")
            with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
                futures = [executor.submit(download_image, url, path) for url, path in download_tasks]
                completed = 0
                for _ in concurrent.futures.as_completed(futures):
                    completed += 1
                    if completed % 20 == 0 or completed == len(download_tasks):
                        print(f"  -> Đã tải {completed}/{len(download_tasks)} ảnh...")
        else:
            print("\nKhông có ảnh mới cần tải.")

        print("\n--- HOÀN TẤT ---")

    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

process_tft_core_data('tft_filtered_data_1/units.json', 'tft_filtered_data_1/traits.json')