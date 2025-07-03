import os
import re
import socket
import pandas as pd
from .models import CustomUser
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse
from django.http import FileResponse
from django.views.generic import ListView
from .forms import RegisterForm, LoginForm
from django.shortcuts import render, redirect
from django.contrib.auth import get_user_model
from django.contrib.auth import login, logout, authenticate
from concurrent.futures import ThreadPoolExecutor, as_completed

User = get_user_model()


class UserListView(ListView):
    template_name = 'userlist.html'
    context_object_name = 'users'
    paginate_by = 10
    model = CustomUser
    ordering = ['username']


def archive_view(request):
    # Arxiv fayllar ro'yxatini olish
    archive_dir = os.path.join(settings.BASE_DIR, 'archives')
    archive_files = []
    if os.path.exists(archive_dir):
        archive_files = sorted(os.listdir(archive_dir), reverse=True)
    return render(request, 'archive.html', {'archive_files': archive_files})


def download_archive(request, filename):
    file_path = os.path.join(settings.BASE_DIR, 'archives', filename)
    if os.path.exists(file_path):
        return FileResponse(open(file_path, 'rb'), as_attachment=True)
    else:
        return HttpResponse("Fayl topilmadi", status=404)


def home_view(request):
    return render(request, 'home.html')


def camera_view(request):
    return render(request, 'camera.html')


def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)  # Ro'yxatdan o'tgandan so'ng avtomatik tizimga kirish
            messages.success(request, "Ro'yxatdan muvaffaqiyatli o'tdingiz!")
            return redirect('home')  # Bosh sahifaga yo'naltirish
    else:
        form = RegisterForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Xush kelibsiz, {username}!")
                return redirect('home')  # Bosh sahifaga yo'naltirish
    else:
        form = LoginForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.success(request, "Tizimdan muvaffaqiyatli chiqdingiz!")
    return redirect('home')  # Bosh sahifaga yo'naltirish


def is_online(ip_address, port=80, timeout=1):
    try:
        sock = socket.create_connection((ip_address, port), timeout)
        sock.close()
        return True
    except (socket.timeout, socket.error):
        return False


def is_valid_ip(ip):
    """IP manzilni tekshirish."""
    pattern = re.compile(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$')
    return pattern.match(ip) is not None


def check_ips(request):
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
                                    'Status': "IP manzil mavjud emas"  # Leave status empty
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
            return render(request, 'results.html',
                          {'results': results, 'online_count': online_count, 'offline_count': offline_count})

        except Exception as e:
            return HttpResponse(f"Xatolik yuz berdi: {str(e)}", status=500)
    return render(request, 'upload.html')
