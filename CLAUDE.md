# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 이 작업공간 개요

쿠팡 상품 데이터 수집 → JSON/CSV 저장 → openpyxl 스타일링 Excel 리포트 생성 파이프라인.
browser-harness(CDP)로 브라우저를 직접 제어해 데이터를 추출한다.

## 파이프라인 구조

```
coupang_search.py   — 쿠팡 검색창에 키워드 입력 후 폼 제출 (browser-harness 스크립트)
coupang_final.py    — 검색 결과 페이지에서 상품 데이터 JS 추출 → JSON 저장
make_xlsx.py        — JSON/하드코딩 데이터를 openpyxl로 스타일드 Excel 생성
```

## 실행 방법

browser-harness 스크립트는 반드시 heredoc 형식으로 실행:
```bash
browser-harness <<'PY'
exec(open('coupang_search.py').read())
PY
```

Excel 생성:
```bash
python make_xlsx.py
```

## 데이터 추출 패턴

- 상품 단위 선택자: `li[class*="productUnit"]`
- 상품명: `[class*="productNameV2"]` 또는 `[class*="productName"]`
- 가격 영역: `[class*="priceArea"]` 전체 텍스트 덤프 후 파싱
- 원가: `del` 태그
- 할인율: `[class*="fw-bg-"]` (쿠팡 빨간 배지)
- 링크: `a` 태그 href → `https://www.coupang.com` + href (쿼리스트링 제거)

쿠팡은 Tailwind 기반 동적 클래스명을 사용하므로 `class*=` 부분 매칭이 기본 전략.

## Excel 스타일 규칙 (make_xlsx.py)

- 헤더 배경: `#E8232A` (쿠팡 레드), 흰색 굵은 글자
- 제목 행: 병합 후 `#FFE5E5` 배경, 수집일 명시
- 짝수 행 대안 배경: `#FFF5F5`
- 가격 형식: `#,##0"원"` / 할인율: `0%` / 평점: `0.0"점"`
- 출력 경로: `C:/Users/MADUP/Desktop/claudecode/`

## 주의사항

- browser-harness 실행 전 쿠팡 탭이 열려 있어야 함 (`new_tab` 또는 기존 탭 활성화)
- 스크래핑 결과는 정확도 등급 표기 필수 (정확/추정/오차 ±N%)
- `coupang_extract.py`는 탐색용 프로토타입, `coupang_final.py`가 최종본
