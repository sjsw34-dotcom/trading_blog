# TASK-5: SEO 최적화 + 테스트 + 런칭

> 먼저 `docs/COMMON.md`를 읽을 것. TASK-1~4가 완성된 상태에서 진행.

---

## 목표

SEO 최적화, 전체 파이프라인 테스트, 런칭 준비.

---

## 1. SEO 최적화

### 1.1 메타 태그 (src/app/report/[date]/page.tsx)

```typescript
export async function generateMetadata({ params }): Promise<Metadata> {
  const report = await getReport(params.date);
  return {
    title: report?.title || `${params.date} 주식 시장 정리`,
    description: report?.meta_description || `${params.date} 한국 주식 상승 하락 종목, 테마 분석, 공시 정리`,
    openGraph: {
      title: report?.title,
      description: report?.meta_description,
      type: 'article',
      publishedTime: report?.published_at,
    },
  };
}
```

### 1.2 sitemap.xml 자동 생성 (src/app/sitemap.ts)

```typescript
import { getLatestReports } from '@/lib/db';

export default async function sitemap() {
  const reports = await getLatestReports(100);
  const reportUrls = reports.map(r => ({
    url: `https://사이트도메인/report/${r.report_date}`,
    lastModified: r.published_at,
    changeFrequency: 'daily',
    priority: 0.8,
  }));

  return [
    { url: 'https://사이트도메인', lastModified: new Date(), changeFrequency: 'daily', priority: 1 },
    ...reportUrls,
  ];
}
```

### 1.3 robots.txt (public/robots.txt)

```
User-agent: *
Allow: /
Sitemap: https://사이트도메인/sitemap.xml
```

### 1.4 Schema.org 구조화 데이터

각 리포트 페이지에 Article 스키마 추가:
```html
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "{리포트 제목}",
  "datePublished": "{발행일}",
  "description": "{메타 디스크립션}",
  "author": { "@type": "Organization", "name": "사이트명" }
}
</script>
```

### 1.5 SEO 타이틀 패턴

아침: `{날짜} 미국 증시 마감 정리 | 나스닥 S&P500 환율 | 사이트명`
마감: `{날짜} 주식 상승 종목 하락 종목 테마 분석 정리 | 사이트명`

---

## 2. 페이지 디자인 가이드

### 메인 페이지 (/)
- 상단: 사이트 로고 + 간단한 소개 문구
- 본문: 리포트 목록 카드 (날짜, 제목, 요약 2줄, morning/closing 태그)
- 하단: 텔레그램 채널 구독 유도 배너

### 리포트 페이지 (/report/[date])
- 상단: 제목 + 날짜 + morning/closing 태그
- 본문: DB의 content (HTML) 렌더링
- 뉴스 링크: 새 탭에서 열기 (target="_blank" rel="noopener")
- 하단: 면책 문구 + 텔레그램 채널 구독 유도
- 사이드바 또는 하단: 이전/다음 리포트 네비게이션

### 디자인 원칙
- Tailwind CSS 기반 깔끔한 디자인
- 다크 모드 지원 (주식 관련 사이트 특성)
- 모바일 반응형 필수
- 상승 = 빨간색, 하락 = 파란색 (한국 주식 컨벤션)
- 테이블은 모바일에서 가로 스크롤

---

## 3. 전체 파이프라인 테스트

### 3.1 단위 테스트
```bash
# 각 collector 독립 테스트
cd python
python -c "from collectors.kis_collector import *; print(get_kr_market_data())"
python -c "from collectors.dart_collector import *; print(get_today_disclosures())"
python -c "from collectors.news_crawler import *; print(get_stock_news('005930'))"
```

### 3.2 통합 테스트
```bash
# 마감 리포트 전체 파이프라인 수동 실행
cd python
python main_closing.py

# 아침 브리핑 전체 파이프라인 수동 실행
python main_morning.py
```

### 3.3 체크리스트
- [ ] KIS API 인증 성공
- [ ] 한국 시세 데이터 수집 성공
- [ ] 미국 시세 데이터 수집 성공
- [ ] 환율 데이터 수집 성공
- [ ] DART 공시 수집 성공
- [ ] 뉴스 크롤링 성공 (제목+URL)
- [ ] Claude API 블로그 글 생성 성공
- [ ] Claude API 테마 분류 성공
- [ ] Neon DB INSERT 성공
- [ ] 텔레그램 메시지 발송 성공
- [ ] Next.js에서 DB 데이터 읽어서 페이지 렌더링 성공
- [ ] 면책 문구 포함 확인
- [ ] 뉴스 링크 동작 확인
- [ ] 투자 조언/추천 없음 확인
- [ ] GitHub Actions 수동 실행 (workflow_dispatch) 성공

### 3.4 에러 케이스 테스트
- [ ] KIS API 실패 시 → pykrx 백업 전환 확인
- [ ] 뉴스 크롤링 실패 시 → 해당 섹션 스킵 확인
- [ ] Claude API 실패 시 → 텔레그램 에러 알림 발송 확인
- [ ] DB 연결 실패 시 → 텔레그램 에러 알림 발송 확인
- [ ] 주말/공휴일 → 파이프라인 스킵 확인

---

## 4. 런칭 체크리스트

### 환경 설정
- [ ] 도메인 구매 및 Vercel 연결
- [ ] Neon DB 생성 + stock_reports 테이블 생성
- [ ] GitHub Secrets 설정 (모든 환경변수)
- [ ] 텔레그램 봇 생성 + 채널 생성 + 봇 관리자 추가
- [ ] Vercel에 Next.js 프로젝트 배포 (`vercel --prod`)

### 콘텐츠 확인
- [ ] 아침 브리핑 1회 수동 실행 → 결과 확인
- [ ] 마감 리포트 1회 수동 실행 → 결과 확인
- [ ] 사이트에서 리포트 정상 표시 확인
- [ ] 텔레그램 채널에서 메시지 수신 확인

### 자동화 시작
- [ ] GitHub Actions cron 활성화 (main 브랜치 push)
- [ ] 3일간 모니터링 — 매일 2회 정상 발행 확인

---

## 5. 런칭 후 운영

| 시점 | 작업 |
|------|------|
| 1~3개월 | 블로그 콘텐츠 축적 + 텔레그램 무료 채널 구독자 확보 |
| 3개월~ | 텔레그램 프리미엄 채널 오픈 (월 9,900원) |
| 승인 시 | 애드릭스 CPA 광고 (스탁론/금융) 블로그 하단 배치 |
| 트래픽 성장 시 | 애드센스 검토 / 유튜브 Shorts 추가 / 추가 수익원 확장 |

---

## 완료 기준

- [ ] SEO: sitemap.xml, robots.txt, Schema.org, 메타 태그 동작
- [ ] 전체 파이프라인 수동 테스트 성공
- [ ] 에러 케이스 테스트 통과
- [ ] 런칭 체크리스트 전체 완료
- [ ] GitHub Actions cron 자동 실행 확인 (최소 3일)
