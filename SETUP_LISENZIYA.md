# Lisenziya — sənin etməli olduqlar (qısa)

Kod tərəfi bu layihədə hazırdır. **GitHub hesabına və Render-ə giriş** yalnız sən edə bilərsən.

## 1) GitHub

1. [github.com](https://github.com) — **New repository** (məs. `orvix-app`).
2. Kompüterdə bu qovluğu əlavə et:
   ```powershell
   cd "C:\Users\USER\Desktop\ORVIX YENI"
   git init
   git add .
   git commit -m "Initial Orvix + license server"
   git branch -M main
   git remote add origin https://github.com/SENIN-ISTIFADECI/orvix-app.git
   git push -u origin main
   ```
   (`SENIN-ISTIFADECI` və repo adını özünə görə dəyiş.)

## 2) Render — lisenziya serveri

1. [render.com](https://render.com) → **New +** → **Web Service**.
2. GitHub repo bağla → qovluğu seçərkən **`license-server`** alt qovluğunu göstər (Render-də “Root Directory” sahəsi: `license-server`).
3. **Build:** `pip install -r requirements.txt`  
   **Start:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
4. **PostgreSQL** əlavə et və Web Service-ə **Link** et (DATABASE_URL avtomatik gəlir).
5. **Environment** əlavə et:
   - `JWT_SECRET` — uzun təsadüfi mətn (məs. 40 simvol)
   - `ADMIN_PASSWORD` — admin panel şifrəsi
   - `TRIAL_DAYS` = `7`
6. **Deploy** et. Sayt ünvanını kopyala: `https://xxxx.onrender.com`

**Admin panel:** brauzerdə `https://xxxx.onrender.com/admin/login` — lisenziya açarı yaratmaq üçün.

## 3) Orvix masaüstü proqramı

İş masasında (və ya `.bat` faylında) **Render URL**-i yaz:

```bat
set ORVIX_LICENSE_SERVER=https://xxxx.onrender.com
```

Yerli kod yazarkən lisenziyanı ötürmək üçün:

```bat
set ORVIX_LICENSE_SKIP=1
```

## Sənin etməyin mümkün olmayanları mən etmərəm

- GitHub-a **login** və **push**
- Render-də **hesab**, **kart** (lazımsa), **Deploy** düyməsi

Qalan kod və struktur layihədə hazırdır.
