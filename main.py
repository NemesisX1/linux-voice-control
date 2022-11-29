# the entry point of this excellent voice control program
# we are in public preview still.
# author: @omegaui
# github: https://github.com/omegaui/linux-voice-control
# license: GNU GPL v3
import wave
from array import array

import click
import pyaudio
import whisper
from termcolor import cprint

import command_manager
import config_manager
import voice_feedback


def trim(frames):
    """Trim the blank spots at the start and end"""

    def _trim(dataframe):
        snd_started = False
        r = array('h')

        for i in dataframe:
            if not snd_started and abs(i) > 500:
                snd_started = True
                r.append(i)

            elif snd_started:
                r.append(i)
        return r

    # Trim to the left
    frames = _trim(frames)

    # Trim to the right
    frames.reverse()
    frames = _trim(frames)
    frames.reverse()
    return frames


def log(text, color=None, attrs=None):
    if attrs is None:
        attrs = []
    if color is None:
        print(text)
    elif config_manager.config['logs']:
        cprint(text, color, attrs=attrs)


@click.command()
@click.option("--model", default="base", help="Model to use",
              type=click.Choice(["tiny", "base", "small", "medium", "large"]))
def main(model='base'):
    """
    the main function ... everything begins from here :param model: default model used is "base" from the available
    models in whisper ["tiny", "base", "small", "medium", "large"]
    """

    # initializing configuration management ...
    config_manager.init()

    # greeting ...
    voice_feedback.speak(config_manager.config['greeting'], wait=True)

    model = model + ".en"  # default langauge is set to english, you can change this anytime just refer to whisper docs
    audio_model = whisper.load_model(model)  # loading the audio model from whisper

    # getting configurations from lvc-config.json file ...
    CHUNK = config_manager.config['chunk-size']  # getting the chunk size configuration
    FORMAT = pyaudio.paInt16
    CHANNELS = config_manager.config['channels']  # getting the number of channels from configuration
    RATE = config_manager.config['rate']  # getting the frequency configuration
    RECORD_SECONDS = config_manager.config['record-duration']  # getting the record duration
    WAVE_OUTPUT_FILENAME = "lvc-last-mic-fetch.wav"  # default file which will be overwritten in every RECORD_SECONDS
    SPEECH_THRESHOLD = config_manager.config['speech-threshold']  # speech threshold default 4000 Hz

    # initializing PyAudio ...
    pyAudio = pyaudio.PyAudio()

    # Opening Microphone Stream with above created configuration ...
    stream = pyAudio.open(format=FORMAT,
                          channels=CHANNELS,
                          rate=RATE,
                          input=True,
                          frames_per_buffer=CHUNK)

    log("🐧 loading commands file ...", "blue")
    # initializing command management ...
    command_manager.init()

    log(f'🚀 voice control ready ... listening every {RECORD_SECONDS} seconds', "blue")

    name = config_manager.config['name']
    log(f'{name} waiting for order ...', "cyan")

    # And here it begins
    while True:
        frames = []
        r = array('h')
        log("listening ...", "blue", attrs=["bold"])
        for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
            data = stream.read(CHUNK)
            frames.append(data)  # stacking every audio frame into the list
            r.extend(array('h', data))
        r = trim(r)
        if len(r) == 0:  # clip is empty
            log('no voice')
            continue
        elif max(r) < SPEECH_THRESHOLD:  # no voice in clip
            log('no speech in clip')
            continue
        print("saving audio ...")

        # writing the wave file
        wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(pyAudio.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        voice_feedback.givetranscribingfeedback()
        log("transcribing audio data ...")
        # transcribing audio ...
        # fp16 isn't supported on every CPU using,
        # fp32 by default.
        result = audio_model.transcribe(WAVE_OUTPUT_FILENAME, fp16=False, language='english')

        log("analyzing results ...", "magenta", attrs=["bold"])
        # analyzing results ...
        analyze_text(result["text"].lower().strip())


def analyze_text(text):
    # validating transcribed text ...
    if text == '':
        return  # no speech data available returning without performing any operation

    log(f'You: {text}', "blue", attrs=["bold"])

    if text[len(text) - 1] in " .!?":
        text = text[0:len(text) - 1]  # removing any punctuation from the transcribed text

    # and here comes the command manager
    # it checks for suitable match of transcribed text against the available commands from the lvc-commands.json file
    command_manager.launch_if_any(text)


# spawning the process
main()
