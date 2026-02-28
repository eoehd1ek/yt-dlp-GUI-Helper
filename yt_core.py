import re


def clean_urls(urls: list[str]) -> list[str]:
    """
    URL 목록에서 '&' 뒤의 파라미터(예: 리스트 ID 등)를 일괄 제거합니다.
    """
    cleaned_urls = []
    for url in urls:
        url = url.strip()
        if not url:
            continue
        if "&" in url:
            url = url.split("&")[0]
        cleaned_urls.append(url)
    return cleaned_urls


def is_valid_time_format(time_str: str) -> bool:
    """
    시간 입력 형식이 올바른지 검증합니다.
    허용 포맷: HH:MM:SS, MM:SS, SS (예: 01:23:45, 12:34, 90)
    """
    if not time_str:
        return False

    pattern = r'^(?:(?:[0-9]{1,2}:)?[0-5]?[0-9]:)?[0-5]?[0-9]$|^[0-9]+$'
    return bool(re.match(pattern, time_str))


def is_valid_times(start: str | None, end: str | None) -> tuple[bool, str]:
    """
    시작 및 종료 시간 입력이 모두 유효한지 검증합니다.
    둘 다 비어있으면 True, 하나라도 존재하면 각각의 형식이 올바른지 확인합니다.
    """
    if not is_valid_time_format(start):
        return False, "시작 시간 형식이 올바르지 않습니다."
    if not is_valid_time_format(end):
        return False, "종료 시간 형식이 올바르지 않습니다."

    start_sec = time_str_to_seconds(start)
    end_sec = time_str_to_seconds(end)
    if end_sec <= start_sec:
        return False, "종료 시간은 시작 시간보다 커야 합니다."

    return True, ""


def time_str_to_seconds(time_str: str) -> int:
    """
    시/분/초 형식의 문자열을 초(Second) 단위 정수로 변환합니다.
    입력예시: "01:30" -> 90 반환
    잘못된 형식이거나 빈 문자열인 경우 -1을 반환합니다.
    """
    if not time_str:
        return -1

    parts = str(time_str).split(':')
    parts.reverse()  # 초, 분, 시 순서로 접근하기 위해 리버스

    try:
        seconds = 0
        for i, part in enumerate(parts):
            seconds += int(part) * (60 ** i)
        return seconds
    except ValueError:
        return -1


def get_premiere_codec_options() -> list[str]:
    """
    프리미어 프로 편집 호환성을 위한 비디오/오디오 코덱 옵션을 반환합니다.
    코덱 제한 없이 최고 화질/음질을 다운로드한 후, MP4(libx264, aac)로 강제 변환합니다.
    """
    return [
        "-f", "bestvideo+bestaudio",
        "--merge-output-format", "mp4",
        "--recode-video", "mp4",
        "--postprocessor-args", '"-c:v libx264 -c:a aac"'
    ]


def build_yt_dlp_command(yt_dlp_path: str, url: str, save_dir: str, download_option_type: int, time_start: str | None = None, time_end: str | None = None) -> list[str]:
    """
    각 다운로드 탭(기능)에 맞는 yt-dlp 명령어를 생성하여 반환합니다.
    """
    cmd = [yt_dlp_path, "-P", f'"{save_dir}"']

    if download_option_type == 0:
        pass

    elif download_option_type == 1:
        cmd.extend(get_premiere_codec_options())

    elif download_option_type == 2:
        cmd.extend(get_premiere_codec_options())

        start_sec = time_str_to_seconds(time_start) if time_start else 0
        end_sec = time_str_to_seconds(time_end) if time_end else ""

        section_arg = f"*{start_sec}-{end_sec}" if end_sec else f"*{start_sec}-"
        cmd.extend(["--download-sections",
                    f'"{section_arg}"',
                    "--force-keyframes-at-cuts"])

    elif download_option_type == 3:
        cmd.extend(["-x",
                    "--audio-format", "mp3",
                    "--audio-quality", "0",
                    "--embed-thumbnail", "--add-metadata"])

    cmd.append(f'"{url}"')
    return cmd
