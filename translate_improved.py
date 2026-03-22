#!/usr/bin/env python3
"""
Improved Translation utility for CryptoSaga book
Uses HuggingFace transformers with better handling
"""

import os
import re
import json
from typing import Dict, List, Tuple

class ImprovedTranslator:
    def __init__(self, model_name="facebook/nllb-200-distilled-600M"):
        """Initialize translator with better model"""
        try:
            from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM
        except ImportError:
            import subprocess
            subprocess.check_call(['pip', 'install', 'transformers', 'torch', 'sentencepiece', '-q'])
            from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM

        print(f"Loading translation model: {model_name}...")
        # Use NLLB model for better Chinese->English translation
        self.translator = pipeline(
            "translation",
            model=model_name,
            device=-1,
            max_length=1024
        )
        print("Model loaded successfully!")

        # Comprehensive terminology dictionary
        self.term_dict = self._build_term_dict()

    def _build_term_dict(self) -> Dict[str, str]:
        """Build comprehensive terminology dictionary"""
        return {
            # Main terms
            "比特币": "Bitcoin",
            "以太坊": "Ethereum",
            "区块链": "blockchain",
            "币圈": "the crypto space",
            "加密货币": "cryptocurrency",
            "数字货币": "digital currency",

            # People
            "中本聪": "Satoshi Nakamoto",
            "大卫·乔姆": "David Chaum",
            "维戴": "Wei Dai",
            "尼克·萨博": "Nick Szabo",
            "哈尔·芬尼": "Hal Finney",
            "周世铭": "Zhou Shiming",
            "维塔利克·布特林": "Vitalik Buterin",
            "赵长鹏": "Changpeng Zhao (CZ)",
            "吴忌寒": "Jihan Wu",
            "烤猫": "Friedcat",
            "蒋信予": "Jiang Xinyu (Friedcat)",
            "詹克团": "Micree Zhan",
            "马克·卡尔佩莱斯": "Mark Karpeles",
            "萨姆·班克曼-弗里德": "Sam Bankman-Fried (SBF)",
            "罗斯·乌布利希": "Ross Ulbricht",

            # Organizations & Projects
            "eCash": "eCash",
            "DigiCash": "DigiCash",
            "b-money": "b-money",
            "Bit Gold": "Bit Gold",
            "以太坊": "Ethereum",
            "以太坊": "Ethereum",
            "门头沟": "Mt. Gox",
            "币安": "Binance",
            "Coinbase": "Coinbase",
            "FTX": "FTX",
            "比特大陆": "Bitmain",
            "烤猫": "Friedcat",
            "ASICMiner": "ASICMiner",
            "Antpool": "Antpool",
            "BTC.com": "BTC.com",
            "丝绸之路": "Silk Road",

            # Technical terms
            "矿工": "miners",
            "挖矿": "mining",
            "矿机": "mining machine",
            "算力": "hashrate",
            "工作量证明": "Proof of Work",
            "权益证明": "Proof of Stake",
            "智能合约": "smart contracts",
            "去中心化": "decentralization",
            "中心化": "centralization",
            "交易所": "exchange",
            "钱包": "wallet",
            "私钥": "private key",
            "公钥": "public key",
            "白皮书": "white paper",
            "创世区块": "Genesis Block",
            "区块": "block",
            "区块链": "blockchain",
            "分叉": "fork",
            "硬分叉": "hard fork",
            "软分叉": "soft fork",
            "哈希": "hash",
            "哈希率": "hash rate",
            "ASIC": "ASIC",
            "GPU": "GPU",
            "CPU": "CPU",
            "FPGA": "FPGA",
            "DAO": "DAO",
            "DeFi": "DeFi",
            "NFT": "NFT",
            "ICO": "ICO",
            "稳定币": "stablecoin",

            # Financial terms
            "首次代币发行": "Initial Coin Offering (ICO)",
            "非同质化代币": "Non-Fungible Token (NFT)",
            "去中心化金融": "Decentralized Finance (DeFi)",
            "量化宽松": "quantitative easing",
            "交易所": "exchange",

            # Historical Events
            "雷曼兄弟": "Lehman Brothers",
            "2008年金融危机": "the 2008 financial crisis",

            # Places
            "香港": "Hong Kong",
            "维多利亚港": "Victoria Harbour",
            "中银大厦": "Bank of China Tower",
            "汇丰总行": "HSBC Headquarters",
            "长江集团中心": "Cheung Kong Center",
            "剑桥大学": "Cambridge University",
            "麻省理工学院": "MIT",
            "华尔街": "Wall Street",
            "纽约": "New York",
            "硅谷": "Silicon Valley",
            "北京": "Beijing",
            "深圳": "Shenzhen",
            "萨尔瓦多": "El Salvador",

            # Other
            "潘多拉魔盒": "Pandora's Box",
            "PayPal": "PayPal",
            "密码学": "cryptography",
            "公钥密码学": "public key cryptography",
            "密码朋克": "Cypherpunk",
        }

    def translate_text(self, text: str) -> str:
        """Translate a single text segment"""
        if not text.strip():
            return text

        # Skip if already mostly English
        english_chars = sum(1 for c in text if ord(c) < 128)
        if english_chars / len(text) > 0.7:
            return text

        # Check if it's a short string (header or quote)
        if len(text.strip()) < 50:
            return text

        try:
            # Use NLLB model
            result = self.translator(text, src_lang="zho_Hans", tgt_lang="eng_Latn")
            translated = result[0]['translation_text']
            return translated
        except Exception as e:
            print(f"Translation error: {e}")
            return text

    def translate_file(self, input_path: str, output_path: str):
        """Translate a markdown file with better handling"""
        print(f"Reading: {input_path}")

        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Process line by line for better control
        lines = content.split('\n')
        translated_lines = []

        for i, line in enumerate(lines):
            # Skip markdown headers (they will be handled specially)
            if line.startswith('#'):
                translated_lines.append(line)
                continue

            # Skip empty lines
            if not line.strip():
                translated_lines.append('')
                continue

            # Skip lines that are mostly English
            english_chars = sum(1 for c in line if ord(c) < 128)
            if english_chars / len(line) > 0.7:
                translated_lines.append(line)
                continue

            # Translate the line
            if len(line) > 10:
                print(f"  Translating line {i+1}...")
                translated = self.translate_text(line)
                translated_lines.append(translated)
            else:
                translated_lines.append(line)

        # Combine and write
        translated_content = '\n'.join(translated_lines)

        # Handle markdown headers separately
        translated_content = self._translate_headers(translated_content)

        print(f"Writing: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(translated_content)

        print(f"Done! Output written to: {output_path}")

    def _translate_headers(self, content: str) -> str:
        """Translate markdown headers"""
        # Match headers like "## 第一部分：xxx" or "### 一、xxx"
        pattern = r'(#{1,6}\s+)([^\n]+)'

        def replace_header(match):
            prefix = match.group(1)
            title = match.group(2)

            # Check if title contains Chinese
            has_chinese = any('\u4e00' <= c <= '\u9fff' for c in title)
            if not has_chinese:
                return match.group(0)

            # Translate the title
            translated = self.translate_text(title)
            return prefix + translated

        return re.sub(pattern, replace_header, content)


def main():
    import sys

    if len(sys.argv) < 3:
        print("Usage: python translate_improved.py <input_file> <output_file>")
        print("Example: python translate_improved.py chapters_revised/前言_风云初现_校订版.md chapters_en/Preface.md")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    translator = ImprovedTranslator()
    translator.translate_file(input_file, output_file)


if __name__ == "__main__":
    main()
