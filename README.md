# 🎓 EduNexus AI — React + FastAPI + PostgreSQL

Streamlit `app.py` ko 3 alag parts me convert kiya gaya hai. Features same hain (6 tabs, 4 roles, sign up / sign in, email workflow, tracker, upload).

```
edunexus/
├── backend/    FastAPI + SQLAlchemy + pandas + plotly   (API + business logic + DB)
│   ├── app/{main,services,database,auth,data,charts,config}.py
│   ├── data/students.csv        <- 1000-student dataset (first start par DB me seed hota hai)
│   └── requirements.txt
└── frontend/   React + Vite (UI)  ->  calls backend via VITE_API_URL
```

## Local run
**Backend** (Terminal 1)
```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Mac/Linux: source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000
```
> Project OneDrive/Dropbox folder me hai to `--reload` mat lagao (sync file change dekh kar server baar-baar restart kar deta hai). Local SQLite DB ab `~/.edunexus/edunexus.db` me banta hai (project folder ke bahar).
Check: http://localhost:8000/api/health  ->  {"ok": true}   |  API docs: http://localhost:8000/docs

**Frontend** (Terminal 2)
```bash
cd frontend
copy .env.example .env         # Mac/Linux: cp .env.example .env
npm install
npm run dev
```
Open http://localhost:5173

## Accounts (Sign up / Sign in)
Har access level ka apna ID format hai aur **password = ID ke last 4 digits**:

| Access level | ID format | Example | Password |
|---|---|---|---|
| Administrator | `ADMIN` + 4 digits | `ADMIN1234` | `1234` |
| Faculty / Mentor | `FAC` + 4 digits | `FAC2001` | `2001` |
| Placement Officer | `PLC` + 4 digits | `PLC3001` | `3001` |
| Student | `STU` + 4 digits (dataset me hona chahiye) | `STU1002` | `1002` |

Pehli baar **Sign up** se account banao (student ke liye sirf ID + password; naam dataset se aata hai), phir **Sign in**.
Student sirf apna data dekh sakta hai. Student jab email "Mark as read" karta hai to staff tracker me status automatically update ho jaata hai.

## Deploy (free tier)
1. **Database** - neon.tech -> New project -> copy connection string (`postgresql://...?sslmode=require`)
2. **Backend** - render.com -> New Web Service -> repo -> Root Directory `backend`
   - Build: `pip install -r requirements.txt`
   - Start: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - Env: `DATABASE_URL`, `JWT_SECRET`, `CORS_ORIGINS` (= your Vercel URL), `PYTHON_VERSION=3.11.9`
3. **Frontend** - vercel.com -> Import repo -> Root Directory `frontend` -> Env `VITE_API_URL` = Render URL
4. Vercel URL ko Render ke `CORS_ORIGINS` me daalo -> redeploy.
