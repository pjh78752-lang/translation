# CALLING 검은 착신 일본판 한글 표시 시험판

**완성된 한글 패치가 아닙니다.** 일본판 SCAJ18의 2,516개 텍스트 슬롯 중 305개(메뉴·장소·일부 초반 대사)를 번역했습니다. 기존 글꼴 14개에 한글 음절 373개를 추가했습니다. 이미지에 들어 있는 글자와 나머지 텍스트는 그대로입니다.

[시험 패치 ZIP 다운로드](https://github.com/pjh78752-lang/translation/raw/refs/heads/main/calling/Calling-Korean-Display-Test-v0.0.1.zip)

## 적용

1. ZIP을 모두 풀고, 추출해 둔 원본 `font.bin`과 `win_mess_jp_jp.bin`을 `install.cmd` 옆에 놓습니다.
2. `install.cmd`를 실행합니다. 파일이 없으면 원본을 선택하는 창이 뜹니다.
3. SUCCESS가 나오면 Dolphin 게임 목록에서 Calling 우클릭 → **Riivolution 패치들로 시작...**을 선택합니다.
4. **Riivolution XML 열기...**에서 생성된 `riivolution/Calling-Korean-Test.xml`을 선택하고 Enabled로 시작합니다.

원본 ISO와 추출 파일은 덮어쓰지 않습니다. 기존 세이브스테이트 대신 게임을 새로 부팅하세요.

## 검증 범위

메시지 길이표, 특수 명령 문자 보존, 기존 글꼴 대응표 보존, 신규 한글 글꼴 데이터, 압축 왕복, IPS 결과 해시, XML 경로를 검사했습니다. 동봉 설치 프로그램은 Linux PowerShell 7.5.4에서 실행 검증했습니다. Windows 5.1과 파일 선택 창은 별도 실행 검증하지 않았습니다.

**전체 ISO가 제작 환경에 없어 Dolphin 게임 실행과 실제 표시를 검증하지 못했습니다.** 시험판의 목적은 실제 화면에서 한글 출력과 배치를 확인하는 것입니다. 동봉 미리보기는 글꼴 데이터를 직접 읽어 만든 것이며 게임 실행 화면이 아닙니다.

게임 ROM 및 원본 추출 파일은 포함하지 않습니다. ZIP 내부의 `사용방법.txt`, `manifest.json`, `FONT-LICENSE.txt`를 참조하세요.
