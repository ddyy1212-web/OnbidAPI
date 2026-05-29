# OnbidAPI

## 환경 변수 설정

프로젝트 루트에 `.env` 파일을 만들고 API 키를 설정하세요.

```env
API_KEY=your_api_key_here
```

`.gitignore`에 `.env`가 등록되어 있어 버전 관리에 포함되지 않습니다.

## 설치

```bash
python3 -m pip install -r requirements.txt
```

> Tesseract OCR과 poppler가 필요합니다.
> Ubuntu 기준:
> ```bash
> sudo apt-get update
> sudo apt-get install -y tesseract-ocr tesseract-ocr-kor poppler-utils
> ```

## 사용법

```bash
python3 onbid_api_pipeline.py
```

## 기능

1. 물건목록 API 호출 → `cltrMngNo`, `pbctCdtnNo` 획득
2. 물건상세 API 호출 → `apslEvlClgList[].urlAdr` PDF URL 및 텍스트 추출
3. 공고상세 API 호출 → `anncmAlCont`, `atchFileList[].urlAdr`
4. PDF 다운로드 및 텍스트 추출
   - `pdfplumber`로 먼저 시도
   - 텍스트가 없으면 `pytesseract` OCR 폴백
5. 키워드 필터링
6. 엑셀 저장 (`output/onbid_results.xlsx`)

## 수정 포인트

- `onbid_api_pipeline.py`의 `BASE_URL`와 API 엔드포인트 경로를 실제 Onbid API 사양에 맞게 수정하세요.
- `get_item_list`, `get_item_detail`, `get_announcement_detail` 함수의 경로와 파라미터는 실제 응답 형태에 맞게 조정해야 합니다.


## 환경 변수 설정

API 키를 노출하지 않기 위해 프로젝트 루트에 `.env` 파일을 생성하고 아래와 같이 설정하세요:

```env
API_KEY=your_api_key_here
```

`.env` 파일은 `.gitignore`에 추가되어 있으므로 버전 관리에 포함되지 않습니다.
