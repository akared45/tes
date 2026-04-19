import requests
import json
import os

api_url = "https://data.metatft.com/lookups/TFTSet17_latest_vi_vn.json"

def download_and_filter_tft_data():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36',
        'Origin': 'https://www.metatft.com',
        'Referer': 'https://www.metatft.com/'
    }

    try:
        print(f"Đang tải dữ liệu từ API...")
        response = requests.get(api_url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            output_dir = 'tft_filtered_data_1'
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            print("Thành công! Bắt đầu tự động trích xuất tất cả các mục...")

            for key, value in data.items():
                file_path = os.path.join(output_dir, f"{key}.json")
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(value, f, ensure_ascii=False, indent=4)

                if isinstance(value, list):
                    count = len(value)
                elif isinstance(value, dict):
                    count = len(value)
                else:
                    count = 1

                print(f"Đã lưu {key}.json - {count} phần tử.")
            
            print(f"\nHoàn tất! Tất cả dữ liệu đã nằm trong: {output_dir}/")
            
        else:
            print(f"Lỗi: Status code {response.status_code}")
    except Exception as e:
        print(f"Lỗi hệ thống: {e}")

download_and_filter_tft_data()