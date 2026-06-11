# Korean Spacing Tool

오프라인 우리말샘 사전 기반 한국어 띄어쓰기 판단 도구입니다.

## 다운로드 (바로 실행)

**[korean-spacing-v0.1.0.zip 다운로드](https://github.com/sophie-linguist/korean-spacing/releases/download/v0.1.0/korean-spacing-v0.1.0.zip)**

1. 위 링크에서 zip 파일을 다운로드합니다.
2. 압축을 풀고 `korean-spacing.exe`를 더블클릭합니다.
3. `dict.db`는 exe와 같은 폴더에 있어야 합니다 (zip에 포함).

> Windows 보안 경고가 뜨면 "추가 정보" → "실행"을 누르세요.

---

## 개발자용 설치 방법

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
