# coding=utf-8

import sys

import dashscope
from dashscope.audio.tts import SpeechSynthesizer

dashscope.api_key = 'sk-29a8bccb6d6d41c7bdabab97826151fd'

result = SpeechSynthesizer.call(model='sambert-zhichu-v1',
                                text='然后，它等待并接收服务器回显的数据',
                                sample_rate=48000)
if result.get_audio_data() is not None:
    with open('output7.wav', 'wb') as f:
        f.write(result.get_audio_data())
    print('SUCCESS: get audio data: %dbytes in output.wav' %
          (sys.getsizeof(result.get_audio_data())))
else:
    print('ERROR: response is %s' % (result.get_response()))