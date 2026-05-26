"""
Critical Flow AI — 학습 집중도 실시간 분석 서버
=================================================
실행: python main.py

[main.py 역할]
  오직 두 가지만 담당합니다.
  1. create_app() 을 호출해 FastAPI 앱 인스턴스를 생성
  2. uvicorn 으로 서버를 구동

  비즈니스 로직, 설정, 라우팅은 모두 src/ 하위 계층에 위임합니다.
"""

import uvicorn

from src.core.app import create_app

app = create_app()

if __name__ == "__main__":
    # reload=False — run_in_executor 스레드와 핫 리로드 충돌 방지
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
