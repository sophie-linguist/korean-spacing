# Korean Spacing Tool

## 설치 방법

```bash
pip install -r requirements.txt
```

## 필요한 환경변수 목록

`.env.example` 파일을 복사해 `.env`를 만든 뒤 값을 설정하세요.

- `KOREAN_SPACING_DB_PATH` (선택): `dict.db` 경로. 미설정 시 현재 작업 폴더의 `dict.db` 또는 실행 파일 옆 `dict.db`를 사용합니다.

## 실행 방법

1. 프로젝트 루트에 `dict.db`를 두거나, `.env`에서 `KOREAN_SPACING_DB_PATH`를 설정합니다.
2. 아래 실행 명령어 중 하나를 사용합니다.

## 실행 명령어

웹 UI:

```bash
python -m shell.webui.app
```

Tkinter UI:

```bash
python -m shell.gui.app
```

로컬 인덱스 빌드:

```bash
python build/build_index.py --source "전체 내려받기_우리말샘_json_20260603" --output "dict.db" --schema "build/schema.sql"
```
