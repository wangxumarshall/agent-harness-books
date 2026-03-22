#!/usr/bin/env python3
"""
Translation utility for CryptoSaga book
Uses HuggingFace transformers for Chinese to English translation
"""

import os
import re
from typing import List, Tuple

# Try to import transformers, install if needed
try:
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
except ImportError:
    import subprocess
    subprocess.check_call(['pip', 'install', 'transformers', 'torch', 'sentencepiece', '-q'])
    from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

class BookTranslator:
    def __init__(self, model_name="Helsinki-NLP/opus-mt-zh-en"):
        print(f"Loading translation model: {model_name}...")
        self.translator = pipeline("translation", model=model_name, device=-1)  # CPU
        print("Model loaded successfully!")

        # Custom terminology dictionary
        self.term_dict = {
            "比特币": "Bitcoin",
            "以太坊": "Ethereum",
            "区块链": "blockchain",
            "币圈": "the crypto space",
            "中本聪": "Satoshi Nakamoto",
            "矿工": "miners",
            "挖矿": "mining",
            "智能合约": "smart contracts",
            "去中心化": "decentralization",
            "交易所": "exchange",
            "钱包": "wallet",
            "私钥": "private key",
            "公钥": "public key",
            "白皮书": "white paper",
            "雷曼兄弟": "Lehman Brothers",
            "维多利亚港": "Victoria Harbour",
            "剑桥大学": "Cambridge University",
            "麻省理工学院": "MIT",
            "大卫·乔姆": "David Chaum",
            "eCash": "eCash",
            "维戴": "Wei Dai",
            "尼克·萨博": "Nick Szabo",
            "哈尔·芬尼": "Hal Finney",
            "公钥密码学": "public key cryptography",
            "工作量证明": "Proof of Work",
            "最长链原则": "the longest chain rule",
            "双重支付": "double-spending",
            "密码学邮件列表": "the cryptography mailing list",
            "数字现金": "DigiCash",
            "潘多拉魔盒": "Pandora's Box",
            "PayPal": "PayPal",
            "非同质化代币": "NFT",
            "去中心化金融": "DeFi",
            "首次代币发行": "ICO",
            "门头沟": "Mt. Gox",
            "币安": "Binance",
            "赵长鹏": "Changpeng Zhao (CZ)",
            "丝绸之路": "Silk Road",
            "罗斯·乌布利希": "Ross Ulbricht",
            "维塔利克·布特林": "Vitalik Buterin",
            "周世铭": "Zhou Shiming",
        }

    def preprocess_text(self, text: str) -> str:
        """Preprocess text before translation"""
        # Replace known terms with English placeholders
        for cn, en in self.term_dict.items():
            text = text.replace(cn, f"__TERM_{en}__")
        return text

    def postprocess_text(self, text: str) -> str:
        """Postprocess translated text"""
        # Restore English terms
        for cn, en in self.term_dict.items():
            text = text.replace(f"__TERM_{en}__", en)
        return text

    def translate_text(self, text: str, max_length: int = 500) -> str:
        """Translate a single text segment"""
        if not text.strip():
            return text

        # Check if text is too long
        if len(text) > max_length * 5:
            # Split and translate in chunks
            return self.translate_long_text(text, max_length)

        # Preprocess
        processed = self.preprocess_text(text)

        # Translate
        try:
            result = self.translator(processed, max_length=max_length)
            translated = result[0]['translation_text']
            # Postprocess
            return self.postprocess_text(translated)
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def translate_long_text(self, text: str, max_length: int = 500) -> str:
        """Translate long text by splitting into paragraphs"""
        paragraphs = text.split('\n')
        translated_paragraphs = []

        for para in paragraphs:
            if para.strip():
                translated = self.translate_text(para, max_length)
                translated_paragraphs.append(translated)
            else:
                translated_paragraphs.append('')

        return '\n'.join(translated_paragraphs)

    def translate_file(self, input_path: str, output_path: str):
        """Translate a markdown file"""
        print(f"Reading: {input_path}")

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Split into sections (by ## headers or double newlines)
        sections = re.split(r'(##+\s+.+)', content)

        translated_sections = []

        # First section (before any header) translate as is
        if sections[0].strip():
            print(f"Translating introduction ({len(sections[0])} chars)...")
            translated = self.translate_text(sections[0])
            translated_sections.append(translated)

        # Process header + content pairs
        for i in range(1, len(sections), 2):
            header = sections[i]
            translated_sections.append(header)  # Keep headers in Chinese (will translate later)

            if i + 1 < len(sections):
                content = sections[i + 1]
                print(f"Translating section ({len(content)} chars)...")
                translated = self.translate_text(content)
                translated_sections.append(translated)

        # Combine and write
        translated_content = ''.join(translated_sections)

        # Translate headers
        headers = re.findall(r'(##+\s+)([^\n]+)', translated_content)
        for header_mark, header_text in headers:
            # Translate just the header text
            if not any(c in header_text for c in ['：', '—', '—']):
                translated_header = self.translate_text(header_text)
                translated_content = translated_content.replace(
                    header_mark + header_text,
                    header_mark + translated_header,
                    1
                )

        print(f"Writing: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)

        print(f"Done! Output written to: {output_path}")


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python translate_utils.py <input_file> <output_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    translator = BookTranslator()
    translator.translate_file(input_file, output_file)


if __name__ == "__main__":
    main()
