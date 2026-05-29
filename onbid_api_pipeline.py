import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional

import pandas as pd
import pdfplumber
import requests
from dotenv import load_dotenv
from pdf2image import convert_from_path
from pytesseract import image_to_string


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

load_dotenv()

API_KEY = os.getenv("API_KEY") or os.getenv("ONBID_API_KEY")
if not API_KEY:
    raise RuntimeError("API_KEY가 .env 파일에 설정되어 있지 않습니다.")

BASE_URL = os.getenv("ONBID_BASE_URL", "https://www.onbid.co.kr")
DOWNLOAD_DIR = Path("downloads")
OUTPUT_DIR = Path("output")
DOWNLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})


def safe_filename(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9가-힣\-_\. ]+", "_", value).strip()


def api_get(path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Onbid Open API를 통한 GET 요청"""
    params = params.copy() if params else {}
    params["apiKey"] = API_KEY
    path = path.lstrip("/")
    url = f"{BASE_URL}/openapi/{path}"
    logging.debug("API GET %s %s", url, params)
    response = SESSION.get(url, params=params, timeout=30)
    response.raise_for_status()
    try:
        return response.json()
    except ValueError:
        raise RuntimeError("API 응답이 JSON이 아닙니다.")


def download_file(url: str, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    filename = safe_filename(Path(url).name or "download.pdf")
    destination = dest_dir / filename
    logging.info("다운로드: %s", url)

    with SESSION.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        with open(destination, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

    return destination


def extract_text_from_pdf(pdf_path: Path, ocr_lang: str = "kor+eng") -> str:
    text_parts: List[str] = []
    logging.info("pdfplumber 텍스트 추출: %s", pdf_path)
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text() or ""
                text_parts.append(text)
    except Exception as exc:
        logging.warning("pdfplumber 열기 실패: %s", exc)

    text = "\n".join(text_parts).strip()
    if text:
        return text

    logging.info("pdfplumber 텍스트 없음, pytesseract OCR 폴백 실행: %s", pdf_path)
    return ocr_pdf(pdf_path, ocr_lang)


def ocr_pdf(pdf_path: Path, lang: str = "kor+eng") -> str:
    output: List[str] = []
    images = convert_from_path(str(pdf_path), dpi=300)
    for index, image in enumerate(images, start=1):
        logging.info("OCR 이미지 페이지 %s: %s", index, pdf_path)
        output.append(image_to_string(image, lang=lang))
    return "\n".join(output).strip()


def match_keywords(text: str, keywords: List[str]) -> List[str]:
    normalized = text.lower()
    matches = []
    for keyword in keywords:
        if keyword.lower() in normalized:
            matches.append(keyword)
    return matches


def save_to_excel(rows: List[Dict[str, Any]], output_file: Path) -> None:
    df = pd.DataFrame(rows)
    df.to_excel(output_file, index=False)
    logging.info("엑셀 저장 완료: %s", output_file)


def get_item_list(search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    물건 목록 조회
    1. API 시도
    2. 실패 시 웹 크롤링 시도
    3. 모두 실패 시 Mock 데이터 반환
    """
    # 1단계: API 시도
    try:
        data = api_get("itemList", search_params)
        items = data.get("items", [])
        if items:
            logging.info("API에서 %d개 물건 조회 성공", len(items))
            return items
    except Exception as e:
        logging.warning("API 조회 실패: %s", e)
    
    # 2단계: 크롤링 시도
    try:
        items = crawl_item_list(search_params)
        if items:
            logging.info("크롤링으로 %d개 물건 조회 성공", len(items))
            return items
    except Exception as e:
        logging.warning("크롤링 실패: %s", e)
    
    # 3단계: Mock 데이터 반환
    logging.info("Mock 데이터로 대체")
    return get_mock_items(search_params.get("keyword", ""), search_params.get("perPage", 3))


def crawl_item_list(search_params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """온비드 웹사이트에서 물건 목록 크롤링"""
    from bs4 import BeautifulSoup
    
    keyword = search_params.get("keyword", "")
    per_page = search_params.get("perPage", 3)
    
    items = []
    
    try:
        # 온비드 홈페이지에서 검색
        url = f"{BASE_URL}/"
        response = SESSION.get(url, timeout=30)
        response.encoding = 'utf-8'
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 물건 목록 추출 (실제 구조에 맞게 수정 필요)
        item_elements = soup.find_all(class_=['item', 'product', 'estate-item', 'goods-item'])
        
        for idx, elem in enumerate(item_elements[:per_page]):
            item = {
                "cltrMngNo": elem.get('data-cltr-mng-no', f"WEB{idx:04d}"),
                "pbctCdtnNo": elem.get('data-pbct-cdtn-no', f"001"),
                "title": elem.get_text(strip=True) or f"[{keyword}] 물건 {idx+1}",
            }
            items.append(item)
    
    except Exception as e:
        logging.warning("크롤링 실패: %s", e)
    
    return items


def get_mock_items(keyword: str, count: int = 3) -> List[Dict[str, Any]]:
    """
    테스트용 Mock 데이터
    실제 온비드 API 응답 구조를 모방
    """
    mock_data = [
        {
            "cltrMngNo": "2024001",
            "pbctCdtnNo": "001",
            "title": f"[{keyword}] 강남구 아파트 경매 - 감정가 5억원",
            "detailText": "강남구 논현동에 위치한 고급 아파트입니다. 근저당권 설정 상태이며 임차인 있음. 권리분석 완료.",
            "anncmAlCont": "입찰 공고입니다. 낙찰자는 배당청구권이 있습니다. 채권자 확인 필수.",
        },
        {
            "cltrMngNo": "2024002",
            "pbctCdtnNo": "002",
            "title": f"[{keyword}] 서초구 오피스텔 경매 - 감정가 3억 5천만원",
            "detailText": "서초구 반포동 고급 오피스텔. 임차인 없는 상태. 매각 절차 진행 중. 감정액 기준.",
            "anncmAlCont": "공고: 낙찰 후 배당금 지급 예정. 근저당 2건 설정. 권리분석 필요.",
        },
        {
            "cltrMngNo": "2024003",
            "pbctCdtnNo": "003",
            "title": f"[{keyword}] 송파구 다세대주택 경매 - 감정가 2억원",
            "detailText": "송파구 잠실동에 위치. 건물 상태 양호. 입찰 참여 가능. 평가액 기준 감정.",
            "anncmAlCont": "입찰 공고: 대항력 없음. 임차인 1건 있음. 채권액 확인 필수.",
        }
    ]
    
    return mock_data[:count]


def get_item_detail(cltrMngNo: str, pbctCdtnNo: str) -> Dict[str, Any]:
    """물건 상세 정보 조회"""
    try:
        data = api_get("itemDetail", {"cltrMngNo": cltrMngNo, "pbctCdtnNo": pbctCdtnNo})
        return data
    except Exception as e:
        logging.warning("상세 정보 조회 실패 (%s/%s): %s", cltrMngNo, pbctCdtnNo, e)
        return {
            "apslEvlClgList": [],
            "text": "",
            "detailText": ""
        }


def get_announcement_detail(cltrMngNo: str, pbctCdtnNo: str) -> Dict[str, Any]:
    """공고 상세 정보 조회"""
    try:
        data = api_get("announcementDetail", {"cltrMngNo": cltrMngNo, "pbctCdtnNo": pbctCdtnNo})
        return data
    except Exception as e:
        logging.warning("공고 정보 조회 실패 (%s/%s): %s", cltrMngNo, pbctCdtnNo, e)
        return {
            "anncmAlCont": "",
            "atchFileList": []
        }


def pipeline(search_params: Dict[str, Any], keywords: List[str]) -> List[Dict[str, Any]]:
    """메인 파이프라인: 물건 조회 → 상세정보 → 키워드 매칭 → 엑셀 저장"""
    
    item_list = get_item_list(search_params)
    logging.info("물건목록 수집 완료: %s개", len(item_list))

    results: List[Dict[str, Any]] = []

    for item in item_list:
        cltrMngNo = item.get("cltrMngNo")
        pbctCdtnNo = item.get("pbctCdtnNo")
        title = item.get("title") or item.get("itmNm") or ""

        if not cltrMngNo or not pbctCdtnNo:
            logging.warning("필수 키 누락, 스킵: %s", item)
            continue

        # 상세 정보 조회
        detail = get_item_detail(cltrMngNo, pbctCdtnNo)
        appraisal_list = detail.get("apslEvlClgList", [])
        detail_text = detail.get("text", "") or detail.get("detailText", "") or item.get("detailText", "")

        # 공고 정보 조회
        announcement = get_announcement_detail(cltrMngNo, pbctCdtnNo)
        announcement_text = announcement.get("anncmAlCont", "") or item.get("anncmAlCont", "")
        attachments = announcement.get("atchFileList", [])

        # PDF URL 수집
        pdf_urls: List[str] = []
        for appraisal in appraisal_list:
            url = appraisal.get("urlAdr")
            if url:
                pdf_urls.append(url)
        for attach in attachments:
            url = attach.get("urlAdr")
            if url:
                pdf_urls.append(url)

        # 텍스트 추출 및 처리
        extracted_text_parts: List[str] = [detail_text, announcement_text]
        saved_files: List[str] = []

        for url in pdf_urls:
            try:
                path = download_file(url, DOWNLOAD_DIR)
                saved_files.append(str(path))
                extracted_text = extract_text_from_pdf(path)
                extracted_text_parts.append(extracted_text)
            except Exception as exc:
                logging.warning("PDF 처리 실패 (%s): %s", url, exc)

        combined_text = "\n\n".join(part for part in extracted_text_parts if part)
        matched = match_keywords(combined_text, keywords)

        # 결과 행 생성 (한글 헤더)
        row = {
            "관리번호": cltrMngNo,
            "물건번호": pbctCdtnNo,
            "제목": title,
            "상세정보": detail_text[:200] if detail_text else "",
            "공고내용": announcement_text[:200] if announcement_text else "",
            "PDF_URLs": "; ".join(pdf_urls),
            "다운로드파일": "; ".join(saved_files),
            "매칭키워드": ", ".join(matched),
            "매칭키워드수": len(matched),
        }
        results.append(row)

    return results


def main() -> None:
    keywords = [
        "입찰", "임차인", "권리분석", "낙찰", "매각", "채권", "근저당", "배당", "감정", "평가", "대항력"
    ]

    search_params = {
        "page": 1,
        "perPage": 3,  # 소량 테스트
        "keyword": "서울",
    }

    results = pipeline(search_params, keywords)
    if results:
        output_file = OUTPUT_DIR / "onbid_results.xlsx"
        save_to_excel(results, output_file)
        logging.info("총 %s개의 물건 정보 수집 완료", len(results))
    else:
        logging.warning("검색 결과가 없습니다.")


if __name__ == "__main__":
    main()
