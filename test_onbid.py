#!/usr/bin/env python3
"""온비드 API 소량 테스트 스크립트"""

import sys
from pathlib import Path

# onbid_api_pipeline 모듈 임포트
from onbid_api_pipeline import pipeline

def test_search():
    """소량 테스트 검색 실행"""
    
    # 소량의 데이터로 테스트하기 위한 검색 파라미터
    search_params = {
        "page": 1,
        "perPage": 3,  # 소량 테스트: 3개만 조회
        "keyword": "서울",  # 서울 지역 검색
    }
    
    # 키워드 리스트
    keywords = [
        "입찰", "임차인", "권리분석", "낙찰", "매각", 
        "채권", "근저당", "배당", "감정", "평가", "대항력"
    ]
    
    print("=" * 70)
    print("온비드 물건검색 시범 테스트 시작")
    print("=" * 70)
    print(f"검색 조건: {search_params}")
    print(f"매칭 키워드: {', '.join(keywords)}")
    print("=" * 70)
    
    try:
        results = pipeline(search_params, keywords)
        
        print(f"\n✅ 수집 완료: {len(results)}개 물건\n")
        print("=" * 70)
        
        for idx, result in enumerate(results, 1):
            print(f"\n[물건 {idx}]")
            print(f"  관리번호: {result.get('관리번호', 'N/A')}")
            print(f"  물건번호: {result.get('물건번호', 'N/A')}")
            print(f"  제목: {result.get('제목', 'N/A')}")
            print(f"  상세정보 (미리보기): {result.get('상세정보', 'N/A')[:50]}...")
            print(f"  공고내용 (미리보기): {result.get('공고내용', 'N/A')[:50]}...")
            print(f"  매칭 키워드 수: {result.get('매칭키워드수', 0)}")
            if result.get('매칭키워드'):
                print(f"  매칭 키워드: {result.get('매칭키워드', '')}")
            pdf_count = len([f for f in result.get('다운로드파일', '').split('; ') if f]) if result.get('다운로드파일') else 0
            print(f"  다운로드 파일: {pdf_count}개")
        
        print("\n" + "=" * 70)
        print("✅ 테스트 완료!")
        print("결과는 output/onbid_results.xlsx에 저장되었습니다.")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_search()
    sys.exit(0 if success else 1)

