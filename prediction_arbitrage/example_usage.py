"""
Example Usage - 3-Platform Arbitrage Bot
간단한 사용 예시 모음
"""

import asyncio
import os
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# ===========================
# 예시 1: Kalshi 클라이언트만 사용
# ===========================

async def example_kalshi_only():
    """Kalshi 마켓 데이터만 가져오기"""
    from kalshi_client import KalshiRestClient

    print("\n" + "="*60)
    print("예시 1: Kalshi 마켓 조회")
    print("="*60)

    client = KalshiRestClient(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD')
    )

    await client.initialize()

    # 상위 5개 마켓 조회
    markets = await client.get_top_markets(limit=5)

    print(f"\n🔹 상위 {len(markets)}개 Kalshi 마켓:")
    for i, market in enumerate(markets, 1):
        print(f"\n{i}. {market.title}")
        print(f"   Ticker: {market.ticker}")
        print(f"   YES: {market.yes_bid} / {market.yes_ask}")
        print(f"   Volume: ${market.volume:,.0f}")

    await client.close()


# ===========================
# 예시 2: Opinion.trade 실시간 가격 모니터링
# ===========================

async def example_opinion_prices():
    """Opinion 실시간 가격 모니터링"""
    from opinion_client import OpinionRestClient

    print("\n" + "="*60)
    print("예시 2: Opinion.trade 가격 조회")
    print("="*60)

    client = OpinionRestClient(
        api_key=os.getenv('OPINION_API_KEY')  # 선택사항
    )

    await client.initialize()

    # 상위 마켓 조회
    markets = await client.get_top_markets(limit=3)

    print(f"\n🔹 상위 {len(markets)}개 Opinion 마켓:")
    for i, market in enumerate(markets, 1):
        print(f"\n{i}. {market.title}")
        print(f"   YES: ${market.yes_price:.4f}" if market.yes_price else "   YES: N/A")
        print(f"   NO: ${market.no_price:.4f}" if market.no_price else "   NO: N/A")
        print(f"   Volume: ${market.volume:,.0f}")

        # 첫 번째 마켓의 오더북 조회
        if i == 1 and market.token_yes_id:
            orderbook = await client.get_orderbook(market.token_yes_id)
            if orderbook:
                print(f"   Best Bid: ${orderbook.get_best_bid():.4f}" if orderbook.get_best_bid() else "   Best Bid: N/A")
                print(f"   Best Ask: ${orderbook.get_best_ask():.4f}" if orderbook.get_best_ask() else "   Best Ask: N/A")

    await client.close()


# ===========================
# 예시 3: 두 플랫폼 간 가격 비교
# ===========================

async def example_price_comparison():
    """Polymarket vs Kalshi 가격 비교"""
    from kalshi_client import KalshiRestClient
    from opinion_client import OpinionRestClient

    print("\n" + "="*60)
    print("예시 3: 플랫폼 간 가격 비교")
    print("="*60)

    # 두 클라이언트 동시 초기화
    kalshi = KalshiRestClient(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD')
    )

    opinion = OpinionRestClient(
        api_key=os.getenv('OPINION_API_KEY')
    )

    await kalshi.initialize()
    await opinion.initialize()

    # 각 플랫폼에서 마켓 가져오기
    kalshi_markets = await kalshi.get_top_markets(limit=5)
    opinion_markets = await opinion.get_top_markets(limit=5)

    print("\n🔹 Kalshi 마켓:")
    for market in kalshi_markets[:3]:
        yes_ask = market.yes_ask if market.yes_ask else 0
        no_ask = market.no_ask if market.no_ask else 0
        total = yes_ask + no_ask
        print(f"  • {market.title[:50]}...")
        print(f"    YES: {yes_ask:.2f}, NO: {no_ask:.2f}, 합계: {total:.2f}")

    print("\n🔹 Opinion 마켓:")
    for market in opinion_markets[:3]:
        yes_price = market.yes_price if market.yes_price else 0
        no_price = market.no_price if market.no_price else 0
        total = yes_price + no_price
        print(f"  • {market.title[:50]}...")
        print(f"    YES: {yes_price:.2f}, NO: {no_price:.2f}, 합계: {total:.2f}")

    print("\n💡 차익거래 팁:")
    print("  - 합계가 1.00 미만인 경우 차익거래 불가능")
    print("  - 두 플랫폼에서 같은 이벤트를 찾아 비교")
    print("  - 수수료와 슬리피지를 고려해야 함")

    await kalshi.close()
    await opinion.close()


# ===========================
# 예시 4: 실시간 WebSocket 모니터링
# ===========================

