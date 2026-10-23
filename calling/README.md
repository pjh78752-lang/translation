# CALLING 검은 착신 일본판 부분 한글화

## 0.0.3 스크린샷 대사 수정 및 Windows 설치 오류 수정

[0.0.3 ISO 제작 도구 — Windows 수정본 다운로드](https://github.com/pjh78752-lang/translation/raw/refs/heads/main/calling/Calling-Korean-v0.0.3-ISO-Kit-Windows-Fix.zip)

[0.0.3 리소스 패치 — Windows 수정본 다운로드](https://github.com/pjh78752-lang/translation/raw/refs/heads/main/calling/Calling-Korean-Partial-v0.0.3-Windows-Fix.zip)

2406번 대사 `携帯の持ち主……？ / 取りに来るって言ってたけど……`를 `휴대전화 주인……? / 찾으러 온다고 했는데……`로 추가 번역했습니다. 기존 0.0.2 번역은 유지하며 번역 슬롯은 1,028개입니다.

초기 0.0.3의 `ConvertFrom-Json` 오류는 UTF-8 JSON을 Windows 기본 인코딩으로 읽어서 발생했습니다. Windows 수정본은 두 PowerShell 스크립트에서 UTF-8 읽기를 명시하고 manifest를 ASCII 이스케이프 JSON으로 저장합니다. 번역과 IPS 파일은 초기 0.0.3과 동일합니다. 새 폴더에 전체 압축을 풀고 `make-iso.cmd`를 실행해 보관한 **원본 일본판 SCAJ18 ISO**에서 별도 ISO를 만드세요.

전체 2,516개 슬롯 중 다른 2,515개 보존, 제어 문자, 한글 매핑, IPS 합성, ZIP 무결성, UTF-8 및 한국어 기본 인코딩으로 manifest를 읽은 결과의 일치를 검사했습니다. Windows PowerShell 실제 실행, 원본 리소스 대상 설치, 전체 ISO 제작 및 게임 실행은 이번 제작 환경에서 검증하지 못했습니다.

**아직 완성판이 아닙니다.** 일본판 SCAJ18용 0.0.2입니다. 전체 2,516개 텍스트 슬롯 중 1,027개와 인물/장 제목 이미지 25개를 번역했습니다.

[0.0.2 ZIP 다운로드](https://github.com/pjh78752-lang/translation/raw/refs/heads/main/calling/Calling-Korean-Partial-v0.0.2.zip)

## 0.0.2에서 추가한 부분

- TV 조사 문구를 포함한 사물 조사 문구 278개(메시지 1273~1550)
- 시작 채팅, 도입부 독백, 초반 대사 추가
- 시점·이동·조사 등 도움말 전체와 관련 메뉴 안내
- 아이템 이름/설명과 휴대전화 안내
- 인물 이름 4개와 장 제목/접미사 등 이미지 총 25개

## 설치 및 이전 버전에서 업데이트

1. 새 ZIP을 **새 폴더**에 모두 풀어 주세요.
2. 이미 추출해 둔 **원본** `font.bin`, `win_mess_jp_jp.bin`, `SubTitle.bin`을 `install.cmd` 옆에 놓습니다. 없으면 실행 도중 원본 파일 선택 창이 뜹니다.
3. `install.cmd`를 실행하고 SUCCESS를 확인합니다.
4. Dolphin에서 Calling 우클릭 → **Riivolution 패치들로 시작...** → **Riivolution XML 열기...**
5. **이번 폴더에 생성된** `riivolution/Calling-Korean-v0.0.2.xml`을 선택하고 Enabled로 시작합니다. 이전 0.0.1 XML을 선택하면 새 번역이 반영되지 않습니다.
6. 기존 세이브스테이트 대신 게임을 새로 부팅해 주세요. 일반 저장 데이터는 보존합니다.

원본 ISO를 다시 만들거나 업로드할 필요는 없습니다. 패치 ZIP에는 ISO나 원본 추출 파일이 포함되지 않습니다.

## 확인 방법과 남은 작업

시작 채팅, 도움말의 시점 설명, TV를 조사할 때 `TV가 있지만 전원이 켜져 있지 않다.`가 한국어로 표시되는지 확인해 주세요. 같은 문구가 일본어면 새 XML의 선택 여부와 실행 방식을 확인해야 합니다.

후반 대사, 긴 문서/일기, 인물 소개, 일부 메뉴 이미지/제작진 표기는 아직 남아 있습니다.

모든 텍스트 슬롯/제어 문자 보존, 기존 글꼴 매핑 보존, 새 한글 666자, 이미지 픽셀 왕복, 압축 왕복, 적용 결과 해시 및 XML 경로를 검사했습니다. 파일 적용기는 Linux PowerShell 7.5.4에서 실행 검증했으며 Windows 파일 선택 창과 PowerShell 5.1은 별도 실행 검증하지 않았습니다.

**제작 환경에는 전체 ISO가 없어 Dolphin 게임 실행과 실제 화면을 검증하지 못했습니다.** 동봉 미리보기는 리소스를 직접 읽어 만든 것이며 게임 실행 화면이 아닙니다. 사용자 PC의 실제 표시와 배치를 확인해야 합니다.

ZIP 안의 `사용방법.txt`, `manifest.json`, `FONT-LICENSE.txt`에 세부 사항이 있습니다. 0.0.1 ZIP은 이전 버전 기록으로 유지합니다.

## 새 ISO에 적용하기

[ISO 제작 도구 ZIP 다운로드](https://github.com/pjh78752-lang/translation/raw/refs/heads/main/calling/Calling-Korean-v0.0.2-ISO-Kit.zip)

Windows용 [Wiimms ISO Tools](https://wit.wiimm.de/download.html)를 별도로 받아 전체 폴더를 압축 해제하세요. 도구 ZIP을 풀고 `make-iso.cmd`를 실행한 다음 `wit.exe`, 원본 일본판 ISO, 새 ISO 저장 경로를 선택합니다. 약 10GB 여유 공간과 NTFS/exFAT 저장 장치가 필요합니다. 원본은 보존하고 새 ISO를 만듭니다. 성공한 새 ISO는 Dolphin에서 일반 실행할 수 있습니다.

기존 부분 번역 0.0.2를 넣는 도구이며 번역 범위는 늘어나지 않습니다. 비실행용 합성 Wii 이미지에서 추출·재생성·파티션 체크섬·패치 파일 재추출 해시를 검증했습니다. 실제 Calling ISO와 Windows GUI 및 게임 실행은 검증하지 못했습니다. 자세한 내용은 ZIP의 `ISO 만들기 사용방법.txt`를 확인하세요.

## 사용자 실행 확인 기록 — 2026-10-23

사용자가 0.0.2 ISO 제작 도구로 만든 새 ISO에 대해 “일단 문제 없이 실행되”라고 보고했습니다. 사용자 PC에서 새 ISO가 실행된 결과이며, 제작 환경에서 직접 게임을 실행한 검증과는 구분합니다. 전체 플레이, 모든 번역 표시 및 후반 구간은 아직 확인되지 않았습니다.

다음 작업에서도 원본 일본판 SCAJ18 ISO를 보존하고, 패치 적용 후 별도 ISO를 만드는 방식을 사용합니다. 실행이 확인된 새 ISO는 Riivolution이나 제작 도구 폴더 없이 단독으로 실행합니다. 임시 `calling-iso-work-…` 폴더는 결과 확인 후 삭제할 수 있습니다.

후속 번역은 현재 부분 번역 0.0.2(텍스트 슬롯 1,027개, 이미지 25개)를 기준으로 이어갑니다. 남은 일본어 문구와 해당 장면을 확인하여 번역 범위를 확장하고 새 버전으로 배포합니다. 기존 파일에 추가 패치를 겹쳐 적용하기보다 보관한 원본에서 새 버전 ISO를 제작합니다.
