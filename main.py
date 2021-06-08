"""This module converts local video and srt to gif."""

import argparse
import subprocess
import sys
from typing import Union, Dict

import chardet
import pysrt
from fuzzysearch import find_near_matches
from pysrt import SubRipFile

FPS = "10"
WIDTH = "480"
OUTPUT_PATH = "output/"
TIME_DURATION = "15"  # duration of clip


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


def render_gif(args: argparse.Namespace, gif_length: str):
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
        stderr=subprocess.DEVNULL,
    )


def search_for_subtitle(subs: SubRipFile, search_string: str) -> list:
    """

    @param subs:
    @param search_string:
    @return:
    """
    search_hits = []
    print("Search results :")
    for data in subs.data:
        near_matches = find_near_matches(
            search_string.lower(), data.text_without_tags.lower(), max_l_dist=1
        )
        if near_matches:
            search_hits.append({"Fuzzy_Distance": near_matches[0].dist, "Solid": data})
            print(f"{data.text_without_tags}")

    if not search_hits:
        print(f"Could not find '{search_string}' in sub")
        sys.exit(1)

    return [min(search_hits, key=lambda x: x["Fuzzy_Distance"]).get("Solid")]


def splice_subs(
        matched_text: list, subs_pysrt: SubRipFile, start_time: str
) -> SubRipFile:
    """

    @param matched_text:
    @param subs_pysrt:
    @param start_time:
    @return:
    """
    matched_sub = matched_text[0]
    part = subs_pysrt.slice(
        starts_after={
            "hours": int(matched_sub.start.hours),
            "minutes": int(matched_sub.start.minutes),
            "seconds": int(matched_sub.start.seconds) - 10,
        },
        ends_before={
            "hours": int(matched_sub.start.hours),
            "minutes": int(matched_sub.start.minutes),
            "seconds": int(matched_sub.start.seconds) + 10,
        },
    )
    part.shift(seconds=-int(start_time))
    return part


def cut_video(subtitle_match_timestamp, cli_args, time_duration, output_path):
    """

    @param subtitle_match_timestamp:
    @param cli_args:
    @param time_duration:
    @param output_path:
    """
    print("Cutting video down in small little pieces.")
    subprocess.run(
        f"ffmpeg -ss {subtitle_match_timestamp} -i {cli_args.video_file} "
        f"-vf subtitles={output_path}cut_subs.srt "
        f" -t {time_duration} -y  {output_path}sub_short.mp4",
        shell=True,
        check=True,
        stderr=subprocess.DEVNULL,
    )
    print("GIFYING...")


if __name__ == "__main__":
    cmd_args = parse_args()
    print(f"Parsing arguments : {cmd_args.video_file}, {cmd_args.subtitle}")

    encoding = detect_encoding(cmd_args.subtitle)
    print(f'Detected encoding : {encoding.get("encoding")}')

    py_srt = pysrt.open(cmd_args.subtitle, encoding=encoding.get("encoding"))
    search_term = cmd_args.find
    matched_subs = search_for_subtitle(py_srt, search_term)
    print(f"Found some subtitles! {len(matched_subs)}")
    SUBTITLE_MATCH_TIMESTAMP = str(
        int(
            matched_subs[0].start.hours * 3600
            + matched_subs[0].start.minutes * 60
            + matched_subs[0].start.seconds
        )
        - 10
    )

    py_srt = splice_subs(matched_subs, py_srt, SUBTITLE_MATCH_TIMESTAMP)

    print(f"Cut subtitles, grabbed {len(py_srt)}")
    py_srt.save(f"{OUTPUT_PATH}cut_subs.srt", encoding="utf-8")

    cut_video(SUBTITLE_MATCH_TIMESTAMP, cmd_args, TIME_DURATION, OUTPUT_PATH)

    render_gif(cmd_args, TIME_DURATION)

    print(f"Output Location:{cmd_args.output_file}")
