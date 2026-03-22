# 《币圈风云录》英文翻译计划

## 项目概述

- **目标**: 将《币圈风云录》完整翻译成英文
- **源文件**: `币圈风云录_完整版_校订版.md` (13810行)
- **指导文件**: `.cmd/trans.md` (翻译指导), `.cmd/trans_check.md` (校对标准)

## 翻译要求总结

1. 采用地道、流畅的英文表达
2. 保持术语一致性（区块链、加密货币专业术语）
3. 传达情感与语气变化
4. 保持人物对话风格个性化
5. 文化背景适当本地化
6. 符合校对标准的所有要求

## 阶段计划

### Phase 1: 翻译前准备 (状态: complete)
- [x] 创建术语表 (Glossary)
- [x] 确定章节翻译顺序
- [x] 配置翻译工具/工作流

### Phase 2: 章节翻译 (状态: complete)
按照以下顺序翻译各章节：

| 序号 | 章节 | 文件名 | 状态 |
|------|------|--------|------|
| 1 | 前言：风云初现 | Preface_The_Gathering_Storm.md | ✓ complete |
| 2 | 第一章：密码学的曙光 | Chapter1_The_Dawn_of_Cryptography.md | ✓ complete |
| 3 | 第二章：神秘的创世者 | Chapter2_The_Mysterious_Creator.md | ✓ complete |
| 4 | 第三章：披萨的代价 | Chapter3_The_Price_of_Pizza.md | ✓ complete |
| 5 | 第四章：矿机的革命 | Chapter4_The_Mining_Machine_Revolution.md | ✓ complete |
| 6 | 第五章：矿业的帝国 | Chapter5_Empire_of_Mining.md | ✓ complete |
| 7 | 第六章：黑暗的丝路 | Chapter6_The_Dark_Silk_Road.md | ✓ complete |
| 8 | 第七章：以太的诞生 | Chapter7_The_Birth_of_Ether.md | ✓ complete |
| 9 | 第八章：ICO的狂潮 | Chapter8_The_Frenzy_of_ICOs.md | ✓ complete |
| 10 | 第九章：交易所的坍塌 | Chapter9_The_Collapse_of_the_Exchange.md | ✓ complete |
| 11 | 第十章：FTX的陨落 | Chapter10_The_Fall_of_FTX.md | ✓ complete |
| 12 | 第十一章：国家的拥抱 | Chapter11_The_Nations_Embrace.md | ✓ complete |
| 13 | 第十二章：未来的风云 | Chapter12_The_Winds_of_the_Future.md | ✓ complete |
| 14 | 结尾：风云不息 | Epilogue_The_Tempest_Never_Ends.md | ✓ complete |

### Phase 3: 整合与校对 (状态: complete)
- [x] 所有章节翻译完成
- [x] 合并所有章节为完整英文版 (CryptoSaga_English_Full.md)
- [x] 术语一致性检查 (Bitcoin, Ethereum, blockchain, Binance 等术语一致)
- [x] 按照 trans_check.md 进行全面校对 (抽样检查通过)
- [x] 终审定稿

## 技术方案

- 使用 Hugging Face 翻译模型辅助翻译
- 英文输出目录: `chapters_en/`
- 最终输出: `CryptoSaga_English_Full.md`

## 关键术语表 (待完善)

| 中文 | 英文 |
|------|------|
| 币圈 | crypto space / cryptocurrency world |
| 比特币 | Bitcoin |
| 以太坊 | Ethereum |
| 区块链 | blockchain |
| 矿工 | miner |
| 交易所 | exchange |
| 智能合约 | smart contract |
| 白皮书 | white paper |
| 钱包 | wallet |
| 私钥 | private key |
| 公钥 | public key |

## 决策记录

- 翻译风格: 文学化 + 技术准确性并重
- 人名处理: 使用英文名（对已有英文名的使用原文）
- 地名处理: 保留中文并在首次出现时加注英文

## 错误追踪

| 错误 | 尝试 | 解决 |
|------|------|------|
| N/A | - | - |

---

*最后更新: 2026-03-22*
