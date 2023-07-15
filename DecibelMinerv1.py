import pyaudio
import numpy as np
import datetime
import os
import pysftp
import uuid
from cryptography.fernet import Fernet
import json

def get_decibel(data):
    fourier = np.fft.fft(data)
    fourier = np.delete(fourier, len(fourier) // 2)
    power = np.abs(fourier) ** 2
    mean_power = np.average(power)
    return 10 * np.log10(mean_power)

def write_to_log(db, current_file):
    now = datetime.datetime.now()
    with open(current_file, 'a') as f:
        f.write(f"{now.strftime('%H:%M:%S')} - {db}\n")

def upload_to_sftp(current_file, config):
    now = datetime.datetime.now()
    local_filename = current_file
    remote_filename = f"/home/fryscrypto/indoor_decibel/FRYdecibels_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"
    cnopts = pysftp.CnOpts()
    cnopts.hostkeys = None 
    with pysftp.Connection(config['host'], username=config['username'], password=config['password'], cnopts=cnopts) as sftp:
        sftp.put(local_filename, remote_filename)
    os.remove(local_filename)  # removes local file after upload

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])

with open("key.key", "rb") as key_file:
    key = key_file.read()

with open("config.json.enc", "rb") as file:
    encrypted_config = file.read()

cipher = Fernet(key)
config = json.loads(cipher.decrypt(encrypted_config))

last_upload_hour = datetime.datetime.now().hour
# Initialize the current_file variable
now = datetime.datetime.now()
current_file = f"FRYdecibels_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"

while True:
    now = datetime.datetime.now()
    
    data = np.frombuffer(stream.read(1024), dtype=np.int16)
    decibel = get_decibel(data)
    write_to_log(decibel, current_file)
    print(f"Recorded {decibel} dB at {now.strftime('%H:%M:%S')}")  # printing for visibility
    
    # Upload the file one minute before the top of the hour
    if now.minute == 59 and now.second == 0:
        upload_to_sftp(current_file, config)

    # Update the filename at the top of the hour
    if now.minute == 0 and now.second == 0 and now.hour != last_upload_hour:
        current_file = f"FRYdecibels_{mac}_{now.strftime('%m%d%Y_%H%M%S')}.log"
        last_upload_hour = now.hour
