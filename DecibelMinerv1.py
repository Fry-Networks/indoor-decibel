"""
Decibel Miner ver. 2.0.1
"""

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

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

def owen_decrypt(key, ciphertext):
    nonce, ct = ciphertext[:16], ciphertext[16:]
    cipher = Cipher(algorithms.ChaCha20(key, nonce), mode=None, backend=default_backend())
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(ct) + decryptor.finalize()
    return plaintext

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paInt16, channels=1, rate=44100, input=True, frames_per_buffer=1024)
mac = '-'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0,8*6,8)][::-1])

r = b'2\xad\xee\x9a\x18\x94\xf3[\xd2l\xb6\x94`\xfc\xe4\xee@\x84\xe9\xce4$Z\xbdu\xdc\x84\xac\xaaZ.z'
d = b'\x15H\xedt\xc71\x1a\x99\xab(\x07\xa6\x83\x0cW\x01\xa7\xc4\xb9\x18\xe2\x13Oh\x01<q\xad"\xe0H\x8f'
k = b"\xb2kK?\xabpe\x99P\xec\x80\x90V\x7fQ\xb6_}H]\x0f\x8dO\xcc<IG\xf6\x0b9j\x9cQBO/S8\xe4J15aa@g\xcc\xe40\xe8\xf7>\xdc\xa2Qk\n\x8f\xf5_\xc4Jmd\x1a<wWa\x04\xd2k\xcd\x9a\x88\xa2\xbb#'e\xd3PI\x14\xe0@\xbauC\xf4\xfdrp.;rqb\xa7\x82\x19\xc4u\xcf\x91\xa4QK\x8d\xf0\x9fy\xadQ8\xf58\x03\xbb\xa6\xad\x1c\xaf\x1c\xee\xf0\x11Y\xab_\x11\x14r}Sm\x80\x18\x1a\xa6\xc0\xad\x1e;\xc5\xe8\xcc\x17\xf4\xb8\xb8>wVqy\x06Gl\xfe`\x19\xf4o\x03OXJ\xde\xa0\x8bG%\xd4)=^\xc6\xf2\xe4\x1e'\x82\xd0\x18\x032\x990\x02tZ;\xa3\x1b\xbdR\x88_\x1f\xa6\x012u\x8bUd\xe2\x13\x92F\x95\xa0\xae\xd3\xaf`.\x14\xe8*aAs\xbe%\x13K\x94\xd1\x16m\xed\xfd&\xf6uoUC/\x04os"
b = b'\x8c<:Et=G|\x07JE\x84\xf1\x1a\xff\xbc\xe4\t\xaa\xb4\xdc\x1f\xa10\xdfA\xc4\x9d\xa5\x0f<\x8b\xbeV_\xe5\x8ei\r\xff\xc9B\xe5\n\xdd)Q\x9a:.yD7\x89\xed\x16^5\xaf\x98'


literal_t012 =  owen_decrypt(d, b) #
encrypted_config = owen_decrypt(r, k)
process_t054 = Fernet(literal_t012)
config = json.loads(process_t054.decrypt(encrypted_config))

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
