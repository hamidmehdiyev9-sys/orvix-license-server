# GitHub-da sıfırdan başlamaq

## 1) Köhnə repozitoriyanı silmək (istəyə bağlı)

GitHub-da **köhnə repo** (məs. `pvaq8-license-server`) üzərində:

1. Repo → **Settings** (parametrlər)
2. Aşağıda **Danger Zone**
3. **Delete this repository** → repoadı və təsdiq yazısını yaz → sil

**Diqqət:** Silinən repo geri gəlmir. Əgər şübhəlisənsə, repo **silmə** — yalnız **yeni boş repo** ilə də davam edə bilərsən.

---

## 2) Yeni boş repo yaratmaq

1. [github.com/new](https://github.com/new)
2. **Repository name:** məs. `orvix-lite` (özün seç)
3. **Public** və ya **Private**
4. **Add a README** işarəsini **çıxart** (boş repo olsun deyə — ilk push üçün daha səliqəli)
5. **Create repository**

Sənə göstərilən səhifədə **HTTPS** ünvanı olacaq, məsələn:

`https://github.com/ISTIFADECI_ADI/orvix-lite.git`

Bunu kopyala.

---

## 3) Kompüterdə layihəni ilk dəfə Git-ə vermək

**PowerShell** (Windows) — `ORVIX YENI` qovluğunda:

```powershell
cd "C:\Users\USER\Desktop\ORVIX YENI"

git init
git add .
git status
git commit -m "Initial commit: Orvix Lite + license server"
git branch -M main
git remote add origin https://github.com/ISTIFADECI_ADI/orvix-lite.git
git push -u origin main
```

`ISTIFADECI_ADI` və `orvix-lite` — öz GitHub istifadəçi adın və yaratdığın repo adı ilə əvəz et.

İlk dəfə `git push` zamanı GitHub **login** istəyə bilər (brauzer və ya token).

---

## 4) Nə yüklənir?

Repo kökündə **bütün layihə** gedir: `orvix/`, `license-server/`, `ORVIX_PRO_v24.py`, `pvaq_analyzer.py`, `.gitignore`, `.github/` və s.

**Yüklənməməli** (`.gitignore` sayəsində):

- `.venv/`, `__pycache__/`
- `.env` (sirrlər)
- `*.db` (lokal SQLite)

---

## 5) Sonrakı dəyişikliklər

```powershell
cd "C:\Users\USER\Desktop\ORVIX YENI"
git add .
git commit -m "Qısa izah: nə dəyişdi"
git push
```

---

## Qısa məzmun

| Addım | Harada |
|--------|--------|
| Köhnə repo sil | GitHub → Settings → Delete |
| Yeni boş repo | github.com/new |
| Kod göndər | `git init` → `add` → `commit` → `remote` → `push` |

Əgər `git` kompüterdə yoxdursa: [Git for Windows](https://git-scm.com/download/win) quraşdır.
