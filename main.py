"""This module converts local video and srt to gif."""

import argparse
import subprocess
import sys
from typing import Union, Dict

import chardet
import pysrt
from pysrt import SubRipFile

FPS = "10"
WIDTH = "480"


def parse_args():
    """

    @return:
    """
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--video_file", "-v", type=str, required=True)
    arg_parser.add_argument("--subtitle", "-s", type=str, required=True)
    arg_parser.add_argument("--find", "-f", type=str, required=True)
    arg_parser.add_argument("--output_file", "-o", type=str, required=False)
    command_line_args = arg_parser.parse_args()
    if not command_line_args.output_file:
        command_line_args.output_file = "outfile.gif"
    return command_line_args


def detect_encoding(subtitle_path: str) -> Dict[str, Union[float, str]]:
    """

    @param subtitle_path:
    @return:
    """
    with open(subtitle_path, "rb") as file:
        msg = file.read()
        result = chardet.detect(msg)
        return result


def burn_subtitles(args: argparse.Namespace, gif_length: str):
    """

    @param args:
    @param gif_length:
    """
    subprocess.run(
        f"ffmpeg -i {OUTPUT_PATH}sub_short.mp4  -t {gif_length} -y -filter_complex '[0:v] "
        f"fps={FPS},scale=w={WIDTH}:h=-1,split [a][b];[a]"
        f"palettegen [p];[b][p] paletteuse=new=1' {OUTPUT_PATH}{args.output_file}",
        shell=True,
        check=True,
    )


def search_for_subtitle(subs: SubRipFile, search_string: str) -> list:
    """

    @param subs:
    @param search_string:
    @return:
    """
    search_hits = []
    for data in subs.data:
        if search_string.lower() in data.text_without_tags.lower():
            search_hits.append(data)
    if search_hits:
        return search_hits

    print(f"Could not find '{search_string}' in sub")
    sys.exit(1)


def cut_subs(matched_text, subs_pysrt, start_time):
    """

    @param matched_text:
    @param subs_pysrt:
    @param start_time:
    @return:
    """
    matched_sub = matched_text[0]
    part = subs_pysrt.slice(
        starts_after={
            "minutes": int(matched_sub.start.minutes),
            "seconds": int(matched_sub.start.seconds) - 10,
        },
        ends_before={
            "minutes": int(matched_sub.start.minutes),
            "seconds": int(matched_sub.start.seconds) + 10,
        },
    )
    part.shift(seconds=-int(start_time))
    return part


if __name__ == "__main__":
    cmd_args = parse_args()
    encoding = detect_encoding(cmd_args.subtitle)
    py_srt = pysrt.open(cmd_args.subtitle, encoding=encoding.get("encoding"))

    search_term = cmd_args.find
    matched_subs = search_for_subtitle(py_srt, search_term)
    SUBTITLE_START_TIME = str(
        int(
            matched_subs[0].start.hours * 3600
            + matched_subs[0].start.minutes * 60
            + matched_subs[0].start.seconds
        )
        - 10
    )

    py_srt = cut_subs(matched_subs, py_srt, SUBTITLE_START_TIME)

    py_srt.save("output/cut_subs.srt", encoding="utf-8")

    print(f"where from:{cmd_args.video_file}")
    print(f"where from:{cmd_args.subtitle}")

    TIME_DURATION = "15"  # duration of clip
    OUTPUT_PATH = "output/"

    subprocess.run(
        f"ffmpeg -ss {SUBTITLE_START_TIME} -i {cmd_args.video_file} "
        f"-vf subtitles=output/cut_subs.srt "
        f" -t {TIME_DURATION} -y  {OUTPUT_PATH}sub_short.mp4",
        shell=True,
        check=True,
    )

    burn_subtitles(cmd_args, TIME_DURATION)

    print(f"Output Location:{cmd_args.output_file}")
