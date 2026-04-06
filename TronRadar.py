"""
Tron Chain RAG System
---------------------
集成功能：
1. 区块数据查询（TronScan API）
2. 地址余额查询（TRX + USDT，via TronGrid RPC）
3. 地址交易爬取 + 频率统计（TronGrid v1 API）

API Key 通过环境变量读取：
  TRON_API_KEY = "your_key_here"
"""
import sys
from datetime import datetime, timedelta, timezone
from typing import Tuple, Optional
import requests
from base58 import b58decode_check
from binascii import hexlify

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# ========================
# 基本配置
# ========================

PROXIES = {
    "http": "http://127.0.0.1:7890",
    "https": "http://127.0.0.1:7890",
}

TIMEOUT = 10  # 超时时间（秒）
TRON_API_KEY = "your_key_here"
BASE_URL = "https://api.trongrid.io"
HEADERS = {"TRON-PRO-API-KEY": TRON_API_KEY}

# -----------------------------
# 1. RPC 相关函数（TRX/USDT）
# -----------------------------
def tron_addr_to_hex(addr: str) -> str:
    try:
        return hexlify(b58decode_check(addr)).decode("utf-8")
    except:
        raise ValueError("无效的波场地址：" + addr)
    
def tron_rpc_post(url: str, json_data: dict) -> Tuple[Optional[dict], str]:
    """
    统一发送波场RPC请求，处理各类异常
    返回: (响应数据, 错误信息)
    """
    try:
        resp = requests.post(
            url,
            json=json_data,
            proxies=PROXIES,
            timeout=TIMEOUT,
            headers={"Content-Type": "application/json"}
        )
        # 检查HTTP状态码
        if resp.status_code != 200:
            return None, f"HTTP错误: {resp.status_code} {resp.reason}"
        
        # 解析JSON
        try:
            data = resp.json()
        except Exception as e:
            return None, f"JSON解析失败: {str(e)}"
        
        # 检查波场RPC返回的错误
        if "Error" in data or "error" in data:
            err_msg = data.get("Error", data.get("error", "未知RPC错误"))
            return None, f"RPC返回错误: {err_msg}"
        
        return data, ""
    
    except requests.exceptions.ProxyError:
        return None, "代理连接失败: 请检查代理是否正常运行"
    except requests.exceptions.ConnectTimeout:
        return None, "连接超时: 网络不通或RPC节点不可用"
    except requests.exceptions.ReadTimeout:
        return None, "读取超时: 响应时间过长"
    except requests.exceptions.ConnectionError:
        return None, "网络连接错误: 请检查网络/代理"
    except Exception as e:
        return None, f"未知网络错误: {str(e)}"
    
def rpc_get_trx_balance(address: str) -> Tuple[float, str]:
    url = "https://api.trongrid.io/wallet/getaccount"
    address_hex = tron_addr_to_hex(address)
    json_data = {"address": address_hex, "visible": False}
    
    # 发送RPC请求
    result, err_msg = tron_rpc_post(url, json_data)
    if err_msg:
        print(f"❌ 获取 {address} TRX余额失败: {err_msg}")
        return 0.0, err_msg
    
    # 区分地址状态
    if not result:  # 空响应 = 未激活地址（无任何交易记录）
        print(f"ℹ️ 地址 {address} 状态: 未激活（链上无交易记录，TRX余额: 0.000000）")
        return 0.0, "未激活地址"
    
    # 已激活地址（有交易记录，即使余额为0也会返回balance字段）
    balance_sun = result.get("balance", 0)
    balance_trx = balance_sun / 1_000_000  # 1 TRX = 1,000,000 sun
    
    if balance_trx == 0:
        print(f"✅ 地址 {address} 状态: 已激活（TRX余额: 0.000000）")
    else:
        print(f"✅ 地址 {address} 状态: 已激活（TRX余额: {balance_trx:.6f}）")
    
    return balance_trx, "已激活地址"

def rpc_get_usdt_balance(address: str) -> Tuple[float, str]:
    url = "https://api.trongrid.io/wallet/triggerconstantcontract"
    usdt_contract = "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t"  # USDT TRC20官方合约
    address_hex = tron_addr_to_hex(address)
    contract_hex = tron_addr_to_hex(usdt_contract)
    
    json_data = {
        "owner_address": address_hex,
        "contract_address": contract_hex,
        "function_selector": "balanceOf(address)",
        "parameter": address_hex.zfill(64),
        "visible": False
    }
    
    # 发送RPC请求
    result, err_msg = tron_rpc_post(url, json_data)
    if err_msg:
        print(f"❌ 获取 {address} USDT余额失败: {err_msg}")
        return 0.0, err_msg
    
    # 解析合约返回值
    if "constant_result" not in result or not result["constant_result"]:
        print(f"ℹ️ 地址 {address} USDT余额: 0.000000（无USDT持有记录）")
        return 0.0, "无USDT"
    
    try:
        hex_balance = result["constant_result"][0]
        balance_wei = int(hex_balance, 16)
        balance_usdt = balance_wei / 1_000_000  # USDT精度6位
        print(f"✅ 地址 {address} USDT余额: {balance_usdt:.6f}")
        return balance_usdt, "正常"
    except Exception as e:
        print(f"❌ 解析USDT余额失败: {str(e)}")
        return 0.0, "解析失败"

