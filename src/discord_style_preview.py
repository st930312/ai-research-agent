"""Send a one-time Discord wide-message style preview using static examples.

Never calls any AI API, search API or database; no scheduled triggers.
"""
import json
import os
import urllib.request
from urllib.parse import urlsplit

SECTIONS = [
    ("🤖 AI / LLM / Agent", [
        ("AI Agent 安全：權限管理將成為重要基礎設施",
         "當 AI Agent 不再只回答問題，而是能夠操作企業內部系統時，風險就從「回答是否正確」擴大到「它能存取哪些資源」。例如讀取內部文件、修改雲端設定或呼叫自動化工具，都需要明確的授權範圍。\n\n值得注意的是，未來的 Agent 平台不能只看模型能力，還需要權限分層、執行紀錄與人工核准機制。這對企業導入 AI、自動化維運及資訊安全都很關鍵。",
         "https://news.ycombinator.com/"),
        ("開發工具開始為 AI Agent 設計專用文件",
         "傳統技術文件主要為人類工程師撰寫，重視範例與背景敘述；AI Agent 則更需要一致的檔案結構、明確的操作限制與可驗證的開發規範。部分開源社群正在探索如何透過專用指引，降低 Agent 在大型程式碼庫中做出錯誤修改的機率。\n\n這類規範的價值不只是節省 Prompt，還能讓開發團隊把編碼準則、測試要求與安全規則維持在同一個位置。",
         "https://github.com/"),
    ]),
    ("🧰 GitHub 開源推薦", [
        ("HelloGitHub：分類介紹值得關注的開源工具",
         "HelloGitHub 會按程式語言與用途介紹開源專案，而不只列出 Star 排名。它的可讀性來自清楚的專案定位、功能摘要，以及讀者可以立即理解的應用場景。\n\n我們的新科技快訊會借鑑這種編輯方式：對每個專案交代它解決什麼問題、相較常見方案有何特色、適合哪些使用者，以及是否值得進一步試用。",
         "https://github.com/521xueweihan/HelloGitHub"),
        ("開源工具推薦應重視實際用途，不只看 Stars",
         "熱門專案不一定符合每位工程師的需求。對開源推薦來說，README 是否完整、是否有可重現的範例、授權方式、維護活躍度和最近的版本更新，通常比單一人氣數字更有參考價值。\n\n因此未來的快訊會盡量提供語言、Stars、主要功能與值得嘗試的理由，並區分「近期爆紅」與「長期成熟、近期更新」兩種情況。",
         "https://github.com/trending"),
    ]),
    ("🛠️ 軟體工程 / DevOps", [
        ("容器化與部署自動化：降低重複維運成本",
         "在開發流程中，環境差異與手動部署往往比撰寫功能本身更容易造成長期負擔。以 Docker、CI/CD 及基礎設施自動化為例，透過可重現的流程能減少「本機可以，正式環境不行」的情況。\n\n值得留意的是，流程自動化不是越複雜越好；小團隊更應重視可讀性、回復機制、憑證保護與故障時的可觀測性，避免為了導入新工具反而增加維護成本。",
         "https://docs.github.com/en/actions"),
        ("技術文件品質直接影響 AI 開發工具的表現",
         "RAG、Coding Agent 與文件搜尋工具都高度依賴來源品質。如果文件包含過期 API、前後矛盾的設定與缺乏上下文的範例，即使換成更強的模型，也可能得到錯誤建議。\n\n改善的起點往往是整理入門說明、認證流程、遷移指引與故障排除文件。對長期維護的服務而言，清楚且版本化的文件，同時改善人類工程師與 AI 工具的工作效率。",
         "https://news.ycombinator.com/"),
    ]),
    ("🚀 科技產業 / 新技術", [
        ("半導體與 AI 算力：關注供應鏈而不只看模型排名",
         "AI 能力的提升不只是模型架構的競賽，也取決於晶片、記憶體、資料中心網路、散熱與電力供應。當運算需求持續增加，硬體可取得性與部署成本就可能直接影響產品推出速度。\n\n因此科技產業的報導除了新產品規格，也值得追蹤實際量產、產能變化、能源需求及軟硬體生態系。這些訊號有時比單次基準測試更能反映技術是否準備好大規模落地。",
         "https://arstechnica.com/"),
        ("衛星通訊與地面行動網路逐漸整合",
         "衛星直連手機等技術讓行動通訊的覆蓋方式出現新選項，尤其在偏遠地區、海上或災害期間可能具有實用價值。不過，真正能提供的服務仍取決於終端設備、頻譜、法規與網路容量。\n\n閱讀這類消息時，應區分「技術展示」、「商業合作」與「已大規模商用」。未來快訊會特別標示發布階段，避免把概念驗證誤認成所有使用者都已能使用的功能。",
         "https://www.theverge.com/"),
    ]),
    ("📊 金融科技 / 半導體", [
        ("金融科技新創的估值與產品落地應分開觀察",
         "市場經常以新一輪融資、估值或收購金額描述金融科技公司的發展，但這些數字不必然代表產品更成熟。對使用者而言，更重要的可能是跨境支付成本、服務覆蓋範圍、合規進度與實際採用情況。\n\n評估相關新聞時，應將已完成的監管許可、正式上線的服務與管理團隊的預期目標區分清楚。這能避免把計畫中的業務擴張寫成已實現的營運成果。",
         "https://techcrunch.com/category/fintech/"),
    ]),
]

def make_messages():
    results = ["# 🛰️ 科技快訊 V2｜排版測試\n-# 以下為固定示範文字，**不是即時新聞**，此測試不呼叫 AI。\n\n本版改用一般 Discord 訊息：分類大標、文章次標、分段內文與來源連結。"]
    for category, items in SECTIONS:
        parts = [f"# {category}", "-# 🧪 排版示範｜非即時新聞"]
        for i, (title, body, link) in enumerate(items, 1):
            parts.append(f"## {i:02d}｜{title}\n\n{body}\n\n🔗 來源範例：{link}")
            if i != len(items):
                parts.append("━━━━━━━━━━━━━━━━")
        message = "\n\n".join(parts)
        if len(message) > 1950:
            raise ValueError(f"Too long for Discord: {category} ({len(message)} chars)")
        results.append(message)
    # Invisible non-empty guard keeps leading/trailing blank lines in Discord.\n    # A plain newline at the edge may be trimmed by the Discord client.\n    return ["\\u200b\\n\\n" + message + "\\n\\n\\u200b" for message in results]\n\ndef main():
    url = os.environ.get("DISCORD_WEBHOOK_URL", "")
    parts = urlsplit(url)
    if parts.scheme != "https" or parts.hostname not in {
        "discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"
    } or "/api/webhooks/" not in parts.path:
        raise RuntimeError("Missing or invalid DISCORD_WEBHOOK_URL")
    messages = make_messages()
    print(f"STYLE_PREVIEW_MESSAGES={len(messages)}", flush=True)
    for i, message in enumerate(messages, 1):
        payload = json.dumps({
            "content": message,
            "allowed_mentions": {"parse": []},
            "flags": 4,
        }, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            url, method="POST", data=payload,
            headers={"Content-Type": "application/json", "User-Agent": "AIResearchAgent-StylePreview/1.0"}
        )
        with urllib.request.urlopen(request, timeout=20) as response:
            if response.status not in (200, 204):
                raise RuntimeError(f"Discord returned HTTP {response.status}")
        print(f"STYLE_PREVIEW_SENT={i}/{len(messages)} chars={len(message)}", flush=True)

if __name__ == "__main__":
    main()
