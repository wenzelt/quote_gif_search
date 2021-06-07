import argparse
import os
from dataclasses import dataclass
from datetime import time
from typing import Union, Dict

import chardet
import pysrt
from pysrt import SubRipFile
from pysubparser import parser
from pysubparser.cleaners import ascii, lower_case

fps = "10"
width = "480"

@dataclass
class Subtitle:
    start_at: time
    end_at: time
    text: list
    index: int
    text_string: str


def parse_subtitle_file(subtitle_path: str):
    subtitles = ascii.clean(
        lower_case.clean(parser.parse(subtitle_path, encoding="iso-8859-1"))
    )
    subs = []
    for i in subtitles:
        subs.append(
            Subtitle(
                start_at=i.start,
                end_at=i.end,
                text=i.lines,
                index=i.index,
                text_string=" ".join(i.lines),
            )
        )
    return subs


def parse_args():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--video_file", "-v", type=str, required=True)
    arg_parser.add_argument("--subtitle", "-s", type=str, required=True)
    arg_parser.add_argument("--find", "-f", type=str, required=True)
    arg_parser.add_argument("--output_file", "-o", type=str, required=False)
    cmd_args = arg_parser.parse_args()
    if not cmd_args.output_file:
        cmd_args.output_file = "outfile.mkv"
    return cmd_args


def detect_encoding(subtitle_path: str) -> Dict[str, Union[float, str]]:
    with open(subtitle_path, "rb") as f:
        msg = f.read()
        result = chardet.detect(msg)
        return result


def burn_subtitles(args: argparse.Namespace, time_duration: str):
    os.system(
        f"ffmpeg -i {output_path}sub_short.mp4  -t {time_duration} -y -filter_complex '[0:v] "
        f"fps={fps},scale=w={width}:h=-1,split [a][b];[a]"
        f"palettegen [p];[b][p] paletteuse=new=1' {output_path}{args.output_file}"
    )


def search_for_subtitle(subs: SubRipFile, search_term: str) -> list:
    matched_subs = []
    for data in subs.data:
        if search_term in data.text_without_tags:
            matched_subs.append(data)
    if matched_subs:
        return matched_subs
    else:
        print("Could not find in sub")
        exit(1)


def cut_subs(matched_subs, subs_pysrt, start_time):
    matched_sub = matched_subs[0]
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
    # subs = parse_subtitle_file(cmd_args.subtitle)

    py_srt = pysrt.open(cmd_args.subtitle, encoding="iso-8859-1")

    search_term = cmd_args.find
    matched_subs = search_for_subtitle(py_srt, search_term)
    subtitle_start_time = str(
        int(
            matched_subs[0].start.hours * 3600
            + matched_subs[0].start.minutes * 60
            + matched_subs[0].start.seconds
        )
        - 10
    )

    py_srt = cut_subs(matched_subs, py_srt, subtitle_start_time)

    py_srt.save("output/cut_subs.srt", encoding="utf-8")
    # subtitle_start_time = matched_subs[0].start
    print(f"where from:{cmd_args.video_file}")
    print(f"where from:{cmd_args.subtitle}")

    time_duration = "15"  # duration of clip
    output_path = "output/"
    encoding = detect_encoding(cmd_args.subtitle)

    os.system(
        f"ffmpeg -ss {subtitle_start_time} -i {cmd_args.video_file} -vf subtitles=output/cut_subs.srt  -t {time_duration} -y  {output_path}/sub_short.mp4"
    )

    burn_subtitles(cmd_args, time_duration)

    print(f"Output Location:{cmd_args.output_file}")