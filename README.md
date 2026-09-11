# 🗓️ 사내 연차관리 (로그인 없는 공용 웹앱)

로그인 없이 링크만 있으면 누구나 접속해서 연차를 신청/조회하고, 승인 처리까지 할 수 있는
Streamlit 웹앱입니다.

## 기능
- 📅 연차 신청 (연차 1일 / 오전·오후 반차 0.5일, 평일 자동 계산)
- 👥 직원 등록/삭제 (이름, 연간 총 연차일수, 입사일)
- ✅ 승인/반려 처리 (별도 로그인 없이 공용 화면에서 처리)
- 📊 직원별 총연차/사용/잔여 현황 + 그래프
- 🗓 승인된 연차를 타임라인(간트차트) 형태로 시각화

## 로컬에서 실행해보기
```bash
pip install -r requirements.txt
streamlit run app.py
```
브라우저에서 `http://localhost:8501` 로 접속됩니다.

---

## GitHub + Streamlit Community Cloud로 무료 배포하기

### 1단계. GitHub 저장소 만들기
1. https://github.com 에서 새 저장소(Repository) 생성 (Public 또는 Private 모두 가능)
2. 이 폴더의 파일들(`app.py`, `requirements.txt`, `.gitignore`, `README.md`)을 업로드
   - GitHub 웹사이트에서 "Add file → Upload files" 로 드래그 앤 드롭해도 되고,
   - 터미널에 git이 설치되어 있다면 아래처럼 해도 됩니다.
   ```bash
   git init
   git add .
   git commit -m "사내 연차관리 앱 초기 버전"
   git branch -M main
   git remote add origin https://github.com/사용자명/저장소명.git
   git push -u origin main
   ```

### 2단계. Streamlit Community Cloud에 배포
1. https://share.streamlit.io 접속 후 GitHub 계정으로 로그인
2. "Create app" (또는 "New app") 클릭
3. 방금 만든 저장소, 브랜치(main), 메인 파일 경로(`app.py`)를 선택
4. "Deploy" 클릭 → 1~2분 후 `https://앱이름.streamlit.app` 형태의 고정 링크가 생성됩니다.
5. 이 링크를 사내 메신저/그룹웨어에 공유하면, 누구나 로그인 없이 바로 접속해 사용할 수 있습니다.

이후 GitHub 저장소에 새 커밋을 푸시하면 배포된 앱도 자동으로 갱신됩니다.

---

## ⚠️ 데이터 저장 관련 중요 참고사항

이 앱은 기본적으로 `leave.db` 라는 SQLite 파일에 데이터를 저장합니다. 평소 사용 중에는
문제없이 누적되지만, **Streamlit Community Cloud는 앱을 재시작(reboot)하거나
다시 배포(redeploy)할 때 서버의 파일 시스템을 초기화**할 수 있습니다. 즉, 앱 코드를
GitHub에 새로 푸시하거나 클라우드에서 앱을 재시작하면 그동안 쌓인 연차 데이터가
사라질 수 있습니다.

사내에서 장기적으로 안정적으로 쓰시려면 아래 중 하나를 권장드립니다.
- **사내 서버/PC에 직접 배포**: 회사 내부 서버나 상시 켜진 PC에서 `streamlit run app.py`로
  구동하면 SQLite 파일이 그대로 유지됩니다 (사내망 전용 링크로 사용 가능).
- **Google Sheets 연동으로 교체**: 데이터 저장소를 SQLite 대신 Google Sheets로 바꾸면,
  Streamlit Cloud가 재시작되어도 데이터가 안전하게 보존됩니다. 필요하시면 이 부분도
  이어서 구현해드릴 수 있습니다.
- **외부 DB 사용**: Supabase, PostgreSQL 등 외부 DB에 연결하는 방식도 가능합니다.

우선은 SQLite 버전으로 빠르게 써보시고, 실사용 단계에서 데이터 유실이 걱정되시면
말씀해주세요 — Google Sheets 연동 버전으로 업그레이드해드리겠습니다.
