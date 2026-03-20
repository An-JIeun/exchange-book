# meet-zool

교환독서를 위한 웹서비스입니다.

- Frontend: Vite + Vue
- Backend: FastAPI (Python)
- DB: MySQL

> 배포는 Render 기준으로 정리했습니다.

## 정리 사항

Vue 전환 후 사용하지 않는 React 기본 파일들을 정리했습니다.

- `frontend/src/App.jsx`
- `frontend/src/App.css`
- `frontend/src/main.jsx`
- `frontend/src/assets/*`
- `frontend/README.md`
- `frontend/eslint.config.js`

## 구현 기능

1. 다인원 유저 사용 (유저 생성/선택)
2. 서재 UI
3. 책 클릭 시 페이지별 밑줄 확인
4. 밑줄 댓글 추가
5. 본인 밑줄 추가
6. 유저별 대시보드 (현재 읽는 책/페이지, 다음 책)

## 실행 방법

### 1) 백엔드 + MySQL

```bash
docker compose up --build
```

API 주소: `http://localhost:8000/api`

### 2) 프론트엔드 (Vite)

```bash
cd frontend
npm install
npm run dev
```

웹 주소: `http://localhost:5173`

로컬 개발에서는 Vite 프록시가 `/api` 요청을 백엔드로 전달합니다.

## 배포 (Render)

Render 배포 구성:

- 백엔드: Render Web Service (Docker)
- 프론트엔드: Render Static Site
- DB: 외부 MySQL 또는 MySQL 호환 DB (예: TiDB Serverless)

관련 파일:

- [render.yaml](render.yaml)
- [backend/.env.render.example](backend/.env.render.example)
- [frontend/.env.production.example](frontend/.env.production.example)

### Render에서 설정할 값

1. 백엔드 서비스 `DATABASE_URL`
2. 프론트 정적 사이트 `VITE_API_BASE` (예: `https://<your-backend>.onrender.com/api`)

### 배포 순서

1. Render에 GitHub 레포 연결
2. Blueprint 배포 시 [render.yaml](render.yaml) 선택
3. 백엔드 `DATABASE_URL` 입력 후 배포
4. 백엔드 URL 확인 (`https://<your-backend>.onrender.com`)
5. 프론트 `VITE_API_BASE`를 `https://<your-backend>.onrender.com/api`로 입력

> 무료 플랜/정책은 수시로 바뀔 수 있으므로 Render 요금 페이지를 함께 확인하세요.

## API 요약

- `POST /api/users`, `GET /api/users`
- `PATCH /api/users/{user_id}/dashboard`
- `POST /api/books`, `GET /api/books`
- `POST /api/underlines`, `GET /api/underlines/book/{book_id}?page={n}`
- `POST /api/comments`, `GET /api/comments/underline/{underline_id}`
- `GET /api/dashboards/{user_id}`
- `GET /api/health`
