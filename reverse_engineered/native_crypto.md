# Native Library — Telink AES-ATT Crypto

## libTelinkCrypto.so

Telink Semiconductor cryptography library, loaded by `com.telink.crypto.AES`.

### Exported Functions

**AES Rijndael primitives (AES/ECB/NoPadding 128-bit):**
```text
0x0e98  _rijndaelSetKey              — Set AES 128-bit key
0x0f20  aes_sw_SwapRowCol           — Row/column swap (AES-ATT byte ordering)
0x0f80  _rijndaelEncrypt            — Encrypt one 16-byte block
0x10a4  _rijndaelDecrypt            — Decrypt one 16-byte block
```

**AES-ATT byte manipulation:**
```text
0x1254  aes_att_swap                — Full 16-byte byte reversal (buf[i] ↔ buf[15-i])
```

**AES-ATT core encryption/decryption:**
```text
0x1278  aes_att_encryption_poly     — Encrypt with polynomial MIC
0x1320  aes_att_decryption_poly     — Decrypt with polynomial MIC
0x13d0  aes_att_encryption          — Basic AES-ATT encrypt
0x14ac  aes_att_decryption          — Basic AES-ATT decrypt
```

**Key derivation (authentication flow):**
```text
0x158c  aes_att_er                  — Encryption Root (key derivation component)
0x1644  aes_att_get_sk              — Get Session Key (from LTK + data)
0x16e4  aes_att_get_ltk             — Get Long Term Key (from PIN/secret)
0x1788  aes_att_enc_ltk            — Encrypt with LTK
```

**Protocol processing:**
```text
0x182c  aes_att_command             — Command mode AES-ATT
0x186c  aes_att_network_info        — Extract network info from crypto state
0x189c  aes_att_encryption_packet   — Packet-mode encryption (main write path)
0x1a60  aes_att_decryption_packet   — Packet-mode decryption (main read path)
```

**State management:**
```text
0x1c58  aes_att_set_crypto_poly     — Set crypto polynomial (4 bytes)
0x1c68  aes_att_get_crypto          — Get crypto state
```

**Device info helpers:**
```text
0x1c78  GetNetworkName              — Get network/device name
0x1d14  GetMacAddress               — Get MAC address
0x1dbc  DeviceInNetowrk             — Check if device is in network (typo in original)
```

**JNI entry points (called from `com.telink.crypto.AES`):**
```text
0x1e2c  Java_com_telink_crypto_AES_encryptCmd
0x1f94  Java_com_telink_crypto_AES_decryptCmd
```

### Authentication Flow

1. User enters 4-digit PIN
2. `aes_att_get_ltk` derives the Long Term Key from the PIN
3. `aes_att_get_sk` derives the Session Key from the LTK + challenge data
4. `aes_att_enc_ltk` may be used during challenge-response auth
5. All subsequent data payloads use `aes_att_encryption_packet` /
   `aes_att_decryption_packet` with the Session Key

### Key Derivation Details

**LTK derivation (aes_att_get_ltk, 0x16e4):**
```text
buffer = {param3[0..7], 0x0000000000000000}  # 8 bytes from param3, 8 bytes zero
temp = param1 XOR param2 XOR buffer           # XOR three 16-byte buffers
LTK = aes_att_decrypt(key, temp)              # AES-ECB decrypt with key
```

**SK derivation (aes_att_get_sk, 0x1644):**
```text
key = param1 XOR param2                        # XOR first two params as encryption key
data = {param3[0..7], param4[0..7]}           # 16-byte challenge/random
SK = aes_att_encrypt(key, data)               # AES-ECB encrypt the challenge
```

**ER function (aes_att_er, 0x158c):**
```text
temp = param1 XOR param2
aes_att_encrypt(temp, {param3[0..7], zeros})  # Encrypt 8-byte challenge with XOR'ed key
writes result back to param3 (first 8 bytes)
```

### Packet Encryption Flow

```
plaintext (16 bytes)
  → aes_att_swap (byte reversal)
  → _rijndaelEncrypt (AES/ECB/NoPadding with session key)
  → aes_att_swap (byte reversal)
  = ciphertext (16 bytes)
```

The poly variants add a polynomial-based MIC (Message Integrity Code) over the
packet, using the global `att_crypto_poly` (4 bytes at 0x13040), which is
set to 0 (poly MIC disabled by default).

## AES.java — Java Encryption Wrapper

`com.telink.crypto.AES` — Java class wrapping both Java AES and native Telink
crypto.

**Two-argument methods (Java AES):**
```java
public static byte[] encrypt(byte[] key, byte[] data) {
    if (!Security) return data;
    byte[] reversedKey = Utils.reverse(key);
    byte[] reversedData = Utils.reverse(data);
    SecretKeySpec keySpec = new SecretKeySpec(reversedKey, "AES");
    Cipher cipher = Cipher.getInstance("AES/ECB/NoPadding");
    cipher.init(Cipher.ENCRYPT_MODE, keySpec);
    return cipher.doFinal(reversedData);
}

public static byte[] decrypt(byte[] key, byte[] data) {
    if (!Security) return data;
    SecretKeySpec keySpec = new SecretKeySpec(key, "AES");
    Cipher cipher = Cipher.getInstance("AES/ECB/NoPadding");
    cipher.init(Cipher.DECRYPT_MODE, keySpec);
    return cipher.doFinal(data);
}
```

**Three-argument methods (native Telink):**
```java
// encrypt(key1, key2, data) → encryptCmd(data, key2, key1)
// decrypt(key1, key2, data) → decryptCmd(data, key2, key1)
public static byte[] encrypt(byte[] bArr, byte[] bArr2, byte[] bArr3) {
    return !Security ? bArr3 : encryptCmd(bArr3, bArr2, bArr);
}
public static byte[] decrypt(byte[] bArr, byte[] bArr2, byte[] bArr3) {
    return !Security ? bArr3 : decryptCmd(bArr3, bArr2, bArr);
}
```

`Security` is a static boolean flag. When `false`, all encryption is bypassed.

## Utils.reverse

```java
public static byte[] reverse(byte[] bArr) {
    int i = 0;
    int length = bArr.length;
    byte[] bArr2 = new byte[length];
    while (true) {
        length--;
        if (length < 0) return bArr2;
        bArr2[length] = bArr[i];
        i++;
    }
}
```

Simple byte array reversal (index 0 ↔ last, 1 ↔ second-to-last, ...).

## libBLEasyConfig.so

BLE EasyConfig library for WiFi provisioning over BLE. Uses JSON-based protocol
over BLE for WiFi configuration. Not related to the DYM mower control protocol.

## Other Libraries

`libGizWifiDaemon.so` / `libSDKLog.so` — Gizwits SDK daemon and logging support.
