import pandas as pd
from django.shortcuts import render, HttpResponse
from concurrent.futures import ThreadPoolExecutor, as_completed
import socket
import re


def is_valid_ip(ip):
    """IP manzilni tekshirish."""
    pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    return pattern.match(ip) is not None



def is_online(ip, port=80, timeout=1):
    """IP manzilni online yoki offline ekanligini tekshirish."""
    try:
        socket.create_connection((ip, port), timeout=timeout)
        return True
    except (socket.timeout, ConnectionRefusedError, OSError):
        return False


def camera_ips(request):
    """
    So'rovni qay tartibda borishini ko'rish mumkun
    :param request:
    :return:
    """
    if request.method == 'POST' and request.FILES.get('file'):
        try:
            excel_file = request.FILES['file']
            xls = pd.ExcelFile(excel_file)
            results = []
            online_count = 0  # Online IP manzillar soni
            offline_count = 0  # Offline IP manzillar soni

            for sheet_name in xls.sheet_names:
                df = pd.read_excel(excel_file, sheet_name=sheet_name)
                if df.empty:
                    results.append({"index": 0, "IP": "N/A", "Status": "Bo'sh varaq"})
                else:
                    # IP manzillarni parallel tekshirish
                    with ThreadPoolExecutor(max_workers=10) as executor:
                        future_to_index = {}  # Indekslarni saqlash uchun
                        for index, row in df.iterrows():
                            ip_address = row.iloc[0] if pd.notna(row.iloc[0]) else None
                            if ip_address and is_valid_ip(ip_address):  # Validate IP address
                                future_to_index[executor.submit(is_online, ip_address)] = index
                            else:
                                # Agar IP manzil noto'g'ri bo'lsa yoki bo'sh bo'lsa
                                results.append({
                                    'index': index,  # Indeksni saqlaymiz
                                    'IP': ip_address if ip_address else "N/A",
                                    **{f'Ustun_{i}': row.iloc[i] if pd.notna(row.iloc[i]) else 'N/A' for i in
                                       range(1, len(row))},  # Qolgan ustunlarni qo'shamiz
                                    'Status': ''  # Leave status empty
                                })
                                continue

                        for future in as_completed(future_to_index):
                            index = future_to_index[future]  # Indeksni olamiz
                            row = df.iloc[index]  # Qatorni indeks orqali olamiz
                            ip_address = row.iloc[0]
                            try:
                                status = "online" if future.result() else "offline"
                                if status == "online":
                                    online_count += 1
                                else:
                                    offline_count += 1
                                results.append({
                                    'index': index,  # Indeksni saqlaymiz
                                    'IP': ip_address,
                                    **{f'Ustun_{i}': row.iloc[i] if pd.notna(row.iloc[i]) else 'N/A' for i in
                                       range(1, len(row))},  # Qolgan ustunlarni qo'shamiz
                                    'Status': status
                                })
                            except Exception as e:
                                results.append({
                                    'index': index,  # Indeksni saqlaymiz
                                    'IP': ip_address,
                                    **{f'Ustun_{i}': row.iloc[i] if pd.notna(row.iloc[i]) else 'N/A' for i in
                                       range(1, len(row))},  # Qolgan ustunlarni qo'shamiz
                                    'Status': 'Xatolik: ' + str(e)
                                })

            # Natijalarni indeks bo'yicha tartiblash
            results.sort(key=lambda x: x['index'])

            # Natijalarni web sahifada ko'rsatish
            return render(request, 'cameraupload.html',
                          {'results': results, 'online_count': online_count, 'offline_count': offline_count})
        except Exception as e:
            return HttpResponse(f"Xatolik yuz berdi: {str(e)}", status=500)
    return render(request, 'camera.html')