def rpc_get_latest_block_number() -> Tuple[int, str]:
    url = "https://api.trongrid.io/wallet/getnowblock"
    result, err_msg = tron_rpc_post(url, {})
    
    if err_msg:
        print(f"❌ 获取最新区块失败: {err_msg}")
        return 0, err_msg
    
    block_num = result["block_header"]["raw_data"]["number"]
    print(f"✅ 最新区块高度: {block_num}")
    return block_num, "正常"

# -----------------------------
# 2.转账记录
# -----------------------------

def tron_paginate_crawl(url, address, limit=200, max_round=500):
    all_data = []
    fingerprint = None
    round_count = 0

    while round_count < max_round:
        params = {"limit": limit}
        if fingerprint:
            params["fingerprint"] = fingerprint

        try:
            resp = requests.get(url.format(address=address), headers=HEADERS, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"Request failed, status: {resp.status_code}")
                break

            res = resp.json()
            data = res.get("data", [])
            if not data:
                break

            all_data.extend(data)
            print(f"Fetched: {len(all_data)} records")

            next_link = res.get("meta", {}).get("links", {}).get("next")
            if not next_link:
                break

            fingerprint = next_link.split("fingerprint=")[-1]
            round_count += 1

        except Exception as e:
            print(f"Error: {str(e)}")
            break

    return all_data

from datetime import datetime, timedelta, timezone

def calculate_recent_freq(all_txs, now=None):
    if now is None:
        now = datetime.now(timezone.utc)

    time_3d_ago = now - timedelta(days=3)
    time_7d_ago = now - timedelta(days=7)

    count_3d = 0
    count_7d = 0

    for tx in all_txs:
        ts = tx.get('block_timestamp')
        if not ts:
            continue

        # 修复：使用 fromtimestamp 对应 UTC 时间
        tx_time = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)


        if tx_time >= time_3d_ago:
            count_3d += 1
        if tx_time >= time_7d_ago:
            count_7d += 1

    return {
        "last_3d_count": count_3d,
        "last_7d_count": count_7d,
        "freq_3d_per_day": round(count_3d / 3, 2),
        "freq_7d_per_day": round(count_7d / 7, 2),
    }

if __name__ == "__main__":
    TARGET_ADDRESS = input("请输入 Tron 地址: ").strip()
    print(f"已设置查询地址为: {TARGET_ADDRESS}")

    print("\n===== 波场地址行为分析 =====")
    print(f"地址: {TARGET_ADDRESS}\n")

    # ----------------------
    # 1. 查询余额（TRX + USDT）
    # ----------------------
    trx_balance, trx_status = rpc_get_trx_balance(TARGET_ADDRESS)
    usdt_balance, usdt_status = rpc_get_usdt_balance(TARGET_ADDRESS)

    print("\n--- 地址余额状态 ---")
    print(f"TRX余额: {trx_balance:.6f}，状态: {trx_status}")
    print(f"USDT余额: {usdt_balance:.6f}，状态: {usdt_status}")

    # ----------------------
    # 2. 爬取交易记录
    # ----------------------
    print("\n=== Crawling TRX Transactions ===")
    trx_txs = tron_paginate_crawl(f"{BASE_URL}/v1/accounts/{{address}}/transactions", TARGET_ADDRESS)

    print("\n=== Crawling TRC20 Transactions (USDT) ===")
    trc20_txs = tron_paginate_crawl(f"{BASE_URL}/v1/accounts/{{address}}/transactions/trc20", TARGET_ADDRESS)

    all_transactions = trx_txs + trc20_txs
    print(f"\n✅ 总交易数: {len(all_transactions)} (TRX: {len(trx_txs)}, TRC20: {len(trc20_txs)})")

    # ----------------------
    # 3. 最近转账频率分析
    # ----------------------
    if all_transactions:
        freq_stats = calculate_recent_freq(all_transactions)
        print("\n======================================")
        print("           最近转账频率统计")
        print("======================================")
        print(f"近 3 天总转账次数：{freq_stats['last_3d_count']} 次")
        print(f"近 7 天总转账次数：{freq_stats['last_7d_count']} 次")
        print(f"日均频率(3天/7天)：{freq_stats['freq_3d_per_day']:.2f} / {freq_stats['freq_7d_per_day']:.2f}")
        print("======================================\n")
    else:
        print("\n⚠️ 未获取到交易数据")



