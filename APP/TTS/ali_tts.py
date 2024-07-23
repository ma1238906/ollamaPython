# coding=utf-8

import sys

import dashscope
from dashscope.audio.tts import SpeechSynthesizer

import os

dashscope.api_key = os.getenv('ALIYUN_API_KEY')


def tts(text: str):
    result = SpeechSynthesizer.call(model='sambert-zhiqi-v1',
                                    text=text,
                                    sample_rate=48000)
    audio = result.get_audio_data()
    if audio is not None:
        return audio
    else:
        return None