async def example_websocket_monitoring():
    """실시간 가격 변동 모니터링 (10초)"""
    from kalshi_client import KalshiWebSocketClient

    print("\n" + "="*60)
    print("예시 4: 실시간 WebSocket 모니터링 (10초)")
    print("="*60)

    update_count = 0

    async def on_orderbook(orderbook):
        nonlocal update_count
        update_count += 1
        print(f"📊 업데이트 {update_count}: {orderbook.ticker}")
        print(f"   YES: {orderbook.get_best_yes_bid():.2f} / {orderbook.get_best_yes_ask():.2f}")

    ws_client = KalshiWebSocketClient(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD'),
        on_orderbook=on_orderbook
    )

    await ws_client.initialize()
    await ws_client.connect()
    await ws_client.subscribe_top_markets(limit=2)

    # 10초간 리스닝
    listener = asyncio.create_task(ws_client.start())
    print("\n⏱️  10초간 실시간 업데이트 수신 중...\n")
    await asyncio.sleep(10)

    await ws_client.stop()
    listener.cancel()

    print(f"\n✅ 총 {update_count}개 업데이트 수신")


# ===========================
# 예시 5: 간단한 차익거래 기회 탐색
# ===========================

async def example_find_opportunities():
    """간단한 차익거래 기회 탐색"""
    from kalshi_client import KalshiRestClient
    from opinion_client import OpinionRestClient
    from decimal import Decimal

    print("\n" + "="*60)
    print("예시 5: 차익거래 기회 탐색")
    print("="*60)

    kalshi = KalshiRestClient(
        email=os.getenv('KALSHI_EMAIL'),
        password=os.getenv('KALSHI_PASSWORD')
    )

    opinion = OpinionRestClient(
        api_key=os.getenv('OPINION_API_KEY')
    )

    await kalshi.initialize()
    await opinion.initialize()

    kalshi_markets = await kalshi.get_top_markets(limit=10)
    opinion_markets = await opinion.get_top_markets(limit=10)

    print(f"\n🔍 {len(kalshi_markets)}개 Kalshi + {len(opinion_markets)}개 Opinion 마켓 분석 중...\n")

    opportunities = []

    for k_market in kalshi_markets:
        if not k_market.yes_ask or not k_market.no_ask:
            continue

        # 간단한 질문 매칭 (실제로는 NLP 사용)
        for o_market in opinion_markets:
            if not o_market.yes_price or not o_market.no_price:
                continue

            # 제목 유사도 체크 (매우 간단한 버전)
            k_words = set(k_market.title.lower().split())
            o_words = set(o_market.title.lower().split())

            if len(k_words & o_words) >= 2:  # 2개 이상 단어 일치
                # Kalshi YES + Opinion NO
                cost1 = k_market.yes_ask + o_market.no_price
                if cost1 < Decimal('1.0'):
                    profit1 = Decimal('1.0') - cost1
                    roi1 = (profit1 / cost1) * 100

                    opportunities.append({
                        'type': 'Kalshi YES + Opinion NO',
                        'k_market': k_market.title,
                        'o_market': o_market.title,
                        'cost': float(cost1),
                        'profit': float(profit1),
                        'roi': float(roi1)
                    })

                # Kalshi NO + Opinion YES
                cost2 = k_market.no_ask + o_market.yes_price
                if cost2 < Decimal('1.0'):
                    profit2 = Decimal('1.0') - cost2
                    roi2 = (profit2 / cost2) * 100

                    opportunities.append({
                        'type': 'Kalshi NO + Opinion YES',
                        'k_market': k_market.title,
                        'o_market': o_market.title,
                        'cost': float(cost2),
                        'profit': float(profit2),
                        'roi': float(roi2)
                    })

    if opportunities:
        # ROI 순으로 정렬
        opportunities.sort(key=lambda x: x['roi'], reverse=True)

        print(f"🎯 {len(opportunities)}개 차익거래 기회 발견!\n")

        for i, opp in enumerate(opportunities[:5], 1):
            print(f"{i}. {opp['type']}")
            print(f"   Kalshi: {opp['k_market'][:40]}...")
            print(f"   Opinion: {opp['o_market'][:40]}...")
            print(f"   비용: ${opp['cost']:.4f}")
            print(f"   수익: ${opp['profit']:.4f}")
            print(f"   ROI: {opp['roi']:.2f}%")
            print()
    else:
        print("❌ 현재 차익거래 기회가 없습니다.")
        print("💡 팁: 더 많은 마켓을 모니터링하거나 매칭 기준을 완화하세요.")

    await kalshi.close()
    await opinion.close()


# ===========================
# 메인 함수
# ===========================

async def main():
    """모든 예시 실행"""

    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║           🤖 3-PLATFORM ARBITRAGE BOT EXAMPLES 🤖           ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)

    # .env 파일 확인
    if not os.getenv('KALSHI_EMAIL'):
        print("⚠️  .env 파일에 KALSHI_EMAIL이 설정되지 않았습니다.")
        print("   .env.template을 참고하여 .env 파일을 생성하세요.\n")
        return

    try:
        # 원하는 예시 선택 (주석 해제하여 실행)

        # await example_kalshi_only()
        # await example_opinion_prices()
        await example_price_comparison()
        # await example_websocket_monitoring()
        # await example_find_opportunities()

        print("\n✅ 예시 실행 완료!")
        print("\n💡 다른 예시를 실행하려면 example_usage.py의 main() 함수를 수정하세요.")

    except Exception as e:
        print(f"\n❌ 에러 발생: {e}")
        print("   크레덴셜을 확인하고 다시 시도하세요.")


if __name__ == "__main__":
    asyncio.run(main())
