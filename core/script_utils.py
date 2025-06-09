# core/script_utils.py

import base64
import hashlib
import random
import string
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad, unpad

__all__ = ['encrypt_password_cryptojs', 'decrypt_password_cryptojs', 'generate_random_string']

def _evp_bytes_to_key(passphrase: bytes, salt: bytes, key_len: int, iv_len: int):
    """
    Deriva key e iv compatíveis com OpenSSL/CryptoJS a partir de uma passphrase e salt.
    """
    derived_bytes = b''
    prev_digest = b''
    while len(derived_bytes) < key_len + iv_len:
        digest_input = prev_digest + passphrase + salt
        prev_digest = hashlib.md5(digest_input).digest()
        derived_bytes += prev_digest
        
    key = derived_bytes[:key_len]
    iv = derived_bytes[key_len:key_len + iv_len]
    return key, iv

def encrypt_password_cryptojs(plain_text_str: str, passphrase_str: str) -> str:
    """
    Criptografa dados da mesma forma que CryptoJS.AES.encrypt(data, passphrase).toString()
    """
    KEY_SIZE_BYTES = 32
    IV_SIZE_BYTES = 16
    SALT_SIZE_BYTES = 8
    
    passphrase_bytes = passphrase_str.encode('utf-8')
    data_bytes = plain_text_str.encode('utf-8')
    salt = get_random_bytes(SALT_SIZE_BYTES)
    
    key, iv = _evp_bytes_to_key(passphrase_bytes, salt, KEY_SIZE_BYTES, IV_SIZE_BYTES)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ciphertext = cipher.encrypt(pad(data_bytes, AES.block_size))

    final_output = b"Salted__" + salt + ciphertext
    return base64.b64encode(final_output).decode('utf-8')

def decrypt_password_cryptojs(base64_encrypted_str: str, passphrase_str: str) -> str:
    """
    Descriptografa uma string no formato OpenSSL/CryptoJS ("Salted__...").
    """
    KEY_SIZE_BYTES = 32
    IV_SIZE_BYTES = 16
    SALT_SIZE_BYTES = 8
    
    data = base64.b64decode(base64_encrypted_str)
    if not data.startswith(b"Salted__"):
        raise ValueError("Ciphertext não está no formato OpenSSL salted.")
        
    salt = data[8:8 + SALT_SIZE_BYTES]
    ciphertext = data[8 + SALT_SIZE_BYTES:]
    
    passphrase_bytes = passphrase_str.encode('utf-8')
    key, iv = _evp_bytes_to_key(passphrase_bytes, salt, KEY_SIZE_BYTES, IV_SIZE_BYTES)
    
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_padded = cipher.decrypt(ciphertext)
    decrypted = unpad(decrypted_padded, AES.block_size)
    
    return decrypted.decode('utf-8')

def generate_random_string(length: int) -> str:
    """Gera uma string aleatória com letras e dígitos."""
    if not isinstance(length, int) or length <= 0:
        raise ValueError("O comprimento deve ser um inteiro positivo.")
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))