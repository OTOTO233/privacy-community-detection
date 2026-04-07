"""
同态加密（Homomorphic Encryption）实现
用于在加密数据上进行计算
"""

import phe as paillier
import numpy as np
from typing import Dict, List, Tuple


class HomomorphicEncryption:
    """同态加密实现（基于Paillier密码系统）"""

    def __init__(self, key_size: int = 2048):
        """
        初始化同态加密系统

        Args:
            key_size: 密钥大小
        """
        self.public_key, self.private_key = paillier.generate_paillier_keypair(
            n_length=key_size
        )

    def encrypt(self, plaintext: float) -> paillier.EncryptedNumber:
        """
        加密单个数值

        Args:
            plaintext: 明文数值

        Returns:
            加密后的数值
        """
        return self.public_key.encrypt(plaintext)

    def encrypt_array(self, plaintext: np.ndarray) -> np.ndarray:
        """
        加密数组

        Args:
            plaintext: 明文数组

        Returns:
            加密后的数组
        """
        encrypted = np.empty(plaintext.shape, dtype=object)
        for idx in np.ndindex(plaintext.shape):
            encrypted[idx] = self.encrypt(float(plaintext[idx]))
        return encrypted

    def decrypt(self, ciphertext: paillier.EncryptedNumber) -> float:
        """
        解密单个数值

        Args:
            ciphertext: 密文

        Returns:
            明文数值
        """
        return float(self.private_key.decrypt(ciphertext))

    def decrypt_array(self, ciphertext: np.ndarray) -> np.ndarray:
        """
        解密数组

        Args:
            ciphertext: 密文数组

        Returns:
            明文数组
        """
        decrypted = np.empty(ciphertext.shape, dtype=float)
        for idx in np.ndindex(ciphertext.shape):
            decrypted[idx] = self.decrypt(ciphertext[idx])
        return decrypted

    def add_encrypted(
            self,
            a: paillier.EncryptedNumber,
            b: paillier.EncryptedNumber
    ) -> paillier.EncryptedNumber:
        """
        加密数值相加（同态性质）

        Args:
            a: 加密数值1
            b: 加密数值2

        Returns:
            加密后的和
        """
        return a + b

    def add_encrypted_array(
            self,
            a: np.ndarray,
            b: np.ndarray
    ) -> np.ndarray:
        """
        加密数组元素相加

        Args:
            a: 加密数组1
            b: 加密数组2

        Returns:
            加密后的和数组
        """
        result = np.empty(a.shape, dtype=object)
        for idx in np.ndindex(a.shape):
            result[idx] = a[idx] + b[idx]
        return result

    def multiply_encrypted_by_plaintext(
            self,
            encrypted: paillier.EncryptedNumber,
            plaintext: float
    ) -> paillier.EncryptedNumber:
        """
        加密数值与明文相乘（同态性质）

        Args:
            encrypted: 加密数值
            plaintext: 明文系数

        Returns:
            加密后的乘积
        """
        return encrypted * plaintext

    def multiply_encrypted_array_by_plaintext(
            self,
            encrypted: np.ndarray,
            plaintext: np.ndarray
    ) -> np.ndarray:
        """
        加密数组与明文数组对应元素相乘

        Args:
            encrypted: 加密数组
            plaintext: 明文数组

        Returns:
            加密后的乘积数组
        """
        result = np.empty(encrypted.shape, dtype=object)
        for idx in np.ndindex(encrypted.shape):
            result[idx] = encrypted[idx] * float(plaintext[idx])
        return result

    def compute_encrypted_dot_product(
            self,
            encrypted_a: np.ndarray,
            plaintext_b: np.ndarray
    ) -> paillier.EncryptedNumber:
        """
        计算加密向量与明文向量的点积（加密结果）

        Args:
            encrypted_a: 加密向量
            plaintext_b: 明文向量

        Returns:
            加密后的点积
        """
        result = self.encrypt(0)
        for i in range(len(encrypted_a)):
            result = result + (encrypted_a[i] * float(plaintext_b[i]))
        return result

    def compute_encrypted_sum(
            self,
            encrypted_array: np.ndarray
    ) -> paillier.EncryptedNumber:
        """
        计算加密数组的和（加密结果）

        Args:
            encrypted_array: 加密数组

        Returns:
            加密后的和
        """
        result = self.encrypt(0)
        for element in encrypted_array.flatten():
            result = result + element
        return result